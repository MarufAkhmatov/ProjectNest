"""Person identity resolution — collapse name-string variants of the same
human into one canonical display name across the whole dataset.

Why this exists: the SAME PM/owner/change-leader shows up under different
strings depending on which Jira export wrote it:
  - Custom fields that only carry an email get turned into an INITIAL form by
    normalize._pretty_person(): "o.saidov@bank.uz" -> "O. Saidov".
  - "Printable"/issuetable HTML exports carry the real Jira display name, the
    FULL form: "Ozod Saidov".
  - Occasional export glitches glue the initial straight onto the last name
    with no separator: "AAbduhalikov" (missing ". ").
Without resolution these read as different people on the PM leaderboard, the
Change-Leaders panel and Owner counts (each variant gets its own row/total).
This module builds one raw -> canonical mapping per ingest, covering every
name string that appears anywhere in the dataset, and is applied to the
pm / owner / change_leader fields of every issue before aggregation.

Scope note: only these three "who's accountable" fields are resolved. Names
that are genuinely 2 letters (Uzbek/Russian names are essentially never that
short) are treated as initials — an acceptable trade-off for this dataset,
documented rather than hidden.
"""
import re

PERSON_FIELDS = ("pm", "owner", "change_leader")

_STRIP_RE = re.compile(r"[.’ʼ`']")
_CONCAT_RE = re.compile(r"^([A-ZА-ЯЁ])([A-ZА-ЯЁ][a-zа-яёʻʼ'\-]{2,})$")
_INITIAL_MAX_LEN = 2   # tokens this short or shorter are treated as an initial


def _strip(s: str) -> str:
    return _STRIP_RE.sub("", s or "").strip()


def _tokens(name: str) -> list[str]:
    return [t for t in re.split(r"\s+", _strip(name)) if t]


def _split_concat(tok: str):
    """'AAbduhalikov' -> ('A', 'Abduhalikov') if it looks like an initial glued
    straight onto the last name (two capitals then a lowercase run)."""
    m = _CONCAT_RE.match(tok)
    return (m.group(1), m.group(2)) if m else None


def _parse_person(raw: str):
    """Return (first_key, last_key, kind) or None if unparseable.
    kind is 'full' (a real first name) or 'initial' (an abbreviation)."""
    toks = _tokens(raw)
    if not toks:
        return None
    if len(toks) == 1:
        split = _split_concat(toks[0])
        if not split:
            return None   # a bare single word (nickname, "Unassigned", …) — leave alone
        first, last, kind = split[0], split[1], "initial"
    else:
        first, last = toks[0], toks[-1]
        kind = "initial" if len(first) <= _INITIAL_MAX_LEN else "full"
    return first.lower(), last.lower(), kind


def build_name_map(names) -> dict[str, str]:
    """names: iterable of raw display-name strings (duplicates are fine).
    Returns {raw_name: canonical_name} for every non-empty, parseable input."""
    raw_list = list(dict.fromkeys(n.strip() for n in names if n and n.strip()))

    parsed: dict[str, tuple[str, str, str] | None] = {r: _parse_person(r) for r in raw_list}

    # 1) Bucket FULL names by EXACT (first_key, last_key) — never fuzzy-merge
    #    two different full first names (e.g. "Ozod Saidov" vs "Olim Saidov"
    #    must stay separate people).
    full_buckets: dict[tuple[str, str], list[str]] = {}
    for raw, p in parsed.items():
        if p and p[2] == "full":
            full_buckets.setdefault((p[0], p[1]), []).append(raw)
    bucket_canon = {k: max(v, key=len) for k, v in full_buckets.items()}

    name_map: dict[str, str] = {}
    for key, raws in full_buckets.items():
        canon = bucket_canon[key]
        for raw in raws:
            name_map[raw] = canon

    # 2) Route INITIAL-form entries to the matching full-name bucket by last
    #    name + first-name prefix ("Sh" -> "Shakhzoda", "M" -> "Ma'ruf").
    initials_by_last: dict[str, list[tuple[str, str]]] = {}
    for raw, p in parsed.items():
        if p and p[2] == "initial":
            initials_by_last.setdefault(p[1], []).append((raw, p[0]))

    for last_key, entries in initials_by_last.items():
        candidates = [(fk, bucket_canon[(fk, lk)]) for (fk, lk) in full_buckets if lk == last_key]
        unmatched: list[tuple[str, str]] = []
        for raw, first_key in entries:
            match = next((canon for fk, canon in candidates
                         if fk.startswith(first_key) or first_key.startswith(fk)), None)
            if match:
                name_map[raw] = match
            else:
                unmatched.append((raw, first_key))
        # No full-name form exists for this last name — merge the initial-only
        # variants that share the same (first_key, last_key) into one canonical.
        by_exact: dict[str, list[str]] = {}
        for raw, first_key in unmatched:
            by_exact.setdefault(first_key, []).append(raw)
        for raws in by_exact.values():
            canon = max(raws, key=len)
            for raw in raws:
                name_map[raw] = canon

    # 3) Anything unparseable (single bare word) maps to itself.
    for raw, p in parsed.items():
        if raw not in name_map:
            name_map[raw] = raw
    return name_map


def resolve_identities(issues: list[dict]) -> dict[str, str]:
    """Canonicalize pm / owner / change_leader across the WHOLE issue list IN
    PLACE, so the same human always appears under one name portfolio-wide.
    Returns the raw->canonical map actually applied (for diagnostics/tests)."""
    names: list[str] = []
    for i in issues:
        for f in PERSON_FIELDS:
            v = i.get(f)
            if v and v != "Unassigned":
                names.append(v)
    name_map = build_name_map(names)
    applied = {}
    for i in issues:
        for f in PERSON_FIELDS:
            v = i.get(f)
            if v and v in name_map and name_map[v] != v:
                i[f] = name_map[v]
                applied[v] = name_map[v]
    return applied
