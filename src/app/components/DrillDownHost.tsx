import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { X, ExternalLink } from "lucide-react";
import { usePortfolio } from "../portfolio";
import { jiraUrl } from "../jira";

const typeColor: Record<string, string> = {
  Epic: "#9b59b6", Task: "#2d7a5f", "New Feature": "#d4a84b", "Sub-task": "#6b7a8d",
};

export function DrillDownHost() {
  const { drill, data } = usePortfolio();
  const base = data?.meta?.jira_base;
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState<any[]>([]);
  const [count, setCount] = useState(0);

  useEffect(() => {
    const handler = (e: Event) => {
      const { title, params } = (e as CustomEvent).detail;
      setTitle(title);
      setOpen(true);
      setLoading(true);
      setRows([]);
      drill(params).then((r) => {
        setRows(r.issues || []);
        setCount(r.count ?? (r.issues || []).length);
        setLoading(false);
      });
    };
    window.addEventListener("pn-drill", handler);
    return () => window.removeEventListener("pn-drill", handler);
  }, [drill]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={() => setOpen(false)}
          style={{ position: "fixed", inset: 0, background: "rgba(10,18,28,0.5)", backdropFilter: "blur(4px)", zIndex: 350, display: "flex", alignItems: "center", justifyContent: "center", padding: 22 }}
        >
          <motion.div
            initial={{ scale: 0.96, y: 16 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.96, y: 16 }}
            onClick={(e) => e.stopPropagation()}
            style={{ background: "var(--card)", borderRadius: 18, boxShadow: "0 30px 80px rgba(0,0,0,0.35)", width: 640, maxWidth: "95vw", height: "min(80vh, 720px)", padding: 22, display: "flex", flexDirection: "column" }}
          >
            <div className="flex items-center justify-between" style={{ marginBottom: 10 }}>
              <div>
                <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text)" }}>{title}</div>
                <div style={{ fontSize: "0.72rem", color: "var(--soft)" }}>{loading ? "Loading…" : `${count} item${count === 1 ? "" : "s"}`}</div>
              </div>
              <button onClick={() => setOpen(false)} style={{ width: 30, height: 30, borderRadius: 9, background: "var(--surface2)", border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <X size={15} color="#6b7a8d" />
              </button>
            </div>

            {/* header row */}
            <div style={{ display: "grid", gridTemplateColumns: "110px 1fr 0.7fr 0.9fr 70px", gap: 8, fontSize: "0.66rem", color: "var(--muted)", paddingBottom: 6, borderBottom: "1px solid var(--divider)" }}>
              <span>Key</span><span>Summary</span><span>Status</span><span>PM</span><span style={{ textAlign: "right" }}>Days</span>
            </div>

            <div className="pn-scroll" style={{ flex: 1, minHeight: 0, overflowY: "auto", paddingRight: 6 }}>
              {!loading && rows.length === 0 && (
                <div style={{ padding: 18, fontSize: "0.8rem", color: "var(--muted)" }}>No matching issues.</div>
              )}
              {rows.map((r) => (
                <div key={r.key} style={{ display: "grid", gridTemplateColumns: "110px 1fr 0.7fr 0.9fr 70px", gap: 8, alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--divider)" }}>
                  <a className="jira-link" href={jiraUrl(r.key, r.url, base)} target="_blank" rel="noopener noreferrer" style={{ fontSize: "0.74rem", fontWeight: 600, color: "var(--text)", display: "flex", alignItems: "center", gap: 4 }}>
                    {r.key} <ExternalLink size={10} />
                  </a>
                  <a className="jira-link" href={jiraUrl(r.key, r.url, base)} target="_blank" rel="noopener noreferrer" title={r.summary} style={{ fontSize: "0.72rem", color: "var(--soft)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {r.summary || "—"}
                  </a>
                  <span style={{ fontSize: "0.66rem", color: typeColor[r.type] || "var(--soft)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={r.status}>{r.status}</span>
                  <span style={{ fontSize: "0.7rem", color: "var(--soft)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={r.pm}>{r.pm}</span>
                  <span style={{ fontSize: "0.7rem", color: "var(--muted)", textAlign: "right" }}>{r.duration_days ?? "—"}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
