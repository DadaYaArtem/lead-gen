"""
One-shot backfill script: fetches ALL unread conversations from HeyReach
for every configured LinkedIn account, compares against what's already in
the DB, and queues the missing ones for analysis.

Run on PythonAnywhere:
    cd /path/to/backend && python backfill_missed_leads.py

Dry-run (shows what would be queued, touches nothing):
    python backfill_missed_leads.py --dry-run
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import httpx

load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

DRY_RUN = "--dry-run" in sys.argv

HEYREACH_API_KEY = os.environ.get("HEYREACH_API_KEY", "")
PROXY_URL = os.environ.get("PROXY_URL")
_accounts_raw = os.environ.get("LINKEDIN_ACCOUNTS", "[]")
LINKEDIN_ACCOUNTS = json.loads(_accounts_raw)

PAGE_SIZE = 50


def _make_client(timeout: int = 30) -> httpx.AsyncClient:
    if PROXY_URL:
        return httpx.AsyncClient(proxy=PROXY_URL, timeout=timeout)
    return httpx.AsyncClient(timeout=timeout)


async def fetch_all_conversations(account_id: int, seen: Optional[bool] = False) -> list:
    """Fetch all conversations for one account. seen=None fetches both seen and unseen."""
    url = "https://api.heyreach.io/api/public/inbox/GetConversationsV2"
    headers = {"X-API-KEY": HEYREACH_API_KEY, "Content-Type": "application/json"}
    all_items = []
    offset = 0

    while True:
        filters: dict = {"linkedInAccountIds": [account_id]}
        if seen is not None:
            filters["seen"] = seen

        payload = {"filters": filters, "offset": offset, "limit": PAGE_SIZE}

        async with _make_client() as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            logger.error(f"HeyReach API error for account {account_id}: {response.status_code} {response.text[:200]}")
            break

        data = response.json()
        items = data.get("items", [])
        all_items.extend(items)

        logger.info(f"  account={account_id} seen={seen} offset={offset} → got {len(items)} items (total so far: {len(all_items)})")

        if len(items) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    return all_items


def get_existing_profile_urls(account_id: int) -> set:
    """Return set of profileUrls already in the DB for this account."""
    from database import get_all_leads_for_account
    leads = get_all_leads_for_account(account_id)
    return {lead.get("profile_url", "") for lead in leads if lead.get("profile_url")}


def get_existing_conversation_ids(account_id: int) -> set:
    """Return set of conversation_ids already in the DB for this account."""
    from database import get_all_leads_for_account
    leads = get_all_leads_for_account(account_id)
    return {lead["conversation_id"] for lead in leads}


async def backfill_account(account_id: int) -> dict:
    logger.info(f"=== Account {account_id} ===")

    all_convs = await fetch_all_conversations(account_id, seen=False)

    logger.info(f"  Total unread from HeyReach: {len(all_convs)}")

    existing_profile_urls = get_existing_profile_urls(account_id)
    existing_conv_ids = get_existing_conversation_ids(account_id)

    queued = 0
    skipped_existing = 0
    skipped_no_profile = 0

    for conv in all_convs:
        cp = conv.get("correspondentProfile", {})
        profile_url = cp.get("profileUrl", "").strip()
        conv_id = conv.get("id") or conv.get("conversationId")

        if not profile_url:
            logger.debug(f"  Skipping conversation with no profileUrl (id={conv_id})")
            skipped_no_profile += 1
            continue

        # Already in DB by profileUrl or by conversation_id → skip
        if profile_url in existing_profile_urls or (conv_id and conv_id in existing_conv_ids):
            logger.debug(f"  Already exists: profileUrl={profile_url}")
            skipped_existing += 1
            continue

        # Resolve the conversation_id we'll use in our DB
        if conv_id:
            db_conv_id = str(conv_id)
            resolution = "heyreach_id"
        else:
            import hashlib
            db_conv_id = hashlib.sha256(f"{profile_url}:{account_id}".encode()).hexdigest()[:16]
            resolution = "hashed_profile"

        lead_name = f"{cp.get('firstName', '')} {cp.get('lastName', '')}".strip() or profile_url

        if DRY_RUN:
            logger.info(f"  [DRY-RUN] Would queue: {lead_name} (conv_id={db_conv_id}, resolution={resolution})")
            queued += 1
            continue

        from database import save_lead, add_to_queue

        profile = {
            "firstName": cp.get("firstName", ""),
            "lastName": cp.get("lastName", ""),
            "companyName": cp.get("companyName", ""),
            "position": cp.get("position", ""),
            "location": cp.get("location", ""),
            "profileUrl": profile_url,
            "headline": cp.get("headline", ""),
        }
        linkedin_messages = conv.get("messages", [])

        save_lead(db_conv_id, account_id, profile, linkedin_messages or None)
        queue_id = add_to_queue(db_conv_id, account_id)

        if queue_id:
            logger.info(f"  Queued: {lead_name} (conv_id={db_conv_id}, resolution={resolution}, queue_id={queue_id})")
            queued += 1
        else:
            logger.info(f"  Already in queue: {lead_name} (conv_id={db_conv_id})")
            skipped_existing += 1

    return {"queued": queued, "skipped_existing": skipped_existing, "skipped_no_profile": skipped_no_profile}


async def main():
    if not HEYREACH_API_KEY:
        logger.error("HEYREACH_API_KEY env var is not set")
        sys.exit(1)

    if not LINKEDIN_ACCOUNTS:
        logger.error("LINKEDIN_ACCOUNTS env var is empty or not set")
        sys.exit(1)

    if DRY_RUN:
        logger.info("=== DRY-RUN MODE — no changes will be made ===")

    # Initialize DB (creates tables / runs migrations if needed)
    from database import init_db
    init_db()

    total_queued = 0
    total_skipped = 0

    for account in LINKEDIN_ACCOUNTS:
        account_id = account.get("id") or account.get("linkedInAccountId") or account
        try:
            stats = await backfill_account(int(account_id))
            total_queued += stats["queued"]
            total_skipped += stats["skipped_existing"]
            logger.info(
                f"  → queued={stats['queued']} skipped={stats['skipped_existing']} "
                f"no_profile={stats['skipped_no_profile']}"
            )
        except Exception as e:
            logger.error(f"Error processing account {account_id}: {e}", exc_info=True)

    logger.info(f"=== Done. Total queued={total_queued}, skipped={total_skipped} ===")
    if DRY_RUN:
        logger.info("(dry-run, no actual changes made)")


if __name__ == "__main__":
    asyncio.run(main())
