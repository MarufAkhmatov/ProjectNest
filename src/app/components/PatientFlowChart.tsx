import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { useI18n } from "../i18n";
import { usePortfolio } from "../portfolio";

export function PatientFlowChart() {
  const { t } = useI18n();
  const { data } = usePortfolio();
  const pf = data?.widgets?.project_flow;
  const total = pf ? pf.total : 860;
  const completedN = pf ? pf.completed : 650;
  const openN = pf ? pf.open : 326;
  const declinedN = pf ? pf.declined : 210;
  const segments = [
    { value: completedN || 0.001, color: "#d4a84b", label: "Completed" },
    { value: openN || 0.001, color: "#9b59b6", label: "Open" },
    { value: declinedN || 0.001, color: "#2d7a5f", label: "Declined" },
  ];
  return (
    <div className="p-6 flex flex-col gap-3" style={{ height: "100%" }}>
      <div className="flex items-center justify-between">
        <span style={{ fontSize: "0.85rem", fontWeight: 300, color: "var(--text)" }}>{t("patient_flow")}</span>
        <button style={{ background: "none", border: "none", cursor: "pointer", color: "#9aa5b4", fontSize: "1rem" }}>···</button>
      </div>

      {/* Donut fills the available space */}
      <div style={{ flex: 1, minHeight: 0, position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={segments}
              cx="50%"
              cy="50%"
              innerRadius="60%"
              outerRadius="85%"
              startAngle={90}
              endAngle={-270}
              paddingAngle={2}
              dataKey="value"
              stroke="none"
              animationBegin={200}
              animationDuration={1100}
            >
              {segments.map((s, i) => (
                <Cell key={i} fill={s.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", pointerEvents: "none" }}>
          <span style={{ fontSize: "1.7rem", fontWeight: 700, color: "var(--text)", lineHeight: 1 }}>{total}</span>
          <span style={{ fontSize: "0.68rem", color: "#9aa5b4", marginTop: 4 }}>{pf ? `${pf.completion_pct}%` : t("capacity68")}</span>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-between" style={{ paddingTop: 2 }}>
        <div className="flex items-center gap-2">
          <span style={{ width: 9, height: 9, borderRadius: 3, background: "#d4a84b", flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text)", lineHeight: 1 }}>{completedN}</div>
            <div style={{ fontSize: "0.65rem", color: "#9aa5b4", marginTop: 2 }}>{t("completed")}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span style={{ width: 9, height: 9, borderRadius: 3, background: "#9b59b6", flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text)", lineHeight: 1 }}>{openN}</div>
            <div style={{ fontSize: "0.65rem", color: "#9aa5b4", marginTop: 2 }}>{t("upcoming")}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
