import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { X, ExternalLink } from "lucide-react";
import { usePortfolio } from "../portfolio";
import { jiraUrl } from "../jira";

function Field({ label, value, link }: { label: string; value: any; link?: string }) {
  const v = (value === null || value === undefined || value === "") ? "—" : String(value);
  return (
    <div style={{ minWidth: 0 }}>
      <div style={{ fontSize: "0.62rem", color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.4 }}>{label}</div>
      {link ? (
        <a className="jira-link" href={link} target="_blank" rel="noopener noreferrer" style={{ fontSize: "0.8rem", color: "var(--text)", fontWeight: 500 }}>{v}</a>
      ) : (
        <div style={{ fontSize: "0.8rem", color: "var(--text)", fontWeight: 500, wordBreak: "break-word" }}>{v}</div>
      )}
    </div>
  );
}

export function IssueDetailHost() {
  const { issueDetail, data } = usePortfolio();
  const base = data?.meta?.jira_base;
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState<any>(null);

  useEffect(() => {
    const handler = (e: Event) => {
      const { key } = (e as CustomEvent).detail;
      setOpen(true); setLoading(true); setRes(null);
      issueDetail(key).then((r) => { setRes(r); setLoading(false); });
    };
    window.addEventListener("pn-issue", handler);
    return () => window.removeEventListener("pn-issue", handler);
  }, [issueDetail]);

  const i = res?.issue;
  const url = i ? jiraUrl(i.key, i.url, base) : "#";

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={() => setOpen(false)}
          style={{ position: "fixed", inset: 0, background: "rgba(10,18,28,0.55)", backdropFilter: "blur(4px)", zIndex: 450, display: "flex", alignItems: "center", justifyContent: "center", padding: 22 }}
        >
          <motion.div
            initial={{ scale: 0.96, y: 16 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.96, y: 16 }}
            onClick={(e) => e.stopPropagation()}
            style={{ background: "var(--card)", borderRadius: 18, boxShadow: "0 30px 80px rgba(0,0,0,0.4)", width: 560, maxWidth: "95vw", maxHeight: "86vh", padding: 24, display: "flex", flexDirection: "column" }}
          >
            {loading || !i ? (
              <div style={{ padding: 30, textAlign: "center", color: "var(--muted)", fontSize: "0.85rem" }}>
                {loading ? "Loading…" : "Issue not found in the active dataset."}
                <div style={{ marginTop: 14 }}>
                  <button onClick={() => setOpen(false)} style={{ padding: "8px 16px", borderRadius: 9, background: "var(--surface2)", border: "none", cursor: "pointer", color: "var(--text)" }}>Close</button>
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-start justify-between" style={{ marginBottom: 14, gap: 10 }}>
                  <div style={{ minWidth: 0 }}>
                    <div className="flex items-center gap-2" style={{ marginBottom: 4 }}>
                      <a className="jira-link" href={url} target="_blank" rel="noopener noreferrer" style={{ fontSize: "0.85rem", fontWeight: 700, color: "#2d7a5f" }}>{i.key}</a>
                      <span style={{ fontSize: "0.62rem", fontWeight: 600, color: "#fff", background: i.is_epic ? "#9b59b6" : "#2d7a5f", borderRadius: 6, padding: "2px 7px" }}>{i.type}</span>
                      <span style={{ fontSize: "0.62rem", fontWeight: 600, color: "var(--text)", background: "var(--surface2)", borderRadius: 6, padding: "2px 7px" }}>{i.status}</span>
                    </div>
                    <div style={{ fontSize: "0.92rem", fontWeight: 600, color: "var(--text)", lineHeight: 1.3 }}>{i.summary || "—"}</div>
                  </div>
                  <button onClick={() => setOpen(false)} style={{ width: 30, height: 30, borderRadius: 9, background: "var(--surface2)", border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <X size={15} color="#6b7a8d" />
                  </button>
                </div>

                <div className="pn-scroll" style={{ overflowY: "auto", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px 18px", paddingRight: 6 }}>
                  <Field label="Project" value={i.project} />
                  <Field label="PM (custom)" value={i.pm} />
                  <Field label="Assignee" value={i.assignee} />
                  <Field label="Reporter" value={i.reporter} />
                  <Field label="Priority" value={i.priority} />
                  <Field label="Project type" value={i.project_type} />
                  <Field label="Customer division" value={i.division} />
                  <Field label="Regulator req." value={i.regulator} />
                  <Field label="Scoring" value={i.scoring} />
                  <Field label="Created" value={(i.created || "").slice(0, 10)} />
                  <Field label="Resolved" value={(i.resolved || "").slice(0, 10)} />
                  <Field label="Due date" value={(i.due || "").slice(0, 10)} />
                  <Field label="Duration (days)" value={res.duration_days} />
                  {i.epic_key && <Field label="Epic link" value={i.epic_key} link={jiraUrl(i.epic_key, "", base)} />}
                  {res.children?.length > 0 && <Field label="Child items" value={res.children.length} />}
                  {i.links?.length > 0 && <Field label="Dependencies" value={i.links.map((l: any) => `${l.type} ${l.target}`).join(", ")} />}
                </div>

                <div className="flex items-center justify-end gap-2" style={{ marginTop: 18 }}>
                  <button onClick={() => setOpen(false)} style={{ padding: "8px 16px", borderRadius: 10, background: "var(--surface2)", border: "none", cursor: "pointer", fontSize: "0.8rem", color: "var(--text)", fontFamily: "var(--font-sans)" }}>Close</button>
                  <a href={url} target="_blank" rel="noopener noreferrer" style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 18px", borderRadius: 10, background: "linear-gradient(135deg,#2d7a5f,#4EB6A6)", color: "#fff", fontSize: "0.8rem", fontWeight: 600, textDecoration: "none" }}>
                    <ExternalLink size={14} /> Open in Jira
                  </a>
                </div>
              </>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
