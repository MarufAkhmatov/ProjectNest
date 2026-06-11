"""Zero-dependency stdlib HTTP server for the Portfolio Intelligence Platform.

Runs on any Python 3.11+ with NO pip installs for CSV ingestion.
(XLSX needs openpyxl, HTML uses a stdlib fallback.) The FastAPI app in
app/main.py is the documented production entrypoint; this server is the
always-runnable equivalent that reuses the exact same engines.

Run:  python backend/server.py   ->  http://localhost:8000
"""
import json
import hashlib
import datetime as dt
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path

from app import parser, normalize, aggregate, aria, storage, config

PORT = 8077


def _ingest_path(path: Path, filename: str):
    raw = path.read_bytes()
    h = hashlib.sha256(raw).hexdigest()[:16]
    issues = storage.parse_cache_get(h)          # fast path: cached parse
    nrows = None
    if issues is None:
        rows = parser.parse_file(path)
        nrows = len(rows)
        if not rows:
            raise ValueError(
                "This file has no data table — it looks like a Jira login/auth page, "
                "not an export. In Jira open your filter (project = PMD OR project = PMO), "
                "then Export -> 'Excel CSV (all fields)' (or Printable HTML / XLSX) and upload that."
            )
        issues = normalize.normalize_rows(rows)
        if not issues:
            cols = ", ".join(list(rows[0].keys())[:12])
            raise ValueError(
                "Found a table but no issue-key column was recognised. "
                f"Detected columns: [{cols}]."
            )
        storage.parse_cache_put(h, issues)        # cache parsed/normalized issues
    payload = aggregate.build(issues)
    meta = {
        "filename": filename, "stored_as": path.name, "rows": nrows if nrows is not None else len(issues),
        "issues": len(issues), "epics": payload["kpis"]["total_epics"],
        "cached": issues is not None and nrows is None,
        "uploaded_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    storage.set_current({"issues": issues, "payload": payload}, meta)
    return meta, payload


def _seed_if_empty():
    if storage.load_current() is None:
        sample = config.TEMP / "sample_jira.csv"
        if sample.exists():
            _ingest_path(sample, "sample_jira.csv")
            print("Seeded dashboard with sample dataset.")


def _payload():
    data = storage.load_current()
    return data.get("payload") if data else None


class Handler(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass

    def do_OPTIONS(self):
        self._send({}, 204)

    def do_GET(self):
        route = urlparse(self.path).path
        if route == "/api/health":
            return self._send({"status": "ok", "has_data": storage.load_current_meta() is not None,
                               "active": storage.load_current_meta()})
        if route == "/api/dashboard":
            p = _payload()
            if not p:
                return self._send({"has_data": False})
            return self._send({"has_data": True, "meta": storage.load_current_meta(),
                               "widgets": p["widgets"], "kpis": p["kpis"]})
        if route == "/api/analytics":
            p = _payload()
            if not p:
                return self._send({"has_data": False})
            return self._send({"has_data": True, **p["analytics"]})
        if route == "/api/uploads":
            return self._send({"history": storage.upload_history()})
        if route == "/api/pm-leaderboard":
            data = storage.load_current()
            if not data:
                return self._send({"has_data": False, "rows": []})
            from app.metrics import engines as E
            period = parse_qs(urlparse(self.path).query).get("period", ["all"])[0]
            return self._send({"has_data": True, **E.pm_leaderboard_period(data["issues"], period)})
        return self._send({"error": "not found"}, 404)

    def do_POST(self):
        route = urlparse(self.path).path
        qs = parse_qs(urlparse(self.path).query)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""

        if route == "/api/upload":
            filename = qs.get("filename", ["upload.csv"])[0]
            saved = storage.save_upload(filename, body)
            try:
                meta, payload = _ingest_path(saved, filename)
            except Exception as e:
                return self._send({"ok": False, "error": str(e)}, 422)
            return self._send({"ok": True, "meta": meta, "kpis": payload["kpis"]})

        if route == "/api/aria":
            try:
                q = json.loads(body or b"{}").get("question", "")
            except Exception:
                q = ""
            p = _payload()
            if not p:
                return self._send({"answer": "No portfolio dataset uploaded yet.", "source": "system"})
            return self._send(aria.ask(q, p))

        return self._send({"error": "not found"}, 404)


if __name__ == "__main__":
    _seed_if_empty()
    print(f"Portfolio Intelligence API -> http://localhost:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
