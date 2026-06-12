"""All portfolio calculation engines. Pure functions over normalized issues."""
import datetime as dt
from .. import config

# ----------------------------- helpers --------------------------------------
def _d(iso):
    return dt.datetime.fromisoformat(iso) if iso else None


def is_done(i):
    return i["status"] in config.DONE_STATUSES or bool(i.get("resolved"))


def is_declined(i):
    return i["status"] in config.DECLINED_STATUSES


def epics(issues):
    return [i for i in issues if i["is_epic"]]


def works(issues):
    return [i for i in issues if not i["is_epic"]]


def percentile(values, p):
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (p / 100.0)
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    return round(s[f] + (s[c] - s[f]) * (k - f), 2)


def stats(values):
    values = [v for v in values if v is not None]
    if not values:
        return {"avg": 0, "median": 0, "p75": 0, "p90": 0, "min": 0, "max": 0, "count": 0}
    s = sorted(values)
    return {
        "avg": round(sum(s) / len(s), 2),
        "median": percentile(s, 50),
        "p75": percentile(s, 75),
        "p90": percentile(s, 90),
        "min": round(s[0], 2),
        "max": round(s[-1], 2),
        "count": len(s),
    }


def pct(part, total):
    return round(100.0 * part / total, 1) if total else 0.0


# --------------------------- per-issue TTM ----------------------------------
def issue_ttm(i):
    disc = sum(h["days"] for h in i["history"] if h["status"] in config.DISCOVERY_STATUSES)
    deliv = sum(h["days"] for h in i["history"] if h["status"] in config.DELIVERY_STATUSES)
    return {"discovery": round(disc, 2), "delivery": round(deliv, 2), "total": round(disc + deliv, 2)}


def issue_lead_time(i):
    """First entry into IN PROGRESS -> exit from TESTING."""
    start = end = None
    for h in i["history"]:
        if h["status"] == "IN PROGRESS" and start is None:
            start = _d(h["entered"])
        if h["status"] == "TESTING":
            end = _d(h["exited"])
    if start and end and end > start:
        return round((end - start).total_seconds() / 86400.0, 2)
    return None


def issue_flow(i):
    active = sum(h["days"] for h in i["history"]
                 if h["status"] in {"IN PROGRESS", "TESTING", "ANALYSIS", "ARCHITECTURE REVIEW"})
    total = sum(h["days"] for h in i["history"]) or 1.0
    return round(100.0 * active / total, 1)


# ----------------------------- KPIs -----------------------------------------
def portfolio_kpis(issues):
    eps = epics(issues)
    total = len(eps)
    completed = sum(1 for e in eps if is_done(e))
    declined = sum(1 for e in eps if is_declined(e))
    open_ = total - completed - declined

    def by_status(st):
        return sum(1 for e in eps if e["status"] == st)

    return {
        "total_portfolio_projects": total,
        "total_epics": total,
        "total_work_items": len(works(issues)),
        "completed_projects": completed,
        "declined_projects": declined,
        "open_projects": open_,
        "completion_pct": pct(completed, total),
        "declined_pct": pct(declined, total),
        "active_pct": pct(open_, total),
        "in_progress": by_status("IN PROGRESS"),
        "in_testing": by_status("TESTING"),
        "in_pilot": by_status("PILOT IO"),
        "waiting_validation": by_status("VALIDATION"),
        "waiting_analysis": by_status("ANALYSIS"),
        "waiting_architecture_review": by_status("ARCHITECTURE REVIEW"),
        "waiting_initiation": by_status("INITIATION"),
    }


# --------------------------- yearly analytics -------------------------------
def yearly_analytics(issues):
    eps = epics(issues)
    yearly, quarterly, monthly = {}, {}, {}
    for e in eps:
        if not is_done(e) or not e.get("resolved"):
            continue
        r = _d(e["resolved"])  # Resolution Date only
        y = r.year
        q = f"{y}-Q{(r.month - 1) // 3 + 1}"
        m = f"{y}-{r.month:02d}"
        yearly[y] = yearly.get(y, 0) + 1
        quarterly[q] = quarterly.get(q, 0) + 1
        monthly[m] = monthly.get(m, 0) + 1

    years = sorted(yearly)
    yoy = {}
    for i, y in enumerate(years):
        if i > 0 and yearly[years[i - 1]]:
            yoy[y] = pct(yearly[y] - yearly[years[i - 1]], yearly[years[i - 1]])
    quarters = sorted(quarterly)
    qoq = {}
    for i, q in enumerate(quarters):
        if i > 0 and quarterly[quarters[i - 1]]:
            qoq[q] = pct(quarterly[q] - quarterly[quarters[i - 1]], quarterly[quarters[i - 1]])

    return {
        "yearly": [{"period": str(y), "completed": yearly[y]} for y in years],
        "quarterly": [{"period": q, "completed": quarterly[q]} for q in quarters],
        "monthly": [{"period": m, "completed": monthly[m]} for m in sorted(monthly)],
        "yoy_growth": [{"period": str(y), "growth_pct": g} for y, g in yoy.items()],
        "qoq_growth": [{"period": q, "growth_pct": g} for q, g in qoq.items()],
        "throughput": sum(yearly.values()),
    }


# ------------------------------ TTM engine ----------------------------------
def ttm_engine(issues):
    def block(items):
        disc = stats([issue_ttm(i)["discovery"] for i in items])
        deliv = stats([issue_ttm(i)["delivery"] for i in items])
        total = stats([issue_ttm(i)["total"] for i in items])
        return {"discovery": disc, "delivery": deliv, "total": total}

    eps = epics(issues)
    tasks = [i for i in issues if i["type"].lower() == "task"]
    feats = [i for i in issues if i["type"].lower() == "new feature"]

    # trend by resolution year (total TTM)
    by_year = {}
    for i in eps:
        if i.get("resolved"):
            y = _d(i["resolved"]).year
            by_year.setdefault(y, []).append(issue_ttm(i)["total"])
    trend = [{"period": str(y), "avg_ttm": stats(by_year[y])["avg"]} for y in sorted(by_year)]

    by_pm = {}
    for i in eps:
        by_pm.setdefault(i["pm"], []).append(issue_ttm(i)["total"])
    by_pm_out = [{"pm": k, **stats(v)} for k, v in sorted(by_pm.items())]

    by_project = {}
    for i in eps:
        by_project.setdefault(i["project"], []).append(issue_ttm(i)["total"])
    by_project_out = [{"project": k, **stats(v)} for k, v in sorted(by_project.items())]

    return {
        "epic": block(eps),
        "task": block(tasks),
        "new_feature": block(feats),
        "overall": stats([issue_ttm(i)["total"] for i in eps]),
        "trend": trend,
        "by_pm": by_pm_out,
        "by_project": by_project_out,
    }


# ---------------------------- Lead time engine ------------------------------
def lead_time_engine(issues):
    eps = epics(issues)
    lt = [issue_lead_time(i) for i in eps]
    lt = [x for x in lt if x is not None]
    by_year = {}
    for i in eps:
        x = issue_lead_time(i)
        if x is not None and i.get("resolved"):
            by_year.setdefault(_d(i["resolved"]).year, []).append(x)
    trend = [{"period": str(y), "avg_lead": stats(by_year[y])["avg"]} for y in sorted(by_year)]
    return {**stats(lt), "trend": trend}


# --------------------------- Flow efficiency --------------------------------
def flow_engine(issues):
    eps = epics(issues)
    per_project, per_pm, all_vals = {}, {}, []
    for i in eps:
        f = issue_flow(i)
        all_vals.append(f)
        per_project.setdefault(i["project"], []).append(f)
        per_pm.setdefault(i["pm"], []).append(f)
    return {
        "portfolio_average": round(sum(all_vals) / len(all_vals), 1) if all_vals else 0,
        "per_project": [{"project": k, "flow_efficiency": round(sum(v) / len(v), 1)} for k, v in per_project.items()],
        "per_pm": [{"pm": k, "flow_efficiency": round(sum(v) / len(v), 1)} for k, v in per_pm.items()],
    }


# --------------------------- Project health ---------------------------------
def _children(epic, issues):
    return [i for i in issues if i.get("epic_key") == epic["key"]]


def project_health(issues):
    eps = epics(issues)
    now = dt.datetime.now()
    scored = []
    for e in eps:
        ch = _children(e, issues)
        ttm = issue_ttm(e)["total"]
        lead = issue_lead_time(e) or 0
        blocked_links = sum(1 for l in e["links"] if l["type"] == "is blocked by")
        dep_count = len(e["links"])
        overdue = sum(1 for c in ch if c.get("due") and not is_done(c) and _d(c["due"]) < now)
        # status aging: days since last status change
        aging = 0.0
        if e["history"]:
            last = _d(e["history"][-1]["entered"])
            if last and not is_done(e):
                aging = (now - last).total_seconds() / 86400.0
        delivered = sum(1 for c in ch if is_done(c))
        delivery_perf = pct(delivered, len(ch)) if ch else (100 if is_done(e) else 50)

        score = 100.0
        score -= min(25, ttm / 30.0)          # slower TTM lowers score
        score -= min(15, lead / 20.0)
        score -= min(15, blocked_links * 7)
        score -= min(10, overdue * 3)
        score -= min(10, dep_count * 2)
        score -= min(15, aging / 14.0)
        score = max(0.0, min(100.0, score)) * 0.6 + delivery_perf * 0.4
        score = round(max(0.0, min(100.0, score)), 1)
        cat = ("Excellent" if score >= 85 else "Good" if score >= 70
               else "Warning" if score >= 50 else "Critical")
        dur = None
        if e.get("created") and e.get("resolved"):
            dur = max(0, (_d(e["resolved"]) - _d(e["created"])).days)
        scored.append({
            "key": e["key"], "url": e.get("url", ""), "project": e["project"], "summary": e["summary"],
            "pm": e["pm"], "status": e["status"], "score": score, "category": cat,
            "ttm": ttm, "lead_time": lead, "blocked": blocked_links,
            "dependencies": dep_count, "overdue_children": overdue,
            "children": len(ch), "completed": is_done(e), "duration_days": dur,
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


# --------------------------- Blocker engine ---------------------------------
def blocker_engine(issues):
    by_key = {i["key"]: i for i in issues}
    edges, blocked_tasks, blocked_projects = [], [], []
    for i in issues:
        for l in i["links"]:
            if l["type"] == "blocks":
                src, dst = i["key"], l["target"]
            elif l["type"] == "is blocked by":
                src, dst = l["target"], i["key"]
            else:
                continue
            s, d = by_key.get(src), by_key.get(dst)
            kind = f"{'Epic' if s and s['is_epic'] else 'Task'} blocks {'Epic' if d and d['is_epic'] else 'Task'}"
            edges.append({"source": src, "target": dst, "kind": kind})

    # An issue is "blocked" if it is the target of a blocks-edge OR has an
    # explicit "is blocked by" link.
    blocked_by_map: dict[str, list[str]] = {}
    for e in edges:
        blocked_by_map.setdefault(e["target"], []).append(e["source"])
    for i in issues:
        blockers = blocked_by_map.get(i["key"], [])
        if blockers and not is_done(i):
            entry = {"key": i["key"], "summary": i["summary"], "pm": i["pm"],
                     "blocked_by": sorted(set(blockers)),
                     "blocked_days": round(issue_ttm(i)["total"], 1),
                     "risk": "High" if len(set(blockers)) > 1 else "Medium"}
            (blocked_projects if i["is_epic"] else blocked_tasks).append(entry)

    # simplified critical path = longest dependency chain
    adj = {}
    for e in edges:
        adj.setdefault(e["source"], []).append(e["target"])
    best = []
    seen = set()

    def dfs(n, path):
        nonlocal best
        if len(path) > len(best):
            best = list(path)
        for nxt in adj.get(n, []):
            if nxt not in path:
                dfs(nxt, path + [nxt])

    for n in adj:
        if n not in seen:
            dfs(n, [n])
    return {
        "edges": edges,
        "blocked_projects": blocked_projects,
        "blocked_tasks": blocked_tasks,
        "critical_path": best,
        "total_blocked": len(blocked_projects) + len(blocked_tasks),
    }


# --------------------------- PM leaderboard ---------------------------------
def pm_leaderboard(issues):
    eps = epics(issues)
    pms = {}
    for e in eps:
        pms.setdefault(e["pm"], []).append(e)
    health = {h["key"]: h["score"] for h in project_health(issues)}

    board = []
    for pm, projs in pms.items():
        completed = sum(1 for p in projs if is_done(p))
        tasks_done = sum(1 for i in works(issues) if i["pm"] == pm and is_done(i))
        ttm_vals = [issue_ttm(p)["total"] for p in projs if is_done(p)]
        lead_vals = [x for x in (issue_lead_time(p) for p in projs) if x is not None]
        flow_vals = [issue_flow(p) for p in projs]
        avg_ttm = round(sum(ttm_vals) / len(ttm_vals), 1) if ttm_vals else 0
        avg_lead = round(sum(lead_vals) / len(lead_vals), 1) if lead_vals else 0
        flow = round(sum(flow_vals) / len(flow_vals), 1) if flow_vals else 0
        success = pct(completed, len(projs))
        avg_health = round(sum(health.get(p["key"], 0) for p in projs) / len(projs), 1)
        # PM score: blend of success, health, flow and speed
        speed = max(0.0, 100 - min(100, avg_ttm / 3.0))
        score = round(success * 0.3 + avg_health * 0.3 + flow * 0.2 + speed * 0.2, 1)
        board.append({
            "pm": pm, "projects_total": len(projs), "projects_completed": completed,
            "tasks_completed": tasks_done, "avg_ttm": avg_ttm, "avg_lead_time": avg_lead,
            "flow_efficiency": flow, "success_rate": success, "pm_score": score,
        })
    board.sort(key=lambda x: x["pm_score"], reverse=True)
    for idx, b in enumerate(board, 1):
        b["rank"] = idx
    return board


def data_quality(issues):
    """Field coverage of the active dataset (how many issues have each field filled)."""
    n = len(issues) or 1
    EMPTY = {"", "unassigned", "не задана", "нет", "none", "не заполнено",
             "не определено", "не назначен", "-", "0"}
    defs = [
        ("Issue key", "key"), ("Type", "type"), ("Status", "status"), ("Project", "project"),
        ("PM (custom)", "pm"), ("Assignee", "assignee"), ("Reporter", "reporter"),
        ("Priority", "priority"), ("Resolved date", "resolved"), ("Created", "created"),
        ("Due date", "due"), ("Epic link", "epic_key"), ("Project type", "project_type"),
        ("Regulator req.", "regulator"), ("Customer division", "division"), ("Scoring", "scoring"),
    ]
    rows = []
    for label, k in defs:
        filled = sum(1 for i in issues if str(i.get(k) or "").strip().lower() not in EMPTY)
        rows.append({"field": label, "filled": filled, "total": len(issues),
                     "pct": round(100 * filled / n, 1)})
    has_history = any(len(i.get("history", [])) > 2 for i in issues)
    return {"total": len(issues), "fields": rows, "has_status_history": has_history,
            "epics": sum(1 for i in issues if i["is_epic"])}


def recent_closures(issues, days=14, limit=30):
    """Items resolved within `days` of the most recent resolution date.

    Used for bell notifications and 'recently closed' celebrations.
    """
    done = [i for i in issues if is_done(i) and i.get("resolved")]
    if not done:
        return {"epics": [], "tasks": [], "ref": None}
    ref = max(_d(i["resolved"]) for i in done)
    cutoff = ref - dt.timedelta(days=days)
    recent = [i for i in done if _d(i["resolved"]) >= cutoff]
    recent.sort(key=lambda i: _d(i["resolved"]), reverse=True)

    def fmt(i):
        return {
            "key": i["key"], "url": i.get("url", ""), "type": i["type"], "pm": i["pm"],
            "summary": i.get("summary", ""), "project": i.get("project", ""),
            "resolved": i["resolved"][:10] if i.get("resolved") else "",
            "duration_days": (max(0, (_d(i["resolved"]) - _d(i["created"])).days)
                              if i.get("created") and i.get("resolved") else None),
        }

    epics_r = [fmt(i) for i in recent if i["is_epic"]][:limit]
    tasks_r = [fmt(i) for i in recent if not i["is_epic"]][:limit]
    return {"epics": epics_r, "tasks": tasks_r, "ref": ref.isoformat(),
            "window_days": days, "total": len(epics_r) + len(tasks_r)}


def pm_leaderboard_period(issues, period="all", ref=None):
    """PM leaderboard filtered to a time window by resolution date.

    period: all | year | quarter | month | week. Counts completed projects (epics)
    and tasks per PM, plus total time spent (sum of TTM days). Ranked by output.
    """
    eps = epics(issues)
    completed = [e for e in eps if is_done(e) and e.get("resolved")]
    if ref is None:
        dates = [_d(e["resolved"]) for e in completed]
        ref = max(dates) if dates else dt.datetime.now()

    def in_win(iso):
        if period == "all":
            return True
        if not iso:
            return False
        d = _d(iso)
        if period == "year":
            return d.year == ref.year
        if period == "quarter":
            return d.year == ref.year and (d.month - 1) // 3 == (ref.month - 1) // 3
        if period == "month":
            return d.year == ref.year and d.month == ref.month
        if period == "week":
            return d.isocalendar()[:2] == ref.isocalendar()[:2]
        return True

    agg: dict[str, dict] = {}
    for e in eps:
        if is_done(e) and in_win(e.get("resolved")):
            a = agg.setdefault(e["pm"], {"projects": 0, "tasks": 0, "time": 0.0})
            a["projects"] += 1
            a["time"] += issue_ttm(e)["total"]
    for w in works(issues):
        if is_done(w) and in_win(w.get("resolved")):
            a = agg.setdefault(w["pm"], {"projects": 0, "tasks": 0, "time": 0.0})
            a["tasks"] += 1
            a["time"] += issue_ttm(w)["total"]

    board = []
    for pm, s in agg.items():
        if pm == "Unassigned":
            continue
        board.append({"pm": pm, "projects_completed": s["projects"],
                      "tasks_completed": s["tasks"], "time_spent": round(s["time"], 1)})
    board.sort(key=lambda b: (b["projects_completed"], b["tasks_completed"], b["time_spent"]), reverse=True)
    for i, b in enumerate(board, 1):
        b["rank"] = i
    return {"period": period, "ref": ref.isoformat() if hasattr(ref, "isoformat") else str(ref),
            "rows": board}


def pm_nominations(board):
    if not board:
        return {}
    def top(key, reverse=True):
        return max(board, key=lambda b: b[key]) if reverse else min(board, key=lambda b: b[key])
    completed = [b for b in board if b["projects_completed"] > 0] or board
    return {
        "best_project_manager": board[0]["pm"],
        "fastest_delivery_manager": min(completed, key=lambda b: b["avg_lead_time"] or 1e9)["pm"],
        "best_quality_manager": top("flow_efficiency")["pm"],
        "highest_throughput_manager": top("projects_completed")["pm"],
        "best_ttm_manager": min(completed, key=lambda b: b["avg_ttm"] or 1e9)["pm"],
        "best_lead_time_manager": min(completed, key=lambda b: b["avg_lead_time"] or 1e9)["pm"],
        "best_portfolio_contributor": top("projects_total")["pm"],
        "most_consistent_pm": top("success_rate")["pm"],
        "top_performer": board[0]["pm"],
    }


# ----------------------------- Top projects ---------------------------------
def top_projects(issues):
    health = project_health(issues)
    done = [h for h in health if h["completed"]]
    return {
        "top_10": health[:10],
        "fastest": sorted([h for h in done if h["ttm"] > 0], key=lambda h: h["ttm"])[:10],
        "highest_quality": sorted(health, key=lambda h: h["score"], reverse=True)[:10],
        "most_complex": sorted(health, key=lambda h: (h["dependencies"], h["children"]), reverse=True)[:10],
        "most_delayed": sorted(health, key=lambda h: (h["overdue_children"], h["ttm"]), reverse=True)[:10],
    }
