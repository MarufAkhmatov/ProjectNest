import { BarChart, Bar, XAxis, ResponsiveContainer, Cell } from "recharts";
import { motion } from "motion/react";

const data = [
  { month: "Jan", value: 72, color: "#d4a84b" },
  { month: "Feb", value: 88, color: "#9b59b6" },
  { month: "Mar", value: 65, color: "#2d7a5f" },
];

export function HRVChart() {
  return (
    <div className="bg-card rounded-2xl p-5 flex flex-col gap-2" style={{ backdropFilter: "blur(12px)", border: "1px solid rgba(255,255,255,0.6)" }}>
      <div className="flex items-center justify-between">
        <span style={{ fontSize: "0.85rem", fontWeight: 500, color: "#1a2030" }}>HRV</span>
        <motion.span
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          style={{ fontSize: "1.1rem", fontWeight: 600, color: "#2d7a5f" }}
        >
          +8%
        </motion.span>
      </div>
      <div style={{ height: 70 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} barSize={24} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <XAxis dataKey="month" tick={{ fontSize: 10, fill: "#9aa5b4" }} axisLine={false} tickLine={false} />
            <Bar dataKey="value" radius={[6, 6, 0, 0]} animationDuration={1000}>
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
