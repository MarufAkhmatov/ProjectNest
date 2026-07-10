"""Local RAG (Retrieval-Augmented Grounding) for Temur.

Embeds every portfolio issue + every knowledge-base document with Ollama's
`nomic-embed-text` model and stores the vectors on disk. At question time we
embed the query, cosine-rank the corpus and hand Temur only the few most
relevant chunks — so answers are grounded in real data instead of guessed.

Pure stdlib (json + math): no numpy, no external services. Fully offline.
"""
from __future__ import annotations
import json
import math
import re
import time
import hashlib
import urllib.request
from pathlib import Path

from app import config

EMBED_MODEL = "nomic-embed-text"
INDEX_FILE = config.ROOT / "ai" / "vector_db" / "index.json"
KB_DIR = config.ROOT / "knowledge_base"
_MEM: dict | None = None          # in-process cache of the loaded index


# --------------------------------------------------------------------------- #
#  embeddings
# --------------------------------------------------------------------------- #
def embed(text: str, timeout: int = 60) -> list[float] | None:
    """Return the embedding vector for `text`, or None if Ollama is unavailable."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        req = urllib.request.Request(
            f"{config.OLLAMA_URL}/api/embeddings",
            data=json.dumps({"model": EMBED_MODEL, "prompt": text[:4000]}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            v = json.loads(r.read()).get("embedding")
            return v if v else None
    except Exception:
        return None


def _cos(a: list[float], b: list[float]) -> float:
    s = da = db = 0.0
    for x, y in zip(a, b):
        s += x * y; da += x * x; db += y * y
    if da == 0 or db == 0:
        return 0.0
    return s / (math.sqrt(da) * math.sqrt(db))


# --------------------------------------------------------------------------- #
#  corpus construction
# --------------------------------------------------------------------------- #
def _issue_doc(i: dict) -> str:
    """A compact, information-dense text for one issue (what we embed)."""
    parts = [
        f"{i.get('key','')} [{i.get('project','')}] {i.get('summary','')}",
        f"type={i.get('type','')} status={i.get('status','')}",
        f"owner={i.get('owner','')} PM={i.get('pm','')} assignee={i.get('assignee','')}",
        f"owner_department={i.get('owner_department','')} change_leader={i.get('change_leader','')}",
    ]
    for f in ("division", "project_type", "scoring", "quarterly_status"):
        if i.get(f):
            parts.append(f"{f}={i[f]}")
    if i.get("description"):
        parts.append(str(i["description"])[:400])
    # Epic/new-feature "passport" fields — grounds retrieval in WHY the item
    # exists and what "done" means for it, not just its current Jira status.
    for label, key in (("justification", "justification"), ("goals", "goals"),
                       ("definition_of_done", "definition_of_done"),
                       ("business_effectiveness", "business_effectiveness")):
        if i.get(key):
            parts.append(f"{label}: " + str(i[key])[:300])
    if i.get("smart_checklist_progress"):
        parts.append(f"checklist_progress={i['smart_checklist_progress']}")
    return " | ".join(p for p in parts if p and not p.endswith("="))


def _kb_docs() -> list[dict]:
    """Chunk every knowledge-base source into ~800-char passages.

    Two sources:
      1. knowledge_base/  — plain .md/.txt methodology notes (fast).
      2. knowladgebasefromdocs/ — the user's real documents (PDF/DOCX/scans/
         images/xlsx). Extracted (with OCR when needed) + cached by docs.py.
    """
    docs = []
    # 1) plain-text knowledge base
    if KB_DIR.exists():
        for f in KB_DIR.rglob("*"):
            if f.suffix.lower() not in (".md", ".txt") or not f.is_file():
                continue
            try:
                raw = f.read_text("utf-8", errors="ignore")
            except Exception:
                continue
            for n, chunk in enumerate(_chunk(raw, 800)):
                docs.append({"id": f"kb:{f.stem}:{n}", "kind": "kb",
                             "source": f.name, "text": chunk})
    # 2) the user's documents (OCR + extraction handled by docs.py)
    try:
        from . import docs as _docsmod
        for d in _docsmod.scan_docs():
            stem = Path(d["source"]).stem
            for n, chunk in enumerate(_chunk(d["text"], 800)):
                docs.append({"id": f"doc:{stem}:{n}", "kind": "doc",
                             "source": d["source"],
                             "text": f"[{d['source']}] {chunk}"})
    except Exception:
        pass
    return docs


def _chunk(text: str, size: int) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    out, buf = [], ""
    for para in text.split("\n\n"):
        if len(buf) + len(para) > size and buf:
            out.append(buf.strip()); buf = ""
        buf += para + "\n\n"
    if buf.strip():
        out.append(buf.strip())
    return [c for c in out if len(c) > 40]


# --------------------------------------------------------------------------- #
#  build / load
# --------------------------------------------------------------------------- #
def _text_hash(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()


def build_index(issues: list[dict], on_progress=None) -> dict:
    """(Re)build the corpus index INCREMENTALLY.

    An item is embedded only if it is NEW or its text CHANGED since the last
    build — unchanged issues/docs reuse their existing vector. So adding a few
    documents costs a few embeddings, not a full re-embed of all ~850 issues.
    """
    global _MEM
    corpus = [{"id": i.get("key"), "kind": "issue", "text": _issue_doc(i),
               "meta": {"key": i.get("key"), "status": i.get("status"),
                        "pm": i.get("pm"), "project": i.get("project")}}
              for i in issues if i.get("key")]
    corpus += _kb_docs()

    # Reuse map from the existing index: (id, text-hash) -> vector.
    prev = _load() or {}
    reuse: dict[tuple, list] = {}
    for r in prev.get("records", []):
        if r.get("vec"):
            reuse[(r.get("id"), _text_hash(r.get("text", "")))] = r["vec"]

    records, total, embedded = [], len(corpus), 0
    for n, d in enumerate(corpus):
        key = (d["id"], _text_hash(d["text"]))
        v = reuse.get(key)
        if v is None:
            v = embed(d["text"])
            if v:
                embedded += 1
        if v:
            records.append({**d, "vec": v})
        if on_progress and n % 25 == 0:
            on_progress(n, total)
    idx = {"model": EMBED_MODEL, "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "count": len(records), "records": records}
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = INDEX_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(idx, ensure_ascii=False), "utf-8")
    tmp.replace(INDEX_FILE)                     # atomic
    _MEM = idx
    return {"count": len(records), "of": total, "embedded": embedded,
            "reused": len(records) - embedded, "built_at": idx["built_at"]}


def build_docs_only(on_progress=None) -> dict:
    """Embed ONLY the knowledge base + documents and merge them into the index,
    leaving existing issue vectors untouched. Fast (~doc-chunk count), so the
    user's documents become searchable immediately without waiting for the full
    ~850-issue re-embed."""
    global _MEM
    prev = _load() or {}
    prev_records = prev.get("records", [])
    # keep everything that is NOT a kb/doc chunk (i.e. issue vectors)
    kept = [r for r in prev_records if r.get("kind") not in ("kb", "doc")]
    reuse = {(r.get("id"), _text_hash(r.get("text", ""))): r["vec"]
             for r in prev_records if r.get("kind") in ("kb", "doc") and r.get("vec")}

    doc_corpus = _kb_docs()
    new_docs, embedded, total = [], 0, len(doc_corpus)
    for n, d in enumerate(doc_corpus):
        key = (d["id"], _text_hash(d["text"]))
        v = reuse.get(key)
        if v is None:
            v = embed(d["text"])
            if v:
                embedded += 1
        if v:
            new_docs.append({**d, "vec": v})
        if on_progress and n % 10 == 0:
            on_progress(n, total)

    records = kept + new_docs
    idx = {"model": EMBED_MODEL, "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "count": len(records), "records": records}
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = INDEX_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(idx, ensure_ascii=False), "utf-8")
    tmp.replace(INDEX_FILE)
    _MEM = idx
    return {"count": len(records), "doc_chunks": len(new_docs), "embedded": embedded,
            "issues_kept": len(kept), "built_at": idx["built_at"]}


def _load() -> dict | None:
    global _MEM
    if _MEM is not None:
        return _MEM
    if INDEX_FILE.exists():
        try:
            _MEM = json.loads(INDEX_FILE.read_text("utf-8"))
        except Exception:
            _MEM = None
    return _MEM


def ready() -> bool:
    idx = _load()
    return bool(idx and idx.get("records"))


def search(query: str, k: int = 6, kinds: set[str] | None = None) -> list[dict]:
    """Top-k most relevant corpus chunks for `query` (empty if index/Ollama down).
    kinds: optional filter (e.g. {"doc"}) to search only that record kind —
    without it, [DOC]/[KB]/[ISSUE] all compete on relevance alone, so a query
    that happens to closely match an issue's own text can crowd out regulation
    chunks. Callers that specifically want bank-document grounding should pass
    kinds={"doc"} rather than relying on query phrasing to bias retrieval."""
    idx = _load()
    if not idx or not idx.get("records"):
        return []
    qv = embed(query, timeout=30)
    if not qv:
        return []
    records = idx["records"] if kinds is None else [r for r in idx["records"] if r.get("kind") in kinds]
    scored = [(_cos(qv, r["vec"]), r) for r in records]
    scored.sort(key=lambda t: t[0], reverse=True)
    out = []
    for score, r in scored[:k]:
        if score < 0.25:
            break
        out.append({"score": round(score, 3), "kind": r.get("kind"),
                    "text": r["text"], "meta": r.get("meta", {})})
    return out


def context_block(query: str, k: int = 6, kinds: set[str] | None = None) -> str:
    """A ready-to-inject 'RETRIEVED' section for Temur's prompt."""
    hits = search(query, k, kinds=kinds)
    if not hits:
        return ""
    lines = ["Most relevant records for this question (retrieved from the live data):"]
    for h in hits:
        kind = h.get("kind")
        tag = "DOC" if kind == "doc" else "KB" if kind == "kb" else "ISSUE"
        lines.append(f"- [{tag}] {h['text']}")
    return "\n".join(lines)
