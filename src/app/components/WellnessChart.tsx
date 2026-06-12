import { useState } from "react";
import { motion } from "motion/react";
import { useI18n } from "../i18n";
import { usePortfolio } from "../portfolio";

const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const heights = [28, 35, 62, 88, 70, 30, 22];
const colors = ["#c8ccd4", "#c8ccd4", "#d4a84b", "#9b59b6", "#2d7a5f", "#c8ccd4", "#c8ccd4"];

const tabs = ["Daily", "Monthly", "Weekly", "Yearly"];

export function WellnessChart() {
  const [active, setActive] = useState("Daily");
  const { t, d: tr } = useI18n();
  const { data } = usePortfolio();
  const w = data?.widgets?.wellness;
  const heightsData = w?.bars?.length ? w.bars : heights;
  const labelsData = w?.labels?.length ? w.labels : days.map((d) => tr.dayShort[d]);
  const pct = w ? w.completion_pct : 64;

  const CHART_H = 210;

  return (
    <div className="p-6 flex flex-col gap-4" style={{ height: "100%" }}>
      <div className="flex items-center justify-between">
        <span style={{ color: "var(--text)", fontSize: "0.85rem", fontWeight: 300 }}>{t("wellness_progress")}</span>
        <span style={{ fontSize: "1.5rem", fontWeight: 600, color: "var(--text)" }}>{pct}%</span>
      </div>

      <div className="flex gap-4">
        {tabs.map(tab => (
          <button
            key={tab}
            onClick={() => setActive(tab)}
            style={{
              fontSize: "0.75rem",
              color: active === tab ? "var(--text)" : "#9aa5b4",
              fontWeight: active === tab ? 600 : 300,
              paddingBottom: "2px",
              background: "none",
              border: "none",
              borderBottom: active === tab ? "2px solid var(--text)" : "2px solid transparent",
              cursor: "pointer",
            }}
          >
            {t("tab_" + tab)}
          </button>
        ))}
      </div>

      <div className="flex items-end gap-2 flex-1" style={{ minHeight: CHART_H + 20 }}>
        {days.map((dy, i) => {
          const stemH = Math.round(((heightsData[i] ?? 0) / 100) * CHART_H);
          return (
            <div key={dy} className="flex flex-col items-center flex-1 gap-1">
              <div className="flex flex-col items-center justify-end" style={{ height: CHART_H, position: "relative" }}>
                {/* lollipop stem */}
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: stemH }}
                  transition={{ duration: 0.7, delay: i * 0.07, ease: "easeOut" }}
                  style={{
                    width: 2,
                    background: colors[i],
                    borderRadius: 2,
                    position: "absolute",
                    bottom: 0,
                  }}
                />
                {/* lollipop head */}
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: i * 0.07 + 0.4 }}
                  style={{
                    width: 11,
                    height: 11,
                    borderRadius: "50%",
                    background: colors[i],
                    position: "absolute",
                    bottom: stemH,
                    transform: "translateY(50%)",
                    boxShadow: colors[i] !== "#c8ccd4" ? `0 0 8px ${colors[i]}88` : "none",
                  }}
                />
              </div>
              <span style={{ fontSize: "0.65rem", color: "#9aa5b4" }}>{labelsData[i]}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
