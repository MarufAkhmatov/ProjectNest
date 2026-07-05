"""Build Temur's RAG index over the currently active dataset.

Usage:  python backend/scripts/build_rag.py
Requires Ollama running with the `nomic-embed-text` model available.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from app import storage, aria, rag, docs  # noqa: E402


def main() -> int:
    if not aria.ollama_up():
        print("Ollama is not running — start it first (ollama serve).")
        return 1
    data = storage.load_current()
    if not data or not data.get("issues"):
        print("No active dataset — upload data first.")
        return 1
    issues = data["issues"]
    ds = docs.status()
    print(f"Documents in {ds['dirs']}: {ds['files']} files, {ds['extracted']} extracted "
          f"(tesseract OCR: {'yes' if ds['tesseract'] else 'NO'}).")
    print(f"Embedding {len(issues)} issues + knowledge base + docs ...")

    def prog(n, total):
        print(f"  {n}/{total}", end="\r", flush=True)

    res = rag.build_index(issues, on_progress=prog)
    print(f"\nDone: {res['count']} vectors indexed at {res['built_at']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
