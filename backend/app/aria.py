"""TEMUR — local Portfolio AI agent.

Grounds answers in the computed portfolio analytics (the active dataset).
Provider order: Claude Code CLI (`claude -p`, no API key — uses the user's
existing Claude Code auth) -> Anthropic Claude API (if ANTHROPIC_API_KEY is set)
-> Ollama (if running) -> deterministic grounded fallback. So Temur is "powered
by Claude" with zero setup, and always works offline via the grounded fallback.
LLM outputs for issue summaries/recommendations are cached on disk (ai_cache).
Set TEMUR_MODEL to override the CLI model (default "haiku").
"""
import os
import re
import math
import json
import shutil
import hashlib
import tempfile
import subprocess
import datetime as dt
import urllib.request
from collections import Counter
from . import config

ASSISTANT_NAME = "Temur"

# ---- local memory / self-learning (persisted, grounded) --------------------
_MEM = config.TEMP / "temur_memory.jsonl"
_FACTS = config.TEMP / "temur_facts.json"


def _load_facts() -> list:
    try:
        return json.loads(_FACTS.read_text(encoding="utf-8"))
    except Exception:
        return []


def remember_fact(text: str) -> list:
    facts = _load_facts()
    facts.append({"ts": dt.datetime.now().isoformat(timespec="seconds"), "text": text})
    facts = facts[-200:]
    try:
        _FACTS.write_text(json.dumps(facts, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return facts


def _log_interaction(q: str, a: str):
    try:
        with open(_MEM, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": dt.datetime.now().isoformat(timespec="seconds"),
                                "q": q, "a": (a or "")[:500]}, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _teach_match(q: str):
    m = re.match(r"\s*(?:remember|запомни|запиши|note that|eslab qol|yodda tut|esla)\b[:,]?\s+(.*)",
                 (q or "").strip(), re.I | re.S)
    if not m or not m.group(1).strip():
        return None
    fact = re.sub(r"^(that|что|ki)\s+", "", m.group(1).strip(), flags=re.I)
    return fact.strip() or None

# Path to the local Claude Code CLI (resolved once).
_CLAUDE_EXE = shutil.which("claude")
# Disk cache for LLM outputs so a given issue is only generated once.
_AICACHE = config.TEMP / "ai_cache"


def _claude_cli(prompt: str, cli_model: str | None = None) -> str | None:
    """Use the local Claude Code CLI (headless) as the LLM — NO API key needed.

    Runs `claude -p` in a neutral directory with project/MCP config disabled, so
    it is a fast single-shot text completion that reuses the user's existing
    Claude Code authentication (subscription). This makes Temur "powered by
    Claude" with zero setup — no ANTHROPIC_API_KEY and no Ollama.
    """
    exe = _CLAUDE_EXE or shutil.which("claude")
    if not exe:
        return None
    model = cli_model or os.environ.get("TEMUR_MODEL", "haiku")
    try:
        # Pass the prompt via STDIN, not argv: the npm `claude.CMD` wrapper goes
        # through cmd.exe on Windows, which mangles newlines in a multi-line
        # argument. Piping the prompt on stdin preserves it exactly.
        proc = subprocess.run(
            [exe, "-p", "--model", model,
             "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}'],
            input=prompt, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120, cwd=tempfile.gettempdir(),
        )
        out = (proc.stdout or "").strip()
        return out or None
    except Exception:
        return None


def _cache_key(prompt: str) -> str:
    seed = os.environ.get("TEMUR_MODEL", "haiku") + "|" + prompt
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _cache_get(key: str):
    f = _AICACHE / (key + ".json")
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _cache_put(key: str, val: dict):
    try:
        _AICACHE.mkdir(parents=True, exist_ok=True)
        (_AICACHE / (key + ".json")).write_text(
            json.dumps(val, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _strip_md(s: str) -> str:
    """Remove Markdown so chat text is clean and TTS doesn't read '**'."""
    if not s:
        return s
    s = re.sub(r"\*\*(.*?)\*\*", r"\1", s, flags=re.S)          # **bold**
    s = re.sub(r"__(.*?)__", r"\1", s, flags=re.S)              # __bold__
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", s)  # *italic*
    s = re.sub(r"`{1,3}([^`]*)`{1,3}", r"\1", s)                # `code`
    s = re.sub(r"^\s{0,3}#{1,6}\s*", "", s, flags=re.M)         # # headings
    s = re.sub(r"^\s{0,3}>\s?", "", s, flags=re.M)              # > quotes
    s = re.sub(r"^\s{0,3}[-*+]\s+", "• ", s, flags=re.M)        # - bullets -> •
    return s.strip()


def _llm(prompt: str, cache: bool = False, model: str | None = None, timeout: int | None = None,
         cli_model: str | None = None):
    """Temur's LLM. Primary engine = config.TEMUR_PRIMARY:
      - "claude-cli": Claude Code CLI first (fast + smart, host login), then the
        Anthropic API if a key is set, then local Ollama as the offline fallback.
      - "ollama": fully local; Claude only if TEMUR_ALLOW_ANTHROPIC=1.
    Returns (text, source). cache=True memoises on disk keyed by prompt + model."""
    key = _cache_key((model or config.ARIA_MODEL) + "|" + prompt) if cache else None
    if key:
        hit = _cache_get(key)
        if hit and hit.get("text"):
            return hit["text"], hit.get("source", "cache")
    if config.TEMUR_PRIMARY == "claude-cli":
        out, src = _claude_cli(prompt, cli_model), "claude-cli"
        if not out:
            out, src = _claude(prompt), "claude"
        if not out:
            out, src = _ollama(prompt, model=model, timeout=timeout), "temur-local"
    else:
        out, src = _ollama(prompt, model=model, timeout=timeout), "temur-local"
        if not out and config.ALLOW_ANTHROPIC:
            out, src = _claude(prompt), "claude"
            if not out:
                out, src = _claude_cli(prompt, cli_model), "claude-cli"
    if out:
        out = _strip_md(out)
        if key:
            _cache_put(key, {"text": out, "source": src})
    return out, src


def _claude(prompt: str) -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps({
                "model": os.environ.get("CLAUDE_MODEL", "claude-3-5-haiku-latest"),
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}],
            }).encode(),
            headers={"Content-Type": "application/json", "x-api-key": key,
                     "anthropic-version": "2023-06-01"},
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
            return "".join(b.get("text", "") for b in data.get("content", [])).strip()
    except Exception:
        return None


def _ollama(prompt: str, model: str | None = None, timeout: int | None = None) -> str | None:
    """Local Temur model via Ollama. Generous timeout (CPU inference is slow); the
    persona/params live in the custom Modelfile so we only pass safety options."""
    try:
        req = urllib.request.Request(
            f"{config.OLLAMA_URL}/api/generate",
            data=json.dumps({
                "model": model or config.ARIA_MODEL,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "30m",           # keep the model warm between questions
                "options": {"temperature": 0.2},   # num_ctx/num_predict come from the Modelfile
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout or config.OLLAMA_TIMEOUT) as r:
            return json.loads(r.read()).get("response", "").strip()
    except Exception:
        return None


def ollama_up() -> bool:
    """True if the Ollama server is reachable (fast check)."""
    try:
        with urllib.request.urlopen(f"{config.OLLAMA_URL}/api/tags", timeout=3):
            return True
    except Exception:
        return False


def _context(analytics: dict, kpis: dict) -> str:
    board = analytics["pm_leaderboard"]
    health = analytics["project_health"]
    blockers = analytics["blockers"]
    ttm = analytics["ttm"]["overall"]
    lines = [
        f"Total projects: {kpis['total_portfolio_projects']}, completed: {kpis['completed_projects']}, "
        f"open: {kpis['open_projects']}, declined: {kpis['declined_projects']} "
        f"(completion {kpis['completion_pct']}%).",
        f"Average total TTM: {ttm['avg']} days (median {ttm['median']}, p90 {ttm['p90']}).",
        f"Average lead time: {analytics['lead_time']['avg']} days.",
        f"Portfolio flow efficiency: {analytics['flow']['portfolio_average']}%.",
        f"Blocked items: {blockers['total_blocked']}.",
    ]
    if board:
        lines.append("Top PM: " + ", ".join(
            f"{b['pm']} (score {b['pm_score']}, {b['projects_completed']} done)" for b in board[:3]))
    if health:
        worst = sorted(health, key=lambda h: h["score"])[:3]
        lines.append("Highest-risk projects: " + ", ".join(
            f"{h['key']} ({h['category']} {h['score']})" for h in worst))
    return "\n".join(lines)


def _rule_based(q: str, analytics: dict, kpis: dict) -> str:
    ql = q.lower()
    board = analytics["pm_leaderboard"]
    health = analytics["project_health"]
    blockers = analytics["blockers"]
    noms = analytics["pm_nominations"]

    if "risk" in ql or "highest risk" in ql:
        worst = sorted(health, key=lambda h: h["score"])[:3]
        if worst:
            return "Highest-risk projects: " + "; ".join(
                f"{h['key']} — {h['summary'] or ''} ({h['category']}, score {h['score']}, "
                f"{h['blocked']} blockers, {h['overdue_children']} overdue)" for h in worst)
    if "best" in ql and ("pm" in ql or "manager" in ql or "perform" in ql):
        if board:
            b = board[0]
            return (f"Best performing PM: {b['pm']} (score {b['pm_score']}, "
                    f"{b['projects_completed']} projects completed, success {b['success_rate']}%, "
                    f"avg TTM {b['avg_ttm']}d).")
    if "ttm" in ql and ("increas" in ql or "why" in ql or "rising" in ql):
        tr = analytics["ttm"]["trend"]
        if len(tr) >= 2:
            return (f"TTM trend: {tr[-2]['period']}={tr[-2]['avg_ttm']}d -> "
                    f"{tr[-1]['period']}={tr[-1]['avg_ttm']}d. Main drivers are time spent in "
                    f"Discovery statuses and blocked dependencies "
                    f"({blockers['total_blocked']} blocked items).")
    if "block" in ql:
        bp = blockers["blocked_projects"][:5]
        if bp:
            return "Blocked projects: " + "; ".join(
                f"{p['key']} (blocked by {', '.join(p['blocked_by'])}, risk {p['risk']})" for p in bp)
        return "No blocked projects detected in the active dataset."
    if "focus" in ql or "management" in ql or "quarter" in ql:
        worst = sorted(health, key=lambda h: h["score"])[:3]
        return ("Management focus this quarter: clear blockers on "
                + ", ".join(h["key"] for h in worst)
                + f"; completion is {kpis['completion_pct']}% with {kpis['open_projects']} open projects.")
    if "fastest" in ql or "lead time" in ql:
        return f"Fastest delivery manager: {noms.get('fastest_delivery_manager', 'n/a')}. Portfolio avg lead time {analytics['lead_time']['avg']}d."
    # default summary
    return (f"Portfolio has {kpis['total_portfolio_projects']} projects, "
            f"{kpis['completion_pct']}% completed, avg TTM {analytics['ttm']['overall']['avg']}d, "
            f"flow efficiency {analytics['flow']['portfolio_average']}%, "
            f"{blockers['total_blocked']} blocked items.")


def _extractive(text: str, n: int = 4) -> str:
    import re
    sents = re.split(r"(?<=[.!?。])\s+|\n+", text)
    sents = [s.strip(" -•\t") for s in sents if len(s.strip()) > 18]
    return " ".join(sents[:n])


def summarize_issue(issue: dict) -> dict:
    """AI summary of an issue from its Quarterly status field + comments."""
    qs = (issue.get("quarterly_status") or "").strip()
    comments = issue.get("comments") or []
    ctext = "\n".join(f"[{c.get('date','')}] {c.get('author','')}: {c.get('text','')}"
                      for c in comments).strip()
    combined = (qs + "\n\n" + ctext).strip()
    if not combined:
        return {"summary": "", "source": "none", "comments_count": 0}

    prompt = (
        f"You are {ASSISTANT_NAME}, a senior PMO analyst. Below is a Jira portfolio "
        "issue's QUARTERLY STATUS report and its COMMENTS. Do NOT copy or paraphrase "
        "sentences verbatim — ANALYZE them. Produce a tight executive summary (3-4 "
        "sentences max) that explicitly covers, in this order: (1) current progress / "
        "where the work really stands, (2) the key blocker or risk, (3) the most "
        "important next step to close it. Be specific and factual; if the source is "
        "thin, say what is unknown rather than inventing detail. Answer in the same "
        "language as the source. Output plain prose only — NO Markdown, no headings, "
        "no '#' or '*' or bold.\n\n"
        f"QUARTERLY STATUS:\n{qs[:4000]}\n\nCOMMENTS:\n{ctext[:4000]}\n\nSUMMARY:"
    )
    out, source = _llm(prompt, cache=True)
    if not out:
        out, source = _extractive(qs or ctext), "extractive"
    return {"summary": out, "source": source, "comments_count": len(comments)}


# --------------------------- issue recommendation ---------------------------
def _issue_facts(issue: dict):
    """Derive the grounded signals used to advise on an open issue."""
    from .metrics import engines as E
    status = issue.get("status", "")
    group = issue.get("status_group", "")
    age = None
    c = E._d(issue.get("created"))
    if c:
        age = (dt.datetime.now() - c).days
    overdue_days = None
    due = E._d(issue.get("due"))
    if due:
        delta = (dt.datetime.now() - due).days
        overdue_days = delta if delta > 0 else None
    blockers = [l for l in (issue.get("links") or [])
                if "block" in (l.get("type") or "").lower()]
    comments = issue.get("comments") or []
    return status, group, age, overdue_days, blockers, comments


def _rule_recommend(status, group, age, overdue_days, blockers, comments, qs) -> str:
    """Deterministic, grounded recommendations when no LLM is available."""
    recs = []
    stage_step = {
        "discovery": (f"Move it out of '{status}': lock scope and acceptance criteria, "
                      "then schedule the analysis/validation sign-off this week so it can "
                      "enter delivery."),
        "delivery": (f"Drive '{status}' to Done: confirm the remaining work is estimated, "
                     "assign a single clear owner, and set a committed completion date."),
        "other": (f"Re-triage it out of '{status}': decide whether it belongs in an active "
                  "discovery or delivery stage, or should be declined."),
    }
    recs.append(stage_step.get(group, stage_step["other"]))

    if blockers:
        recs.append("Clear blocking dependencies first ("
                    + ", ".join(b.get("target", "?") for b in blockers)
                    + ") — raise them at the next stand-up and get owners committed.")
    else:
        recs.append("No formal blockers are recorded — if work is stalled, capture the real "
                    "impediment as a linked blocker so it gets management visibility.")

    if overdue_days:
        recs.append(f"It is {overdue_days} days past its due date — escalate to the PM/"
                    "sponsor and agree a realistic revised date now.")
    elif age is not None and age > 90:
        recs.append(f"It has been open {age} days without resolution — review whether to "
                    "split, de-scope, or decline it to stop aging WIP.")

    if not comments:
        recs.append("There is no discussion on record — request a written status update from "
                    "the assignee so progress is auditable.")
    else:
        recs.append("Follow up on the latest comment thread and convert any open questions "
                    "into action items with named owners and dates.")

    if not (qs or "").strip():
        recs.append("Quarterly status is empty — fill it in so leadership can see progress, "
                    "risks and the path to close.")

    return "\n".join(f"• {r}" for r in recs)


def recommend_issue(issue: dict) -> dict:
    """Concrete recommendations on how to successfully CLOSE an open issue.

    Grounds on current status/stage, age, overdue, blockers, comments and the
    quarterly status. Claude -> Ollama -> deterministic grounded fallback.
    """
    status, group, age, overdue_days, blockers, comments = _issue_facts(issue)
    qs = (issue.get("quarterly_status") or "").strip()
    ctext = "\n".join(f"[{c.get('date', '')}] {c.get('author', '')}: {c.get('text', '')}"
                      for c in comments[-8:]).strip()

    owner = (issue.get("owner") or "").strip()
    change_leader = (issue.get("change_leader") or "").strip()
    # Long-stalled in an early stage → the market demand may no longer be real.
    from .metrics import engines as _E
    stage_age = _E._age_days(issue)
    _stuck = (not _E.is_done(issue) and (status or "").upper() in _E.STUCK_STAGES
              and stage_age is not None and stage_age >= 100)
    facts = [
        f"Key: {issue.get('key')}",
        f"Summary: {issue.get('summary', '')}",
        f"Type: {issue.get('type')}",
        f"Current status: {status} (stage: {group or 'unknown'})",
        f"OWNER (владелец — the business owner/initiator ACCOUNTABLE for this item): "
        f"{owner or 'not set'}",
        f"CHANGE LEADER (stakeholder driving it — advise THEM on stop/continue): "
        f"{change_leader or 'not set'}",
        f"Owner department: {issue.get('owner_department') or 'n/a'}",
        f"PM: {issue.get('pm')}; Assignee: {issue.get('assignee') or 'unassigned'}",
        f"Priority: {issue.get('priority') or 'n/a'}",
        f"Age since created: {age if age is not None else 'unknown'} days",
        f"Days in the CURRENT stage: {stage_age if stage_age is not None else 'unknown'}",
    ]
    if _stuck:
        facts.append(
            f"STALLED: this item has sat {stage_age} days in the early '{status}' stage "
            "without moving — a red flag that it may be stale or no longer a market priority.")
    if overdue_days:
        facts.append(f"OVERDUE by {overdue_days} days (past the due date)")
    if blockers:
        facts.append("Blocking dependencies: "
                     + ", ".join(f"{b.get('type')} {b.get('target')}" for b in blockers))
    facts.append(f"Comments on record: {len(comments)}")
    factstr = "\n".join(facts)

    owner_rule = (
        f"The OWNER of this item is {owner}. This person is accountable and must drive the work — "
        f"address the action items to {owner} by name (e.g. \"{owner} should…\"). "
        if owner else
        "No owner (владелец) is set — the FIRST recommendation must be to assign an accountable "
        "owner, since without one the item cannot be driven to completion. ")

    stuck_rule = ""
    if _stuck:
        who = change_leader or owner or "the change leader"
        stuck_rule = (
            f"IMPORTANT — this item has been STALLED {stage_age} days in the early '{status}' stage. "
            "Do NOT just suggest 'push it forward'. Recommend: (1) hand it to BUSINESS ANALYSIS to "
            "re-verify whether the market demand / regulatory need is STILL actual (check competitors, "
            "current market, whether the original problem still exists); (2) based on that, advise "
            f"{who} (the change leader) with an explicit STOP-or-CONTINUE decision — if the demand is "
            "gone, recommend declining/parking it to stop wasting capacity; if still valid, give the "
            "concrete unblocking step and a committed restart date. Make the stop/continue call the "
            "CENTRAL recommendation. ")

    # Pull the bank's regulations relevant to THIS item so the advice checks
    # compliance and follows the mandated process (committee, scoring, stages…).
    reg = ""
    try:
        from app import rag
        rb = rag.context_block(
            f"{issue.get('type','')} {issue.get('summary','')} "
            "порядок управления проектами проектный комитет владелец этапы паспорт продукта", k=5)
        if rb:
            reg = "\n\nBANK REGULATIONS (official documents — the process the item MUST follow):\n" + rb
    except Exception:
        pass

    prompt = (
        f"You are {ASSISTANT_NAME}, a senior PMO delivery advisor. The Jira issue below "
        "is still OPEN. Using the facts, the quarterly status, the latest comments and the "
        "BANK REGULATIONS below, give 3-5 SPECIFIC, actionable recommendations to move it to "
        "successful completion THE WAY THE REGULATIONS REQUIRE. "
        f"{owner_rule}{stuck_rule}"
        "Check the item against the regulations: is it following the mandated process (project "
        "committee, scoring, required stages/artifacts, approvals)? If a required step is missing "
        "or done out of order, say so and give the compliant next step, citing the document by "
        "name. Cover: the immediate next step for its stage, clearing blockers, the main risk, and "
        "WHO should act (the owner). Answer in the same language as the source. Output 3-5 "
        "plain-text bullet lines, each starting with '- ' — NO Markdown, no '#', no '*'. "
        "No preamble, do not restate the raw data.\n\n"
        f"ISSUE FACTS:\n{factstr}\n\nQUARTERLY STATUS:\n{qs[:2500]}\n\n"
        f"LATEST COMMENTS:\n{ctext[:2000]}{reg}\n\nRECOMMENDATIONS:"
    )
    out, source = _llm(prompt, cache=True)
    if not out:
        out = _rule_recommend(status, group, age, overdue_days, blockers, comments, qs)
        source = "grounded"
    return {"recommendation": out, "source": source, "status": status,
            "age_days": age, "blockers": len(blockers)}


# --------------------- epic-quality recommendation --------------------------
# Plain-language description of each problem type, per language. Used both to
# build the LLM brief and as the deterministic grounded fallback.
_PROBLEM_TEXT = {
    "summary_missing":      {"en": "the title is empty",
                              "ru": "не заполнено название",
                              "uz": "sarlavha bo'sh"},
    "summary_placeholder":  {"en": "the title is a placeholder/test value, not a real project name",
                              "ru": "название — заглушка/тестовое значение, а не реальное имя проекта",
                              "uz": "sarlavha haqiqiy loyiha nomi emas, balki test/qoralama qiymat"},
    "summary_short":        {"en": "the title is too short to be meaningful",
                              "ru": "название слишком короткое и неинформативное",
                              "uz": "sarlavha juda qisqa va ma'nosiz"},
    "description_missing":  {"en": "there is no description at all",
                              "ru": "полностью отсутствует описание",
                              "uz": "tavsif umuman yo'q"},
    "description_placeholder": {"en": "the description is a placeholder/test text",
                              "ru": "описание — заглушка/тестовый текст",
                              "uz": "tavsif test/qoralama matn"},
    "description_link_only": {"en": "the description is only a link, with no explanatory text",
                              "ru": "описание содержит только ссылку без пояснительного текста",
                              "uz": "tavsifda faqat havola bor, izohlovchi matn yo'q"},
    "description_short":    {"en": "the description is too short to explain the goal and scope",
                              "ru": "описание слишком короткое, не раскрывает цель и объём работ",
                              "uz": "tavsif juda qisqa, maqsad va ko'lamni ochib bermaydi"},
    "missing_pm":           {"en": "no Project Manager (PM) is assigned",
                              "ru": "не назначен менеджер проекта (PM)",
                              "uz": "loyiha menejeri (PM) tayinlanmagan"},
    "missing_due":          {"en": "no due date is set",
                              "ru": "не указан срок (due date)",
                              "uz": "muddat (due date) ko'rsatilmagan"},
    "missing_division":     {"en": "the customer division is not filled",
                              "ru": "не заполнено подразделение заказчика",
                              "uz": "buyurtmachi bo'limi to'ldirilmagan"},
    "missing_scoring":      {"en": "the scoring is not done (empty or 0)",
                              "ru": "не проставлен скоринг-балл (пусто или 0)",
                              "uz": "skoring-ball qo'yilmagan (bo'sh yoki 0)"},
    "missing_project_type": {"en": "the project type is not set",
                              "ru": "не указан тип проекта",
                              "uz": "loyiha turi ko'rsatilmagan"},
}

_EQ_FIX = {
    "ru": {
        "summary_missing": "задайте чёткое название проекта (что и для кого делается)",
        "summary_placeholder": "замените тестовое название на реальное название проекта",
        "summary_short": "расширьте название, чтобы из него была понятна суть проекта",
        "description_missing": "добавьте описание на 3–5 предложений: цель, объём работ и ожидаемый результат",
        "description_placeholder": "замените заглушку реальным описанием: цель, объём, ожидаемый результат",
        "description_link_only": "добавьте текстовое описание помимо ссылки: цель, объём, результат",
        "description_short": "дополните описание: цель, объём работ, критерии готовности",
        "missing_pm": "назначьте менеджера проекта (PM)",
        "missing_due": "укажите срок выполнения (due date)",
        "missing_division": "укажите подразделение заказчика",
        "missing_scoring": "проставьте скоринг-балл",
        "missing_project_type": "укажите тип проекта",
    },
    "en": {
        "summary_missing": "set a clear project title (what is built and for whom)",
        "summary_placeholder": "replace the test title with the real project name",
        "summary_short": "expand the title so the project's purpose is clear",
        "description_missing": "add a 3–5 sentence description: goal, scope and expected outcome",
        "description_placeholder": "replace the placeholder with a real description: goal, scope, outcome",
        "description_link_only": "add explanatory text besides the link: goal, scope, outcome",
        "description_short": "expand the description: goal, scope of work, definition of done",
        "missing_pm": "assign a Project Manager (PM)",
        "missing_due": "set a due date",
        "missing_division": "fill in the customer division",
        "missing_scoring": "complete the scoring",
        "missing_project_type": "set the project type",
    },
    "uz": {
        "summary_missing": "aniq loyiha nomini qo'ying (nima va kim uchun qilinmoqda)",
        "summary_placeholder": "test nomni haqiqiy loyiha nomi bilan almashtiring",
        "summary_short": "nomni kengaytiring, loyiha mohiyati tushunarli bo'lsin",
        "description_missing": "3–5 gaplik tavsif qo'shing: maqsad, ish ko'lami va kutilgan natija",
        "description_placeholder": "qoralamani haqiqiy tavsif bilan almashtiring: maqsad, ko'lam, natija",
        "description_link_only": "havoladan tashqari izoh matnini qo'shing: maqsad, ko'lam, natija",
        "description_short": "tavsifni to'ldiring: maqsad, ish ko'lami, tayyorlik mezonlari",
        "missing_pm": "loyiha menejerini (PM) tayinlang",
        "missing_due": "bajarilish muddatini (due date) ko'rsating",
        "missing_division": "buyurtmachi bo'limini ko'rsating",
        "missing_scoring": "skoring-ballni qo'ying",
        "missing_project_type": "loyiha turini ko'rsating",
    },
}

_EQ_TMPL = {
    "ru": {"greet": "Здравствуйте, {who}!",
           "intro": "По недавно созданному эпику {key} «{title}» есть замечания по оформлению — просьба доработать:",
           "outro": "Пожалуйста, дополните карточку, чтобы эпик можно было корректно взять в работу. Спасибо!"},
    "en": {"greet": "Hello, {who}!",
           "intro": "The recently created epic {key} \"{title}\" needs some cleanup — please update the following:",
           "outro": "Please complete the card so the epic can be picked up correctly. Thank you!"},
    "uz": {"greet": "Assalomu alaykum, {who}!",
           "intro": "Yaqinda yaratilgan {key} «{title}» epigida rasmiylashtirish bo'yicha kamchiliklar bor — to'ldirishingizni so'raymiz:",
           "outro": "Iltimos, kartochkani to'ldiring, shunda epikni to'g'ri ishga olish mumkin bo'ladi. Rahmat!"},
}


def _eq_grounded(epic, problems, L):
    fix = _EQ_FIX.get(L, _EQ_FIX["ru"])
    tmpl = _EQ_TMPL.get(L, _EQ_TMPL["ru"])
    who = (epic.get("reporter") or "").strip() or {"ru": "коллега", "en": "colleague", "uz": "hamkasb"}[L]
    title = (epic.get("summary") or "").strip() or {"ru": "(без названия)", "en": "(untitled)", "uz": "(nomsiz)"}[L]
    # de-dup fix lines, keep order, high-severity first
    seen, lines = set(), []
    for sev in ("high", "med", "low"):
        for p in problems:
            if p["severity"] != sev:
                continue
            f = fix.get(p["type"])
            if f and f not in seen:
                seen.add(f)
                lines.append(f"- {f[0].upper()}{f[1:]}.")
    body = "\n".join(lines)
    return (f"{tmpl['greet'].format(who=who)}\n\n"
            f"{tmpl['intro'].format(key=epic.get('key',''), title=title)}\n\n"
            f"{body}\n\n{tmpl['outro']}")


def recommend_epic_quality(epic, problems, lang="ru") -> dict:
    """Draft the message a PM can forward to the epic's author to get the card
    fixed. Specific to the detected problems, professional and constructive.
    LLM (cached) -> deterministic grounded fallback. PM's reputation depends on
    this being concrete and correct, so the brief is fully grounded."""
    L = lang if lang in ("en", "ru", "uz") else "ru"
    if not problems:
        msg = {"ru": "Замечаний по оформлению нет — эпик заполнен корректно.",
               "en": "No quality issues — the epic is filled in correctly.",
               "uz": "Kamchilik yo'q — epik to'g'ri to'ldirilgan."}[L]
        return {"recommendation": msg, "source": "grounded", "problems": []}

    who = (epic.get("reporter") or "").strip()
    prob_lines = []
    for p in problems:
        txt = _PROBLEM_TEXT.get(p["type"], {}).get(L) or p["type"]
        prob_lines.append(f"- {txt}")
    probs_str = "\n".join(prob_lines)

    desc = (epic.get("description") or "").strip()
    prompt = (
        f"You are {ASSISTANT_NAME}, a senior PMO project manager. A newly created Jira EPIC has "
        "quality problems in how it was filled in by its author. Write a SHORT, professional and "
        "constructive message that the PM will forward to the author asking them to fix the card. "
        "Address the author by name if given. Be SPECIFIC to the listed problems and tell them "
        "exactly what to add for each (e.g. what a good description must cover: goal, scope, expected "
        "outcome). Do NOT invent facts about the project that are not given. Keep a respectful, "
        "collegial tone — never condescending. Use short bullet lines starting with '- '. "
        f"Write entirely in {_LANG_NAME[L]}. Plain text only — no Markdown, no '#', no '*'.\n\n"
        f"EPIC: {epic.get('key','')} — \"{epic.get('summary','')}\"\n"
        f"AUTHOR: {who or 'unknown'}\n"
        f"CURRENT DESCRIPTION: {desc[:1200] or '(empty)'}\n\n"
        f"PROBLEMS TO ADDRESS:\n{probs_str}\n\nMESSAGE:"
    )
    out, source = _llm(prompt, cache=True)
    if not out:
        out, source = _eq_grounded(epic, problems, L), "grounded"
    return {"recommendation": out, "source": source, "problems": problems}


_STOP = set("the a an of to in on for and or is are was with by from at as this that "
            "и в на по для с от до за из не что как это или а но бы же то так уже еще "
            "va uchun bilan bu ushbu yoki ham emas".split())


def _tokens(s: str) -> list:
    toks = re.findall(r"[0-9a-zA-ZЀ-ӿ]{3,}", (s or "").lower())
    return [w for w in toks if w not in _STOP]


def _issue_text(i: dict) -> str:
    parts = [i.get("summary", ""), i.get("quarterly_status", "")]
    for c in (i.get("comments") or [])[:5]:
        parts.append(c.get("text", ""))
    return " ".join(parts)


def similar_issues(text: str, issues: list, top: int = 6):
    """TF-IDF cosine similarity between a free-text description and the portfolio
    issues (summary + quarterly status + comments). Pure stdlib."""
    docs = [(i, _tokens(_issue_text(i))) for i in issues]
    docs = [(i, tk) for i, tk in docs if tk]
    if not docs:
        return []
    df = Counter()
    for _, tk in docs:
        for w in set(tk):
            df[w] += 1
    N = len(docs)

    def vec(tk):
        tf = Counter(tk)
        n = len(tk)
        return {w: (c / n) * math.log((N + 1) / (df.get(w, 0) + 1) + 1) for w, c in tf.items()}

    q = vec(_tokens(text))
    if not q:
        return []
    qn = math.sqrt(sum(v * v for v in q.values())) or 1.0
    scored = []
    for i, tk in docs:
        d = vec(tk)
        dot = sum(w_v * d.get(w, 0.0) for w, w_v in q.items())
        if dot <= 0:
            continue
        dn = math.sqrt(sum(v * v for v in d.values())) or 1.0
        scored.append((dot / (qn * dn), i))
    scored.sort(key=lambda x: -x[0])
    return [(round(s, 3), i) for s, i in scored[:top]]


def recommend_from_description(text: str, issues: list) -> dict:
    """Analyze a new task/report description, find similar past projects and how
    they were handled, and recommend an approach (LLM -> grounded fallback)."""
    from .metrics import engines as E
    sims = similar_issues(text, issues, top=6)
    similar, ctx_lines = [], []
    for score, i in sims:
        dur = None
        c, r = E._d(i.get("created")), E._d(i.get("resolved"))
        if c and r and r >= c:
            dur = (r - c).days
        done = E.is_done(i)
        qs = (i.get("quarterly_status") or "").strip()
        similar.append({"key": i["key"], "summary": i.get("summary", ""), "status": i["status"],
                        "is_done": done, "duration_days": dur, "pm": i.get("pm"), "score": score})
        ctx_lines.append(
            f"- {i['key']} [{'DONE' if done else i['status']}]"
            f"{' in ' + str(dur) + 'd' if dur is not None else ''}: {i.get('summary', '')}"
            + (f" | note: {qs[:200]}" if qs else ""))
    ctx = "\n".join(ctx_lines) if ctx_lines else "(no similar issues found)"

    prompt = (
        f"You are {ASSISTANT_NAME}, a PMO delivery advisor. A NEW task/report is described below. "
        "Using the SIMILAR PAST PROJECTS from this portfolio (with their outcome, duration and status "
        "notes), advise concisely: (1) which past projects are most relevant and what to reuse from how "
        "they were handled, (2) a realistic effort/duration estimate based on them, (3) the main risks, "
        "(4) concrete next steps. Reference the issue keys. Plain text, no Markdown, answer in the same "
        f"language as the input.\n\nNEW TASK:\n{text[:3000]}\n\nSIMILAR PAST PROJECTS:\n{ctx}\n\nADVICE:")
    out, source = _llm(prompt)
    if not out:
        done = [s for s in similar if s["is_done"] and s["duration_days"] is not None]
        if done:
            avg = round(sum(s["duration_days"] for s in done) / len(done))
            out = ("Most similar completed projects: "
                   + "; ".join(f"{s['key']} ({s['duration_days']}d)" for s in done[:4])
                   + f". Reuse their delivery approach; expected duration ≈ {avg} days. "
                   "Confirm scope, assign an owner and set milestones.")
        else:
            out = ("No closely matching completed projects found — treat this as a new initiative: "
                   "define scope and acceptance criteria, assign a PM, and set clear milestones.")
        source = "grounded"
    return {"recommendation": out, "source": source, "similar": similar}


_MONTHS = {
    "january": 1, "jan": 1, "январ": 1, "yanvar": 1,
    "february": 2, "feb": 2, "феврал": 2, "fevral": 2,
    "march": 3, "mar": 3, "март": 3, "mart": 3,
    "april": 4, "apr": 4, "апрел": 4, "aprel": 4,
    "may": 5, "май": 5, "may": 5,
    "june": 6, "jun": 6, "июн": 6, "iyun": 6,
    "july": 7, "jul": 7, "июл": 7, "iyul": 7,
    "august": 8, "aug": 8, "август": 8, "avgust": 8,
    "september": 9, "sep": 9, "сентябр": 9, "sentabr": 9,
    "october": 10, "oct": 10, "октябр": 10, "oktabr": 10,
    "november": 11, "nov": 11, "ноябр": 11, "noyabr": 11,
    "december": 12, "dec": 12, "декабр": 12, "dekabr": 12,
}


# Action verbs (EN/RU/UZ + latin-typed Russian) that signal the user wants the
# UI to DO something (open / show / switch...) rather than asking a question.
_VERB_RE = (r"ko'?rsat|курсат|chiqar|ochib|\boch\b|oching|o'?tkaz|\bo'?t\b|show|open|"
            r"go to|switch|покаж|показ|открой|откры|перейд|переключ|вывед|выведи|"
            r"\blist\b|ro'?yxat|руйхат|otkro|otkri|pokaj|pokazh|pakaj|vived|pereyd")

# Pipeline statuses for drill-by-status ("show projects in testing").
_STATUS_PATTERNS = [
    (r"backlog|бэклог|беклог", "BACKLOG"),
    (r"validat|валидац", "VALIDATION"),
    (r"анализе|tahlil bosqich", "ANALYSIS"),
    (r"architect|архитектур|arxitektur", "ARCHITECTURE REVIEW"),
    (r"initiat|инициац", "INITIATION"),
    (r"in progress|в процессе|jarayonda", "IN PROGRESS"),
    (r"testing|тестиров|test(?:da|dagi)\b", "TESTING"),
    (r"pilot|пилот", "PILOT IO"),
]


def detect_action(question: str, pm_names: list | None = None, last_action: dict | None = None,
                  history: list | None = None):
    """Map a natural-language request to a dashboard UI action. Deterministic,
    multilingual (EN/RU/UZ). Returns an action dict or None. This is what lets
    Temur 'drive' the dashboard: switch pages (dashboard/calendar/risk), open
    popups (TTM, kanban, risk panels, issue details, admin, data/epic quality,
    analyze), apply filters (year / quarter / month / day / type / PM / status /
    period), and control theme, language and celebrations."""
    ql = " " + (question or "").lower() + " "

    def has(*xs):
        return any(x in ql for x in xs)

    def w(*pats):
        return any(re.search(p, ql) for p in pats)

    verb = re.search(_VERB_RE, ql) is not None

    # ---- shared time parsing: year / quarter / month / day ----
    year, month_num, day = None, None, None
    fm = re.search(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b", ql)
    if fm:
        year, month_num, day = fm.group(1), int(fm.group(2)), int(fm.group(3))
    else:
        ym = re.search(r"\b(20\d{2})\b", ql)
        if ym:
            year = ym.group(1)
        mm = re.search(r"\b(20\d{2})[-/.](\d{1,2})\b", ql)
        if mm:
            month_num = int(mm.group(2))
        else:
            for name, num in _MONTHS.items():
                if name in ql:
                    month_num = num
                    break
        if month_num:
            mo_alt = "|".join(_MONTHS)
            dm = (re.search(r"\b([0-3]?\d)\s*[-–]?\s*(?:" + mo_alt + r")", ql)
                  or re.search(r"(?:" + mo_alt + r")\w*\s+([0-3]?\d)\b", ql))
            if dm:
                d_ = int(dm.group(1))
                if 1 <= d_ <= 31:
                    day = d_
    quarter = None
    qm = re.search(r"q\s*([1-4])|([1-4])\s*-?\s*(?:кв|quarter|chorak|квартал)", ql)
    if qm and year:
        quarter = f"{year}-Q{qm.group(1) or qm.group(2)}"
    month = f"{year}-{month_num:02d}" if (year and month_num) else None

    type_f = "all"
    if has("epic", "эпик", "epik"):
        type_f = "Epic"
    elif has("new feature", "feature", "фич", "новая функц", "yangi funksiya"):
        type_f = "New Feature"

    # ---- close popups / windows ----
    if w(r"\byop\b|yopib|yoping|закрой|закрыть|close\b") and \
       has("oyna", "окн", "popup", "попап", "modal", "модал", "window", "hammasini", "все", " all "):
        return {"type": "close_popups"}

    # ---- "back" — close whatever is open and return to the dashboard ----
    if w(r"\bnazad\b|назад|\bback\b|orqaga|ortga"):
        return {"type": "back"}

    # ---- "open THEM" — collect the issue keys from Temur's LAST answer and
    # open them together in one drill popup (or the single card directly).
    # "kakie elementi zablokirovannie? otkroy ix" → list of exactly those keys.
    if verb and history and w(r"\bix\b|\bих\b|\bthem\b|ularni|barchasini|vse iz nih|все из них"):
        keys: list = []
        for h in reversed(history):
            if h.get("role") != "user":
                found = re.findall(r"\b([A-Za-z][A-Za-z0-9]+-\d+)\b", str(h.get("text", "")))
                if found:
                    keys = [k.upper() for k in dict.fromkeys(found)]
                    break
        if len(keys) == 1:
            return {"type": "open_issue", "params": {"key": keys[0]}}
        if keys:
            label = ", ".join(keys[:3]) + ("…" if len(keys) > 3 else "")
            return {"type": "drill", "params": {"scope": "all", "keys": ",".join(keys[:40])},
                    "scope": "all", "label": label}

    # ---- Temur answer-mode (turbo / fast / smart) ----
    if has("rejim", "режим", "mode") and has("temur", "темур", "javob", "ответ", "answer",
                                             "turbo", "турбо", "smart", "смарт", "flash", "aqlli", "tez"):
        if has("turbo", "турбо"):
            return {"type": "temur_mode", "params": {"mode": "turbo"}}
        if has("smart", "смарт", "aqlli", "pro"):
            return {"type": "temur_mode", "params": {"mode": "smart"}}
        if has("fast", "flash", "tez", "быстр"):
            return {"type": "temur_mode", "params": {"mode": "fast"}}

    # ---- theme (dark / light) ----
    if w(r"\btema|\btheme|rejim|режим|\bmode\b|тему\b|тема\b|темн|тёмн"):
        if has("dark", "тёмн", "темн", "qorong", "tungi", "night", "qora "):
            return {"type": "theme", "params": {"mode": "dark"}}
        if has("light", "светл", "yorug", "kunduz", "oq "):
            return {"type": "theme", "params": {"mode": "light"}}
        if has("almashtir", "смени", "переключ", "toggle", "o'zgartir", "ozgartir"):
            return {"type": "theme", "params": {"mode": "toggle"}}

    # ---- UI language ----
    if has(" til", "tilga", "tilida", "язык", "language") or \
       w(r"inglizchaga|ruschaga|o'?zbekchaga|на английск|на русск|на узбекск|to english|to russian|to uzbek"):
        if has("ingliz", "english", "англий"):
            return {"type": "set_lang", "params": {"lang": "en"}}
        if has("rus", "русск", "russian"):
            return {"type": "set_lang", "params": {"lang": "ru"}}
        if has("o'zbek", "ozbek", "узбек", "uzbek"):
            return {"type": "set_lang", "params": {"lang": "uz"}}

    # ---- celebrations (confetti) toggle ----
    if has("konfetti", "конфетти", "celebrat", "поздравл", "bayram", "tabrik"):
        on = has("yoq", "включ", " on ", "enable")
        off = has("o'chir", "ochir", "выключ", "отключ", " off ", "disable")
        return {"type": "celebrations", "params": {"mode": "on" if on else "off" if off else "toggle"}}

    # ---- calendar page (+ mode / granularity / date filters) ----
    if has("kalendar", "календар", "calendar", "taqvim"):
        p = {}
        if has("yaratilgan", "создан", "created", "ochilgan"):
            p["mode"] = "created"
        elif has("yopilgan", "yakunlangan", "закрыт", "заверш", "resolved", "tugatilgan", "выполн"):
            p["mode"] = "resolved"
        if w(r"kunlik|по дням|day view|kun ko'?rinish"):
            p["gran"] = "day"
        elif w(r"haftalik|hafta\b|недел|week"):
            p["gran"] = "week"
        elif w(r"\boy(?:lik|ni|ga|da)?\b|месяц|month"):
            p["gran"] = "month"
        elif w(r"yillik|\byil\b|год|year"):
            p["gran"] = "year"
        cal_year = year or str(dt.datetime.now().year)
        if has("bugun", "today", "сегодня"):
            p["today"] = True
            p.setdefault("gran", "day")
        elif month_num:
            p["date"] = f"{cal_year}-{month_num:02d}-{(day or 1):02d}"
            # a bare "2025 yil/год" match must not override the month/day focus
            if day:
                p["gran"] = "day"
            elif p.get("gran") in (None, "year"):
                p["gran"] = "month"
        elif year:
            p["date"] = f"{year}-01-01"
            p.setdefault("gran", "year")
        if has("keyingi", "next ", "следующ"):
            p["step"] = 1
        elif has("oldingi", "previous", "предыдущ", "прошл"):
            p["step"] = -1
        if has("kattalashtir", "zoom in", "приблиз", "yaqinlashtir"):
            p["zoom"] = 1
        elif has("kichiklashtir", "zoom out", "отдал", "uzoqlashtir"):
            p["zoom"] = -1
        return {"type": "calendar", "params": p}

    # ---- kanban board ----
    if has("kanban", "канбан", "доск", "taxta") or w(r"\bboard\b"):
        return {"type": "open_kanban"}

    # ---- change leaders analytics (workload per stakeholder + stuck items) ----
    if has("change leader", "чендж лидер", "ченж лидер", "чейндж", "стейкхолдер",
           "steykxolder", "change-leader", "лидер изменен") or \
       (has("qotib", "qotgan", "застрял", "stalled", "stuck", "yotgan", "yotib") and
            has("epik", "epic", "эпик", "loyiha", "проект", "feature", "фич")):
        return {"type": "open_change_leaders"}

    # ---- issue detail: Jira key(s) explicitly referenced ----
    kms = re.findall(r"\b([a-z]{2,}-\d+)\b", ql)
    if len(kms) > 1:
        keys = [k.upper() for k in dict.fromkeys(kms)]
        return {"type": "drill", "params": {"scope": "all", "keys": ",".join(keys[:40])},
                "scope": "all", "label": ", ".join(keys[:3]) + ("…" if len(keys) > 3 else "")}
    if kms:
        return {"type": "open_issue", "params": {"key": kms[0].upper()}}

    # ---- TTM: dashboard trend panel or the analysis modal ----
    if has("ttm", "time to market", "ттм", "lead time", "лид тайм", "цикл", "длительност", "davomiylik"):
        if has("trend", "тренд", "tren ", "trent"):
            p = {}
            if w(r"\boylik|месяц|month"):
                p["gran"] = "month"
            elif w(r"chorak|квартал|quarter|kvartal"):
                p["gran"] = "quarter"
            elif w(r"yillik|год|year"):
                p["gran"] = "year"
            if type_f != "all":
                p["type"] = type_f
            if has("chiziq", "лини", "line", "graph"):
                p["view"] = "graph"
            elif has("ustun", "столб", "bar"):
                p["view"] = "bar"
            if has("2026 dan", "from 2026", "с 2026"):
                p["scope"] = "start"
            elif has("barcha yillar", "all years", "все годы", "hamma yillar"):
                p["scope"] = "full"
            return {"type": "ttm_panel", "params": p}
        if month:
            period, value = "month", month
        elif quarter:
            period, value = "quarter", quarter
        elif year:
            period, value = "year", year
        else:
            period, value = "all", ""
        return {"type": "open_ttm", "params": {"type": type_f, "period": period, "value": value}}

    # ---- data quality / new-epic quality ----
    if has("data qual", "sifat", "качеств", "field coverage", "покрыти", "qamrov"):
        if has("epik", "epic", "эпик"):
            return {"type": "open_eq"}
        return {"type": "open_dq"}
    if has("yangi epik", "new epic", "новые эпик", "новых эпик", "epic quality", "оформлени"):
        return {"type": "open_eq"}

    # ---- admin panel (frontend shows it only for admins) ----
    if has("admin", "админ") or (has("foydalanuvch", "пользовател", " user") and
                                 has("qo'sh", "qosh", "add", "добав", "parol", "парол", "password",
                                     "o'chir", "ochir", "удал", "delete", "boshqar", "manage", "panel")):
        return {"type": "open_admin"}

    # ---- analyze a new task / report against the portfolio ----
    if (has("analyze", "tahlil", "анализ") and has("yangi", "new ", "нов", "matn", "text",
                                                   "hisobot", "report", "отчет", "отчёт")) or \
       has("o'xshash loyiha", "oxshash loyiha", "similar project", "похожие проект"):
        return {"type": "open_analyze"}

    # ---- risk page: methodology / cohorts / panels / navigation ----
    if has("metodolog", "методолог", "methodology", "uslubiyat"):
        return {"type": "risk", "params": {"methodology": True}}
    if verb:
        if has("kritik", "critical", "критич", "kritich"):
            return {"type": "risk", "params": {"cohort": "critical"}}
        if has("xavf ostida", "at risk", "риском", "риске", "riskli", "pod riskom", "riskom"):
            return {"type": "risk", "params": {"cohort": "at_risk"}}
        if has("kechik", "delayed", "задерж", "запозд", "zaderj"):
            return {"type": "risk", "params": {"cohort": "delayed"}}
        if has("muddati o'tgan", "muddati otgan", "overdue", "просроч", "prosroch"):
            return {"type": "risk", "params": {"cohort": "overdue"}}
        if has("bloklangan", "blocked", "блокир", "blokirov", "blakirov", "zablokir", "zablakir"):
            return {"type": "risk", "params": {"cohort": "blocked"}}
        if has(" wip", "вип "):
            return {"type": "risk", "params": {"cohort": "wip"}}
        if has("reyestr", "register", "реестр"):
            return {"type": "risk", "params": {"panel": "register"}}
        if has("aging", "eskirgan", "старе", "qarigan"):
            return {"type": "risk", "params": {"panel": "aging"}}
        if has("heatmap", "хитмап", "issiqlik", "теплов"):
            return {"type": "risk", "params": {"panel": "heatmap"}}
        if has("insight", "инсайт"):
            return {"type": "risk", "params": {"panel": "insights"}}
    if has("risk", "риск", "xavf") and (verb or has("sahifa", "страниц", "page", "монитор", "bo'lim", "панел", "panel")):
        return {"type": "navigate", "params": {"view": "risk"}}

    # ---- navigation: back to the main dashboard ----
    if verb and has("bosh sahifa", "asosiy sahifa", "dashboard", "дашборд", "главн", "portfel sahifa", "портфель", "home"):
        return {"type": "navigate", "params": {"view": "dashboard"}}

    # ---- PM leaderboard period filter ----
    if has("leaderboard", "лидерборд", "reyting", "рейтинг", "лидер"):
        p = None
        if w(r"haftalik|hafta\b|недел|week"):
            p = "week"
        elif w(r"\boylik|месяц|month"):
            p = "month"
        elif w(r"chorak|квартал|quarter|kvartal"):
            p = "quarter"
        elif w(r"yillik|год|year"):
            p = "year"
        elif has("barcha davr", "hammasi", "all time", "за все", "все время"):
            p = "all"
        if p or verb:
            return {"type": "pm_board", "params": {"period": p or "all"}}

    # ---- flow (created vs resolved) panel granularity ----
    if verb and has("oqim", "поток", "flow", "throughput", "yaratilgan va yopilgan", "created vs resolved"):
        p = "month"
        if w(r"chorak|квартал|quarter|kvartal"):
            p = "quarter"
        elif w(r"yillik|год|year"):
            p = "year"
        return {"type": "flow_panel", "params": {"granularity": p}}

    def _drill(prm, label=""):
        if month:
            prm["period"], prm["value"] = "month", month
        elif quarter:
            prm["period"], prm["value"] = "quarter", quarter
        elif year:
            prm["period"], prm["value"] = "year", year
        if type_f != "all" and "type" not in prm:
            prm["type"] = type_f
        a = {"type": "drill", "params": prm, "scope": prm.get("scope", "epics")}
        if prm.get("state"):
            a["state"] = prm["state"]
        if label:
            a["label"] = label
        return a

    # ---- drill: a specific PM's projects / tasks ----
    if pm_names and (verb or has("loyiha", "project", "проект", "vazifa", "task", "задач")):
        for pm in pm_names:
            toks = [tk for tk in re.split(r"[\s.,]+", str(pm).lower())
                    if len(tk) >= 4 and tk not in ("temur",)]
            if toks and any(tk in ql for tk in toks):
                prm = {"scope": "tasks" if has("vazifa", "task", "задач") else "epics", "pm": pm}
                if has("yakunlangan", "completed", "заверш", "tugat", "yopilgan"):
                    prm["state"] = "completed"
                elif has("ochiq", "open", "откры"):
                    prm["state"] = "open"
                return _drill(prm, label=str(pm))

    # ---- drill: free-text topic search ("Islamic bo'yicha vazifalar",
    # "kakie zadachi po islamskomu bankingu") — fuzzy, translit-tolerant ----
    # HOW/WHY/WHAT-ORDER questions are informational (about process/regulations)
    # and must go to the LLM (grounded on the docs), not open a list.
    _is_question = bool(re.search(
        r"\bkak\b|\bqanday\b|qanaqa|\bкак\b|\bпочему\b|\bзачем\b|\bnega\b|"
        r"на\s+как|какой\s+порядок|qanday\s+tartib|tartibi\s+qanday|"
        r"\bчто\s+говорит|\bnima\s+deyil|расскажи|объясни|tushuntir|izohla|"
        r"должен|должн|kerak\b|to'?g'?ri\s+yo'?l|соответству|muvofiq|\bzid\b|"
        r"\bwhy\b|\bhow\b|should\b|according", ql))
    if not _is_question and has(
            "vazifa", "task", "zadach", "задач", "loyiha", "proekt", "проект",
            "project", "epik", "epic", "issue"):
        topic = None
        m1 = re.search(r"([\w'’\-]{4,30}(?:\s+[\w'’\-]{3,20})?)\s+(?:bo'?yicha|buyicha|haqida\w*|tegishli)", ql)
        m2 = re.search(r"(?:\bpo\b|\bпо\b|\babout\b|\bпро\b)\s+([\w'’\-]{3,30}(?:\s+[\w'’\-]{3,20})?)", ql)
        if m1:
            topic = m1.group(1)
        elif m2:
            topic = m2.group(1)
        if topic:
            _tstop = ("yil", "oy", "chorak", "hafta", "year", "month", "quarter", "week",
                      "год", "месяц", "квартал", "недел", "epic", "epik", "эпик", "task",
                      "задач", "zadach", "vazifa", "loyiha", "проект", "proekt", "project",
                      "yakunlang", "заверш", "completed", "tugat", "yopilgan", "ochiq",
                      "открыт", "open", "rad", "отклон", "declin", "shu", "этой", "это")
            words = [w for w in re.split(r"\s+", topic.strip(" ?.!,"))
                     if w and not re.fullmatch(r"20\d{2}", w)
                     and not any(w.startswith(s) for s in _tstop)]
            if words:
                prm = {"scope": "all", "text": " ".join(words[:4])}
                if has("yakunlang", "заверш", "completed", "tugat", "yopilgan"):
                    prm["state"] = "completed"
                elif has("ochiq", "открыт", "open "):
                    prm["state"] = "open"
                return _drill(prm, label=" ".join(words[:4]))

    # ---- drill: by pipeline status ----
    if verb:
        for pat, st in _STATUS_PATTERNS:
            if re.search(pat, ql):
                return _drill({"scope": "epics", "status": st}, label=st)

    # ---- drill-down lists by completion state ----
    if has("declin", "отклон", "отмен", "rad et"):
        return _drill({"scope": "epics", "state": "declined"})
    if has("completed", "complete", "closed", "заверш", "выполн", "yakunlang", "tugat", "tamomlang", "yopilgan"):
        return _drill({"scope": "epics", "state": "completed"})
    if has("open project", "открыт", "ochiq", "в работе", "unfinished", "не заверш"):
        return _drill({"scope": "epics", "state": "open"})

    # ---- contextual refinement: a short follow-up tweaks the LAST action ----
    # "tip epic", "endi 2025", "oylik qil" right after opening TTM / a drill /
    # the calendar should MODIFY that view instead of being treated as a fresh
    # question. The frontend sends the previous action back as last_action.
    # Guard: only SHORT, non-interrogative messages qualify — "2025 da nechta
    # loyiha yopildi?" must stay a question for the LLM, not become a filter.
    _qwords = ("necht", "qancha", "сколько", "how many", "how much", "nega ", "почему",
               "why ", "kim ", "кто ", "who ", "nima ", "что ", "what ", "qaysi", "какой", "which")
    if (last_action and isinstance(last_action, dict)
            and len((question or "").split()) <= 5 and not has(*_qwords)):
        t0 = last_action.get("type")
        p0 = dict(last_action.get("params") or {})
        if t0 == "open_ttm":
            ch = False
            if type_f != "all" and p0.get("type") != type_f:
                p0["type"] = type_f
                ch = True
            elif has("vse", "все", " all ", "hammasi", "barcha tur") and p0.get("type") != "all":
                p0["type"] = "all"
                ch = True
            # bare "q1" after "period 2026" → derive the year from the last filter
            if not quarter and not month:
                qm2 = re.search(r"\bq\s*([1-4])\b|\b([1-4])\s*-?\s*(?:кв|quarter|chorak|квартал)", ql)
                if qm2:
                    ym2 = re.search(r"(20\d{2})", str(p0.get("value") or ""))
                    yy = year or (ym2.group(1) if ym2 else str(dt.datetime.now().year))
                    quarter = f"{yy}-Q{qm2.group(1) or qm2.group(2)}"
            if month:
                p0["period"], p0["value"], ch = "month", month, True
            elif quarter:
                p0["period"], p0["value"], ch = "quarter", quarter, True
            elif year:
                p0["period"], p0["value"], ch = "year", year, True
            if ch:
                p0.setdefault("type", "all")
                p0.setdefault("period", "all")
                p0.setdefault("value", "")
                return {"type": "open_ttm", "params": p0}
        if t0 == "drill":
            ch = False
            if type_f != "all" and p0.get("type") != type_f:
                p0["type"] = type_f
                ch = True
            if month:
                p0["period"], p0["value"], ch = "month", month, True
            elif quarter:
                p0["period"], p0["value"], ch = "quarter", quarter, True
            elif year:
                p0["period"], p0["value"], ch = "year", year, True
            if ch:
                a = {"type": "drill", "params": p0, "scope": p0.get("scope", "epics")}
                if p0.get("state"):
                    a["state"] = p0["state"]
                return a
        if t0 == "calendar":
            p = {}
            if has("yaratilgan", "создан", "created"):
                p["mode"] = "created"
            elif has("yopilgan", "yakunlangan", "закрыт", "resolved"):
                p["mode"] = "resolved"
            if w(r"kunlik|по дням"):
                p["gran"] = "day"
            elif w(r"haftalik|hafta\b|недел|week"):
                p["gran"] = "week"
            elif w(r"\boy(?:lik|ni|ga|da)?\b|месяц|month"):
                p["gran"] = "month"
            elif w(r"yillik|год|year"):
                p["gran"] = "year"
            if has("bugun", "today", "сегодня"):
                p["today"] = True
            elif month_num:
                p["date"] = f"{year or dt.datetime.now().year}-{month_num:02d}-{(day or 1):02d}"
                p.setdefault("gran", "day" if day else "month")
            elif year:
                p["date"] = f"{year}-01-01"
            if has("keyingi", "next ", "следующ"):
                p["step"] = 1
            elif has("oldingi", "previous", "предыдущ", "прошл"):
                p["step"] = -1
            if p:
                return {"type": "calendar", "params": p}
        if t0 == "pm_board":
            p = None
            if w(r"haftalik|hafta\b|недел|week"):
                p = "week"
            elif w(r"\boylik|месяц|month"):
                p = "month"
            elif w(r"chorak|квартал|quarter|kvartal"):
                p = "quarter"
            elif w(r"yillik|год|year"):
                p = "year"
            elif has("hammasi", "все", "all time", "barcha davr"):
                p = "all"
            if p:
                return {"type": "pm_board", "params": {"period": p}}
    return None


_STATE_L = {
    "open": {"en": "open", "ru": "открытые", "uz": "ochiq"},
    "completed": {"en": "completed", "ru": "завершённые", "uz": "yakunlangan"},
    "declined": {"en": "declined", "ru": "отклонённые", "uz": "rad etilgan"},
}


_VIEW_L = {
    "dashboard": {"en": "the portfolio dashboard", "ru": "главный дашборд", "uz": "asosiy dashboard"},
    "calendar": {"en": "the calendar", "ru": "календарь", "uz": "kalendar"},
    "risk": {"en": "the risk monitor", "ru": "риск-монитор", "uz": "risk monitori"},
}
_GRAN_L = {
    "day": {"en": "day", "ru": "день", "uz": "kun"},
    "week": {"en": "week", "ru": "неделя", "uz": "hafta"},
    "month": {"en": "month", "ru": "месяц", "uz": "oy"},
    "quarter": {"en": "quarter", "ru": "квартал", "uz": "chorak"},
    "year": {"en": "year", "ru": "год", "uz": "yil"},
    "all": {"en": "all time", "ru": "всё время", "uz": "barcha davr"},
}
_COHORT_L = {
    "at_risk": {"en": "at-risk projects", "ru": "проекты под риском", "uz": "xavf ostidagi loyihalar"},
    "critical": {"en": "critical projects", "ru": "критичные проекты", "uz": "kritik loyihalar"},
    "delayed": {"en": "delayed projects", "ru": "задержанные проекты", "uz": "kechikkan loyihalar"},
    "overdue": {"en": "overdue tasks", "ru": "просроченные задачи", "uz": "muddati o'tgan vazifalar"},
    "blocked": {"en": "blocked items", "ru": "заблокированные элементы", "uz": "bloklangan elementlar"},
    "wip": {"en": "work in progress", "ru": "работа в процессе", "uz": "ishdagi loyihalar"},
}
_RPANEL_L = {
    "register": {"en": "the risk register", "ru": "реестр рисков", "uz": "risk reyestri"},
    "aging": {"en": "the aging panel", "ru": "панель старения", "uz": "eskirgan ishlar paneli"},
    "heatmap": {"en": "the PM risk heatmap", "ru": "тепловую карту рисков по PM", "uz": "PM risk xaritasi"},
    "insights": {"en": "the insights panel", "ru": "панель инсайтов", "uz": "insaytlar paneli"},
    "blocked": {"en": "the blocked panel", "ru": "панель блокировок", "uz": "bloklanganlar paneli"},
}
_LANG_L = {"en": {"en": "English", "ru": "английский", "uz": "ingliz tili"},
           "ru": {"en": "Russian", "ru": "русский", "uz": "rus tili"},
           "uz": {"en": "Uzbek", "ru": "узбекский", "uz": "o'zbek tili"}}


def _action_message(a: dict, lang: str = "en") -> str:
    L = lang if lang in ("en", "ru", "uz") else "en"
    t = a.get("type")
    p = a.get("params") or {}
    if t == "open_ttm":
        allw = {"en": "all types", "ru": "все типы", "uz": "barcha turlar"}[L]
        scope = p["type"] if p.get("type", "all") != "all" else allw
        per = f" · {p['value']}" if p.get("value") else ""
        return {"en": f"Opening TTM analysis ({scope}{per}).",
                "ru": f"Открываю анализ TTM ({scope}{per}).",
                "uz": f"TTM tahlilini ochyapman ({scope}{per})."}[L]
    if t == "ttm_panel":
        g = _GRAN_L.get(p.get("gran", ""), {}).get(L, "")
        return {"en": f"Adjusting the TTM trend panel{f' ({g})' if g else ''}.",
                "ru": f"Настраиваю панель тренда TTM{f' ({g})' if g else ''}.",
                "uz": f"TTM trend panelini sozlayapman{f' ({g})' if g else ''}."}[L]
    if t == "drill":
        who = a.get("label")
        if who:
            return {"en": f"Showing the list for {who}.",
                    "ru": f"Показываю список: {who}.",
                    "uz": f"{who} bo'yicha ro'yxatni ko'rsatyapman."}[L]
        st = _STATE_L.get(a.get("state", ""), {}).get(L, a.get("state", ""))
        per = a.get("params", {}).get("value", "")
        per = f" · {per}" if per else ""
        return {"en": f"Showing {st} portfolio projects{per}.",
                "ru": f"Показываю {st} проекты портфеля{per}.",
                "uz": f"{st} portfel loyihalarini ko'rsatyapman{per}."}[L]
    if t == "open_issue":
        k = p.get("key", "")
        return {"en": f"Opening issue {k}.", "ru": f"Открываю задачу {k}.",
                "uz": f"{k} masalasini ochyapman."}[L]
    if t == "open_dq":
        return {"en": "Opening the data-quality panel.",
                "ru": "Открываю панель качества данных.",
                "uz": "Ma'lumot sifati panelini ochyapman."}[L]
    if t == "open_eq":
        return {"en": "Opening the new-epic quality review.",
                "ru": "Открываю проверку качества новых эпиков.",
                "uz": "Yangi epiklar sifati tekshiruvini ochyapman."}[L]
    if t == "open_admin":
        return {"en": "Opening the admin panel (admins only).",
                "ru": "Открываю админ-панель (только для админа).",
                "uz": "Admin panelni ochyapman (faqat admin uchun)."}[L]
    if t == "open_analyze":
        return {"en": "Opening the new-task analyzer — paste the description there.",
                "ru": "Открываю анализ новой задачи — вставьте туда описание.",
                "uz": "Yangi vazifa tahlilini ochyapman — tavsifni shu yerga joylang."}[L]
    if t == "open_kanban":
        return {"en": "Opening the kanban board.",
                "ru": "Открываю канбан-доску.",
                "uz": "Kanban doskasini ochyapman."}[L]
    if t == "open_change_leaders":
        return {"en": "Opening the change-leaders view (workload + long-stalled items).",
                "ru": "Открываю обзор change leader'ов (загрузка + застрявшие элементы).",
                "uz": "Change leader'lar ko'rinishini ochyapman (yuklama + qotgan elementlar)."}[L]
    if t == "navigate":
        v = _VIEW_L.get(p.get("view", ""), {}).get(L, p.get("view", ""))
        return {"en": f"Opening {v}.", "ru": f"Открываю {v}.", "uz": f"{v.capitalize()}ni ochyapman."}[L]
    if t == "calendar":
        g = _GRAN_L.get(p.get("gran", ""), {}).get(L, "")
        d = p.get("date", "")
        det = " · ".join(x for x in (g, d) if x)
        det = f" ({det})" if det else ""
        return {"en": f"Opening the calendar{det}.",
                "ru": f"Открываю календарь{det}.",
                "uz": f"Kalendarni ochyapman{det}."}[L]
    if t == "risk":
        if p.get("methodology"):
            return {"en": "Opening the risk methodology.",
                    "ru": "Открываю методологию рисков.",
                    "uz": "Risk metodologiyasini ochyapman."}[L]
        if p.get("cohort"):
            c = _COHORT_L.get(p["cohort"], {}).get(L, p["cohort"])
            return {"en": f"Opening {c} on the risk monitor.",
                    "ru": f"Открываю {c} на риск-мониторе.",
                    "uz": f"Risk monitorida {c}ni ochyapman."}[L]
        pn = _RPANEL_L.get(p.get("panel", ""), {}).get(L, p.get("panel", ""))
        return {"en": f"Expanding {pn}.", "ru": f"Разворачиваю {pn}.",
                "uz": f"{pn.capitalize()}ni kattalashtiryapman."}[L]
    if t == "pm_board":
        g = _GRAN_L.get(p.get("period", "all"), {}).get(L, "")
        return {"en": f"Setting the PM leaderboard to: {g}.",
                "ru": f"Ставлю лидерборд PM на период: {g}.",
                "uz": f"PM reytingini {g} davriga o'rnatyapman."}[L]
    if t == "flow_panel":
        g = _GRAN_L.get(p.get("granularity", "month"), {}).get(L, "")
        return {"en": f"Switching the created/resolved flow to: {g}.",
                "ru": f"Переключаю поток создано/закрыто на: {g}.",
                "uz": f"Yaratilgan/yopilgan oqimini {g} kesimiga o'tkazyapman."}[L]
    if t == "theme":
        m = p.get("mode", "toggle")
        return {"en": {"dark": "Switching to dark mode.", "light": "Switching to light mode.",
                       "toggle": "Toggling the theme."}[m],
                "ru": {"dark": "Включаю тёмную тему.", "light": "Включаю светлую тему.",
                       "toggle": "Переключаю тему."}[m],
                "uz": {"dark": "Tungi rejimga o'tkazyapman.", "light": "Kunduzgi rejimga o'tkazyapman.",
                       "toggle": "Temani almashtiryapman."}[m]}[L]
    if t == "set_lang":
        n = _LANG_L.get(p.get("lang", ""), {}).get(L, p.get("lang", ""))
        return {"en": f"Switching the interface to {n}.",
                "ru": f"Переключаю интерфейс на {n}.",
                "uz": f"Interfeysni {n}ga o'tkazyapman."}[L]
    if t == "celebrations":
        m = p.get("mode", "toggle")
        return {"en": {"on": "Celebrations ON.", "off": "Celebrations OFF.", "toggle": "Toggling celebrations."}[m],
                "ru": {"on": "Поздравления включены.", "off": "Поздравления выключены.", "toggle": "Переключаю поздравления."}[m],
                "uz": {"on": "Tabriklar yoqildi.", "off": "Tabriklar o'chirildi.", "toggle": "Tabriklarni almashtiryapman."}[m]}[L]
    if t == "close_popups":
        return {"en": "Closing all popups.", "ru": "Закрываю все окна.",
                "uz": "Barcha oynalarni yopyapman."}[L]
    if t == "back":
        return {"en": "Going back to the dashboard.", "ru": "Возвращаюсь на дашборд.",
                "uz": "Dashboardga qaytyapman."}[L]
    if t == "temur_mode":
        m = p.get("mode", "fast")
        return {"en": f"Switching my answer mode to {m}.",
                "ru": f"Переключаю режим ответа на {m}.",
                "uz": f"Javob rejimini {m}ga o'tkazyapman."}[L]
    return {"en": "Done.", "ru": "Готово.", "uz": "Tayyor."}[L]


_LANG_NAME = {"en": "English", "ru": "Russian", "uz": "Uzbek"}

_HELP_TEXT = {
    "uz": ("Men portfel bo'yicha savollarga javob beraman va dashboardni o'zim boshqara olaman. "
           "Masalan: \"kalendarni och\", \"2025 dekabrni ko'rsat\", \"kanban doskani och\", "
           "\"TTM tahlilini 2026 uchun och\", \"kritik loyihalarni ko'rsat\", \"bloklanganlarni och\", "
           "\"yakunlangan loyihalar ro'yxati\", \"PMD-123 ni och\", \"[PM ismi] loyihalarini ko'rsat\", "
           "\"reytingni oylik qil\", \"tungi rejimga o't\", \"ruschaga o't\", \"hamma oynalarni yop\". "
           "Savollar: risklar, TTM, blokerlar, PM samaradorligi, muddati o'tganlar va istalgan masala haqida."),
    "ru": ("Я отвечаю на вопросы по портфелю и сам управляю дашбордом. Например: \"открой календарь\", "
           "\"покажи декабрь 2025\", \"открой канбан\", \"открой анализ TTM за 2026\", "
           "\"покажи критичные проекты\", \"открой заблокированные\", \"список завершённых проектов\", "
           "\"открой PMD-123\", \"покажи проекты [PM]\", \"лидерборд за месяц\", \"тёмная тема\", "
           "\"переключи на узбекский\", \"закрой все окна\". Вопросы: риски, TTM, блокеры, "
           "эффективность PM, просрочки и любая задача."),
    "en": ("I answer portfolio questions and can drive the dashboard myself. For example: "
           "\"open the calendar\", \"show December 2025\", \"open the kanban board\", "
           "\"open TTM analysis for 2026\", \"show critical projects\", \"open blocked items\", "
           "\"list completed projects\", \"open PMD-123\", \"show [PM]'s projects\", "
           "\"leaderboard by month\", \"dark mode\", \"switch to Russian\", \"close all popups\". "
           "Questions: risks, TTM, blockers, PM performance, overdue items and any issue."),
}


def _conv_ctx(history: list | None, ui: dict | None) -> str:
    """Conversation memory + UI awareness block for the LLM prompt."""
    parts = []
    if history:
        lines = []
        for h in history[-8:]:
            who = "User" if (h.get("role") == "user") else "Temur"
            txt = str(h.get("text", ""))[:220]
            if txt:
                lines.append(f"{who}: {txt}")
        if lines:
            parts.append("RECENT CONVERSATION (oldest first — use it to resolve follow-ups "
                         "like 'and for Epic?', 'what about 2025?'):\n" + "\n".join(lines))
    if ui:
        view = ui.get("view") or "dashboard"
        popup = ui.get("popup")
        parts.append(f"USER'S CURRENT SCREEN: page={view}"
                     + (f", open popup=\"{popup}\"" if popup else ", no popup open")
                     + ". Take this into account when the user says 'here', 'this page', 'now'.")
    return ("\n\n" + "\n\n".join(parts)) if parts else ""


def ask(question: str, payload: dict, lang: str = "en", scope: str = None, context: str = None,
        mode: str = "fast", probe: bool = False, history: list | None = None,
        ui: dict | None = None, last_action: dict | None = None) -> dict:
    L = lang if lang in ("en", "ru", "uz") else "en"
    # Answer mode: Turbo (instant 3B) / Flash (fast 7B) / Pro (smart 14B, slower).
    smart = mode == "smart"
    _model = (config.TEMUR_MODEL_SMART if smart
              else config.TEMUR_MODEL_TURBO if mode == "turbo"
              else config.TEMUR_MODEL_FAST)
    _to = config.OLLAMA_TIMEOUT_SMART if smart else config.OLLAMA_TIMEOUT

    # Teach intent: persist a fact locally so Temur "learns" across sessions.
    fact = _teach_match(question)
    if fact:
        remember_fact(fact)
        msg = {"en": f"Got it — I’ll remember: {fact}",
               "ru": f"Понял — запомню: {fact}",
               "uz": f"Tushundim — eslab qolaman: {fact}"}[L]
        _log_interaction(question, msg)
        return {"answer": msg, "source": "memory", "action": None,
                "assistant": ASSISTANT_NAME, "grounded_on": "memory"}

    # Dashboard-control intent WINS over everything (even the page scope): the
    # user may give a command while a popup is open ("close all", "open X").
    # `probe=True` runs ONLY this fast detection and returns — no LLM — so the
    # frontend can decide whether to show the page/global scope prompt.
    _analytics = payload.get("analytics") or {}
    pm_names = [b.get("pm") for b in (_analytics.get("pm_leaderboard") or []) if b.get("pm")]
    _early = detect_action(question, pm_names, last_action, history)
    if _early:
        msg = _action_message(_early, L)
        _log_interaction(question, msg)
        return {"answer": msg, "source": "action", "action": _early,
                "assistant": ASSISTANT_NAME, "grounded_on": "active_dataset"}
    if probe:
        return {"answer": None, "source": "probe", "action": None,
                "assistant": ASSISTANT_NAME, "grounded_on": None}

    conv = _conv_ctx(history, ui)

    # PAGE scope: answer about the popup the user is looking at. If the popup is
    # an ISSUE card, pull the FULL issue record (status, age, overdue, blockers,
    # quarterly report, comments) so Temur ASSESSES the item like an analyst and
    # can give concrete recommendations — not just read the visible fields.
    if scope == "page" and context:
        ctx = context[:6000]
        issue_facts = ""
        km = re.search(r"\b([A-Za-z][A-Za-z0-9]+-\d+)\b", context[:300])
        if km:
            try:
                from . import storage as _storage
                _data = _storage.load_current()
                iss = next((i for i in (_data or {}).get("issues", [])
                            if i["key"].upper() == km.group(1).upper()), None)
            except Exception:
                iss = None
            if iss:
                status, group, age, overdue_days, blockers, comments = _issue_facts(iss)
                qs = (iss.get("quarterly_status") or "").strip()
                ctext = "\n".join(f"[{c.get('date', '')}] {c.get('author', '')}: {c.get('text', '')}"
                                  for c in (comments or [])[-5:]).strip()
                _own = (iss.get("owner") or "").strip()
                lines = [f"Key: {iss.get('key')} — {iss.get('summary', '')}",
                         f"Status: {status} (stage: {group or 'unknown'})",
                         f"OWNER (владелец — accountable business owner): {_own or 'not set'}",
                         f"PM: {iss.get('pm') or 'n/a'}",
                         f"Age since created: {age} days" if age is not None else "",
                         f"OVERDUE by {overdue_days} days" if overdue_days else "",
                         ("Blocking dependencies: " + ", ".join(b.get("target", "?") for b in blockers))
                         if blockers else "No linked blockers recorded",
                         f"Comments on record: {len(comments or [])}"]
                issue_facts = ("\n\nFULL ISSUE RECORD (beyond the visible fields — use it to assess "
                               "the REAL state):\n" + "\n".join(l for l in lines if l)
                               + (f"\nQUARTERLY STATUS:\n{qs[:1500]}" if qs else "")
                               + (f"\nLATEST COMMENTS:\n{ctext[:1500]}" if ctext else ""))
        # Regulations relevant to the open item, for compliance-checked advice.
        reg = ""
        try:
            from app import rag
            rb = rag.context_block((context[:200] +
                  " порядок управления проектами проектный комитет владелец этапы"), k=4)
            if rb:
                reg = "\n\nBANK REGULATIONS (official documents the item must comply with):\n" + rb
        except Exception:
            pass
        prompt = (
            f"You are {ASSISTANT_NAME}, a sharp PMO analyst. The user is looking at a specific view "
            "(a popup). Answer from the on-screen data, the full issue record and the BANK "
            "REGULATIONS below — do not use other parts of the portfolio. Think like an analyst: "
            "first assess the item's real state (stage, age, deadline, blockers, latest progress) "
            "and whether it COMPLIES with the regulations (mandated process, committee, scoring, "
            "required stages/approvals), then answer the question directly; if the user asks about "
            "quality, health or advice, ALSO give 2-4 concrete recommendations that follow the "
            "regulations (cite the document by name) and assign each action to the OWNER (владелец) "
            "by name — that person is accountable (if no owner is set, say assigning one is step 1). "
            "If something truly isn't in the data, say so. Be concise. Plain text only — no Markdown. "
            f"Reply in {_LANG_NAME[L]} (or the language of the question).{conv}\n\n"
            f"ON-SCREEN DATA (\"{(context.splitlines() or [''])[0][:80]}\"):\n{ctx}{issue_facts}{reg}\n\n"
            f"QUESTION: {question}\n\nANSWER:"
        )
        answer, source = _llm(prompt, model=_model, timeout=_to)
        if not answer and smart:                       # Pro failed → fall back to Flash
            answer, source = _llm(prompt)
        if not answer:
            answer = _extractive(ctx, 4) or {"en": "I couldn't read this view's data.",
                                             "ru": "Не удалось прочитать данные этого экрана.",
                                             "uz": "Bu sahifa ma'lumotini o'qiy olmadim."}[L]
            source = "grounded"
        _log_interaction(question, answer)
        return {"answer": answer, "source": source, "action": None,
                "assistant": ASSISTANT_NAME, "grounded_on": "page"}

    analytics = payload["analytics"]
    kpis = payload["kpis"]

    # Capabilities / help intent: answer instantly with what Temur can do.
    if re.search(r"nima(?:lar)? qila olasan|qanday yordam|imkoniyat|what can you do|"
                 r"help me|что ты умеешь|что умеешь|чем можешь помочь", (question or "").lower()):
        msg = _HELP_TEXT[L]
        _log_interaction(question, msg)
        return {"answer": msg, "source": "help", "action": None,
                "assistant": ASSISTANT_NAME, "grounded_on": "capabilities"}

    # (dashboard-control intent already handled at the top of ask())
    ctx = _context(analytics, kpis)
    facts = _load_facts()
    facts_ctx = ("\n\nKNOWN FACTS (taught by the user, treat as authoritative):\n"
                 + "\n".join("- " + f["text"] for f in facts[-15:])) if facts else ""
    # RAG: pull the handful of issues / knowledge-base passages most relevant to
    # THIS question so Temur grounds specifics (keys, PMs, metrics) instead of guessing.
    retrieved = ""
    try:
        from app import rag
        rb = rag.context_block(question, k=6)
        if rb:
            retrieved = "\n\n" + rb
    except Exception:
        pass
    prompt = (
        f"You are {ASSISTANT_NAME}, a sharp, friendly portfolio analyst for a Jira PMD/PMO "
        "portfolio. Reply like a helpful human colleague: natural, warm, concise (2-4 sentences), "
        "and specific with numbers. Ground every claim in the facts and retrieved records below; "
        "if something isn't there, say so instead of inventing it. "
        "Retrieved records tagged [DOC] are the bank's official documents (structure, the Project "
        "and Committee / PMO-department regulations, new-product specs) — when the question touches "
        "process, roles, approvals or how an epic/new feature must be handled, base your answer on "
        "those [DOC] passages and refer to the document by name. "
        "Write PLAIN TEXT only — never use Markdown, asterisks, '#' or bullet characters. "
        f"Reply in {_LANG_NAME[L]} (or the language of the question if it differs).{conv}\n\n"
        f"PORTFOLIO FACTS:\n{ctx}{facts_ctx}{retrieved}\n\nQUESTION: {question}\n\nANSWER:"
    )
    answer, source = _llm(prompt, model=_model, timeout=_to)
    if not answer and smart:                           # Pro failed → fall back to Flash
        answer, source = _llm(prompt)
    if not answer:
        answer, source = _rule_based(question, analytics, kpis), "grounded"
    _log_interaction(question, answer)
    return {"answer": answer, "source": source, "action": None,
            "assistant": ASSISTANT_NAME, "grounded_on": "active_dataset"}
