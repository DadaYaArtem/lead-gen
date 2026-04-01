# Interexy Lead Analyzer

B2B sales intelligence tool that automatically analyzes LinkedIn "catch-up" leads from HeyReach and generates personalized follow-up messages using OpenAI.

## How It Works

### Automatic Mode (Webhook-driven)
1. **Lead replies on LinkedIn** → HeyReach detects the reply
2. **HeyReach sends webhook** → POST to `/api/webhook/heyreach`
3. **Auto-analysis starts** → Classification → Research → Message generation
4. **Results saved to SQLite** → Available instantly in the UI
5. **Lead gen opens the app** → Sees ready results, no waiting needed

### Manual Mode (On-demand)
1. Select LinkedIn account from dropdown
2. Click "Run Analysis" button
3. Wait for pipeline to complete (5-10 minutes)
4. View results

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Frontend | React 19, Tailwind CSS, Shadcn UI |
| AI | OpenAI GPT-4o (Responses API) |
| LinkedIn Data | HeyReach API |
| Database | SQLite (persistent storage) |

---

## Project Structure

```
lead-gen/
├── backend/
│   ├── server.py          # FastAPI app — all API endpoints and pipeline logic
│   ├── classifier.py      # Intent classifier (gpt-4o-mini, 10 intent types)
│   ├── database.py        # SQLite database module (leads, analyses, messages)
│   ├── webhook_handler.py # HeyReach webhook event processor
│   ├── queue_processor.py # Background queue processor for auto-analysis
│   ├── prompts/
│   │   ├── base_research.py   # Universal lead research prompt (GPT-4o + web search)
│   │   ├── catchup.py         # Message generation for catchup / general leads
│   │   └── no_thanks.py       # Message generation for soft objection leads
│   ├── requirements.txt   # Python dependencies
│   └── .env               # API keys (not committed to git)
└── frontend/
    ├── src/
    │   ├── App.js                     # State management and API calls
    │   └── components/
    │       ├── Dashboard.jsx          # Main UI layout
    │       ├── LeadCard.jsx           # Individual lead display
    │       └── MessageGroup.jsx       # Message variants display
    ├── package.json
    └── .env               # Frontend config (not committed to git)
```

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ — **system-wide installation required**: download from [nodejs.org](https://nodejs.org/) (LTS version recommended). Do **not** rely on a Node.js bundled inside a Python virtualenv — it won't be accessible from a regular terminal.
- npm (bundled with Node.js)

### 1. Clone and configure environment

**Backend** — create `backend/.env`:
```env
HEYREACH_API_KEY=your_heyreach_api_key
OPENAI_API_KEY=your_openai_api_key
LINKEDIN_ACCOUNTS=[{"id":12345,"name":"Account Name"},{"id":67890,"name":"Another Account"}]
```

**Frontend** — create `frontend/.env`:
```env
REACT_APP_BACKEND_URL=http://localhost:8000
```

### 2. Start backend

```bash
pip install -r backend/requirements.txt
uvicorn backend.server:app --reload --port 8000
```

### 3. Start frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm start
```

Frontend: **http://localhost:3000**
Backend API docs: **http://localhost:8000/docs**

> All commands above are run from the repository root (`lead-gen/`), except `npm` commands which require `cd frontend` first.

---

## Local Development with ngrok (Testing Webhooks)

To test automatic lead analysis when leads reply on LinkedIn, you need to expose your local server to the internet using ngrok.

### Step 1: Install ngrok

```bash
# macOS
brew install ngrok

# Windows (via winget)
winget install ngrok

# Linux
snap install ngrok

# Or download from https://ngrok.com/download
```

### Step 2: Register for free ngrok account

1. Go to https://dashboard.ngrok.com/signup
2. Create account
3. Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken
4. Run: `ngrok config add-authtoken YOUR_TOKEN`

### Step 3: Start the full stack

**Terminal 1 — Backend:**
```bash
cd lead-gen
pip install -r backend/requirements.txt
uvicorn backend.server:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd lead-gen/frontend
npm install --legacy-peer-deps
npm start
```

**Terminal 3 — ngrok:**
```bash
ngrok http 8000
```

You should see:
```
Session Status                online
Forwarding                    https://abc123.ngrok.io -> http://localhost:8000
```

**Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)

### Step 4: Configure HeyReach webhook

1. Go to HeyReach Dashboard → Settings → Webhooks
2. Click **Add Webhook**
3. Configure:
   - **URL**: `https://YOUR_NGROK_URL.ngrok.io/api/webhook/heyreach`
   - **Event**: `EVERY_MESSAGE_REPLY_RECEIVED`
   - **Method**: POST
4. Click **Save**

### Step 5: Test the webhook

**Option A — Send a test message from HeyReach:**
1. In HeyReach, find a conversation
2. Send a message to the lead
3. Wait for their reply
4. Check backend logs for: `INFO: Received webhook`

**Option B — Use the test script:**
```bash
cd backend
python test_webhook.py
# Select: 5 (ALL tests)
```

**Option C — Use curl:**
```bash
curl -X POST http://localhost:8000/api/webhook/heyreach \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test-123",
    "sender": {"id": 54937, "first_name": "Test"},
    "lead": {"profile_url": "https://linkedin.com/in/test"}
  }'
```

### Step 6: Verify processing

**Check queue status:**
```bash
curl http://localhost:8000/api/queue/stats
# Expected: {"stats":{"pending":0,"processing":0,"completed":1,"error":0}}
```

**Check leads in database:**
```bash
cd backend
python view_leads.py
```

**Check ngrok logs:**
- Open browser: http://127.0.0.1:4040
- You should see POST requests to `/api/webhook/heyreach`

### Step 7: View results in UI

1. Open http://localhost:3000
2. Select LinkedIn account
3. You should see analyzed leads with messages

---

## Troubleshooting ngrok

| Problem | Solution |
|---------|----------|
| ngrok URL changes on restart | Free tier has random URLs. Use a paid plan for custom domains |
| Webhook not received | Check ngrok is running and URL in HeyReach matches |
| "Connection refused" | Make sure backend is running on port 8000 |
| Queue stuck on pending | Check backend logs for errors. Restart if needed |
| 404 on webhook endpoint | URL should be `https://XXX.ngrok.io/api/webhook/heyreach` (with /api) |

---

## HeyReach Webhook Setup

For detailed setup instructions with ngrok, see [Local Development with ngrok](#local-development-with-ngrok-testing-webhooks) above.

### Quick Setup

1. Go to HeyReach dashboard → Settings → Webhooks
2. Add new webhook with:
   - **URL**: `https://your-domain.com/api/webhook/heyreach` (or ngrok URL for local dev)
   - **Event**: `EVERY_MESSAGE_REPLY_RECEIVED`
   - **Method**: POST
3. Save and test

### Webhook Payload

HeyReach sends JSON payload in this format:
```json
{
  "is_inmail": false,
  "recent_messages": [
    {"creation_time": "2026-04-01T13:08:22.377Z", "message": "hey", "is_reply": true}
  ],
  "conversation_id": "2-OTE3...",
  "sender": {
    "id": 110357,
    "first_name": "Artem",
    "last_name": "Morozov",
    "profile_url": "https://www.linkedin.com/in/..."
  },
  "lead": {
    "id": "918418165",
    "profile_url": "https://www.linkedin.com/in/helen-..."
  }
}
```

---

## API Reference

All endpoints are prefixed with `/api`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/accounts` | Returns list of available LinkedIn accounts |
| `POST` | `/webhook/heyreach` | HeyReach webhook endpoint (auto-analysis) |
| `POST` | `/run-analysis` | Start manual analysis pipeline. Body: `{"account_id": 12345}` |
| `GET` | `/status/{job_id}` | Poll job status (pending / processing / done / error) |
| `GET` | `/results/{job_id}` | Fetch complete results after job completes |
| `GET` | `/leads/{account_id}` | Get all analyzed leads from database |
| `GET` | `/queue/stats` | Get background queue statistics |
| `POST` | `/retry-leads` | Retry failed leads. Body: `{"job_id": "...", "lead_names": ["Name"]}` |

---

## Database Schema

SQLite database (`backend/leads.db`) stores all analyzed leads:

- **leads**: Conversation metadata (conversation_id, account_id, timestamps)
- **lead_profiles**: Profile info (name, company, position, LinkedIn URL)
- **classifications**: Intent classification (intent, confidence, reasoning)
- **analyses**: Deep research results (company info, funding, pain points, qualification)
- **messages**: Generated message variants (messages JSON, top 3 recommendations)
- **processing_queue**: Background job queue (pending/processing/completed/error)

---

## Important Notes for Deployment

### Persistence
- **SQLite database** stores all results permanently
- Results survive server restarts
- Queue processor runs continuously in background

### Automatic Analysis Flow
1. Webhook received → conversation queued
2. Queue processor picks up → fetches from HeyReach
3. Classification → Deep analysis → Message generation
4. All results saved to database
5. Frontend polls `/leads/{account_id}` every 5 seconds

### API Costs
- Each lead costs approximately **$0.05–0.20** in OpenAI API usage (GPT-4o with web search)
- HeyReach API: standard plan limits apply

### Adding / Removing LinkedIn Accounts
Edit the `LINKEDIN_ACCOUNTS` array in `backend/.env` and restart the backend:
```env
LINKEDIN_ACCOUNTS=[
  {"id": 54937, "name": "Helen Grant"},
  {"id": 110357, "name": "Artem Morozov"}
]
```

---

## CLI Utilities

| Command | Description |
|---------|-------------|
| `python view_leads.py` | View all leads from database |
| `python view_leads.py --account-id 54937` | View leads for specific account |
| `python view_leads.py --verbose` | Show full message text |
| `python view_leads.py --stats` | Show queue statistics only |
| `python test_webhook.py` | Send test webhooks (interactive) |
| `python debug_webhook.py` | Diagnose webhook connectivity |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `npm: command not found` / `npm is not recognized` | Node.js is not installed system-wide. Download and install it from [nodejs.org](https://nodejs.org/) (LTS). A Node.js that lives inside a Python venv is not on your PATH. |
| `npm install` fails with peer dependency error | Use `npm install --legacy-peer-deps` |
| `emergentintegrations` package not found | Skip it — it's listed in requirements.txt but not used in the code |
| `Analysis failed: Expecting value: line N column N` | JSON parsing error from OpenAI — handled automatically by `json-repair`. Retry the lead using the "Retry Selected" button |
| Frontend shows blank page after build | Check that `REACT_APP_BACKEND_URL` is set correctly in `frontend/.env` before running `npm run build` |
| Backend CORS error | Add your frontend URL to `CORS_ORIGINS` in `backend/.env` |
| Webhook not received | Verify HeyReach webhook URL is correct and publicly accessible (use ngrok for local testing). Check ngrok logs at http://127.0.0.1:4040 |
| Queue stuck | Check `GET /api/queue/stats` — if pending > 0 for long time, restart backend |
| No leads showing in UI | Run `python view_leads.py` to check database. Check backend logs for "Received webhook" messages |
| "Lead not found" on delete | The conversation_id might not match. Check database: `sqlite3 backend/leads.db "SELECT conversation_id, full_name FROM leads;"` |

---

## Backlog / Planned Features

- Export results to CSV/PDF
- Analysis history with MongoDB persistence
- Manual lead input by LinkedIn URL
- Send messages directly back to HeyReach
- Analytics dashboard
- Webhook signature verification

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `npm: command not found` / `npm is not recognized` | Node.js is not installed system-wide. Download and install it from [nodejs.org](https://nodejs.org/) (LTS). A Node.js that lives inside a Python venv is not on your PATH. |
| `npm install` fails with peer dependency error | Use `npm install --legacy-peer-deps` |
| `emergentintegrations` package not found | Skip it — it's listed in requirements.txt but not used in the code |
| `Analysis failed: Expecting value: line N column N` | JSON parsing error from OpenAI — handled automatically by `json-repair`. Retry the lead using the "Retry Selected" button |
| Frontend shows blank page after build | Check that `REACT_APP_BACKEND_URL` is set correctly in `frontend/.env` before running `npm run build` |
| Backend CORS error | Add your frontend URL to `CORS_ORIGINS` in `backend/.env` |
| Webhook not received | Verify HeyReach webhook URL is correct and publicly accessible (use ngrok for local testing) |
| Queue stuck | Check `GET /api/queue/stats` — if pending > 0 for long time, restart backend |
