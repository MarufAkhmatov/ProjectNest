import { useState } from "react";
import { motion } from "motion/react";
import {
  Calendar, Users, LayoutGrid, FileText,
  Search, Settings, Bell, ArrowUpRight, ArrowDownRight,
  ChevronDown, MessageCircle, Sparkles,
} from "lucide-react";
import { WellnessChart } from "./components/WellnessChart";
import { StressRecoveryChart } from "./components/StressRecoveryChart";
import { HRVChart } from "./components/HRVChart";
import { GlucoseGauge } from "./components/GlucoseGauge";
import { PatientFlowChart } from "./components/PatientFlowChart";
import { SuggestedSteps } from "./components/SuggestedSteps";
import { HealthcareProviders } from "./components/HealthcareProviders";
import { AriaPanel } from "./components/AriaPanel";

/* ---------- shared glass tokens ---------- */
const glassPanel: React.CSSProperties = {
  background: "rgba(255,255,255,0.42)",
  backdropFilter: "blur(22px)",
  WebkitBackdropFilter: "blur(22px)",
  border: "1px solid rgba(255,255,255,0.55)",
  boxShadow:
    "0 8px 28px rgba(31,45,61,0.08), inset 0 1px 1px rgba(255,255,255,0.65)",
};

const glassCircle: React.CSSProperties = {
  background: "rgba(255,255,255,0.32)",
  border: "1px solid rgba(255,255,255,0.5)",
  boxShadow:
    "inset 0 1px 2px rgba(255,255,255,0.5), 0 3px 8px rgba(31,45,61,0.06)",
  backdropFilter: "blur(14px)",
  WebkitBackdropFilter: "blur(14px)",
};

/* big frosted content panel that holds the data sections */
const bigPanel: React.CSSProperties = {
  background: "rgba(247,250,250,0.72)",
  backdropFilter: "blur(26px)",
  WebkitBackdropFilter: "blur(26px)",
  border: "1px solid rgba(255,255,255,0.6)",
  borderRadius: 28,
  boxShadow:
    "0 18px 50px rgba(31,55,75,0.14), inset 0 1px 1px rgba(255,255,255,0.75)",
  overflow: "hidden",
};

const divider = "1px solid rgba(90,115,130,0.13)";

const navIcons = [
  { icon: Calendar, label: "Calendar" },
  { icon: Users, label: "Patients" },
  { icon: LayoutGrid, label: "Records" },
  { icon: FileText, label: "Documents" },
];

/* ---------- equalizer-style sparkline ---------- */
function BarSparkline({ up = true }: { up?: boolean }) {
  const bars = up
    ? [5, 9, 6, 12, 8, 14, 9, 16, 11, 7, 13, 9, 6, 10, 7]
    : [14, 10, 13, 8, 15, 9, 12, 7, 13, 9, 6, 11, 8, 12, 7];
  const max = Math.max(...bars);
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 1.5, height: 30 }}>
      {bars.map((b, i) => (
        <motion.div
          key={i}
          initial={{ height: 0 }}
          animate={{ height: `${(b / max) * 100}%` }}
          transition={{ duration: 0.5, delay: i * 0.025, ease: "easeOut" }}
          style={{
            width: 2.5,
            borderRadius: 2,
            background: "#2a3344",
            opacity: 0.35 + (b / max) * 0.6,
          }}
        />
      ))}
    </div>
  );
}

/* ---------- stat (no card behind — sits on the glass surface) ---------- */
function StatCard({
  value, label, up,
}: { value: string; label: string; up: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      style={{ display: "flex", alignItems: "center", gap: 16 }}
    >
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
          <span style={{ fontSize: "1.7rem", fontWeight: 700, color: "#1a2030", letterSpacing: "-0.5px", lineHeight: 1 }}>
            {value}
          </span>
          <span
            style={{
              display: "flex", alignItems: "center", justifyContent: "center",
              width: 19, height: 19, borderRadius: 6,
              background: up ? "#d8efe0" : "#fbe1e1",
              color: up ? "#1f9d57" : "#e53e3e",
            }}
          >
            {up ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
          </span>
        </div>
        <div style={{ fontSize: "0.72rem", color: "#8a97a6", marginTop: 4 }}>{label}</div>
      </div>
      <BarSparkline up={up} />
    </motion.div>
  );
}

export default function App() {
  const [activeNav] = useState("Dashboard");

  return (
    <div
      style={{
        width: "100%",
        minHeight: "100vh",
        background:
          "linear-gradient(155deg, #a7bccf 0%, #b6c8d8 45%, #c4d2dd 100%)",
        fontFamily: "'Poppins', sans-serif",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* ===================== TOP NAV ===================== */}
      <header
        style={{
          display: "flex", alignItems: "center", gap: 16,
          padding: "18px 30px",
          position: "sticky", top: 0, zIndex: 50,
        }}
      >
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
          <div
            style={{
              width: 40, height: 40, borderRadius: "50%",
              display: "flex", alignItems: "center", justifyContent: "center",
              ...glassCircle,
            }}
          >
            <Sparkles size={18} color="#2d7a5f" />
          </div>
          <span style={{ fontSize: "1.1rem", fontWeight: 600, color: "#1a2030" }}>CareNest</span>
        </div>

        <div style={{ flex: 1 }} />

        {/* Center neo-glass nav */}
        <div
          style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: 6, borderRadius: 999,
            ...glassPanel,
          }}
        >
          {/* Active Dashboard pill */}
          <button
            style={{
              display: "flex", alignItems: "center", gap: 9,
              padding: "8px 16px 8px 8px", borderRadius: 999,
              background: "#ffffff", border: "none", cursor: "pointer",
              boxShadow: "0 3px 12px rgba(31,45,61,0.12)",
              fontSize: "0.83rem", fontWeight: 600, color: "#1a2030",
            }}
          >
            <span style={{
              width: 26, height: 26, borderRadius: "50%",
              background: "#eef3f1", display: "flex",
              alignItems: "center", justifyContent: "center",
            }}>
              <MessageCircle size={14} color="#2d7a5f" />
            </span>
            Dashboard
            <ChevronDown size={14} color="#9aa5b4" />
          </button>

          {navIcons.map(({ icon: Icon, label }) => (
            <button
              key={label}
              title={label}
              style={{
                width: 40, height: 40, borderRadius: "50%",
                display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer", color: "#5a6b7d",
                ...glassCircle,
              }}
            >
              <Icon size={17} />
            </button>
          ))}
        </div>

        <div style={{ flex: 1 }} />

        {/* Search + actions */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              display: "flex", alignItems: "center", gap: 9,
              borderRadius: 999, padding: "9px 18px", width: 220,
              ...glassPanel,
            }}
          >
            <Search size={15} color="#9aa5b4" />
            <input
              placeholder="Search..."
              style={{
                border: "none", outline: "none", background: "transparent",
                fontSize: "0.82rem", color: "#1a2030",
                fontFamily: "Poppins, sans-serif", width: "100%",
              }}
            />
          </div>

          <button style={{ width: 42, height: 42, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", ...glassCircle }}>
            <Settings size={17} color="#5a6b7d" />
          </button>
          <button style={{ width: 42, height: 42, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", position: "relative", ...glassCircle }}>
            <Bell size={17} color="#5a6b7d" />
            <span style={{ position: "absolute", top: 8, right: 9, width: 7, height: 7, borderRadius: "50%", background: "#e53e3e", border: "1.5px solid #eef2f0" }} />
          </button>
          <img
            src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=64&h=64&fit=crop&auto=format"
            alt="User"
            style={{ width: 42, height: 42, borderRadius: "50%", objectFit: "cover", border: "2px solid rgba(255,255,255,0.8)", cursor: "pointer" }}
          />
        </div>
      </header>

      {/* ===================== MAIN ===================== */}
      <main style={{ flex: 1, padding: "8px 30px 30px", display: "flex", flexDirection: "column", gap: 18 }}>

        {/* Hero + Stats row */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: 24, flexWrap: "wrap" }}>
          <div>
            <motion.h1
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              style={{ fontSize: "2rem", fontWeight: 700, color: "#1a2030", margin: 0, letterSpacing: "-0.5px" }}
            >
              Dashboard Overview
            </motion.h1>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.15 }}
              style={{ fontSize: "0.82rem", color: "#7a8796", margin: "4px 0 0 0" }}
            >
              Welcome back! Here's what's happening with your clients today.
            </motion.p>
          </div>
          <div style={{ flex: 1 }} />
          <div style={{ display: "flex", gap: 34, flexWrap: "wrap", alignItems: "center", paddingTop: 4 }}>
            <StatCard value="1,360" label="Total Appointments" up />
            <StatCard value="2,654" label="Active Patients" up />
            <StatCard value="54" label="Critical Alerts" up={false} />
          </div>
        </div>

        {/* Row 1: ONE unified panel — Wellness | Stress/Recovery+HRV+Glucose | Patient Flow */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.12 }}
          style={{
            ...bigPanel,
            display: "grid",
            gridTemplateColumns: "1.3fr 1.15fr 1fr",
            alignItems: "stretch",
          }}
        >
          <div style={{ borderRight: divider }}>
            <WellnessChart />
          </div>

          <div style={{ borderRight: divider, display: "flex", flexDirection: "column" }}>
            <div style={{ borderBottom: divider }}>
              <StressRecoveryChart />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", flex: 1 }}>
              <div style={{ borderRight: divider }}>
                <HRVChart />
              </div>
              <GlucoseGauge />
            </div>
          </div>

          <div>
            <PatientFlowChart />
          </div>
        </motion.div>

        {/* Row 2: unified panel (Suggested Steps | Healthcare Providers) + Aria card */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "3.2fr 1.1fr",
          gap: 16,
          alignItems: "stretch",
        }}>
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            style={{
              ...bigPanel,
              display: "grid",
              gridTemplateColumns: "1.4fr 1.8fr",
              alignItems: "stretch",
            }}
          >
            <div style={{ borderRight: divider }}>
              <SuggestedSteps />
            </div>
            <div>
              <HealthcareProviders />
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.52 }}>
            <AriaPanel />
          </motion.div>
        </div>

      </main>
    </div>
  );
}
