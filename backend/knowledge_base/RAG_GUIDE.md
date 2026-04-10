# RAG Knowledge Base — How It Works

## Overview

The RAG (Retrieval-Augmented Generation) system gives the per-lead AI chat and the standalone Case Library access to Interexy's real project portfolio. When a sales rep asks "which case suits this lead?" or "do we have healthcare experience?", the AI responds with specific, accurate information — not hallucinations.

---

## Architecture

```
User asks question in chat
        │
        ▼
  Last user message
        │
        ▼ (non-ASCII query? → gpt-4o-mini translates to English keywords)
  text-embedding-3-small
  (embed the query)
        │
        ▼
  Cosine similarity
  against case embeddings
        │
        ├── score ≥ 0.35 → inject into system prompt
        ├── score < 0.35 but ≥ 0.05 → fallback: return top-K anyway
        └── all scores < 0.05 → no cases injected
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
        ├── case_eon.md
        ├── case_scale_ai.md
        └── your_case.md            ← add more here
```

---

## Case File Format

Each case is a plain Markdown file in `backend/knowledge_base/cases/`. Filename = case ID.

**Required format:**

```markdown
---
industry:
  - energy
  - utilities
tech_stack:
  - Python
  - React
client_type: enterprise
region: DACH
---

# Client Name

## Общая информация
- Клиент: ...
- Локация: ...
- Отрасль: ...
- Формат: Outstaff / Outsource
- Статус: Активный / Завершён

## Команда
- Размер: N человек

## Стек
- ...

## Проблема клиента
Описание проблемы.

## Решение
Что сделал Interexy.

## Ключевые задачи / Ключевые фичи
- ...

## Результаты / Значимость
- ...

## Ссылки
- Сайт: https://...
```

### Frontmatter fields

| Field | Type | Values |
|-------|------|--------|
| `industry` | list | `energy`, `healthcare`, `ai_ml`, `iot`, `real_estate`, `fintech`, etc. |
| `tech_stack` | list | `Python`, `Swift`, `React`, `Node.js`, `Kotlin`, etc. |
| `client_type` | string | `enterprise`, `scaleup`, `startup` |
| `region` | string | `DACH`, `UK`, `US`, `EU`, etc. |

> **Important:** The frontmatter is parsed automatically by `rag.py`. All 4 fields are used for the sidebar display in the Case Library UI.

---

## How Embeddings Work

1. On each retrieval request, `rag.py` loads all `.md` files from `cases/`
2. Checks `embeddings_cache.json` for each case
3. For each case:
   - If the file's MD5 hash matches the cache → use cached embedding (no API call)
   - If the hash changed (file was edited) → regenerate the embedding
4. Cache saved back to `embeddings_cache.json` after updates
5. Retrieval = embed the user's query → cosine similarity → return top-3

**Multilingual queries:** Non-ASCII queries (e.g. Russian) are translated to English keywords via `gpt-4o-mini` before embedding. This significantly improves cross-lingual retrieval quality.

**Cost:** `text-embedding-3-small` costs ~$0.00002 per 1K tokens. Embedding 200 cases (~500 tokens each) ≈ $0.002 total, cached forever until files change.

---

## Retrieval Logic

- **Primary threshold: 0.35** — cases above this are considered relevant
- **Fallback floor: 0.05** — if nothing exceeds 0.35 (e.g. "show me all cases"), return top-K above 0.05 anyway
- Logged in server output: `RAG: retrieved N case(s)` or `RAG: no cases above threshold — using fallback`

To tune thresholds, edit `rag.py → retrieve_cases(threshold=..., fallback_floor=...)`.

---

## API Endpoints

### `GET /api/knowledge-base`

```json
{
  "cases": [
    {
      "id": "case_eon",
      "title": "E.ON",
      "industry": ["energy", "utilities"],
      "tech_stack": ["Data Vault", "ETL", "BI"],
      "client_type": "enterprise",
      "region": "DACH",
      "is_populated": true
    }
  ],
  "total": 10,
  "populated": 10
}
```

### `POST /api/chat` (lead-aware, updated response)

```json
{
  "reply": "Based on your lead's healthcare background, the most relevant case is...",
  "retrieved_cases": [
    {"id": "case_medkitdoc", "title": "MedKitDoc", "score": 0.71}
  ]
}
```

### `POST /api/case-chat` (standalone)

Same response shape — no lead context required.

---

## Adding a New Case

1. Create `backend/knowledge_base/cases/case_yourname.md`
2. Add the YAML frontmatter and Russian-language body (see format above)
3. The embedding is generated automatically on the next chat/retrieval request
4. No server restart required

---

## Troubleshooting

**Cases not showing up in sidebar:**
- Ensure the file is in `knowledge_base/cases/` and ends with `.md`
- Check `GET /api/knowledge-base` — `is_populated` must be `true` (file > 100 chars)

**Cases not being retrieved in chat:**
- Check server logs for `RAG:` messages
- Try a more specific query (e.g. "healthcare Bluetooth" instead of "покажи кейсы")
- Russian queries are auto-translated — check log for `Query normalized:`

**Cache seems stale:**
Delete `backend/knowledge_base/embeddings_cache.json` — regenerated on next request.

**`embeddings_cache.json` was accidentally committed:**
`git rm --cached backend/knowledge_base/embeddings_cache.json`


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
