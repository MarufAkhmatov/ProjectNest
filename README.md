# ProjectNest — Portfolio Intelligence

Jira PMD/PMO portfel dashboardi: epiklar, TTM analitikasi, risk monitori,
kalendar va lokal **Temur AI** assistenti (Ollama, offline).

## Nima qiladi

- **Portfolio dashboard** — KPI'lar, Delivery Flow, TTM trend, Top Projects, PM Leaderboard, Project Flow (kanban bilan)
- **Kalendar** — yopilgan/yaratilgan ishlar kun/hafta/oy/yil kesimida
- **Risk monitor** — risk reyestri, aging, bloklanganlar, PM heatmap, insaytlar
- **Temur AI** — savollarga javob beradi (RAG + lokal LLM) va dashboardni ovoz/matn bilan boshqaradi:
  sahifalarni ochadi, filtrlarni (yil/oy/kun/tip/PM/status) qo'llaydi, popuplarni ochib-yopadi.
  Senariylar: [docs/TEMUR_SENARIYLAR.md](docs/TEMUR_SENARIYLAR.md)
- **Ma'lumot manbai** — Jira eksportlari (CSV / XLSX / HTML), History XLSX bilan aniq TTM

## Ishga tushirish

```bash
npm install
npm run build          # frontend -> dist/
python backend/server.py   # http://localhost:8080 (SPA + API bitta portda)
```

Dev rejim: `npm run dev` (Vite, API proksi backendga).

Lokal AI (ixtiyoriy): `ai/setup-temur.ps1` — Ollama modellarini tortadi va RAG indeksini quradi.

## Struktura

```
backend/     Python HTTP server + analitika (app/metrics), Temur AI (app/aria.py, app/rag.py)
src/         React + Vite frontend (src/app/components — panellar va popuplar)
ai/          Ollama Modelfile'lar va sozlash skriptlari
docs/        Hujjatlar (Temur senariylari, handoff)
knowledge_base/  RAG uchun metodologiya hujjatlari
```
