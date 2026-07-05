import { useState, useEffect } from "react";
import { motion } from "motion/react";
import { X, Users, AlertTriangle, ChevronDown, ChevronRight, ExternalLink } from "lucide-react";
import { usePortfolio } from "../portfolio";
import { useI18n } from "../i18n";
import { openIssue } from "../issue";
import { statusColor } from "../status";
import { jiraUrl } from "../jira";
import { usePopupOpenSignal, useTemurBesidePad, setPageContext } from "../popup";

const RED = "#e0574f", GREEN = "#2e9e5f", AMBER = "#d4a84b", TEAL = "#0c5563";

/**
 * Change-leader analytics: every epic / new feature grouped by the change leader
 * (stakeholder driving it). Shows workload (total / done / open), and — the point
 * of the panel — items STUCK 100+ days in an early stage (Backlog / Validation /
 * Need Info / Analysis), which should be re-validated against the market before
 * more effort is spent. Click any row to open the issue; click "🧠" to ask Temur.
 */
export function ChangeLeadersModal({ onClose }: { onClose: () => void }) {
  const { changeLeaders, data } = usePortfolio();
  const { t: tr } = useI18n();
  const base = data?.meta?.jira_base;
  const [res, setRes] = useState<any>(null);
  const [open, setOpen] = useState<Set<string>>(new Set());
  const [tab, setTab] = useState<"leaders" | "stuck">("leaders");
  usePopupOpenSignal(true);
  const besidePad = useTemurBesidePad();

  useEffect(() => { changeLeaders(100).then(setRes); }, [changeLeaders]);

  const leaders: any[] = res?.leaders || [];
  const stuck: any[] = res?.stuck || [];

  // Publish as Temur page-context so "give advice on the stuck ones" is scoped.
  useEffect(() => {
    if (!res) return;
    const text =
      `Change leaders (${res.total_leaders}), items ${res.total_items}, stuck 100+ days ${res.total_stuck}.\n` +
      leaders.slice(0, 20).map((g) =>
        `${g.change_leader}: ${g.total} items, ${g.done} done, ${g.open} open, ${g.stuck} stuck`).join("\n") +
      "\nSTUCK ITEMS:\n" +
      stuck.slice(0, 40).map((s) => `${s.key} [${s.status}] ${s.age_days}d — ${s.summary}`).join("\n");
    setPageContext({ title: tr("cl_title"), text });
    return () => setPageContext(null);
  }, [res]);

  const toggle = (k: string) =>
    setOpen((p) => { const n = new Set(p); n.has(k) ? n.delete(k) : n.add(k); return n; });

  const pill = (active: boolean): React.CSSProperties => ({
    padding: "6px 14px", borderRadius: 999, border: "none", cursor: "pointer", fontSize: "0.74rem",
    fontWeight: active ? 700 : 500, background: active ? TEAL : "var(--surface2)",
    color: active ? "#fff" : "var(--soft)", fontFamily: "var(--font-sans)",
  });

  const StuckRow = ({ s }: { s: any }) => (
    <div style={{ display: "grid", gridTemplateColumns: "88px 1fr 84px 60px", gap: 8, alignItems: "center", padding: "7px 0", borderBottom: "1px solid var(--divider)" }}>
      <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
        <span className="jira-link" onClick={() => openIssue(s.key)} style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--text)", cursor: "pointer" }}>{s.key}</span>
        <a href={jiraUrl(s.key, s.url, base)} target="_blank" rel="noopener noreferrer" style={{ display: "flex", color: "#9aa5b4" }}><ExternalLink size={9} /></a>
      </span>
      <span onClick={() => openIssue(s.key)} style={{ fontSize: "0.72rem", color: "var(--soft)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", cursor: "pointer" }} title={s.summary}>{s.summary || "—"}</span>
      <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
        <span style={{ width: 7, height: 7, borderRadius: 2, background: statusColor(s.status) }} />
        <span style={{ fontSize: "0.62rem", color: "var(--muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{s.status}</span>
      </span>
      <span style={{ fontSize: "0.72rem", fontWeight: 700, color: RED, textAlign: "right" }}>{s.age_days}{tr("ttm_days") || "d"}</span>
    </div>
  );

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      onClick={onClose}
      style={{ position: "fixed", inset: 0, background: "rgba(10,18,28,0.5)", backdropFilter: "blur(4px)", zIndex: 340, display: "flex", alignItems: "center", justifyContent: "center", padding: 22, ...besidePad }}
    >
      <motion.div
        initial={{ scale: 0.96, y: 16 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.96, y: 16 }}
        onClick={(e) => e.stopPropagation()}
        style={{ background: "var(--card)", borderRadius: 18, boxShadow: "0 30px 80px rgba(0,0,0,0.35)", width: 720, maxWidth: "95vw", height: "min(84vh, 780px)", padding: 22, display: "flex", flexDirection: "column" }}
      >
        <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
          <div className="flex items-center gap-2">
            <Users size={18} color={TEAL} />
            <span style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text)" }}>{tr("cl_title")}</span>
            {res && <span style={{ fontSize: "0.72rem", color: "var(--muted)" }}>· {res.total_leaders} {tr("cl_leaders")}, {res.total_items} {tr("cl_items")}</span>}
          </div>
          <button onClick={onClose} style={{ width: 30, height: 30, borderRadius: 9, background: "var(--surface2)", border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <X size={15} color="#6b7a8d" />
          </button>
        </div>

        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <button style={pill(tab === "leaders")} onClick={() => setTab("leaders")}>{tr("cl_by_leader")}</button>
          <button style={{ ...pill(tab === "stuck"), display: "flex", alignItems: "center", gap: 6 }} onClick={() => setTab("stuck")}>
            <AlertTriangle size={13} /> {tr("cl_stuck")} {res ? `(${res.total_stuck})` : ""}
          </button>
        </div>

        <div className="pn-scroll" style={{ flex: 1, minHeight: 0, overflowY: "auto", paddingRight: 6 }}>
          {!res && <div style={{ padding: 18, color: "var(--muted)", fontSize: "0.85rem" }}>{tr("dd_loading")}</div>}

          {res && tab === "stuck" && (
            <>
              <div style={{ fontSize: "0.72rem", color: "var(--soft)", marginBottom: 8, lineHeight: 1.5 }}>{tr("cl_stuck_hint")}</div>
              {stuck.length === 0 ? <div style={{ padding: 12, color: "var(--muted)", fontSize: "0.82rem" }}>{tr("cl_no_stuck")}</div>
                : stuck.map((s) => <StuckRow key={s.key} s={s} />)}
            </>
          )}

          {res && tab === "leaders" && leaders.map((g) => {
            const isOpen = open.has(g.change_leader);
            return (
              <div key={g.change_leader} style={{ borderBottom: "1px solid var(--divider)" }}>
                <div onClick={() => toggle(g.change_leader)} style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 4px", cursor: "pointer" }}>
                  {isOpen ? <ChevronDown size={15} color="#9aa5b4" /> : <ChevronRight size={15} color="#9aa5b4" />}
                  <span style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--text)", flex: 1, minWidth: 0, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {g.change_leader === "—" ? tr("cl_unassigned") : g.change_leader}
                  </span>
                  <span style={{ display: "flex", gap: 6, alignItems: "center", flexShrink: 0 }}>
                    <Badge n={g.total} label={tr("cl_total")} color={TEAL} />
                    <Badge n={g.done} label={tr("cl_done")} color={GREEN} />
                    <Badge n={g.open} label={tr("cl_open")} color={AMBER} />
                    {g.stuck > 0 && <Badge n={g.stuck} label={tr("cl_stuck")} color={RED} />}
                  </span>
                </div>
                {isOpen && (
                  <div style={{ padding: "0 0 10px 23px" }}>
                    {g.departments?.length > 0 && (
                      <div style={{ fontSize: "0.64rem", color: "var(--muted)", marginBottom: 6 }}>{tr("cl_depts")}: {g.departments.join("; ")}</div>
                    )}
                    {g.items.map((s: any) => (
                      <div key={s.key} style={{ display: "grid", gridTemplateColumns: "88px 1fr 84px 60px", gap: 8, alignItems: "center", padding: "6px 0", borderBottom: "1px solid var(--divider)", opacity: s.done ? 0.55 : 1 }}>
                        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                          <span className="jira-link" onClick={() => openIssue(s.key)} style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--text)", cursor: "pointer" }}>{s.key}</span>
                          {s.stuck && <AlertTriangle size={11} color={RED} />}
                        </span>
                        <span onClick={() => openIssue(s.key)} style={{ fontSize: "0.7rem", color: "var(--soft)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", cursor: "pointer" }} title={s.summary}>{s.summary || "—"}</span>
                        <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                          <span style={{ width: 7, height: 7, borderRadius: 2, background: statusColor(s.status) }} />
                          <span style={{ fontSize: "0.6rem", color: "var(--muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{s.status}</span>
                        </span>
                        <span style={{ fontSize: "0.68rem", color: s.stuck ? RED : "var(--muted)", fontWeight: s.stuck ? 700 : 400, textAlign: "right" }}>{s.age_days != null ? `${s.age_days}${tr("ttm_days") || "d"}` : "—"}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </motion.div>
    </motion.div>
  );
}

function Badge({ n, label, color }: { n: number; label: string; color: string }) {
  return (
    <span title={label} style={{ fontSize: "0.66rem", fontWeight: 700, color: "#fff", background: color, borderRadius: 6, padding: "1px 7px", minWidth: 20, textAlign: "center" }}>{n}</span>
  );
}
