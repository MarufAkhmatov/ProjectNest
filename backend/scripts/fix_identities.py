"""One-off fix: apply person-identity resolution to the CURRENTLY loaded
dataset in place, without requiring a re-upload. Safe to re-run any time —
resolve_identities() is idempotent (already-canonical names map to themselves).

Usage: python backend/scripts/fix_identities.py
"""
import sys
import datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from app import storage, aggregate, identity  # noqa: E402


def main() -> int:
    cur = storage.load_current()
    if not cur or not cur.get("issues"):
        print("No active dataset — nothing to fix.")
        return 1
    issues = cur["issues"]
    applied = identity.resolve_identities(issues)
    if not applied:
        print("No duplicate name variants found — dataset already clean.")
        return 0

    print(f"Merged {len(applied)} name variant(s):")
    for raw, canon in sorted(applied.items()):
        print(f"  {raw!r} -> {canon!r}")

    payload = aggregate.build(issues)
    meta = storage.load_current_meta() or {}
    meta = {**meta, "identity_fix_applied_at": dt.datetime.now().isoformat(timespec="seconds")}
    storage.set_current({"issues": issues, "payload": payload}, meta)
    print(f"\nSaved. {len(issues)} issues re-aggregated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
