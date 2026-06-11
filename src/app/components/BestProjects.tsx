import { motion } from "motion/react";
import { useI18n } from "../i18n";
import { usePortfolio } from "../portfolio";

const fallback = [
  { name: "Cardio Care", pct: 82, color: "#2d7a5f" },
  { name: "Wellness 2.0", pct: 64, color: "#9b59b6" },
  { name: "Lab Sync", pct: 47, color: "#d4a84b" },
];

export function BestProjects() {
  const { t } = useI18n();
  const { data } = usePortfolio();
  const projects = data?.widgets?.top_projects?.length ? data.widgets.top_projects : fallback;
  return (
    <div className="p-6 flex flex-col gap-4" style={{ height: "100%" }}>
      <span style={{ fontSize: "0.9rem", fontWeight: 600, color: "#1a2030" }}>
        {t("best_projects")}
      </span>

      <div className="flex flex-col gap-5" style={{ flex: 1, justifyContent: "center" }}>
        {projects.map((p: any, i: number) => (
          <div key={i} className="flex flex-col gap-2">
            <div className="flex items-center justify-between gap-2">
              <div style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
                <span style={{ fontSize: "0.76rem", fontWeight: 600, color: "#1a2030" }}>{p.key || p.name}</span>
                {p.summary && (
                  <span style={{ fontSize: "0.63rem", color: "#9aa5b4", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: 165 }} title={p.summary}>
                    {p.summary}
                  </span>
                )}
              </div>
              <span style={{ fontSize: "0.72rem", fontWeight: 600, color: p.color, flexShrink: 0 }}>{p.pct}%</span>
            </div>
            <div style={{ height: 6, borderRadius: 6, background: "#eef1f4", overflow: "hidden" }}>
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${p.pct}%` }}
                transition={{ duration: 0.9, delay: i * 0.12, ease: "easeOut" }}
                style={{ height: "100%", borderRadius: 6, background: p.color }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
