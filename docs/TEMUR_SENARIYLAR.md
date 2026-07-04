# TEMUR AI — Foydalanuvchi senariylari va dashboard boshqaruvi

Temur endi ikki narsani qiladi:

1. **Javob beradi** — portfel ma'lumotlari (RAG + analytics) asosida savollarga.
2. **Dashboardni boshqaradi** — sahifalarni almashtiradi, popup/panellarni ochadi,
   filtrlarni (yil, oy, kun, chorak, tip, PM, status, davr) qo'llaydi, tema/tilni
   almashtiradi, oynalarni yopadi.

Buyruq oqimi: savol → `backend/app/aria.py :: detect_action()` (deterministik,
UZ/RU/EN) → action JSON → `src/app/actions.ts :: runDashboardAction()` →
CustomEvent → tegishli komponent. LLM kutilmaydi — UI bir zumda javob beradi.

---

## A. BOSHQARUV SENARIYLARI (Temur UI'ni harakatga keltiradi)

### A1. Sahifa navigatsiyasi

| Ibora (UZ / RU / EN) | Action |
|---|---|
| «kalendarni och» / «открой календарь» / "open the calendar" | `calendar` → Kalendar sahifasi |
| «risk sahifasiga o't» / «перейди на риск-монитор» / "go to the risk page" | `navigate: risk` |
| «bosh sahifani och», «dashboardga qayt» / «покажи главный дашборд» / "open the dashboard" | `navigate: dashboard` |

### A2. Kalendar filtrlari (yil / oy / kun / hafta + rejim)

| Ibora | Natija |
|---|---|
| «kalendarda 2025 yilni ko'rsat» | Kalendar → yillik ko'rinish, 2025 |
| «2025 dekabr oyini kalendarga chiqar» / «открой календарь за декабрь 2025» | Oylik ko'rinish, 2025-12 |
| «kalendarda 15 dekabr 2025 ni och» | Kunlik ko'rinish, 2025-12-15 |
| «bugungi kalendarni ko'rsat» / «календарь на сегодня» / "today's calendar" | Kunlik, bugun |
| «kalendarni haftalik qil» / «покажи по неделям» | Haftalik ko'rinish |
| «kalendarda yaratilgan loyihalarni ko'rsat» / «созданные в календаре» | Rejim: **Created** |
| «kalendarda yopilganlarni ko'rsat» / «закрытые в календаре» | Rejim: **Resolved** |
| «keyingi oyga o't kalendarda» / «kalendarda oldingi hafta» | Davr qadam ±1 |
| «kalendarni kattalashtir / kichiklashtir» | Zoom ± |

### A3. TTM tahlili (modal) va TTM trend paneli

| Ibora | Natija |
|---|---|
| «TTM tahlilini och» / «открой анализ TTM» / "open TTM analysis" | TTM modal (barcha turlar) |
| «2026 yil uchun TTM ni ko'rsat» | TTM modal, davr = 2026 |
| «2025 Q3 TTM» / «TTM за 3 квартал 2025» | TTM modal, chorak = 2025-Q3 |
| «2026 mart oyi uchun epiklar TTM i» | TTM modal, tip = Epic, oy = 2026-03 |
| «TTM trendini oylik qilib ko'rsat» / «тренд TTM по месяцам» | Dashboard trend paneli → oy kesimi |
| «TTM trendini ustunlar bilan ko'rsat» / «тренд линиями» | Panel ko'rinishi: bars/lines |
| «TTM trendini 2026 dan boshlab ko'rsat» | Panel scope: From 2026 |

### A4. Loyiha ro'yxatlari (drill-down popup)

| Ibora | Filtr |
|---|---|
| «yakunlangan loyihalarni ko'rsat» / «покажи завершённые» / "show completed projects" | state=completed |
| «2025 da yakunlangan loyihalar» | state=completed + period=year 2025 |
| «ochiq loyihalar ro'yxati» / «открытые проекты» / "open projects" | state=open |
| «rad etilgan loyihalar» / «отклонённые» / "declined" | state=declined |
| «testing bosqichidagi loyihalarni ko'rsat» / «покажи проекты в тестировании» | status=TESTING (backlog, validation, analysis, architecture, initiation, in progress, pilot ham ishlaydi) |
| «[PM ismi] loyihalarini ko'rsat» / «покажи проекты Саидова» | pm=… (aktiv PM ro'yxatidan avtomatik topiladi) |
| «[PM ismi] vazifalarini ko'rsat» | pm=… scope=tasks |
| «[PM] ning yakunlangan loyihalari 2025» | pm + state + period birga |

### A5. Issue kartochkasi

| Ibora | Natija |
|---|---|
| «PMD-123 ni och» / «открой PMD-123» / "open PMD-123" | Issue detail popup (AI xulosa + tavsiyalar bilan) |

### A6. Kanban

| Ibora | Natija |
|---|---|
| «kanban doskani och» / «открой канбан» / "open the kanban board" | Flow Kanban modal |

### A7. Risk monitori (kohortalar, panellar, metodologiya)

| Ibora | Natija |
|---|---|
| «kritik loyihalarni ko'rsat» / «покажи критичные» | Risk sahifasi → Critical kohorta popup |
| «xavf ostidagi loyihalarni och» / "show at-risk projects" | At-risk kohorta |
| «kechikkan loyihalarni ko'rsat» / «задержанные» | Delayed kohorta |
| «muddati o'tgan vazifalarni ko'rsat» / «просроченные» | Overdue kohorta |
| «bloklanganlarni och» / «заблокированные» / "show blocked items" | Blocked kohorta |
| «WIP ni ko'rsat» | WIP kohorta |
| «risk reyestrini katta qilib och» / «разверни реестр рисков» | Register panel maximize |
| «aging panelini ko'rsat», «heatmapni och», «insaytlarni ko'rsat» | Tegishli panel maximize |
| «risk metodologiyasini och» / «методология рисков» | Methodology modal |

### A8. PM reytingi va oqim (flow) paneli

| Ibora | Natija |
|---|---|
| «reytingni oylik qilib ko'rsat» / «лидерборд за месяц» / "leaderboard by month" | PM Leaderboard davri: month (week/quarter/year/all ham) |
| «oqim grafigini yillik qilib ko'rsat» / «поток по годам» | Created/Resolved paneli: year |

### A9. Sifat panellari, tahlil, admin

| Ibora | Natija |
|---|---|
| «ma'lumot sifatini och» / «качество данных» / "data quality" | Data-Quality modal |
| «yangi epiklar sifatini tekshir» / «качество новых эпиков» | Epic-Quality modal |
| «yangi vazifani tahlil qil» / «проанализируй новый отчёт» / "analyze a new task" | Analyze modal (o'xshash loyihalar qidiruvi) |
| «admin panelni och» / «открой админку» | Admin panel (faqat admin roli) |

### A10. Interfeys sozlamalari

| Ibora | Natija |
|---|---|
| «tungi rejimga o't» / «тёмная тема» / "dark mode" | Tema: dark |
| «kunduzgi rejim» / «светлая тема» / "light mode" | Tema: light |
| «temani almashtir» / «переключи тему» | Tema: toggle |
| «ruschaga o't» / «переключи на узбекский» / "switch to English" | Interfeys tili: ru / uz / en |
| «konfettini yoq / o'chir» / «включи поздравления» | Tabriklar on/off |
| «smart rejimga o't», «turbo rejim» / «режим turbo» | Temur javob rejimi (turbo/fast/smart) |
| «hamma oynalarni yop» / «закрой все окна» / "close all popups" | Barcha popup/modallar yopiladi |

---

## B. MA'LUMOT SAVOLLARI (LLM + RAG, action'siz)

Bular UI'ni harakatga keltirmaydi — Temur to'g'ridan-to'g'ri javob beradi
(portfel analitikasi + RAG indeksidan):

- **Portfel holati:** «portfel qanday ahvolda?», «nechta loyiha ochiq?», «completion nechchi foiz?»
- **Risklar (savol shaklida):** «qaysi loyiha eng riskli?», «nega X loyiha qizil zonada?»
- **TTM (savol shaklida):** «nega TTM oshyapti?», «o'rtacha lead time qancha?»
- **Blokerlar:** «nimalar bloklangan?», «X ni nima bloklayapti?»
- **PM samaradorligi:** «qaysi PM eng yaxshi ishlayapti?», «eng tez yetkazadigan PM kim?»
- **Issue tafsiloti:** «PMD-123 bo'yicha nima gap?» (kalit yozilsa kartochka ham ochiladi)
- **Fokus:** «bu chorakda menejment nimaga e'tibor berishi kerak?»
- **O'rgatish:** «eslab qol: …» — Temur faktni doimiy xotiraga yozadi
- **Yordam:** «nimalar qila olasan?» / «что ты умеешь?» / "what can you do?" — imkoniyatlar ro'yxati
- **Popup ichida:** biror popup ochiq bo'lsa Temur «shu sahifadan» yoki «butun portfeldan» deb so'raydi (page-scope)

---

## C. TEXNIK XARITA (action → event → komponent)

| Action turi | CustomEvent | Komponent |
|---|---|---|
| `navigate` | `pn-nav` | App.tsx (view switch) |
| `calendar` | `pn-nav` + `pn-cal` | CalendarView (mode/gran/date/step/zoom) |
| `open_ttm` | `pn-open-ttm` | App → TtmModal (type/period/value preset) |
| `ttm_panel` | `pn-nav` + `pn-ttm-panel` | TtmComparePanel (gran/type/scope/view) |
| `drill` | `pn-drill` | DrillDownHost (state/status/pm/period/value/type) |
| `open_issue` | `pn-issue` | IssueDetailHost |
| `open_kanban` | `pn-nav` + `pn-open-kanban` | PatientFlowChart → FlowKanbanModal |
| `risk` | `pn-nav` + `pn-risk` | RiskDashboard (cohort/panel/methodology; data kelguncha buferlanadi) |
| `pm_board` | `pn-nav` + `pn-pm-period` | HealthcareProviders (period) |
| `flow_panel` | `pn-nav` + `pn-flow-panel` | WellnessChart (granularity) |
| `open_dq` | `pn-open-dq` | App → DataQualityModal |
| `open_eq` | `pn-open-eq` | App → EpicQualityModal |
| `open_analyze` | `pn-open-analyze` | App → AnalyzeModal |
| `open_admin` | `pn-open-admin` | App → AdminPanel (faqat admin) |
| `theme` | `pn-theme` | ThemeProvider |
| `set_lang` | `pn-lang` | I18nProvider |
| `celebrations` | `pn-celebrations` | App (confetti toggle) |
| `close_popups` | `pn-close-popups` | App + barcha popup hostlar |
| `temur_mode` | (lokal) | AriaPanel (turbo/fast/smart) |

Eslatmalar:
- Action'lar **LLM'siz**, deterministik regex bilan aniqlanadi — javob bir zumda.
- PM ismlari aktiv datasetdagi `pm_leaderboard`dan olinadi (4+ harfli token mosligi).
- Ovozli buyruqlar ham xuddi shu yo'ldan o'tadi («Temur, kanbanni och»).
- Popup ochiq payt Temur o'ng tomonda suzuvchi dokda qoladi — ketma-ket buyruq berish mumkin.
