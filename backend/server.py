from fastapi import FastAPI, APIRouter, HTTPException, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import sys
import logging
import uuid
import asyncio
import json
import hashlib
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from json_repair import repair_json
from cover_letter_generator import process_job, append_to_google_sheet, update_google_sheet_row, user_profiles

ROOT_DIR = Path(__file__).parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / '.env')

from classifier import classify_conversations
from prompts import create_analysis_prompt, create_catchup_messages_prompt, create_no_thanks_messages_prompt, create_chat_system_prompt, create_case_chat_system_prompt
from database import init_db, get_all_leads_for_account, get_lead_by_conversation_id, get_queue_stats
from webhook_handler import process_webhook_event
from rag import retrieve_cases, get_cases_metadata

HEYREACH_API_KEY = os.environ.get('HEYREACH_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
PROXY_URL = os.environ.get('PROXY_URL')

_accounts_raw = os.environ.get('LINKEDIN_ACCOUNTS', '[]')
LINKEDIN_ACCOUNTS = json.loads(_accounts_raw)


def _make_client(timeout: int = 30) -> httpx.AsyncClient:
    if PROXY_URL:
        return httpx.AsyncClient(
            transport=httpx.AsyncHTTPTransport(proxy=PROXY_URL),
            timeout=timeout,
        )
    return httpx.AsyncClient(timeout=timeout)

app = FastAPI()
api_router = APIRouter(prefix="/api")

jobs: Dict[str, Dict[str, Any]] = {}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Session persistence helpers (SQLite)
# ---------------------------------------------------------------------------

import sqlite3

SESSIONS_DB_PATH = ROOT_DIR / "sessions.db"

def _get_sessions_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(SESSIONS_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _init_sessions_db():
    with _get_sessions_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT 'New session',
                messages TEXT NOT NULL DEFAULT '[]',
                saved_state TEXT,
                last_job_description TEXT,
                timestamp INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 0,
                pass_count INTEGER NOT NULL DEFAULT 0,
                saved INTEGER NOT NULL DEFAULT 0,
                is_generating INTEGER NOT NULL DEFAULT 0,
                profile_rows TEXT NOT NULL DEFAULT '{}'
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)")
        # Migrate existing databases
        try:
            conn.execute("ALTER TABLE user_sessions ADD COLUMN profile_rows TEXT NOT NULL DEFAULT '{}'")
        except Exception:
            pass  # column already exists
        # Drop legacy sheet_row column if present (SQLite ignores unknown columns on SELECT *)
        conn.commit()

def _session_row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d['messages'] = json.loads(d['messages'] or '[]')
    d['saved_state'] = json.loads(d['saved_state']) if d['saved_state'] else None
    d['active'] = bool(d['active'])
    d['saved'] = bool(d['saved'])
    d['is_generating'] = bool(d['is_generating'])
    d['profile_rows'] = json.loads(d.get('profile_rows') or '{}')
    return d

def _db_get_user_sessions(user_id: str) -> List[dict]:
    with _get_sessions_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM user_sessions WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,)
        ).fetchall()
    return [_session_row_to_dict(r) for r in rows]

def _db_get_session(user_id: str, session_id: str) -> Optional[dict]:
    with _get_sessions_conn() as conn:
        row = conn.execute(
            "SELECT * FROM user_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id)
        ).fetchone()
    return _session_row_to_dict(row) if row else None

def _db_create_session(user_id: str, session_id: str, title: str, timestamp: int) -> dict:
    with _get_sessions_conn() as conn:
        conn.execute(
            """INSERT INTO user_sessions (id, user_id, title, messages, saved_state,
               last_job_description, timestamp, active, pass_count, saved, is_generating, profile_rows)
               VALUES (?, ?, ?, '[]', NULL, NULL, ?, 0, 0, 0, 0, '{}')""",
            (session_id, user_id, title, timestamp)
        )
        conn.commit()
    return _db_get_session(user_id, session_id)

def _db_update_session(session_id: str, **kwargs):
    if not kwargs:
        return
    set_clauses = []
    values = []
    for k, v in kwargs.items():
        set_clauses.append(f"{k} = ?")
        if k in ('messages', 'saved_state', 'profile_rows') and not isinstance(v, str):
            values.append(json.dumps(v))
        elif isinstance(v, bool):
            values.append(int(v))
        else:
            values.append(v)
    values.append(session_id)
    with _get_sessions_conn() as conn:
        conn.execute(
            f"UPDATE user_sessions SET {', '.join(set_clauses)} WHERE id = ?",
            values
        )
        conn.commit()

def _db_delete_session(user_id: str, session_id: str) -> bool:
    with _get_sessions_conn() as conn:
        cur = conn.execute(
            "DELETE FROM user_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0

def _db_count_user_sessions(user_id: str) -> int:
    with _get_sessions_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM user_sessions WHERE user_id = ?",
            (user_id,)
        ).fetchone()
    return row[0]

def _db_delete_oldest_session(user_id: str):
    with _get_sessions_conn() as conn:
        row = conn.execute(
            "SELECT id FROM user_sessions WHERE user_id = ? ORDER BY timestamp ASC LIMIT 1",
            (user_id,)
        ).fetchone()
        if row:
            conn.execute("DELETE FROM user_sessions WHERE id = ?", (row[0],))
            conn.commit()

def _trim_history(history: List[dict]) -> List[dict]:
    MAX_HISTORY_CHARS = 150000
    total = sum(len(msg.get("content", "")) for msg in history)
    if total <= MAX_HISTORY_CHARS:
        return history
    new_history = []
    current = 0
    for msg in reversed(history):
        current += len(msg.get("content", ""))
        if current > MAX_HISTORY_CHARS:
            break
        new_history.append(msg)
    return list(reversed(new_history))


# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    init_db()
    _init_sessions_db()
    logger.info("Database initialized")
    from queue_processor import start_queue_processor
    start_queue_processor()
    logger.info("Background queue processor started")


async def fetch_unread_conversations(account_id: int) -> list:
    url = "https://api.heyreach.io/api/public/inbox/GetConversationsV2"
    headers = {"X-API-KEY": HEYREACH_API_KEY, "Content-Type": "application/json"}
    limit = 50
    all_items = []
    offset = 0
    async with _make_client(timeout=30) as client:
        while True:
            payload = {
                "filters": {"linkedInAccountIds": [account_id], "seen": False},
                "offset": offset,
                "limit": limit,
            }
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                raise Exception(f"HeyReach API error: {response.status_code} - {response.text}")
            data = response.json()
            items = data.get('items', [])
            all_items.extend(items)
            if len(items) < limit:
                break
            offset += limit
    return all_items


def extract_openai_text(data: dict) -> str:
    output_array = data.get('output', [])
    for item in output_array:
        if item.get('type') == 'message':
            for content_item in item.get('content', []):
                if content_item.get('type') == 'output_text':
                    return content_item.get('text', '')
    return ''


def parse_json_from_text(text: str) -> dict:
    text = text.replace('```json', '').replace('```', '').strip()
    json_start = text.find('{')
    json_end = text.rfind('}') + 1
    if json_start != -1 and json_end > json_start:
        text = text[json_start:json_end]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = repair_json(text, return_objects=True)
        if isinstance(repaired, dict):
            return repaired
        raise ValueError(f"Could not parse JSON even after repair")


async def call_openai(prompt: str, use_web_search: bool = False, timeout_sec: int = 180) -> dict:
    url = "https://api.openai.com/v1/responses"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o",
        "tools": [{"type": "web_search"}] if use_web_search else [],
        "input": prompt
    }
    async with _make_client(timeout=timeout_sec) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text[:500]}")
        data = response.json()
        output_text = extract_openai_text(data)
        if not output_text:
            raise Exception("No output_text in OpenAI response")
        return parse_json_from_text(output_text)


async def call_openai_chat(system_prompt: str, messages: list, timeout_sec: int = 90) -> str:
    url = "https://api.openai.com/v1/responses"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-5.1",
        "tools": [{"type": "web_search"}],
        "input": [
            {"role": "developer", "content": system_prompt},
            *[{"role": m["role"], "content": m["content"]} for m in messages],
        ],
    }
    async with _make_client(timeout=timeout_sec) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text[:500]}")
        data = response.json()
        reply = extract_openai_text(data)
        if not reply:
            raise Exception("No output_text in OpenAI response")
        return reply


async def run_analysis_pipeline(job_id: str, account_id: int):
    from database import save_lead, save_classification, save_analysis, save_messages
    job = jobs[job_id]
    try:
        job['step'] = 'fetching'
        job['status_text'] = 'Fetching unread conversations from HeyReach...'
        logger.info(f"[{job_id}] Fetching conversations for account {account_id}")
        conversations = await fetch_unread_conversations(account_id)
        job['total_conversations'] = len(conversations)
        job['status_text'] = f'Found {len(conversations)} unread conversations. Classifying intent...'
        if not conversations:
            job['step'] = 'done'
            job['status_text'] = 'No unread conversations found'
            job['completed'] = True
            return
        job['step'] = 'classifying'
        logger.info(f"[{job_id}] Classifying {len(conversations)} conversations")
        classifications = await classify_conversations(conversations)
        classified_convs = [(conversations[c['index']], c) for c in classifications if c['index'] < len(conversations)]
        job['total_leads'] = len(classified_convs)
        job['leads_info'] = []
        if not classified_convs:
            job['step'] = 'done'
            job['status_text'] = 'No conversations with recent replies found'
            job['completed'] = True
            return
        intent_counts = {}
        for _, cls in classified_convs:
            intent_counts[cls['intent']] = intent_counts.get(cls['intent'], 0) + 1
        counts_str = ', '.join(f"{k}: {v}" for k, v in intent_counts.items())
        job['status_text'] = f'Classified {len(classified_convs)} conversations ({counts_str}). Starting analysis...'
        for conv, cls in classified_convs:
            profile = conv.get('correspondentProfile', {})
            job['leads_info'].append({
                'name': f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip(),
                'company': profile.get('companyName', ''),
                'position': profile.get('position', ''),
                'location': profile.get('location', ''),
                'profileUrl': profile.get('profileUrl', ''),
                'headline': profile.get('headline', ''),
                'intent': cls['intent'],
                'intent_confidence': cls['confidence'],
                'status': 'pending',
                'step': 'waiting',
                'conversation': conv
            })
        job['step'] = 'analyzing'
        for idx, (conv, cls) in enumerate(classified_convs):
            lead_info = job['leads_info'][idx]
            lead_name = lead_info['name']
            lead_company = lead_info['company']
            intent = lead_info['intent']
            try:
                lead_info['status'] = 'processing'
                lead_info['step'] = 'analyzing'
                job['processed'] = idx
                job['status_text'] = f'Analyzing {lead_name} [{intent}] ({idx + 1}/{len(classified_convs)})...'
                logger.info(f"[{job_id}] Analyzing lead {idx + 1}: {lead_name} (intent={intent})")
                profile = conv.get('correspondentProfile', {})
                conversation_id = conv.get('conversationId')
                if not conversation_id:
                    profile_url = profile.get('profileUrl', '')
                    if profile_url:
                        unique_str = f"{profile_url}:{account_id}"
                        conversation_id = hashlib.sha256(unique_str.encode()).hexdigest()[:16]
                    else:
                        conversation_id = str(uuid.uuid4())
                from database import get_lead_by_conversation_id
                existing_lead = get_lead_by_conversation_id(conversation_id)
                if existing_lead:
                    logger.info(f"[{job_id}] Updating existing lead: {lead_name} (conversation_id={conversation_id})")
                else:
                    logger.info(f"[{job_id}] Creating new lead: {lead_name} (conversation_id={conversation_id})")
                linkedin_messages = conv.get('messages', [])
                lead_id = save_lead(conversation_id, account_id, profile, linkedin_messages)
                save_classification(lead_id, intent, cls['confidence'], cls.get('reasoning', ''))
                analysis_prompt = create_analysis_prompt(conv)
                analysis = await call_openai(analysis_prompt, use_web_search=True, timeout_sec=180)
                lead_info['analysis'] = analysis
                save_analysis(lead_id, analysis)
                lead_info['step'] = 'generating_messages'
                job['status_text'] = f'Generating messages for {lead_name} ({idx + 1}/{len(classified_convs)})...'
                logger.info(f"[{job_id}] Generating messages for {lead_name}")
                if intent == 'soft_objection':
                    msg_prompt = create_no_thanks_messages_prompt(
                        analysis, lead_name, lead_company, lead_info.get('position', '')
                    )
                else:
                    msg_prompt = create_catchup_messages_prompt(
                        analysis, lead_name, lead_company, lead_info.get('position', ''), intent
                    )
                messages_data = await call_openai(msg_prompt, use_web_search=False, timeout_sec=120)
                lead_info['messages_data'] = messages_data
                save_messages(lead_id, messages_data)
                lead_info['status'] = 'done'
                lead_info['step'] = 'done'
                logger.info(f"[{job_id}] Lead {lead_name} done")
            except Exception as e:
                logger.error(f"[{job_id}] Lead {lead_name} failed: {e}")
                lead_info['status'] = 'failed'
                lead_info['step'] = 'failed'
                lead_info['error'] = str(e)
            if idx < len(classified_convs) - 1:
                job['status_text'] = f'Completed {lead_name}. Pausing before next lead...'
                await asyncio.sleep(5)
        job['processed'] = len(classified_convs)
        job['step'] = 'done'
        job['completed'] = True
        done_count = sum(1 for l in job['leads_info'] if l['status'] == 'done')
        failed_count = sum(1 for l in job['leads_info'] if l['status'] == 'failed')
        job['status_text'] = f'Analysis complete! {done_count} successful, {failed_count} failed out of {len(classified_convs)} leads.'
    except Exception as e:
        logger.error(f"[{job_id}] Pipeline error: {e}")
        job['step'] = 'error'
        job['error'] = str(e)
        job['status_text'] = f'Error: {str(e)}'
        job['completed'] = True


async def retry_leads_pipeline(job_id: str, lead_names: List[str]):
    from database import save_analysis, save_messages
    job = jobs[job_id]
    try:
        leads_to_retry = [li for li in job['leads_info'] if li['name'] in lead_names]
        for idx, lead_info in enumerate(leads_to_retry):
            lead_name = lead_info['name']
            lead_company = lead_info['company']
            conv = lead_info.get('conversation', {})
            try:
                lead_info['status'] = 'processing'
                lead_info['step'] = 'analyzing'
                job['status_text'] = f'Retrying {lead_name} ({idx + 1}/{len(leads_to_retry)})...'
                logger.info(f"[{job_id}] Retrying lead: {lead_name}")
                analysis_prompt = create_analysis_prompt(conv)
                analysis = await call_openai(analysis_prompt, use_web_search=True, timeout_sec=180)
                lead_info['analysis'] = analysis
                profile = conv.get('correspondentProfile', {})
                conversation_id = conv.get('conversationId', str(uuid.uuid4()))
                lead_id_result = get_lead_by_conversation_id(conversation_id)
                if lead_id_result:
                    save_analysis(lead_id_result['id'], analysis)
                lead_info['step'] = 'generating_messages'
                job['status_text'] = f'Generating messages for {lead_name} ({idx + 1}/{len(leads_to_retry)})...'
                intent = lead_info.get('intent', 'catchup_thanks')
                if intent == 'soft_objection':
                    msg_prompt = create_no_thanks_messages_prompt(
                        analysis, lead_name, lead_company, lead_info.get('position', '')
                    )
                else:
                    msg_prompt = create_catchup_messages_prompt(
                        analysis, lead_name, lead_company, lead_info.get('position', ''), intent
                    )
                messages_data = await call_openai(msg_prompt, use_web_search=False, timeout_sec=120)
                lead_info['messages_data'] = messages_data
                lead_info['error'] = None
                if lead_id_result:
                    save_messages(lead_id_result['id'], messages_data)
                lead_info['status'] = 'done'
                lead_info['step'] = 'done'
                logger.info(f"[{job_id}] Retry done: {lead_name}")
            except Exception as e:
                logger.error(f"[{job_id}] Retry failed for {lead_name}: {e}")
                lead_info['status'] = 'failed'
                lead_info['step'] = 'failed'
                lead_info['error'] = str(e)
            if idx < len(leads_to_retry) - 1:
                await asyncio.sleep(5)
        done_count = sum(1 for l in job['leads_info'] if l['status'] == 'done')
        failed_count = sum(1 for l in job['leads_info'] if l['status'] == 'failed')
        job['processed'] = len(job['leads_info'])
        job['step'] = 'done'
        job['completed'] = True
        job['status_text'] = f'Retry complete! {done_count} successful, {failed_count} failed.'
    except Exception as e:
        logger.error(f"[{job_id}] Retry pipeline error: {e}")
        job['step'] = 'error'
        job['error'] = str(e)
        job['status_text'] = f'Retry error: {str(e)}'
        job['completed'] = True


@api_router.get("/")
async def root():
    return {"message": "Interexy Lead Analyzer API"}


@api_router.get("/accounts")
async def get_accounts():
    return {"accounts": LINKEDIN_ACCOUNTS}


@api_router.post("/webhook/heyreach")
async def heyreach_webhook(request: Request):
    try:
        body = await request.json()
        logger.info(f"Received webhook: {json.dumps(body)[:500]}")
        success = await process_webhook_event(body)
        if success:
            return {"status": "queued", "message": "Conversation queued for analysis"}
        else:
            return {"status": "skipped", "message": "Event skipped or already processed"}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing error: {str(e)}")


@api_router.get("/leads/{account_id}")
async def get_leads(account_id: int):
    try:
        leads = get_all_leads_for_account(account_id)
        return {"leads": leads}
    except Exception as e:
        logger.error(f"Error fetching leads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/queue/stats")
async def get_stats():
    stats = get_queue_stats()
    return {"stats": stats}


@api_router.get("/leads")
async def get_all_leads():
    import sqlite3
    from database import get_db_connection
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT account_id FROM leads")
        account_ids = [row[0] for row in cursor.fetchall()]
    all_leads = []
    for acc_id in account_ids:
        leads = get_all_leads_for_account(acc_id)
        all_leads.extend(leads)
    return {"leads": all_leads, "total": len(all_leads)}


@api_router.delete("/leads/{conversation_id}")
async def delete_lead(conversation_id: str):
    try:
        from database import delete_lead as db_delete_lead
        logger.info(f"Attempting to delete lead: {conversation_id}")
        deleted = db_delete_lead(conversation_id)
        if deleted:
            logger.info(f"Successfully deleted lead: {conversation_id}")
            return {"status": "success", "message": f"Lead {conversation_id} deleted"}
        else:
            logger.warning(f"Lead not found: {conversation_id}")
            raise HTTPException(status_code=404, detail="Lead not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting lead {conversation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete lead: {str(e)}")


class CleanupRequest(BaseModel):
    account_id: int


@api_router.post("/cleanup/preview")
async def cleanup_preview(request: CleanupRequest):
    from database import get_all_leads_for_account
    account_id = request.account_id
    try:
        unseen = await fetch_unread_conversations(account_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"HeyReach API error: {str(e)}")
    sample_keys = list(unseen[0].keys()) if unseen else []
    sample_id_fields = {k: unseen[0].get(k) for k in ('id', 'conversationId', 'conversation_id') if unseen and unseen[0].get(k)} if unseen else {}
    unseen_ids = {conv.get('id') or conv.get('conversationId') for conv in unseen}
    unseen_ids.discard(None)
    db_leads = get_all_leads_for_account(account_id)
    would_delete = [l.get('conversation_id') for l in db_leads if l.get('conversation_id') and l.get('conversation_id') not in unseen_ids]
    return {
        "unseen_count": len(unseen),
        "unseen_ids_sample": list(unseen_ids)[:5],
        "heyreach_field_keys": sample_keys,
        "heyreach_id_fields": sample_id_fields,
        "db_leads_count": len(db_leads),
        "would_delete_count": len(would_delete),
        "would_delete": would_delete,
    }


@api_router.post("/cleanup")
async def cleanup_handled_leads(request: CleanupRequest):
    from database import get_all_leads_for_account, delete_lead as db_delete_lead
    account_id = request.account_id
    try:
        unseen = await fetch_unread_conversations(account_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"HeyReach API error: {str(e)}")
    unseen_profile_urls = {
        conv.get('correspondentProfile', {}).get('profileUrl')
        for conv in unseen
    }
    unseen_profile_urls.discard(None)
    db_leads = get_all_leads_for_account(account_id)
    if not db_leads:
        return {"deleted": 0, "message": "No leads in database"}
    if not unseen_profile_urls:
        logger.warning(f"Cleanup aborted: HeyReach returned 0 unseen for account {account_id}")
        return {"deleted": 0, "aborted": True, "reason": "HeyReach returned no unseen conversations — refusing to delete all leads"}
    deleted = []
    for lead in db_leads:
        cid = lead.get('conversation_id')
        profile_url = lead.get('profile_url')
        if cid and profile_url not in unseen_profile_urls:
            try:
                db_delete_lead(cid)
                deleted.append(cid)
                logger.info(f"Cleanup: deleted handled lead {cid} ({profile_url})")
            except Exception as e:
                logger.error(f"Cleanup: error deleting lead {cid}: {e}")
    logger.info(f"Cleanup for account {account_id}: deleted {len(deleted)} handled leads")
    return {"deleted": len(deleted), "conversation_ids": deleted}


class RunAnalysisRequest(BaseModel):
    account_id: int


@api_router.get("/knowledge-base")
async def get_knowledge_base():
    try:
        cases = get_cases_metadata()
        return {
            "cases": cases,
            "total": len(cases),
            "populated": sum(1 for c in cases if c["is_populated"]),
        }
    except Exception as e:
        logger.error(f"Error reading knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/run-analysis")
async def run_analysis(request: RunAnalysisRequest):
    if not HEYREACH_API_KEY or not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Missing API keys configuration")
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        'job_id': job_id,
        'step': 'starting',
        'status_text': 'Starting analysis...',
        'total_conversations': 0,
        'total_leads': 0,
        'processed': 0,
        'leads_info': [],
        'completed': False,
        'error': None,
        'account_id': request.account_id,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    asyncio.create_task(run_analysis_pipeline(job_id, request.account_id))
    return {"job_id": job_id, "message": "Analysis started"}


class RetryLeadsRequest(BaseModel):
    job_id: str
    lead_names: List[str]


@api_router.post("/retry-leads")
async def retry_leads(request: RetryLeadsRequest):
    job = jobs.get(request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.get('completed'):
        raise HTTPException(status_code=400, detail="Job is still running")
    for lead_info in job['leads_info']:
        if lead_info['name'] in request.lead_names:
            lead_info['status'] = 'pending'
            lead_info['step'] = 'waiting'
            lead_info['error'] = None
    job['completed'] = False
    job['step'] = 'retrying'
    job['status_text'] = f'Retrying {len(request.lead_names)} lead(s)...'
    job['error'] = None
    asyncio.create_task(retry_leads_pipeline(request.job_id, request.lead_names))
    return {"message": f"Retry started for {len(request.lead_names)} lead(s)"}


@api_router.get("/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    leads_summary = []
    for lead in job.get('leads_info', []):
        leads_summary.append({
            'name': lead.get('name', ''),
            'company': lead.get('company', ''),
            'position': lead.get('position', ''),
            'location': lead.get('location', ''),
            'intent': lead.get('intent', ''),
            'status': lead.get('status', 'pending'),
            'step': lead.get('step', 'waiting'),
            'error': lead.get('error')
        })
    return {
        'job_id': job_id,
        'step': job['step'],
        'status_text': job['status_text'],
        'total_conversations': job['total_conversations'],
        'total_leads': job['total_leads'],
        'processed': job['processed'],
        'completed': job['completed'],
        'error': job.get('error'),
        'leads': leads_summary
    }


@api_router.get("/results/{job_id}")
async def get_results(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    results = []
    for lead in job.get('leads_info', []):
        analysis = lead.get('analysis', {})
        messages_data = lead.get('messages_data', {})
        qualification = analysis.get('qualification', {})
        results.append({
            'name': lead.get('name', ''),
            'company': lead.get('company', ''),
            'position': lead.get('position', ''),
            'location': lead.get('location', ''),
            'profileUrl': lead.get('profileUrl', ''),
            'headline': lead.get('headline', ''),
            'intent': lead.get('intent', ''),
            'intent_confidence': lead.get('intent_confidence', ''),
            'status': lead.get('status', 'pending'),
            'error': lead.get('error'),
            'fit_score': qualification.get('fit_score', 0),
            'qualification_status': qualification.get('status', ''),
            'executive_summary': analysis.get('executive_summary', ''),
            'analysis': analysis,
            'messages': messages_data.get('messages', []),
            'recommended_top_3': messages_data.get('recommended_top_3', []),
            'strategy_notes': messages_data.get('notes', '')
        })
    return {
        'job_id': job_id,
        'completed': job['completed'],
        'total_leads': job['total_leads'],
        'results': results
    }


class ChatMessageItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    conversation_id: str
    lead_name: str
    messages: List[ChatMessageItem]
    job_id: Optional[str] = None


@api_router.post("/chat")
async def chat_with_lead(request: ChatRequest):
    from database import get_lead_by_conversation_id as db_get_lead
    lead_context = None
    db_lead = db_get_lead(request.conversation_id)
    if db_lead:
        analysis = db_lead.get('analysis', {})
        generated = db_lead.get('messages', {})
        lead_context = {
            'name': db_lead.get('full_name') or request.lead_name,
            'company': db_lead.get('company_name', ''),
            'position': db_lead.get('position', ''),
            'location': db_lead.get('location', ''),
            'intent': db_lead.get('intent', ''),
            'intent_confidence': db_lead.get('confidence', ''),
            'executive_summary': analysis.get('executive_summary', ''),
            'analysis': analysis,
            'linkedin_messages': db_lead.get('linkedin_messages', []),
            'generated_messages': generated.get('messages', []),
            'recommended_top_3': generated.get('recommended_top_3', []),
            'strategy_notes': generated.get('notes', ''),
        }
    if lead_context is None and request.job_id:
        job = jobs.get(request.job_id)
        if job:
            mem_lead = next(
                (li for li in job.get('leads_info', []) if li.get('name') == request.lead_name),
                None
            )
            if mem_lead:
                analysis = mem_lead.get('analysis', {})
                lead_context = {
                    'name': mem_lead.get('name', request.lead_name),
                    'company': mem_lead.get('company', ''),
                    'position': mem_lead.get('position', ''),
                    'location': mem_lead.get('location', ''),
                    'intent': mem_lead.get('intent', ''),
                    'intent_confidence': mem_lead.get('intent_confidence', ''),
                    'executive_summary': analysis.get('executive_summary', ''),
                    'analysis': analysis,
                    'linkedin_messages': [],
                    'generated_messages': [],
                    'recommended_top_3': [],
                    'strategy_notes': '',
                }
    if lead_context is None:
        raise HTTPException(
            status_code=404,
            detail=f"Lead '{request.lead_name}' not found in DB or active job"
        )
    retrieved_cases = []
    if OPENAI_API_KEY and request.messages:
        last_user_msg = next(
            (m.content for m in reversed(request.messages) if m.role == "user"), ""
        )
        if last_user_msg:
            try:
                retrieved_cases = await retrieve_cases(last_user_msg, OPENAI_API_KEY)
                if retrieved_cases:
                    logger.info(
                        f"RAG: retrieved {len(retrieved_cases)} case(s) for query "
                        f"'{last_user_msg[:60]}...' (top score: {retrieved_cases[0]['score']})"
                    )
            except Exception as e:
                logger.warning(f"RAG retrieval failed (non-fatal): {e}")
    system_prompt = create_chat_system_prompt(lead_context, retrieved_cases=retrieved_cases or None)
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    try:
        reply = await call_openai_chat(system_prompt, messages, timeout_sec=90)
    except Exception as e:
        logger.error(f"Chat error for lead {request.lead_name}: {e}")
        raise HTTPException(status_code=500, detail=f"OpenAI request failed: {str(e)}")
    return {"reply": reply, "retrieved_cases": [{"id": c["id"], "title": c["title"], "score": c["score"]} for c in retrieved_cases]}


class CaseChatRequest(BaseModel):
    messages: List[ChatMessageItem]


@api_router.post("/case-chat")
async def chat_with_cases(request: CaseChatRequest):
    retrieved_cases = []
    if OPENAI_API_KEY and request.messages:
        last_user_msg = next(
            (m.content for m in reversed(request.messages) if m.role == "user"), ""
        )
        if last_user_msg:
            try:
                retrieved_cases = await retrieve_cases(last_user_msg, OPENAI_API_KEY)
                if retrieved_cases:
                    logger.info(
                        f"Case RAG: retrieved {len(retrieved_cases)} case(s) for query "
                        f"'{last_user_msg[:60]}' (top score: {retrieved_cases[0]['score']:.2f})"
                    )
            except Exception as e:
                logger.warning(f"Case RAG retrieval failed (non-fatal): {e}")
    system_prompt = create_case_chat_system_prompt(retrieved_cases=retrieved_cases or None)
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    try:
        reply = await call_openai_chat(system_prompt, messages, timeout_sec=90)
    except Exception as e:
        logger.error(f"Case chat error: {e}")
        raise HTTPException(status_code=500, detail=f"OpenAI request failed: {str(e)}")
    return {
        "reply": reply,
        "retrieved_cases": [
            {"id": c["id"], "title": c["title"], "score": c["score"]}
            for c in retrieved_cases
        ],
    }


MAX_SESSIONS_PER_USER = 20


class CreateSessionRequest(BaseModel):
    user_id: str
    title: Optional[str] = "New session"


class GenerateCoverLetterRequest(BaseModel):
    job_description: str
    user_id: str
    session_id: Optional[str] = None


class ResetSessionRequest(BaseModel):
    user_id: str


class SaveCoverLetterRequest(BaseModel):
    job_description: str
    profile_name: str
    cover_letter: str
    screening_answers: str = ""
    user_id: str
    session_id: str


@api_router.post("/sessions/create")
async def create_session(request: CreateSessionRequest):
    user_id = request.user_id
    count = _db_count_user_sessions(user_id)
    if count >= MAX_SESSIONS_PER_USER:
        _db_delete_oldest_session(user_id)
    session_id = str(uuid.uuid4())
    timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    session = _db_create_session(user_id, session_id, request.title or "New session", timestamp)
    return {"session_id": session_id, "session": {
        **session,
        "message_count": 0,
    }}


@api_router.get("/sessions/{user_id}")
async def list_sessions(user_id: str):
    sessions = _db_get_user_sessions(user_id)
    result = []
    for s in sessions:
        result.append({
            "id": s["id"],
            "title": s["title"],
            "timestamp": s["timestamp"],
            "active": s["active"],
            "message_count": len(s.get("messages", [])),
            "pass_count": s["pass_count"],
            "saved": s["saved"],
            "is_generating": s["is_generating"],
        })
    return {"sessions": result}


@api_router.get("/sessions/{user_id}/{session_id}")
async def get_session(user_id: str, session_id: str):
    session = _db_get_session(user_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    _db_update_session(session_id, active=1)
    return {
        "session": {
            "id": session["id"],
            "title": session["title"],
            "messages": session["messages"],
            "saved_state": session["saved_state"],
            "last_job_description": session["last_job_description"],
            "timestamp": session["timestamp"],
            "pass_count": session["pass_count"],
            "saved": session["saved"],
            "is_generating": session["is_generating"],
        }
    }


@api_router.delete("/sessions/{user_id}/{session_id}")
async def delete_session(user_id: str, session_id: str):
    deleted = _db_delete_session(user_id, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted"}


@api_router.get("/sessions/{user_id}/{session_id}/status")
async def get_session_status(user_id: str, session_id: str):
    session = _db_get_session(user_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = session.get("messages", [])
    return {
        "is_generating": session["is_generating"],
        "messages_count": len(messages),
        "pass_count": session["pass_count"],
        "has_result": any(m.get("result") or m.get("error") for m in messages),
        "saved": session["saved"],
    }


@api_router.post("/save-cover-letter")
async def save_cover_letter(request: SaveCoverLetterRequest):
    session = _db_get_session(request.user_id, request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Per-profile row map: { profile_name: sheet_row_number }
    profile_rows: dict = session.get("profile_rows") or {}
    existing_row = profile_rows.get(request.profile_name)

    if existing_row:
        update_google_sheet_row(
            row_number=existing_row,
            job_description=request.job_description,
            profile_name=request.profile_name,
            cover_letter=request.cover_letter,
            screening_answers=request.screening_answers,
        )
        sheet_row = existing_row
        logger.info(f"Updated Sheets row {sheet_row} for profile '{request.profile_name}' session {request.session_id}")
    else:
        sheet_row = append_to_google_sheet(
            request.job_description,
            request.profile_name,
            request.cover_letter,
            request.screening_answers,
        )
        logger.info(f"Appended Sheets row {sheet_row} for profile '{request.profile_name}' session {request.session_id}")

    # Persist the updated map and mark the session as having at least one saved profile
    profile_rows[request.profile_name] = sheet_row
    _db_update_session(request.session_id, saved=1, profile_rows=profile_rows)
    return {
        "status": "saved",
        "session_id": request.session_id,
        "profile_name": request.profile_name,
        "sheet_row": sheet_row,
    }


@api_router.post("/generate-cover-letter")
async def generate_cover_letter(request: GenerateCoverLetterRequest):
    user_id = request.user_id
    session_id = request.session_id

    if not session_id:
        create_req = CreateSessionRequest(user_id=user_id, title=request.job_description[:30])
        new_session_resp = await create_session(create_req)
        session_id = new_session_resp["session_id"]

    session = _db_get_session(user_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    conversation_history = session.get("messages", [])
    saved_state = session.get("saved_state")

    _db_update_session(session_id, is_generating=1)

    try:
        result, new_saved_state = await process_job(
            job_description=request.job_description,
            conversation_history=conversation_history,
            saved_state=saved_state
        )
        logger.info("=== RESULT FROM process_job ===")
        logger.info(json.dumps(result, indent=2, ensure_ascii=False))
        logger.info("=== END RESULT ===")
        if "error" in result:
            _db_update_session(session_id, is_generating=0)
            raise HTTPException(status_code=400, detail=result["error"])

        if isinstance(result, dict) and isinstance(result.get("__error__"), str):
            error_text = (
                "The model returned an invalid response format, so the generated profiles "
                "cannot be shown.\n\n"
                f"Details: {result['__error__']}"
            )

            updated_messages = list(conversation_history)
            updated_messages.append({"role": "user", "content": request.job_description})
            updated_messages.append({
                "role": "assistant",
                "content": error_text,
                "error": error_text,
            })
            updated_messages = _trim_history(updated_messages)

            new_title = session["title"]
            if new_title == "New session":
                new_title = request.job_description[:30]

            _db_update_session(
                session_id,
                messages=updated_messages,
                saved_state=new_saved_state,
                last_job_description=request.job_description,
                timestamp=int(datetime.now(timezone.utc).timestamp() * 1000),
                title=new_title,
                pass_count=0,
                is_generating=0,
            )

            return {
                "error": error_text,
                "session_id": session_id,
                "invalid_model_response": True,
            }

        all_cases = new_saved_state.get("cases", []) if new_saved_state else []

        updated_messages = list(conversation_history)
        updated_messages.append({"role": "user", "content": request.job_description})
        assistant_msg = {
            "role": "assistant",
            "content": "Generated cover letters",
            "result": result,
            "all_cases": all_cases,
        }
        updated_messages.append(assistant_msg)
        updated_messages = _trim_history(updated_messages)

        pass_count = sum(
            1 for profile_data in result.values()
            if profile_data.get("job_evaluation", {}).get("decision") == "PASS"
        )

        new_title = session["title"]
        if new_title == "New session":
            new_title = request.job_description[:30]

        _db_update_session(
            session_id,
            messages=updated_messages,
            saved_state=new_saved_state,
            last_job_description=request.job_description,
            timestamp=int(datetime.now(timezone.utc).timestamp() * 1000),
            title=new_title,
            pass_count=pass_count,
            is_generating=0,
        )

        return {
            "result": result,
            "saved_state": new_saved_state,
            "session_id": session_id,
            "all_cases": all_cases,
        }
    except HTTPException:
        raise
    except Exception as e:
        _db_update_session(session_id, is_generating=0)
        logger.error(f"Error generating cover letter for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/reset-session")
async def reset_session(request: ResetSessionRequest):
    sessions = _db_get_user_sessions(request.user_id)
    for s in sessions:
        _db_delete_session(request.user_id, s["id"])
    return {"status": "reset", "user_id": request.user_id}


@api_router.get("/profiles")
async def get_profiles():
    profiles = [
        {
            "name": p["name"],
            "position": p["position"],
            "min_salary_per_hour_usd": p.get("min_salary_per_hour_usd"),
            "portfolio_link": p.get("portfolio_link"),
            "priority_cases": p.get("priority_cases", [])
        }
        for p in user_profiles
    ]
    return {"profiles": profiles}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True, log_level="info", log_config=None)