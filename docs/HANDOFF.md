# ProjectNest — Session Handoff / Context

Paste this into a new session to continue instantly. (Conversation language: Uzbek.)

## What this is
**ProjectNest** = a **Portfolio Intelligence Platform** for a Jira **PMD/PMO** portfolio,
built ON TOP of an already-approved "healthcare" dashboard UI.
**RULE #1: the approved dashboard's visual design/layout/colors must not change — only data.**
The user DOES authorize targeted redesigns when explicitly asked (TTM panel, Project Flow,
the Portfolio-Progress panel → now "Delivery Flow", Top Projects ⓘ + clickable rows,
Delivery Flow's bars → segmented vertical sticks, and brand-new pages like Calendar / Risk).
UI is localized **EN / RU / UZ**, light + dark theme.

- Repo: https://github.com/MarufAkhmatov/Dashboard-for-Sigmintation (branch `main`)
- **Local (PRIMARY — use this path):** `C:\Users\ASUS\Desktop\ProjectNest`
  *(Moved from Downloads on 2026-06-21. Scheduled Task, watchdog, and Desktop shortcuts all updated.)*

## Stack & how to run
- **Frontend**: Vite + React + TS. Built to `dist/` via `npm run build` (from `Desktop\ProjectNest`).
- **Backend**: **Python 3.14 stdlib HTTP server** (`backend/server.py`). Stdlib only + `openpyxl`.
  FastAPI/pydantic do NOT build on 3.14.

### ★ PRODUCTION model — ONE resilient process on :8080
- `backend/server.py` serves **both** the SPA (`dist/`) **and** `/api` on a single port.
  Port = env `PN_PORT` (default 8077 for dev; **prod runs PN_PORT=8080**). Same-origin → no proxy.
- **Auth**: `/api/login`, `/api/logout`, `/api/me`; all `/api/*` require a valid HMAC-signed `pn_session`
  cookie (30-day). `/api/health` is public. Static SPA is public. **All DATA is gated.**
  Credentials stored in `storage/auth.json` — **multi-user format as of 2026-06-21** (see Auth section).
- **Resilience**: `serve-prod.ps1` is a watchdog loop — every 15s, if :8080 is down, restarts Python hidden.
  If the watchdog itself dies, run: `Start-ScheduledTask -TaskName ProjectNest`.
- **Auto-start**: Scheduled Task **"ProjectNest"** (trigger=AtLogOn, RestartCount=999) runs `serve-prod.ps1`
  from `C:\Users\ASUS\Desktop\ProjectNest\serve-prod.ps1`. `serve-prod.ps1` uses `$MyInvocation` to find
  its own path dynamically — works wherever the folder lives.
- Frontend gate: `src/app/components/AuthGate.tsx` wraps the app; checks `/api/me`, shows login screen.

### Dev model
- `npm run dev` → http://localhost:5173 (HMR), proxies `/api` → :8077.
- `python backend/server.py` (default 8077 dev port). Login required.

### Access URLs
- **PC:** http://localhost:8080
- **Phone (same Wi-Fi):** `http://<LAN-IP>:8080` — firewall rule "ProjectNest 8080" enabled (all profiles).
  LAN IP: run `Get-NetIPAddress -AddressFamily IPv4` — last seen **192.168.2.158**.
  Requires same subnet, no client-isolation. Type `http://` not `https://`.
- **Secure tunnel:** `start-tunnel.ps1` → cloudflared → `https://<name>.trycloudflare.com` (URL changes each run).

### Desktop shortcuts (created 2026-06-21)
- **ProjectNest Dashboard.url** → `http://localhost:8080`
- **ProjectNest (Papka).lnk** → `C:\Users\ASUS\Desktop\ProjectNest`

---

## Auth — Multi-user system (added 2026-06-21)

`storage/auth.json` uses a **`{"users": [...]}` array format** (replaced the old single-user format).
`_load_users()` in `server.py` auto-migrates the old format if needed (reads fresh each login).

### Accounts
One `admin` account plus 19 `pm` accounts (usernames = corporate e-mail addresses).
Credentials live ONLY in `storage/auth.json` (gitignored) — never commit them.

**Login is case-sensitive** — the admin username starts with a capital letter. All PM usernames are lowercase email addresses.

### Admin API endpoints (require `role: admin`)
| Endpoint | Method | Action |
|----------|--------|--------|
| `/api/admin/users` | GET | List all users (no passwords) |
| `/api/admin/users` | POST `{username, password, role, name}` | Create user |
| `/api/admin/users/reset` | POST `{username, password}` | Reset password |
| `/api/admin/users/delete` | POST `{username}` | Delete user |

Safety: cannot delete the last admin. Non-admin gets 403. Secret HMAC key in `storage/.auth_secret`.

---

## Data reality (IMPORTANT)
Daily Jira exports; PMD + PMO merged. Files:
1. **CSV "all fields"** — rich (PM, comments, links, regulator/division/scoring, **description**).
   Person fields are emails → prettified. Key col = `Ключ проблемы`.
2. **HTML "Printable"** — real display names.
3. **History (Current fields) XLSX** — changelog (status transitions) → EXACT TTM.
   **Without history XLSX, TTM phases collapse** (Delivery=0, Lead=0, Discovery=total).

- **Daily ingest order:** PMD CSV (replace) → PMO CSV (merge) → PMD History (enrich) → PMO History (enrich).
  FE batch-upload auto-sorts this for you.
- **Current active dataset:** 823 issues / 138 epics / projects [PMD, PMO] / 150 history-enriched.
  Last ingest: 2026-06-18 15:05.
- **After parser/normalize change → clear `storage/temp/cache/*.json` AND re-ingest.**
- **After backend code change → restart server** (kill :8080 python; watchdog relaunches in ≤15s,
  or `Start-ScheduledTask -TaskName ProjectNest`).

---

## Backend layout (`backend/app/`)
- `parser.py` — CSV/XLSX/HTML + `is_history_file()` + `parse_jira_history()`.
- `normalize.py` — aliases EN/RU/UZ, status fix, strips custom-field wrapper, email→name, clean comments.
  Fields: `key, project, type, is_epic, status, status_group, summary, description, pm, assignee, reporter,
  created, resolved, due, epic_key, story_points, priority, project_type, regulator, division, scoring,
  quarterly_status, comments, links, history`. `description` added 2026-06-16 for epic QA engine.
  Status audit: `reset_status_audit()` / `get_status_audit()` / `stop_status_audit()` per ingest.
- `config.py` — status taxonomy, DISCOVERY/DELIVERY/DONE/DECLINED sets, ROOT/STORAGE paths.
- `metrics/engines.py` — pure fns: `issue_ttm`, `ttm_analysis`, `portfolio_kpis`, `epic_status_flow`,
  `project_health` (0–100 → **this is the % in Top Projects, NOT completion**), `pm_leaderboard(_period)`,
  `filter_issues`, `calendar_events`, `risk_insights`, `flow_balance`,
  **`epic_quality` + `epic_problems`** (epic QA, added 2026-06-16).
- `aggregate.py` — `top_projects` = top 3 epics by `project_health` score.
- `aria.py` — **Temur AI**. Provider chain: Anthropic API → Claude CLI → Ollama → grounded fallback.
  `ask(q, payload, lang, scope, context)`: detect_action, intent, grounded/LLM answer.
  `recommend_epic_quality(epic, problems, lang)` — PM-to-author message, multilingual, LLM→grounded fallback.
- `storage.py` — `storage/current/dataset.json`; persists status audit.
- `server.py` — multi-user auth: `_load_users()`, `_save_users()`, `_find_user()`, `_is_admin()`.

---

## Key endpoints (require session cookie except health/me/login)
```
/api/health (public) · /api/me · /api/login · /api/logout
/api/dashboard · /api/analytics · /api/uploads
/api/ttm · /api/issues · /api/issue · /api/issue-summary · /api/issue-recommend
/api/pm-leaderboard · /api/notifications · /api/data-quality · /api/status-audit
/api/calendar?mode=resolved|created
/api/risk · /api/flow?granularity=month|quarter|year
/api/epic-quality?project=PMD&days=90
/api/epic-quality-recommend?key=&lang=
/api/analyze (POST) · /api/aria (POST {question,lang,scope,context})
/api/admin/users (GET+POST, admin only)
/api/admin/users/reset (POST, admin only)
/api/admin/users/delete (POST, admin only)
```

---

## Frontend layout (`src/app/`)
- `main.tsx` — providers: Theme → I18n → **AuthGate** → Portfolio → App.
- `useBreakpoint.ts` — `mobile | tablet | desktop`. Re-syncs `setBp(get())` in `useEffect` on mount
  + `orientationchange` listener. Without this: mobile users got the desktop layout.
- `portfolio.tsx` — context with all API methods. Includes:
  - `userRole: string | null` and `userName: string | null` (fetched from `/api/me` on mount).
  - `adminUsers()`, `adminAddUser()`, `adminResetPassword()`, `adminDeleteUser()` (admin panel methods).
  - `uploadBatch(files, mode, onProgress)` — smart-sorts: issue CSVs first → history XLSX last.
  - `epicQuality()`, `epicQualityRecommend(key, lang)`.
- `App.tsx` — header controls: lang, theme, multi-file upload (progress badge), ⚠️ epic QA alert,
  🎉 celebrations, ⚙️ DQ, 👤 admin panel button (**`UserCog` icon, blue — only if `userRole === "admin"`**),
  🔔 bell, avatar. Mobile **hamburger** includes all items incl. Admin Panel if admin.
  Top-nav page switch: `dashboard | calendar | risk`.
- `components/AdminPanel.tsx` (**new 2026-06-21**) — User Management modal (admin only):
  - Lists all 20 users with name, email login, role badge (Admin=blue, PM=grey).
  - **Add user** — inline expandable form (username/email, display name, password, role dropdown).
  - **Reset password** — per-row 🔑 button opens inline password input; Enter or Confirm to save.
  - **Delete user** — 🗑 button with `window.confirm`; blocked if deleting the last admin.
  - Uses `usePopupOpenSignal(true)` + `useTemurBesidePad()`.
- `components/BestProjects.tsx` — Top Projects panel. ⓘ methodology popover (top-right). Full project name
  (no truncation). Score stacked `99% / HEALTH`. Whole row clickable → `openIssue(key)`. Jira ↗ icon.
- `components/WellnessChart.tsx` — Delivery Flow. Custom `<SegmentedBar>` shape for recharts:
  stacked pill ticks (`seg=2.4, gap=3.6, rx=seg/2`) matching Project Flow donut spokes.
- `components/EpicQualityModal.tsx` — ⚠️ new-epic QA modal. Severity strip, problem badges, quality score,
  author/PM/date, "Draft author feedback" → lazy `/api/epic-quality-recommend`. Cards have `flexShrink: 0`.
- `components/CalendarView.tsx` — Calendar page (resolved/created, Day/Week/Month/Year, zoom, scroll).
- `components/RiskDashboard.tsx` — Risk page (6 KPI metrics, register, heatmap, aging, blocked, AI insights).
- `popup.ts` — `usePopupOpen`, `useTemurBesidePad`, `setPageContext` (Temur scope-choice: page vs global).
- `i18n.tsx` — EN/RU/UZ. Admin panel keys: `tip_admin`, `admin_title/subtitle`, `admin_col_*`,
  `admin_role_admin/pm`, `admin_add/reset/delete`, `admin_field_*`, `admin_err_*`, `admin_ok_*`.

---

## DONE 2026-06-21 session

### Admin Panel & multi-user auth
- **`storage/auth.json`** rewritten to `{"users": [...]}` array format with 20 accounts (1 admin + 19 PMs).
- **`backend/server.py`**: replaced `_load_auth()` with `_load_users()`, `_save_users()`, `_find_user()`,
  `_is_admin()`. Login handler checks against users array, returns `{ok, user, role}`. `/api/me` now
  returns `{authed, user, role, name}`. Added GET `/api/admin/users` + POST `/api/admin/users`,
  `/api/admin/users/reset`, `/api/admin/users/delete` — all require `_is_admin()` (403 otherwise).
  Cannot delete the last admin. `_send_login(user, role)` signature updated to return role.
- **`src/app/portfolio.tsx`**: `userRole` + `userName` state (fetched from `/api/me` on mount).
  Added `adminUsers`, `adminAddUser`, `adminResetPassword`, `adminDeleteUser` methods.
- **`src/app/components/AdminPanel.tsx`**: new modal component (see above).
- **`src/app/i18n.tsx`**: added admin panel translation keys in EN, RU, UZ.
- **`src/app/App.tsx`**: added `UserCog` lucide import, `adminOpen` state, admin button in header
  (desktop, admin-only), admin item in hamburger (admin-only), `<AdminPanel>` in AnimatePresence.

### Project relocated to Desktop
- Project folder copied from `Downloads\...\DashboardForJiraTasksAndCalendars-main (1)\DashboardForJiraTasksAndCalendars-main`
  to **`C:\Users\ASUS\Desktop\ProjectNest`**.
- Scheduled Task "ProjectNest" updated to run `serve-prod.ps1` from new path.
- Desktop shortcuts recreated pointing to new path.
- Server restarted from new location — verified `http://localhost:8080` returns 200, dataset intact.

### Current build
- Bundle: `dist/assets/index-BYHJnLIO.js` (built 2026-06-21, 921 KB).
- All 06-18 + 06-21 changes are live in production (:8080).

---

## DONE 2026-06-18 session
- **Top Projects redesign** (`BestProjects.tsx`): ⓘ methodology popover, full name, stacked HEALTH label,
  clickable rows → `openIssue`, Jira ↗ icon with `stopPropagation`.
- **Delivery Flow segmented bars** (`WellnessChart.tsx`): `<SegmentedBar>` — seg=2.4, gap=3.6, rx=seg/2.
- **EpicQualityModal mobile fix**: added `flexShrink: 0` to cards.
- **Login creds**: admin credentials rotated (see `storage/auth.json`, gitignored).
- **Build + deploy**: bundle `index-BsLnuH-x.js` (superseded by 2026-06-21 build).

## DONE 2026-06-16 session
- **New-epic Quality Alert**: ⚠️ header button, `EpicQualityModal`, `epic_quality` + `epic_problems` engine,
  `recommend_epic_quality` in aria.py, `/api/epic-quality` + `/api/epic-quality-recommend` endpoints.
  `description` field added to `normalize.py` (needed re-ingest).
- **Mobile/tablet chart fix**: definite `height` on chart cards in App.tsx.

## DONE (parallel session, between 06-16 and 06-18)
- **`useBreakpoint.ts` mobile fix**: `setBp(get())` in `useEffect` + `orientationchange`.
- **TTM collapse fix**: full re-ingest (PMD+PMO CSV + 2 History XLSX) after partial upload.
- **Multi-file batch upload**: `uploadBatch` in portfolio.tsx, `<input multiple>`, progress badge.
- **Status audit pipeline**: normalize.py records raw→canonical remaps; `/api/status-audit`; meta carries summary.
- **LAN access debugged**: IP had changed from DHCP (192.168.1.x → 192.168.2.x).

## DONE (earlier sessions)
- Calendar page, Risk Dashboard, Delivery Flow panel, proportional sparklines, Temur scope-choice (page/global),
  single-process server (SPA+API on :8080), login auth, watchdog, Scheduled Task, firewall.

---

## NEXT (pending, no files/data yet)
- **Product Teams TTM** — team = Jira project key, separate storage namespace, Classic⇄Product toggle.
- **Status audit in UI** — badge/icon near DQ panel listing mixed/dead events from last ingest.
- CSV+HTML hybrid name merge; Postgres + RBAC/SSO (enterprise scale) — later.

---

## Gotchas
- **Primary project path:** `C:\Users\ASUS\Desktop\ProjectNest` — always edit files here.
- **Login case-sensitive:** `Admin` (capital A). PM logins: lowercase email e.g. `m.axmatov@ipakyulibank.uz`.
- **Admin Panel** only appears for `role: admin` users (UserCog button in header, blue).
- Python 3.14: stdlib only (+openpyxl). No pandas/pydantic/FastAPI.
- After backend code change → restart server (kill :8080 python; watchdog relaunches in ≤15s).
- After parser/normalize change → clear `storage/temp/cache/*.json` AND re-ingest.
- **Without history XLSX, TTM phases collapse** (Delivery=0, Lead=0). Always pair CSV with history XLSX.
- **Top Projects %** = `project_health` score (0–100), NOT completion. ⓘ popover exists for this reason.
- `recharts` inside flex: `position:absolute; inset:0` child needs **definite `height`** on mobile (not just min-height).
- Flex column scroll containers: child cards default `flex-shrink:1` → squash. Set `flexShrink: 0`.
- `useTemurBesidePad()` returns full `padding` shorthand (avoid mixing with `paddingRight` longhand).
- LAN IP from DHCP may change — always check with `Get-NetIPAddress -AddressFamily IPv4`.
- Claude CLI for Temur: needs user host login → Scheduled Task AtLogOn (NOT SYSTEM, NOT Docker).
- `serve-prod.ps1` uses `$MyInvocation.MyCommand.Path` → path-independent, works from any location.
