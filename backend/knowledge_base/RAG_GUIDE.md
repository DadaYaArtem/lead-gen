# RAG Knowledge Base — How It Works

## Overview

The RAG (Retrieval-Augmented Generation) system gives the per-lead AI chat access to Interexy's real project portfolio. When a sales rep asks "which case suits this lead?" or "do we have healthcare experience?", the AI responds with specific, accurate information — not hallucinations.

---

## Architecture

```
User asks question in chat
        │
        ▼
  Last user message
        │
        ▼
  text-embedding-3-small
  (embed the query)
        │
        ▼
  Cosine similarity
  against case embeddings
        │
        ├── score ≥ 0.35 → inject into system prompt
        └── score < 0.35 → chat continues without cases
        │
        ▼
  GPT-5.1 answers with
  specific case references
```

---

## File Structure

```
backend/
├── rag.py                          ← RAG engine (load, embed, retrieve)
└── knowledge_base/
    ├── embeddings_cache.json       ← auto-generated, gitignored
    └── cases/
        ├── rwe_energy.md           ← case study #1
        ├── eon_digital.md          ← case study #2
        ├── healthcare_remote_monitoring.md  ← case study #3
        └── your_case.md            ← add more here
```

---

## How Cases Are Stored

Each case is a plain Markdown file in `backend/knowledge_base/cases/`. Filename = case ID (used in logs and API responses).

**Required format:**

```markdown
# Case Title

**Industry:** Energy / Utilities
**Tags:** energy, mobile, field-operations, IoT
**Client:** Client name (or "Confidential")
**Engagement type:** Staff augmentation / Product development
**Timeline:** 12 months
**Team:** 6 Interexy engineers

---

## Problem
What challenge the client faced and why they needed Interexy.

## Solution
What Interexy built and how.

## Outcome
Measurable results (reduce X by Y%, shipped in Z months, etc.)

## Key Achievements
Notable technical or business wins.
```

> **Important:** Keep `**Industry:**` and `**Tags:**` on their own lines — the API listing endpoint parses them to build the case metadata response.

---

## How Embeddings Work

1. When the server starts, `rag.py` loads all `.md` files from `cases/`
2. On the first chat message that triggers retrieval, it checks `embeddings_cache.json`
3. For each case:
   - If the file's MD5 hash matches the cache → use cached embedding (no API call)
   - If the hash changed (file was edited) → regenerate the embedding
4. Cache is saved back to `embeddings_cache.json` after any updates
5. Retrieval = embed the user's query → cosine similarity against all cached vectors → return top-3 above threshold

**Cost:** `text-embedding-3-small` costs ~$0.00002 per 1K tokens. Embedding 200 cases (~500 tokens each) costs ≈ $0.002 total, cached forever until files change.

---

## Retrieval Threshold

Default: **0.35** (35% cosine similarity).

- Below this → case is too unrelated and is not injected into the prompt
- Above this → case is included with its relevance score shown to the model
- If no cases match → chat continues normally without RAG context

To tune the threshold, edit `rag.py → retrieve_cases(threshold=0.35)`.

---

## API Endpoints

### `GET /api/knowledge-base`
Lists all available cases with metadata.

```json
{
  "cases": [
    {
      "id": "rwe_energy",
      "title": "RWE Energy — Mobile Field Operations Platform",
      "industry": "Energy / Utilities",
      "tags": "energy, utilities, mobile, field-operations, IoT",
      "is_populated": true
    }
  ],
  "total": 3,
  "populated": 3
}
```

### `POST /api/chat` (updated response)
The chat response now includes retrieved cases metadata:

```json
{
  "reply": "Based on your lead's healthcare background, the most relevant case is...",
  "retrieved_cases": [
    {"id": "healthcare_remote_monitoring", "title": "Healthcare Mobile App — Remote Patient Monitoring", "score": 0.71}
  ]
}
```

---

## Adding a New Case

1. Create a new `.md` file in `backend/knowledge_base/cases/`
2. Follow the format above (especially `**Industry:**` and `**Tags:**` lines)
3. The embedding will be generated automatically on the next chat request
4. No server restart required (cases are loaded at retrieval time, not at startup)

---

## What's Not Yet Implemented (Part 2)

- **Standalone case mode** — a dedicated chat interface without a specific lead, for questions like "what fintech cases do we have?"
- New frontend component for case search
- New `/api/case-chat` endpoint

---

## Example Queries That Benefit from RAG

| Sales rep asks | RAG finds | AI answers |
|---|---|---|
| "Which case should I mention for this healthcare lead?" | `healthcare_remote_monitoring.md` (score ~0.70) | Specific reference to the BLE medical device project |
| "Do we have energy sector experience?" | `rwe_energy.md`, `eon_digital.md` (score ~0.65) | Both energy cases with specific outcomes |
| "What proof points to use in follow-up?" | Best matching case by industry | Specific metrics from that project |
| "Tell me about the lead's company size" | No cases match (score < 0.35) | Answers from lead analysis only |

---

## Troubleshooting

**Cache seems stale / embeddings not updating:**  
Delete `backend/knowledge_base/embeddings_cache.json` — it will be regenerated on the next chat request.

**Cases not being retrieved:**  
- Check `is_populated: true` in `GET /api/knowledge-base` — placeholder files with < 100 chars are skipped
- Try lowering the threshold in `rag.py`
- Check server logs for `RAG: retrieved N case(s)` messages

**`embeddings_cache.json` was accidentally committed:**  
Run `git rm --cached backend/knowledge_base/embeddings_cache.json` — it's already in `.gitignore`.
