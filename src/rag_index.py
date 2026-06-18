"""Semantic RAG index for Manim examples.

Builds an embedding index over a corpus of (description -> Manim code) examples
so that, given ANY prompt, we can retrieve the most semantically similar working
examples to feed the code generator. Falls back gracefully when the index or the
API is unavailable.

Corpus sources (whatever is present):
- templates/*.py            (our tested templates)
- basis/blocks.py           (the building-block library, as one example)
- data/manimbench.json      (optional; 417 examples, via download_manimbench.py)

Cache: data/rag_embeddings.json  (so we only embed once).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from .config import Config

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "templates"
BASIS_FILE = ROOT / "basis" / "blocks.py"
DATA_DIR = ROOT / "data"
MANIMBENCH_FILE = DATA_DIR / "manimbench.json"
CACHE_FILE = DATA_DIR / "rag_embeddings.json"

EMBED_MODEL = "text-embedding-3-small"


# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------
def _first_docstring(text: str) -> str:
    """Grab the first line of a module docstring as a description."""
    stripped = text.lstrip()
    for quote in ('"""', "'''"):
        if stripped.startswith(quote):
            end = stripped.find(quote, 3)
            if end != -1:
                return stripped[3:end].strip().splitlines()[0]
    return ""


def build_corpus() -> list[dict]:
    """Collect (description, code, source) examples from all available sources."""
    corpus: list[dict] = []

    for path in sorted(TEMPLATES_DIR.glob("*.py")):
        code = path.read_text(encoding="utf-8")
        desc = _first_docstring(code) or f"Manim animation template: {path.stem}"
        corpus.append({"description": desc, "code": code, "source": f"template:{path.name}"})

    if BASIS_FILE.exists():
        code = BASIS_FILE.read_text(encoding="utf-8")
        corpus.append({
            "description": "Reusable Manim building blocks: oscillator, pendulum, "
                           "projectile, phasor, traveling wave, traced graph, vectors.",
            "code": code,
            "source": "basis:blocks.py",
        })

    if MANIMBENCH_FILE.exists():
        try:
            items = json.loads(MANIMBENCH_FILE.read_text(encoding="utf-8"))
            for it in items:
                desc = (it.get("description") or it.get("text") or "").strip()
                code = (it.get("code") or "").strip()
                if desc and code:
                    corpus.append({"description": desc, "code": code, "source": "manimbench"})
        except Exception:
            pass

    return corpus


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
def _client():
    from openai import OpenAI
    cfg = Config.load()
    if not cfg.is_configured:
        raise RuntimeError("OPENAI_API_KEY not set; cannot build semantic index.")
    return OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)


def _embed(texts: list[str]) -> list[list[float]]:
    client = _client()
    # batch to stay well within limits
    out: list[list[float]] = []
    for i in range(0, len(texts), 100):
        chunk = texts[i:i + 100]
        resp = client.embeddings.create(model=EMBED_MODEL, input=chunk)
        out.extend([d.embedding for d in resp.data])
    return out


def build_index(force: bool = False) -> dict:
    """Build (or load cached) the embedding index over the corpus."""
    DATA_DIR.mkdir(exist_ok=True)
    corpus = build_corpus()
    signature = [c["source"] + str(len(c["code"])) for c in corpus]

    if CACHE_FILE.exists() and not force:
        cached = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if cached.get("signature") == signature:
            return cached

    texts = [f"{c['description']}" for c in corpus]
    embeddings = _embed(texts)
    index = {"signature": signature, "items": corpus, "embeddings": embeddings}
    CACHE_FILE.write_text(json.dumps(index), encoding="utf-8")
    return index


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb + 1e-9)


def semantic_search(query: str, k: int = 1) -> list[dict]:
    """Return the top-k most similar examples to the query, or [] on failure."""
    # OpenAI embeddings aren't available on the Gemini endpoint -> skip cleanly
    # so the caller falls back to keyword retrieval.
    cfg = Config.load()
    if cfg.base_url and "googleapis" in cfg.base_url:
        return []
    try:
        index = build_index()
        q_emb = _embed([query])[0]
    except Exception:
        return []  # caller falls back to keyword retrieval

    scored = [
        (_cosine(q_emb, emb), item)
        for emb, item in zip(index["embeddings"], index["items"])
    ]
    scored.sort(key=lambda s: s[0], reverse=True)
    return [item for _, item in scored[:k]]
