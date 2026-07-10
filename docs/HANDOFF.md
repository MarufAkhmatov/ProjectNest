# ProjectNest — Session Handoff / Context

Paste this into a new session to continue instantly. (Conversation language: Uzbek.)

## What this is
**ProjectNest** = a **Portfolio Intelligence Platform** for a Jira **PMD/PMO** portfolio
at a bank, with a local AI assistant **Temur** that (1) answers portfolio questions,
(2) **drives the dashboard itself** (opens panels, applies filters, switches pages —
no clicking needed), and (3) grounds its analysis/recommendations in **both** the
issue's own data **and** the bank's normative documents (via a local RAG index), so
advice is objective and cites real regulations by name/section.
UI is localized **EN / RU / UZ**, light + dark theme.

- **Repo:** https://github.com/MarufAkhmatov/ProjectNest (branch `main`) — renamed from
  `Dashboard-for-Sigmintation` on 2026-07-04; old URL auto-redirects. **Public repo** —
  consider making it private (bank-internal tool); not yet done, ask the user first.
- **Local (PRIMARY — always edit here):** `C:\Users\ASUS\Desktop\ProjectNest`
- **CI:** GitHub Actions (`.github/workflows/ci.yml`) — frontend typecheck+build,
  backend compile+selftest, runs on every push to `main`.
- **Docker:** `docker compose up -d --build` → `projectnest-backend` (stdlib API) +
  `projectnest-web` (nginx + built SPA) on :8080 (or `PN_WEB_PORT=xxxx` to override).

## Stack & how to run
- **Frontend**: Vite + React + TS. Built to `dist/` via `npm run build`. `npm run typecheck`
  runs `tsc --noEmit` (tsconfig.json added 2026-07-04 — didn't exist before).
- **Backend**: **Python 3.14 stdlib HTTP server** (`backend/server.py`). Stdlib +
  `openpyxl`, `pymupdf` (PDF), `python-docx`, `Pillow`, `pytesseract` (OCR). No pandas/
  pydantic/FastAPI (don't build on 3.14).
- **Local AI**: Ollama, fully local (no Anthropic API calls in production) — model
  `temur` (qwen2.5:7b-instruct based, custom Modelfile), embeddings `nomic-embed-text`.
  CPU-only machine: cold start ~2 min, warm reply ~20s, full RAG rebuild ~40 min for
  ~870 issues (but **incremental** — see RAG section below, so this is rare).

### ★ PRODUCTION model — ONE resilient process on :8080
- `backend/server.py` serves **both** the SPA (`dist/`) **and** `/api` on one port
  (env `PN_PORT`, prod = 8080). Same-origin → no proxy.
- **Auth**: `/api/login`, `/api/logout`, `/api/me`; all other `/api/*` require a valid
  HMAC-signed `pn_session` cookie. `/api/health` public. Credentials in
  `storage/auth.json` (gitignored, multi-user `{"users":[...]}` format).
- **Resilience**: `serve-prod.ps1` watchdog — polls every **5s** (tightened 2026-07-05,
  was 15s), restarts Python hidden if :8080 is down, pins `PN_PORT=8080`. Scheduled
  Task **"ProjectNest"** (AtLogOn) runs it. If dead: `Start-ScheduledTask -TaskName ProjectNest`.
- ⚠️ **Known recurring trap**: an OLD watchdog from the original `Downloads\...` path can
  reappear (someone manually launches `serve-prod.ps1` from there) and race for :8080
  with STALE code/data. **First check whenever "changes aren't showing up":**
  `Get-NetTCPConnection -LocalPort 8080` → owning process's CommandLine MUST point at
  `Desktop\ProjectNest\backend\server.py`. Kill anything else holding :8080.

### Dev model
- `npm run dev` → http://localhost:5173, proxies `/api` → :8077.
- `python backend/server.py` (default 8077 dev port).

---

## Data reality — daily Jira exports (IMPORTANT, changed 2026-07-10)
6 files, both PMD and PMO now export **both CSV and HTML** (PMD used to be HTML-only):
1. **PMD CSV** — rich (owner, change leader, justification/goals/DoD/business-eff, etc).
2. **PMD HTML** (issuetable format) — supplementary, real display names.
3. **PMO CSV** — same, PMO project.
4. **PMO HTML** — supplementary for PMO.
5. **PMD History (Current fields) XLSX** — changelog → exact TTM.
6. **PMO History XLSX** — same for PMO.

**Correct re-ingest order** (mirrors the frontend's own `uploadBatch()` sort — alpha,
non-history first, history last): PMD CSV (**replace**) → PMD HTML (**merge**) → PMO CSV
(**merge**) → PMO HTML (**merge**) → PMD History → PMO History.
- CSV = rich/authoritative (full overwrite by key). HTML = supplementary (**fills blank
  fields only**, never clobbers CSV data).
- **Current active dataset** (as of 2026-07-10): ~870 issues / 139 epics / [PMD, PMO].
- **After parser/normalize.py change → bump `_PARSE_SCHEMA` in `server.py`** (currently
  `"v6-owner-dept-restore-epicname-fallback"`) — the on-disk parse cache is keyed by
  file-hash + this string; without bumping it, re-uploading the SAME file bytes silently
  serves the OLD parsed shape.
- **Without History XLSX, TTM phases collapse** (Delivery=0, Lead=0).

### Full field list now captured (`normalize.py` issue dict)
`key, project, type, is_epic, status, status_group, summary, description, pm, assignee,
reporter, owner, owner_department, change_leader, justification, goals,
definition_of_done, business_effectiveness, smart_checklist_progress,
smart_checklist_items, created, resolved, due, epic_key, story_points, priority,
project_type, regulator, division, scoring, quarterly_status, comments, links, history`

**Person/accountability fields (added 2026-07-05/06):**
- `owner` — from **"Владелец"** (the important one; "ФИО владельца" only a fallback).
  This is who's accountable and who recommendations address action items to.
- `owner_department` = `_get(row,"division")` ("Подразделение заказчика") **or**
  `_get(row,"epic_name")` ("Epic Name") as fallback. Per the user (2026-07-10, confirmed
  twice after an initial wrong guess): these — plus the concept "Подразделение
  владельца" — are ALL the same thing in this bank's PMD workflow; PMD's team
  repurposes "Epic Name" to hold the department when the division field is blank
  (division IS filled on ~93% of PMD rows, but when it's not, Epic Name is the real
  data, not noise — do NOT drop this fallback again without asking). UI shows ONE
  unified field labeled "Owner's department" (the old separate "Customer Division"
  row was redundant and removed from `IssueDetailHost.tsx`).
- `change_leader` — PMO: `Change leader`; PMD: `Approver`/`Approved by` (the stakeholder
  driving the item — used for the Change-Leaders analytics panel).

**Epic/feature "passport" fields (added 2026-07-10):**
- `justification` (Обоснование), `goals` (Цели), `definition_of_done` (Задачи DoD),
  `business_effectiveness` (Бизнес-эффективность) — free text, truncated to 300 chars
  when embedded in RAG, 400 when sent to the LLM as facts.
- `smart_checklist_progress` — clean ratio ("6/6 - Done"). `smart_checklist_items` —
  cleaned ✓/○ list, parsed out of Jira Smart Checklist's verbose serialized-object dump
  via `normalize._parse_smart_checklist()` (regex-based, best-effort; raw blob is NEVER
  stored). PMD-only in practice today; PMO doesn't export these 3.
- `_get()` in `normalize.py` also now strips a leading `'` — an Excel/Jira CSV artifact
  that force-texts cells starting with `-` (very common on bullet-list fields).

---

## Person identity resolution (added 2026-07-06) — `backend/app/identity.py`
**Problem**: the SAME human appears under different name-strings depending on which
export wrote it — a custom field with only an email becomes an INITIAL form via
`normalize._pretty_person()` ("o.saidov@bank.uz" → "O. Saidov"), while an HTML export
carries the FULL display name ("Ozod Saidov"). A CSV (overwrites) and HTML (fills-blanks-
only) landing on DIFFERENT epics for the same person leaves BOTH forms live at once —
splitting that person across two PM-Leaderboard rows / two Change-Leader cohorts / two
Owner counts.
**Fix**: `identity.resolve_identities(issues)` groups all `pm`/`owner`/`change_leader`
values dataset-wide by (last-name, first-name-or-initial-prefix) — full names bucket by
EXACT match (so two genuinely different first names sharing a surname never merge);
initial forms (incl. 2-letter Uzbek/Russian digraphs like "Sh"→"Shakhzoda") route to the
matching full-name bucket by prefix. Runs **automatically** in `server.py::_ingest_path()`
after every merge, before `aggregate.build()` — no action needed on future uploads.
**Known gap**: Uzbek patronymic-suffix names ("Firstname Middlename угли/қизи", 4 tokens)
use `toks[-1]` as the grouping key which is the suffix, not a real surname — currently
harmless (no false merges observed) but would need `_parse_person()` extended if a
duplicate ever surfaces for such a name.
One-off fix script for a dataset already loaded (no re-upload needed):
`python backend/scripts/fix_identities.py` (idempotent).

---

## Temur AI — dashboard control (added 2026-07-04) — `backend/app/aria.py` + `src/app/actions.ts`
Temur doesn't just chat — it can **drive the UI**. `aria.detect_action(question, pm_names,
last_action, history)` deterministically (no LLM, instant) maps natural-language commands
(EN/RU/UZ, incl. Latin-typed Russian) to ~20 action types: navigate pages, calendar
filters (year/month/day/mode), TTM modal + trend panel, drill-downs (by state/status/PM
name/period, incl. free-text topic search with Cyrillic↔Latin transliteration), kanban,
risk cohorts/panels, PM leaderboard period, flow granularity, theme, UI language,
celebrations toggle, close-all-popups, "back", and **"open them"** (extracts issue keys
from Temur's own last answer and opens them together in one drill list). Contextual
refinement: a short follow-up ("tip epic", "2025 uchun") tweaks the LAST action instead
of being treated as a fresh question (guarded so real questions don't get swallowed).
Frontend: `runDashboardAction()` in `actions.ts` turns the action dict into the same
CustomEvents the on-screen buttons fire. Full scenario catalog: `docs/TEMUR_SENARIYLAR.md`.
**Conversation memory + UI-state awareness**: the frontend sends the last ~8 messages and
current page/popup to `/api/aria`; Temur's prompts include this so follow-ups and "what's
on my screen" questions work. Page-scope (issue card open) answers pull the FULL issue
record (not just visible fields) and ASSESS it like an analyst (age, blockers, stage) —
see the RAG section below for how regulations get pulled in too.

---

## RAG — knowledge base + regulations grounding — `backend/app/rag.py` + `docs.py`
Local vector index (`ai/vector_db/index.json`), embeds with `nomic-embed-text` via Ollama.
Three record kinds in one corpus: `issue` (every Jira issue, compact doc via
`rag._issue_doc()`), `kb` (plain .md/.txt in `knowledge_base/`), `doc` (real bank
documents in **`knowladgebasefromdocs/`** — user drops PDFs/DOCX/scans/images there,
`docs.py` extracts text, OCR's scanned pages with Tesseract rus+uzb+uzb_cyrl+eng, caches
extracted text by content-hash so OCR runs once).
- **`knowladgebasefromdocs/` is gitignored** (confidential bank docs — structure, project/
  committee/PMO-department regulations, new-product policy) — only `README.md` +
  `.gitkeep` are tracked. Currently has 6 real documents loaded.
- **Incremental rebuild**: `rag.build_index()` reuses existing vectors keyed by
  `(id, sha1(text))` — only issues/docs whose text actually CHANGED get re-embedded. A
  batch of 5+ uploads used to trigger a rebuild per-file that raced and left a
  partial/stale index (fixed 2026-07-10 with a `pending`-flag debounce in
  `server.py::_rebuild_rag_async()` — a request during a build now re-runs the build once
  more against the final dataset instead of being dropped).
- **`rag.build_docs_only()`**: fast path to index JUST the documents (a few minutes)
  without re-embedding all ~870 issues — use this after adding a new document.
- **`kinds` filter (added 2026-07-10)**: `search()`/`context_block()` take an optional
  `kinds: set[str]` param. Without it, `[DOC]`/`[KB]`/`[ISSUE]` compete purely on query-
  relevance, so a query resembling an issue's own text can crowd out regulation chunks.
  `aria.py`'s `recommend_issue()` and the page-scope issue analysis both pass
  `kinds={"doc"}` for their regulation retrieval — grounding is now **structurally
  guaranteed**, not gambled on query phrasing.
- **Verified working**: PMD-780's recommendation cites both its own numbers (153.7 млрд
  сум projected volume, RICE score) AND specific regulation sections ("Положению о
  проектном комитете раздел 3.1", "раздел 17", "раздел 18") in the same response.

---

## Change-Leaders analytics (added 2026-07-05/06)
`metrics/engines.change_leaders(issues, stuck_days=100)` groups every epic/new-feature by
`change_leader` — workload (total/done/open/declined), departments, and items **STUCK
100+ days** in an early stage (BACKLOG/VALIDATION/NEED INFO/ANALYSIS/INITIATION) via
`_age_days()` (days since entering the CURRENT status, from changelog history). Endpoint
`/api/change-leaders?stuck_days=100`. Frontend: `ChangeLeadersModal.tsx` (By-Leader +
Stuck tabs), header 👥 button, Temur action ("change leaderlarni ko'rsat" / "qotib qolgan
epiklar").
**Temur's stuck-item advice** (`recommend_issue()` in aria.py): for a long-stalled item,
the recommendation is NOT "push it forward" — it tells the **owner** to hand it to
Business Analysis to re-verify the market demand is still real, then gives the **change
leader** an explicit STOP-or-CONTINUE call. Verified on real data (PMO-41, 649d in
ANALYSIS).

---

## Backend layout (`backend/app/`)
- `parser.py` — CSV/XLSX/HTML. `_parse_jira_issuetable()` (HTML issuetable format) now
  **generically captures arbitrary custom columns**: maps `customfield_XXXXX` header
  labels (from `<th class="headerrow-customfield_X">`) to their real names, stores data
  cells under both canonical AND real-label keys — so any NEW Jira custom field just
  needs an alias in `normalize.py`, no parser change. `_parse_jira_printable()` (older
  format) is similarly generic via a `<b>Label:</b>` regex.
- `normalize.py` — `_ALIASES` dict (canonical field → raw column-header variants,
  case-insensitive EXACT match via `_get()`), person-name prettification, comment
  cleaning, status canonicalization (+ mixed-script Cyrillic/Latin detection),
  `_parse_smart_checklist()`. See "Full field list" above.
- `identity.py` — person name-variant resolution (see section above).
- `docs.py` — document text extraction (PDF/DOCX/XLSX/images/HTML) + OCR for the RAG
  knowledge base.
- `rag.py` — vector index build/search/context_block (see RAG section above).
- `config.py` — status taxonomy, paths.
- `metrics/engines.py` — `issue_ttm`, `ttm_analysis`, `portfolio_kpis`, `project_health`
  (0–100, = Top Projects %, NOT completion), `pm_leaderboard(_period)`, `filter_issues`
  (supports `text=` fuzzy topic search and `keys=` multi-key lookup), `calendar_events`,
  `risk_insights`, `flow_balance`, `epic_quality`/`epic_problems`, `change_leaders`,
  `_age_days`, `STUCK_STAGES`.
- `aggregate.py` — `top_projects` = top 3 epics by `project_health`.
- `aria.py` — **Temur AI**. `ask()` (main entry — action detection → page-scope →
  general chat, all with conversation history + UI-state), `recommend_issue()`,
  `recommend_epic_quality()`, `detect_action()` (dashboard control), `_action_message()`.
- `storage.py` — `storage/current/dataset.json` + status audit + parse-cache.
- `server.py` — HTTP handler, multi-user auth, `_ingest_path()` (upload → parse → merge
  → **identity resolution** → aggregate → save → async RAG rebuild), `_PARSE_SCHEMA`.

## Frontend layout (`src/app/`)
- `main.tsx` — Theme → I18n → AuthGate → Portfolio → App.
- `actions.ts` (2026-07-04) — `runDashboardAction()`, the Temur→UI action bus.
- `portfolio.tsx` — API context. `changeLeaders(stuckDays)` added 2026-07-05.
- `App.tsx` — header controls incl. 👥 Change-Leaders button; listens for Temur's
  `pn-nav`/`pn-cal`/`pn-risk`/`pn-*` CustomEvents; page switch `dashboard|calendar|risk`.
- `components/ChangeLeadersModal.tsx` (2026-07-05) — By-Leader / Stuck-100+-days tabs.
- `components/IssueDetailHost.tsx` — issue popup. Fields incl. Owner/Owner's dept/Change
  leader, and (2026-07-10) Justification/Goals/DoD/Business-effectiveness (as dedicated
  text blocks matching the Quarterly-Status pattern) + Checklist progress/items.
- `components/AdminPanel.tsx` — user management (admin only).
- `components/CalendarView.tsx`, `RiskDashboard.tsx` — Calendar / Risk pages.
- `popup.ts` — `usePopupOpen`, `useTemurBesidePad`, `setPageContext`, `setUiView` (Temur
  UI-state awareness).
- `i18n.tsx` — EN/RU/UZ. Search for `f_owner`, `f_justification`, `cl_` (Change-Leaders),
  admin panel keys.

## Key endpoints
```
/api/health (public) · /api/me · /api/login · /api/logout
/api/dashboard · /api/analytics · /api/uploads
/api/ttm · /api/issues (scope/state/pm/status/period/text/keys) · /api/issue · /api/issue-summary · /api/issue-recommend
/api/pm-leaderboard · /api/notifications · /api/data-quality · /api/status-audit
/api/calendar?mode=resolved|created
/api/risk · /api/change-leaders?stuck_days=100 · /api/flow?granularity=
/api/epic-quality?project=PMD&days=90 · /api/epic-quality-recommend?key=&lang=
/api/analyze (POST) · /api/aria (POST {question,lang,scope,context,mode,probe,history,ui,last_action})
/api/temur/status · /api/temur/rebuild-rag (POST, admin)
/api/admin/users (GET+POST) · /api/admin/users/reset · /api/admin/users/delete
```

---

## DONE 2026-07-10 session (this session — see individual commits for detail)
1. **Rebrand + repo hygiene**: title/README/package.json ProjectNest (was Figma template
   "Clone Web Page with Animation"); deleted unused healthcare-template components
   (GlucoseGauge/HRVChart/StressRecoveryChart/SuggestedSteps, figma import assets);
   renamed PatientFlowChart→ProjectFlowChart, HealthcareProviders→PmLeaderboard,
   WellnessChart→DeliveryFlowChart; `.gitignore` hardened (secrets/binaries); GitHub repo
   renamed `Dashboard-for-Sigmintation`→`ProjectNest`.
2. **CI/CD**: `.github/workflows/ci.yml` added. **Docker**: old broken postgres/chroma
   compose replaced with the actually-working stdlib-backend+nginx stack, renamed
   `projectnest-*`.
3. **Audit fixes**: Temur's Send button threw (MouseEvent passed into a string param);
   AdminPanel's Temur-beside padding applied to the wrong element; `tsconfig.json` added.
4. **Temur dashboard control** (`actions.ts` + `aria.detect_action`): ~20 action types,
   conversation memory, UI-state awareness, contextual refinement, "open them" (opens
   issue keys from Temur's own last answer), translit-Russian command support, fuzzy
   translit-tolerant topic search, faster watchdog (5s poll).
5. **Owner/Owner's-department/Change-Leader fields**: read from Владелец / Подразделение
   заказчика (same field for both projects — see "Full field list" above, corrected
   later same day) / Change leader(PMO)-Approver(PMD); shown in issue popup; embedded
   in RAG; recommendations address the owner by name.
6. **Person identity resolution** (`identity.py`): dedups PM/owner/change-leader name
   variants dataset-wide (see section above). Fixed a live-data bug (parse-cache didn't
   invalidate on schema change → served owner-less records after the code shipped).
7. **Change-Leaders analytics + stuck-item detection + Temur BA-handoff advice** (see
   sections above).
8. **Knowledge base RAG** (`docs.py` + `rag.py` docs integration): OCR'd 6 real bank
   documents, incremental+docs-only rebuild paths, `kinds` filter fix for grounding.
9. **Epic/feature "passport" fields** (justification/goals/DoD/business-effectiveness/
   Smart-Checklist): read, shown in UI, embedded in RAG, fed into Temur's recommendation
   facts alongside doc-filtered regulation retrieval. Also fixed a general Excel
   leading-apostrophe CSV artifact affecting all text fields.
10. Live dataset re-ingested with all of the above (870 issues / 139 epics); RAG fully
    rebuilt; verified end-to-end in browser (PMD-780 popup + grounded recommendation
    citing specific regulation sections).
11. **owner_department unified with customer division** (see "Full field list" above)
    — removed the buggy PMD-specific "Epic Name" fallback; dropped the now-redundant
    "Customer Division" field row from `IssueDetailHost.tsx`.
12. **Dependencies-field JS-junk bug fixed** (`normalize._get_links()`): matching was too
    broad (`"link" in column_name`), catching the unrelated JSD field "Linked major
    incidents" whose HTML export cell is an unrendered JS widget stub — was showing as
    `depends on resourcePhaseCheckpoint.defer.then(() => WRM.require(...))` in the
    popup. Narrowed to the real link-relationship column pattern + a defensive
    JS-syntax value filter. Real Blocks/Depends/Relates links (364 issues) unaffected.
13. **owner_department correction reverted then re-fixed correctly**: item 11 above
    initially DROPPED the Epic Name fallback (assumed it was noise from one example,
    "Payme QR"). The user corrected this — Epic Name genuinely IS how PMD records the
    department when division is blank; restored the fallback (division → epic_name).
    Lesson: don't override the user's stated data-model knowledge based on a single
    example that merely LOOKS wrong.

## DONE 2026-06-21 session
- Multi-user auth + Admin Panel (`storage/auth.json` `{"users":[...]}` format, 20
  accounts). Project relocated Downloads→`Desktop\ProjectNest`.

## DONE 2026-06-16/18 session
- New-epic Quality Alert (`EpicQualityModal`, `epic_quality`/`epic_problems` engine).
- Top Projects redesign, Delivery Flow segmented bars, mobile chart height fixes.

## DONE (earlier)
- Calendar page, Risk Dashboard, Delivery Flow panel, Temur scope-choice (page/global),
  single-process server, login auth, watchdog, Scheduled Task, LAN/QR access.

---

## NEXT (pending, no work started)
- **Epic-quality checks for new fields**: `epic_problems()` doesn't yet flag missing
  justification/goals/DoD as quality issues (deliberately out of scope so far — only
  RAG-grounding was requested; ask before extending).
- **assignee/reporter identity resolution**: only pm/owner/change_leader are deduped
  today; assignee/reporter could have the same email-vs-display-name split issue.
- **One empty source file**: `knowladgebasefromdocs/politics/Politika po novim
  produktam (1).pdf` was 0 bytes (bad copy) — user was asked to replace it; a NEWER
  correctly-sized version WAS added and indexed (2026-07-05), but worth double-checking
  nothing else in that folder is silently empty.
- **Repo visibility**: still public on GitHub — flagged to the user, not yet changed.
- **Uzbek patronymic-suffix names** in identity.py — documented gap, no action needed
  unless a real duplicate surfaces.
- Product Teams TTM, Postgres + RBAC/SSO — long-standing, not started.

---

## Gotchas
- **Primary project path:** `C:\Users\ASUS\Desktop\ProjectNest` — always edit here.
- **:8080 split-brain**: see the ⚠️ note under "PRODUCTION model" above — check the
  owning process's CommandLine FIRST whenever changes don't seem to apply.
- **Parse-cache invalidation**: any `parser.py`/`normalize.py` field-shape change needs
  a `_PARSE_SCHEMA` bump in `server.py`, or re-uploads of the same file silently keep
  serving the old parsed shape.
- **RAG rebuild cost**: full corpus (~870 issues) embed ≈ 40 min on this CPU-only
  machine (~2.75s/embed). The incremental design means this only happens once after a
  wide-reaching change (e.g. adding a new field to `_issue_doc()`); routine daily
  uploads only re-embed the issues that actually changed.
- **`knowladgebasefromdocs/`** contains confidential bank documents — gitignored, never
  commit real files from it (only `README.md`/`.gitkeep` are tracked).
- Login case-sensitive: `Admin` (capital A). PM logins: lowercase email.
- Python 3.14: stdlib only (+openpyxl, pymupdf, python-docx, Pillow, pytesseract).
- After backend code change → restart server (kill :8080 python; watchdog relaunches
  in ≤5s).
- **Without History XLSX, TTM phases collapse** (Delivery=0, Lead=0).
- **Top Projects %** = `project_health` score (0–100), NOT completion.
- `recharts` inside flex needs a **definite `height`** on mobile, not just min-height.
- `useTemurBesidePad()` returns a full `padding` shorthand (don't mix with longhand).
- Bash tool piping Cyrillic through `python -c "print(...)"` without
  `PYTHONIOENCODING=utf-8` mangles terminal OUTPUT ONLY (cosmetic) — the underlying
  JSON/UTF-8 data is fine; don't mistake this for a real bug when debugging via curl+python.
