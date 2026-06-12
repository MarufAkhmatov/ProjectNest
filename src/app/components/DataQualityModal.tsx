import { useState, useEffect } from "react";
import { motion } from "motion/react";
import { X, Database, AlertTriangle, CheckCircle2 } from "lucide-react";
import { usePortfolio } from "../portfolio";

export function DataQualityModal({ onClose }: { onClose: () => void }) {
  const { dataQuality } = usePortfolio();
  const [dq, setDq] = useState<any>(null);

  useEffect(() => { dataQuality().then(setDq); }, [dataQuality]);

  const barColor = (p: number) => (p >= 80 ? "#2d7a5f" : p >= 40 ? "#d4a84b" : "#e07a7a");

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      onClick={onClose}
      style={{ position: "fixed", inset: 0, background: "rgba(10,18,28,0.5)", backdropFilter: "blur(4px)", zIndex: 300, display: "flex", alignItems: "center", justifyContent: "center", padding: 22 }}
    >
      <motion.div
        initial={{ scale: 0.96, y: 16 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.96, y: 16 }}
        onClick={(e) => e.stopPropagation()}
        style={{ background: "var(--card)", borderRadius: 18, boxShadow: "0 30px 80px rgba(0,0,0,0.35)", width: 520, maxWidth: "94vw", height: "min(80vh, 720px)", padding: 24, display: "flex", flexDirection: "column" }}
      >
        <div className="flex items-center justify-between" style={{ marginBottom: 6 }}>
          <div className="flex items-center gap-2">
            <Database size={18} color="#2d7a5f" />
            <span style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text)" }}>Data Quality — field coverage</span>
          </div>
          <button onClick={onClose} style={{ width: 30, height: 30, borderRadius: 9, background: "var(--surface2)", border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <X size={15} color="#6b7a8d" />
          </button>
        </div>

        {dq && dq.has_data !== false ? (
          <>
            <div style={{ fontSize: "0.78rem", color: "var(--soft)", marginBottom: 12 }}>
              {dq.total} issues · {dq.epics} epics (portfolio projects)
            </div>

            <div className="pn-scroll" style={{ flex: 1, minHeight: 0, overflowY: "auto", paddingRight: 6 }}>
              {(dq.fields || []).map((f: any) => (
                <div key={f.field} style={{ marginBottom: 12 }}>
                  <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
                    <span style={{ fontSize: "0.78rem", color: "var(--text)" }}>{f.field}</span>
                    <span style={{ fontSize: "0.72rem", fontWeight: 600, color: barColor(f.pct) }}>
                      {f.filled}/{f.total} · {f.pct}%
                    </span>
                  </div>
                  <div style={{ height: 6, borderRadius: 6, background: "var(--surface2)", overflow: "hidden" }}>
                    <div style={{ width: `${f.pct}%`, height: "100%", borderRadius: 6, background: barColor(f.pct) }} />
                  </div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 12, padding: "10px 12px", borderRadius: 10, background: "var(--surface2)", display: "flex", gap: 8, alignItems: "flex-start" }}>
              {dq.has_status_history ? (
                <>
                  <CheckCircle2 size={16} color="#2d7a5f" style={{ marginTop: 1, flexShrink: 0 }} />
                  <span style={{ fontSize: "0.72rem", color: "var(--soft)" }}>Status history present — TTM (Discovery/Delivery), Lead Time & Flow Efficiency are computed exactly.</span>
                </>
              ) : (
                <>
                  <AlertTriangle size={16} color="#d4a84b" style={{ marginTop: 1, flexShrink: 0 }} />
                  <span style={{ fontSize: "0.72rem", color: "var(--soft)" }}>No status-change history in this export → Discovery/Delivery TTM, Lead Time & Flow Efficiency are approximate. Upload a changelog for exact time-in-status metrics.</span>
                </>
              )}
            </div>
          </>
        ) : (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--muted)", fontSize: "0.85rem" }}>
            {dq ? "No dataset uploaded yet." : "Loading…"}
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}
