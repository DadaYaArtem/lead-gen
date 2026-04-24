"""
Webhook handler for HeyReach events.
Processes EVERY_MESSAGE_REPLY_RECEIVED events and queues conversations for analysis.
"""
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

_PROFILE_URL_FETCH_MAX_PAGES = 5
_PROFILE_URL_FETCH_PAGE_SIZE = 50


def _extract_message_timestamp(data: Dict[str, Any]) -> str:
    """Extract message timestamp from webhook payload.

    HeyReach may use different field names; fall back to current UTC time
    if none are found so we always have a value to compare.
    """
    message = data.get('message', {})
    for field in ('sentAt', 'timestamp', 'createdAt', 'sent_at', 'created_at'):
        value = message.get(field)
        if value:
            return str(value)
    return datetime.now(timezone.utc).isoformat()


def _stable_conversation_id(profile_url: str, account_id: int) -> str:
    """Generate a stable, deterministic conversation_id from profileUrl + account_id."""
    raw = f"{profile_url}:{account_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _resolve_conversation_id(data: Dict[str, Any]) -> tuple[Optional[str], str]:
    """
    Resolve a stable conversation_id from webhook payload.

    Resolution order:
      1. conversationId present in payload → use directly
      2. Existing lead in DB by (account_id, profileUrl) → reuse its conversation_id
      3. profileUrl present → generate sha256(profileUrl:account_id)[:16]
      4. None of the above → return (None, reason)

    Returns (conversation_id, resolution_path) where resolution_path is one of:
      'direct', 'existing_by_profile', 'hashed_profile_fallback', 'skipped'
    """
    from database import get_lead_by_account_and_profile_url

    conversation_id = data.get('conversationId')
    account_id = data.get('linkedInAccountId')
    profile_url = (data.get('correspondent') or {}).get('profileUrl', '').strip()

    if conversation_id:
        return conversation_id, 'direct'

    if not account_id:
        return None, 'skipped:no_account_id'

    if profile_url:
        existing = get_lead_by_account_and_profile_url(account_id, profile_url)
        if existing:
            return existing['conversation_id'], 'existing_by_profile'
        return _stable_conversation_id(profile_url, account_id), 'hashed_profile_fallback'

    return None, 'skipped:no_profile_url'


async def _fetch_conversation_by_profile_url(
    profile_url: str,
    account_id: int,
    headers: Dict[str, str],
) -> Optional[Dict[str, Any]]:
    """
    Scan GetConversationsV2 for a conversation whose correspondentProfile.profileUrl
    matches profile_url. Checks unseen (seen=False) pages first, then seen pages.
    Stops as soon as a match is found or max pages exhausted.
    """
    from server import _make_client

    url = "https://api.heyreach.io/api/public/inbox/GetConversationsV2"

    for seen_flag in (False, True):
        for page in range(_PROFILE_URL_FETCH_MAX_PAGES):
            payload = {
                "filters": {
                    "linkedInAccountIds": [account_id],
                    "seen": seen_flag,
                },
                "offset": page * _PROFILE_URL_FETCH_PAGE_SIZE,
                "limit": _PROFILE_URL_FETCH_PAGE_SIZE,
            }
            try:
                async with _make_client(timeout=30) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    if response.status_code != 200:
                        logger.error(
                            f"HeyReach API error during profileUrl scan "
                            f"(seen={seen_flag}, page={page}): {response.status_code}"
                        )
                        return None
                    batch = response.json().get('items', [])
            except Exception as e:
                logger.error(f"Exception during profileUrl scan (seen={seen_flag}, page={page}): {e}")
                return None

            if not batch:
                break  # no more pages for this seen_flag

            for item in batch:
                cp = item.get('correspondentProfile', {})
                if cp.get('profileUrl', '').strip() == profile_url:
                    logger.info(
                        f"Found conversation by profileUrl match "
                        f"(seen={seen_flag}, page={page}, profileUrl={profile_url})"
                    )
                    return item

    logger.warning(
        f"Conversation not found by profileUrl={profile_url} "
        f"after scanning {_PROFILE_URL_FETCH_MAX_PAGES} pages (seen=False then True)"
    )
    return None


async def fetch_conversation_from_heyreach(conversation_id: str, account_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch full conversation details from HeyReach API.

    Primary path: filter by conversationId (fast, single request).
    Fallback path: if not found and we have a profileUrl stored for this conversation_id,
    scan GetConversationsV2 by profileUrl match (used when conversation_id is a hashed synthetic key).
    """
    from server import HEYREACH_API_KEY, _make_client

    url = "https://api.heyreach.io/api/public/inbox/GetConversationsV2"
    headers = {
        "X-API-KEY": HEYREACH_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "filters": {
            "linkedInAccountIds": [account_id],
            "conversationId": conversation_id,
        },
        "offset": 0,
        "limit": 1,
    }

    try:
        async with _make_client(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error(f"HeyReach API error: {response.status_code} - {response.text[:200]}")
                return None

            data = response.json()
            items = data.get('items', [])

            if items:
                return items[0]

            logger.warning(
                f"Conversation {conversation_id} not found by ID; "
                "attempting profileUrl fallback fetch"
            )
    except Exception as e:
        logger.error(f"Error fetching conversation {conversation_id}: {e}")
        return None

    # Fallback: look up the profileUrl we saved for this synthetic conversation_id
    from database import get_profile_url_by_conversation_id

    profile_url = get_profile_url_by_conversation_id(conversation_id)
    if not profile_url:
        logger.warning(
            f"No profileUrl in DB for conversation {conversation_id}; cannot do fallback fetch"
        )
        return None

    return await _fetch_conversation_by_profile_url(profile_url, account_id, headers)


async def process_webhook_event(event_data: Dict[str, Any]) -> bool:
    """
    Process incoming webhook event from HeyReach.

    Expected event structure:
    {
        "event": "EVERY_MESSAGE_REPLY_RECEIVED",
        "data": {
            "conversationId": "abc123",   # may be absent
            "linkedInAccountId": 12345,
            "message": {...},
            "correspondent": {"profileUrl": "...", ...}
        }
    }

    When conversationId is absent, a stable synthetic ID is derived from profileUrl so
    the event is still queued and processed instead of being silently dropped.

    Re-queues analysis whenever the incoming message is newer than the last
    stored analysis, so fresh replies always trigger a fresh run.

    Returns True if successfully queued, False otherwise.
    """
    from database import add_to_queue, save_lead, get_lead_analysis_time, update_last_message_at

    event_type = event_data.get('event', '')
    data = event_data.get('data', {})

    if event_type != 'EVERY_MESSAGE_REPLY_RECEIVED':
        logger.info(f"Ignoring event type: {event_type}")
        return False

    account_id = data.get('linkedInAccountId')
    if not account_id:
        logger.error(f"Missing linkedInAccountId in webhook data: {data}")
        return False

    conversation_id, resolution_path = _resolve_conversation_id(data)

    if not conversation_id:
        logger.error(
            f"Cannot resolve conversation_id for webhook event "
            f"(reason={resolution_path}, account_id={account_id}): {data}"
        )
        return False

    logger.info(
        f"Resolved conversation_id={conversation_id} via {resolution_path} "
        f"(account_id={account_id})"
    )

    # Extract the timestamp of the incoming message
    message_ts = _extract_message_timestamp(data)

    # Save/update lead profile from webhook data early so last_message_at can be set
    correspondent = data.get('correspondent', {})
    if correspondent:
        profile = {
            'firstName': correspondent.get('firstName', ''),
            'lastName': correspondent.get('lastName', ''),
            'companyName': correspondent.get('companyName', ''),
            'position': correspondent.get('position', ''),
            'location': correspondent.get('location', ''),
            'profileUrl': correspondent.get('profileUrl', ''),
            'headline': correspondent.get('headline', ''),
        }
        save_lead(conversation_id, account_id, profile)

    # Record when this message arrived
    update_last_message_at(conversation_id, message_ts)

    # Decide whether to re-run analysis
    analyzed_at = get_lead_analysis_time(conversation_id)
    if analyzed_at and analyzed_at >= message_ts:
        logger.info(
            f"Lead {conversation_id} analysis is up to date "
            f"(analyzed_at={analyzed_at}, message_ts={message_ts}), skipping"
        )
        return False

    # Queue for (re-)analysis — add_to_queue skips if already pending/processing
    queue_id = add_to_queue(conversation_id, account_id)
    if queue_id is None:
        logger.info(f"Conversation {conversation_id} already in queue")
        return False

    logger.info(
        f"Queued conversation {conversation_id} for account {account_id} "
        f"(queue_id={queue_id}, resolution={resolution_path}, "
        f"message_ts={message_ts}, analyzed_at={analyzed_at})"
    )
    return True
