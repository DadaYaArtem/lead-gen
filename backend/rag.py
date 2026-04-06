"""
RAG (Retrieval-Augmented Generation) engine for Interexy's case study knowledge base.

How it works:
1. Case studies are stored as Markdown files in knowledge_base/cases/
2. Each file is embedded once using text-embedding-3-small and cached locally
3. Cache uses MD5 hashes of file contents — auto-invalidates when a case is edited
4. At query time: embed the query, compute cosine similarity, return top-K cases

No extra dependencies — cosine similarity is computed with the math module.
"""
import json
import logging
import math
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ─────────────────────────── Paths ───────────────────────────────────────────

_BASE_DIR = Path(__file__).parent / "knowledge_base"
_CASES_DIR = _BASE_DIR / "cases"
_CACHE_FILE = _BASE_DIR / "embeddings_cache.json"

# ─────────────────────────── Cosine similarity ───────────────────────────────

def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ─────────────────────────── Case loading ────────────────────────────────────

def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def load_cases() -> List[Dict[str, Any]]:
    """Load all .md case files from knowledge_base/cases/.

    Returns a list of dicts with keys: id, title, content, path, hash.
    Files with empty content (placeholders) are included — they just won't
    match any query meaningfully.
    """
    if not _CASES_DIR.exists():
        logger.warning(f"Cases directory not found: {_CASES_DIR}")
        return []

    cases = []
    for md_file in sorted(_CASES_DIR.glob("*.md")):
        content = md_file.read_text(encoding="utf-8").strip()
        # Extract title from first # heading, fall back to filename
        title = md_file.stem.replace("_", " ").title()
        for line in content.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break

        cases.append({
            "id": md_file.stem,
            "title": title,
            "content": content,
            "path": str(md_file),
            "hash": _md5(content),
        })

    logger.info(f"Loaded {len(cases)} case(s) from knowledge base")
    return cases


# ─────────────────────────── Embedding & cache ───────────────────────────────

def _load_cache() -> Dict[str, Any]:
    if _CACHE_FILE.exists():
        try:
            return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Corrupted embeddings cache — will regenerate")
    return {}


def _save_cache(cache: Dict[str, Any]) -> None:
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


async def _embed_text(text: str, api_key: str) -> List[float]:
    """Call OpenAI text-embedding-3-small and return the embedding vector."""
    url = "https://api.openai.com/v1/embeddings"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "text-embedding-3-small", "input": text}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]


async def get_embeddings(
    cases: List[Dict[str, Any]], api_key: str
) -> Dict[str, List[float]]:
    """Return embeddings for all cases, using cache where possible.

    Cache key = case id. The entry stores {hash, embedding}.
    If the file's MD5 hash has changed, the embedding is regenerated.
    """
    cache = _load_cache()
    embeddings: Dict[str, List[float]] = {}
    updated = False

    for case in cases:
        cid = case["id"]
        cached = cache.get(cid, {})

        if cached.get("hash") == case["hash"] and cached.get("embedding"):
            embeddings[cid] = cached["embedding"]
            continue

        if not case["content"]:
            logger.debug(f"Skipping empty case: {cid}")
            continue

        logger.info(f"Generating embedding for case: {cid}")
        try:
            vec = await _embed_text(case["content"], api_key)
            embeddings[cid] = vec
            cache[cid] = {"hash": case["hash"], "embedding": vec}
            updated = True
        except Exception as e:
            logger.error(f"Failed to embed case {cid}: {e}")

    if updated:
        _save_cache(cache)

    return embeddings


# ─────────────────────────── Retrieval ───────────────────────────────────────

async def retrieve_cases(
    query: str,
    api_key: str,
    top_k: int = 3,
    threshold: float = 0.35,
) -> List[Dict[str, Any]]:
    """Find the most relevant case studies for a given query.

    Returns a list of case dicts (id, title, content, score), sorted by
    descending similarity. Only cases above `threshold` are returned.
    Empty placeholder cases are skipped.
    """
    cases = load_cases()
    if not cases:
        return []

    # Filter out empty placeholders
    populated = [c for c in cases if len(c["content"]) > 100]
    if not populated:
        return []

    embeddings = await get_embeddings(populated, api_key)
    if not embeddings:
        return []

    try:
        query_vec = await _embed_text(query, api_key)
    except Exception as e:
        logger.error(f"Failed to embed query: {e}")
        return []

    scored = []
    for case in populated:
        vec = embeddings.get(case["id"])
        if vec is None:
            continue
        score = _cosine_similarity(query_vec, vec)
        if score >= threshold:
            scored.append({**case, "score": round(score, 4)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# ─────────────────────────── Metadata (for API listing) ──────────────────────

def get_cases_metadata() -> List[Dict[str, str]]:
    """Return lightweight metadata for all cases (no embeddings, no full content).

    Used by GET /api/knowledge-base.
    """
    cases = load_cases()
    result = []
    for c in cases:
        # Extract industry/tags from the markdown front-matter-style fields
        lines = c["content"].splitlines()
        industry = ""
        tags = ""
        for line in lines:
            if line.startswith("**Industry:**"):
                industry = line.split(":", 1)[1].strip().lstrip("*")
            elif line.startswith("**Tags:**"):
                tags = line.split(":", 1)[1].strip().lstrip("*")

        result.append({
            "id": c["id"],
            "title": c["title"],
            "industry": industry,
            "tags": tags,
            "is_populated": len(c["content"]) > 100,
        })
    return result
