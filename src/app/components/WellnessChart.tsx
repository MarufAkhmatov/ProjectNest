import { useState } from "react";
import { motion } from "motion/react";

const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const heights = [28, 35, 62, 88, 70, 30, 22];
const colors = ["#c8ccd4", "#c8ccd4", "#d4a84b", "#9b59b6", "#2d7a5f", "#c8ccd4", "#c8ccd4"];

const tabs = ["Daily", "Monthly", "Weekly", "Yearly"];

export function WellnessChart() {
  const [active, setActive] = useState("Daily");

  const CHART_H = 150;

  return (
    <div className="bg-card rounded-2xl p-5 flex flex-col gap-4" style={{ backdropFilter: "blur(12px)", border: "1px solid rgba(255,255,255,0.6)", height: "100%" }}>
      <div className="flex items-center justify-between">
        <span style={{ color: "#1a2030", fontSize: "0.85rem", fontWeight: 500 }}>Your Wellness Progress</span>
        <span style={{ fontSize: "1.5rem", fontWeight: 600, color: "#1a2030" }}>64%</span>
      </div>

      <div className="flex gap-4">
        {tabs.map(t => (
          <button
            key={t}
            onClick={() => setActive(t)}
            style={{
              fontSize: "0.75rem",
              color: active === t ? "#1a2030" : "#9aa5b4",
              fontWeight: active === t ? 600 : 400,
              borderBottom: active === t ? "2px solid #1a2030" : "2px solid transparent",
              paddingBottom: "2px",
              background: "none",
              border: "none",
              borderBottom: active === t ? "2px solid #1a2030" : "2px solid transparent",
              cursor: "pointer",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="flex items-end gap-2 flex-1" style={{ minHeight: CHART_H + 20 }}>
        {days.map((d, i) => {
          const stemH = Math.round((heights[i] / 100) * CHART_H);
          return (
            <div key={d} className="flex flex-col items-center flex-1 gap-1">
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
              <span style={{ fontSize: "0.65rem", color: "#9aa5b4" }}>{d}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
