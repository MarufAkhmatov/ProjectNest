"""Normalize raw Jira rows into a canonical issue model.

Canonical issue keys:
  key, project, type, is_epic, status, status_group, summary,
  pm (assignee), created, resolved, due, epic_key, story_points,
  links: [{type, target}], history: [{status, entered, exited, days}]
"""
import json
import datetime as dt
from . import config

# ---- flexible column lookup -------------------------------------------------
_ALIASES = {
    "key": ["issue key", "key", "issue id", "id",
            "ключ вопроса", "ключ задачи", "ключ", "kalit", "masala kaliti"],
    "type": ["issue type", "type", "issuetype",
             "тип задачи", "тип запроса", "тип", "tur", "masala turi"],
    "status": ["status", "статус", "holat"],
    "summary": ["summary", "title", "тема", "краткое описание", "резюме", "mavzu", "qisqacha"],
    # PM is graded STRICTLY from the custom "PM" field — never the assignee.
    "pm": ["pm", "project manager", "менеджер проекта", "менеджер", "menejer", "loyiha menejeri"],
    "assignee": ["assignee", "исполнитель", "ответственный", "ijrochi", "mas'ul"],
    "reporter": ["reporter", "creator", "автор", "создатель", "muallif"],
    "created": ["created", "created date", "creation date",
                "создано", "дата создания", "yaratilgan", "yaratilgan sana"],
    "resolved": ["resolved", "resolution date", "resolutiondate", "done date", "completed",
                 "дата решения", "решено", "дата завершения", "hal qilingan", "yakunlangan sana"],
    "due": ["due date", "duedate", "due", "срок", "срок исполнения", "muddat"],
    "updated": ["updated", "обновлено", "обновленo", "yangilangan", "last updated"],
    "resolution": ["resolution", "решение", "resolution name", "hal"],
    "priority": ["priority", "приоритет", "muhimlik"],
    "project_type": ["project type", "тип проекта", "loyiha turi"],
    "regulator": ["требование регулятора", "regulator requirement", "regulator"],
    "division": ["подразделение заказчика", "customer division", "division", "bo'lim"],
    "scoring": ["скоринг-балл", "scoring", "score"],
    "project": ["project", "project key", "project name", "проект", "loyiha"],
    "epic_key": ["epic link", "parent", "parent key", "epic", "parent link",
                 "эпик", "ссылка на эпик", "родитель", "epik"],
    "story_points": ["story points", "story point estimate", "points",
                     "очки истории", "ballar"],
    "history": ["status history", "changelog", "status changes", "history",
                "история статусов", "журнал изменений", "holat tarixi"],
}


def _get(row: dict, field: str) -> str:
    low = {k.lower().strip(): v for k, v in row.items()}
    for a in _ALIASES.get(field, [field]):
        if a in low and str(low[a]).strip():
            return str(low[a]).strip()
    return ""


_UNASSIGNED = {"не назначен", "не назначено", "unassigned", "none", "", "автоматический"}


def _pm(row: dict) -> str:
    """Strictly the custom 'PM' field. Empty -> 'Unassigned' (no assignee fallback)."""
    v = _get(row, "pm").strip()
    if v.lower() in _UNASSIGNED:
        return "Unassigned"
    return v


def _get_links(row: dict) -> list[dict]:
    out = []
    for k, v in row.items():
        kl = k.lower()
        if not v:
            continue
        if "blocks" in kl or "blocked" in kl or "depend" in kl or "link" in kl:
            ltype = "blocks" if "blocks" in kl and "blocked" not in kl else (
                "is blocked by" if "blocked" in kl else "depends on")
            for target in str(v).split("|"):
                target = target.strip()
                if target:
                    out.append({"type": ltype, "target": target})
    return out


# ---- date parsing -----------------------------------------------------------
_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
    "%d/%b/%y %I:%M %p", "%d/%b/%Y %I:%M %p", "%d/%b/%y", "%d/%b/%Y",
    "%m/%d/%Y %H:%M", "%m/%d/%Y", "%d.%m.%Y %H:%M", "%d.%m.%Y", "%d-%m-%Y",
    "%Y/%m/%d",
]


def parse_date(s: str):
    if not s:
        return None
    s = str(s).strip()
    s = s.replace("Z", "").split("+")[0].strip()
    for fmt in _DATE_FORMATS:
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return dt.datetime.fromisoformat(s)
    except Exception:
        return None


def _iso(d):
    return d.isoformat() if isinstance(d, dt.datetime) else None


# ---- status normalization ---------------------------------------------------
# Cyrillic homoglyphs -> Latin (so "Dоne"/"Tеsting"/"Аnаlysis" match EN canonicals)
_HOMO = str.maketrans({
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O",
    "Р": "P", "С": "C", "Т": "T", "Х": "X", "а": "a", "е": "e", "о": "o",
    "с": "c", "р": "p", "х": "x", "у": "y", "к": "k", "м": "m", "т": "t",
})


def canon_status(s: str) -> str:
    raw = (s or "").strip().upper()
    if raw in config.STATUS_SYNONYMS:
        return config.STATUS_SYNONYMS[raw]
    norm = raw.translate(_HOMO)
    return config.STATUS_SYNONYMS.get(norm, norm)


_TYPE = {
    "epic": "Epic",
    "task": "Task", "задача": "Task", "масала": "Task",
    "new feature": "New Feature", "новая функциональность": "New Feature", "yangi funksiya": "New Feature",
    "story": "Story", "история": "Story",
    "sub-task": "Sub-task", "subtask": "Sub-task", "подзадача": "Sub-task",
    "bug": "Bug", "ошибка": "Bug",
}


def canon_type(s: str) -> str:
    return _TYPE.get((s or "").strip().lower(), (s or "Task").strip())


def status_group(s: str) -> str:
    s = canon_status(s)
    if s in config.DISCOVERY_STATUSES:
        return "discovery"
    if s in config.DELIVERY_STATUSES:
        return "delivery"
    if s in config.DECLINED_STATUSES:
        return "declined"
    return "other"


# ---- status history ---------------------------------------------------------
def _parse_history(raw: str, created, resolved, current_status):
    """Return [{status, entered, exited, days}] sorted by entered.

    Accepts a JSON list in the 'Status History' column:
      [{"status": "...", "entered": "ISO", "exited": "ISO"}]
    Falls back to a minimal 2-point history from created/resolved.
    """
    events = []
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                for e in data:
                    st = canon_status(e.get("status", ""))
                    ent = parse_date(e.get("entered") or e.get("from") or e.get("date"))
                    ext = parse_date(e.get("exited") or e.get("to"))
                    if st and ent:
                        events.append([st, ent, ext])
        except Exception:
            events = []

    if not events:
        # Minimal fallback: assume created in first discovery status, ended at resolution.
        if created:
            first = "BACKLOG"
            events.append([first, created, resolved])
        if resolved and current_status:
            events.append([canon_status(current_status), resolved, resolved])

    events.sort(key=lambda x: x[1])
    out = []
    for i, (st, ent, ext) in enumerate(events):
        end = ext
        if end is None:
            end = events[i + 1][1] if i + 1 < len(events) else (resolved or dt.datetime.now())
        days = max(0.0, (end - ent).total_seconds() / 86400.0)
        out.append({"status": st, "entered": _iso(ent), "exited": _iso(end), "days": round(days, 3)})
    return out


# ---- main -------------------------------------------------------------------
def normalize_rows(rows: list[dict], default_project: str = "") -> list[dict]:
    issues = []
    for row in rows:
        key = _get(row, "key")
        if not key:
            continue
        itype = canon_type(_get(row, "type") or "Task")
        status_c = canon_status(_get(row, "status") or "BACKLOG")
        created = parse_date(_get(row, "created"))
        updated = parse_date(_get(row, "updated"))
        resolved = parse_date(_get(row, "resolved"))
        due = parse_date(_get(row, "due"))
        sp = _get(row, "story_points")
        try:
            sp_val = float(sp) if sp else None
        except ValueError:
            sp_val = None

        # Completion / decline from resolution + status
        rl = _get(row, "resolution").strip().lower()
        declined = (status_c in config.DECLINED_STATUSES) or (rl in config.RESOLUTION_DECLINED)
        done = (status_c in config.DONE_STATUSES) or (rl in config.RESOLUTION_DONE)
        if declined:
            status_c = "DECLINED"
            resolved = None
        elif done and not resolved:
            # exports often omit a Resolution Date column -> use Updated as proxy
            resolved = updated or created

        is_epic = itype.strip().lower() in config.EPIC_TYPES
        project = _get(row, "project") or default_project or key.split("-")[0]
        history = _parse_history(_get(row, "history"), created, resolved, status_c)
        issues.append({
            "key": key,
            "project": project,
            "type": itype,
            "is_epic": is_epic,
            "status": status_c,
            "status_group": status_group(status_c),
            "summary": _get(row, "summary"),
            "pm": _pm(row),
            "assignee": _get(row, "assignee"),
            "reporter": _get(row, "reporter"),
            "created": _iso(created),
            "resolved": _iso(resolved),
            "due": _iso(due),
            "epic_key": _get(row, "epic_key"),
            "story_points": sp_val,
            "priority": _get(row, "priority"),
            "project_type": _get(row, "project_type"),
            "regulator": _get(row, "regulator"),
            "division": _get(row, "division"),
            "scoring": _get(row, "scoring"),
            "links": _get_links(row),
            "history": history,
        })
    return issues
