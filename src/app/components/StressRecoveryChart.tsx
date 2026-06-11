import { motion } from "motion/react";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Dot } from "recharts";

const data = [
  { day: "Sun", value: 0.62 },
  { day: "Mon", value: 0.58 },
  { day: "Tue", value: 0.71 },
  { day: "Wed", value: 0.55 },
  { day: "Thu", value: 0.48 },
  { day: "Fri", value: 0.52 },
  { day: "Sat", value: 0.40 },
];

export function StressRecoveryChart() {
  return (
    <div className="bg-card rounded-2xl p-5 flex flex-col gap-3" style={{ backdropFilter: "blur(12px)", border: "1px solid rgba(255,255,255,0.6)" }}>
      <div className="flex items-center justify-between">
        <span style={{ fontSize: "0.85rem", fontWeight: 500, color: "#1a2030" }}>Stress / Recovery Balance</span>
        <span style={{ fontSize: "1.3rem", fontWeight: 600, color: "#1a2030" }}>+0.34</span>
      </div>

      <div style={{ height: 90 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 8, left: -30, bottom: 0 }}>
            <XAxis dataKey="day" tick={{ fontSize: 10, fill: "#9aa5b4" }} axisLine={false} tickLine={false} />
            <YAxis hide />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#1a2030"
              strokeWidth={1.5}
              dot={{ r: 3, fill: "#1a2030", strokeWidth: 0 }}
              activeDot={{ r: 4, fill: "#2d7a5f" }}
              animationDuration={1200}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center gap-2 mt-1">
        <div style={{ width: 28, height: 28, borderRadius: 6, background: "#e8f0e8", flexShrink: 0, overflow: "hidden" }}>
          <img src="https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=56&h=56&fit=crop&auto=format" alt="Doctor" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </div>
        <p style={{ fontSize: "0.68rem", color: "#6b7a8d", lineHeight: 1.4 }}>
          You reached optimal recovery. Keeping your bedtime consistent will sustain this
        </p>
      </div>
    </div>
  );
}
