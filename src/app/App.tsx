import { useState, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Calendar, Users, LayoutGrid, FileText,
  Search, Settings, Bell, ChevronDown, MessageCircle, Sparkles, X, Upload,
} from "lucide-react";
import { usePortfolio } from "./portfolio";
import { WellnessChart } from "./components/WellnessChart";
import { StressRecoveryChart } from "./components/StressRecoveryChart";
import { HRVChart } from "./components/HRVChart";
import { GlucoseGauge } from "./components/GlucoseGauge";
import { PatientFlowChart } from "./components/PatientFlowChart";
import { HealthcareProviders } from "./components/HealthcareProviders";
import { AriaPanel } from "./components/AriaPanel";
import { BestProjects } from "./components/BestProjects";
import { useI18n, LANGS } from "./i18n";
import { useBreakpoint } from "./useBreakpoint";

/* ---------- glass tokens (nav) ---------- */
const glassPanel: React.CSSProperties = {
  background: "rgba(255,255,255,0.4)",
  backdropFilter: "blur(22px)",
  WebkitBackdropFilter: "blur(22px)",
  border: "1px solid rgba(255,255,255,0.5)",
  boxShadow: "0 8px 26px rgba(20,40,55,0.10), inset 0 1px 1px rgba(255,255,255,0.6)",
};
const glassCircle: React.CSSProperties = {
  background: "rgba(255,255,255,0.3)",
  border: "1px solid rgba(255,255,255,0.45)",
  boxShadow: "inset 0 1px 2px rgba(255,255,255,0.45), 0 3px 8px rgba(20,40,55,0.08)",
  backdropFilter: "blur(14px)",
  WebkitBackdropFilter: "blur(14px)",
};

/* ---------- white card ---------- */
const card: React.CSSProperties = {
  background: "#ffffff",
  borderRadius: 14,
  boxShadow: "0 8px 24px rgba(0,0,0,0.06)",
  overflow: "hidden",
};
const innerDivider = "1px solid #eef1f4";
const GAP = 10;

const navIcons = [
  { icon: Calendar, label: "Calendar" },
  { icon: Users, label: "Patients" },
  { icon: LayoutGrid, label: "Records" },
  { icon: FileText, label: "Documents" },
];

/* ---------- header metric sparkline ---------- */
function MetricBars() {
  const bars = [6, 10, 7, 13, 9, 15, 8, 14, 10, 16, 9, 12, 7, 11, 8];
  const max = Math.max(...bars);
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 2.5, height: 40, filter: "drop-shadow(0 0 4px rgba(255,255,255,0.5))" }}>
      {bars.map((b, i) => (
        <motion.div
          key={i}
          initial={{ height: 0 }}
          animate={{ height: `${(b / max) * 100}%` }}
          transition={{ duration: 0.5, delay: i * 0.02, ease: "easeOut" }}
          style={{ width: 2, borderRadius: 2, background: "rgba(255,255,255,0.55)" }}
        />
      ))}
    </div>
  );
}

function Metric({ value, label }: { value: string; label: string }) {
  return (
    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }} style={{ display: "flex", alignItems: "center", gap: 13 }}>
      <MetricBars />
      <div>
        <div style={{ fontSize: 40, fontWeight: 300, color: "#ffffff", lineHeight: 1, letterSpacing: "-1px" }}>{value}</div>
        <div style={{ fontSize: 13, fontWeight: 300, color: "rgba(255,255,255,0.78)", marginTop: 6, whiteSpace: "nowrap" }}>{label}</div>
      </div>
    </motion.div>
  );
}

export default function App() {
  const { t, lang, setLang } = useI18n();
  const bp = useBreakpoint();
  const isDesktop = bp === "desktop";
  const isTablet = bp === "tablet";
  const isMobile = bp === "mobile";
  const [ariaOpen, setAriaOpen] = useState(false);
  const { data, upload, online } = usePortfolio();
  const hm = data?.widgets?.header_metrics;
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setUploading(true);
    try {
      const r = await upload(f);
      alert(r?.ok ? `Loaded ${r.meta.issues} issues (${r.meta.epics} projects) from ${f.name}` : `Upload failed: ${r?.error || "error"}`);
    } catch {
      alert("Upload failed — is the backend running? (python backend/server.py)");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  /* Stress + HRV + Glucose grouped card */
  const stressCard = (extra: React.CSSProperties = {}) => (
    <div style={{ ...card, display: "flex", flexDirection: "column", ...extra }}>
      <div style={{ borderBottom: innerDivider }}>
        <StressRecoveryChart />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", flex: 1 }}>
        <div style={{ borderRight: innerDivider }}>
          <HRVChart />
        </div>
        <GlucoseGauge />
      </div>
    </div>
  );

  return (
    <div
      style={{
        width: "100%",
        minHeight: "100vh",
        height: isDesktop ? "100vh" : "auto",
        overflow: isDesktop ? "hidden" : "auto",
        background: "linear-gradient(180deg, #7A9AA8 0%, #B7CFD7 50%, #DCECEF 100%)",
        fontFamily: "var(--font-sans)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* ===================== TOP NAV ===================== */}
      <header style={{ display: "flex", alignItems: "center", gap: 14, padding: isMobile ? "16px 18px 6px" : "20px 32px 8px", position: "sticky", top: 0, zIndex: 50 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
          <div style={{ width: 40, height: 40, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, overflow: "hidden", ...glassCircle }}>
            <img src="/ipak-logo.svg" alt="IPAK" style={{ width: 26, height: 26, objectFit: "contain" }} />
          </div>
          <span style={{ fontSize: "1.1rem", fontWeight: 300, color: "#ffffff" }}>ProjectNest</span>
        </div>

        <div style={{ flex: 1 }} />

        {/* centered neo-glass nav — desktop only */}
        {isDesktop && (
          <>
            <div style={{ display: "flex", alignItems: "center", gap: 6, padding: 6, borderRadius: 999, ...glassPanel }}>
              <button style={{ display: "flex", alignItems: "center", gap: 9, padding: "8px 16px 8px 8px", borderRadius: 999, background: "#ffffff", border: "none", cursor: "pointer", boxShadow: "0 3px 12px rgba(20,40,55,0.12)", fontSize: "0.83rem", fontWeight: 300, color: "#1a2030" }}>
                <span style={{ width: 26, height: 26, borderRadius: "50%", background: "#e9f2f0", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <MessageCircle size={14} color="#0c5563" />
                </span>
                {t("nav_dashboard")}
                <ChevronDown size={14} color="#9aa5b4" />
              </button>
              {navIcons.map(({ icon: Icon, label }) => (
                <button key={label} title={label} style={{ width: 40, height: 40, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", color: "#3f5560", ...glassCircle }}>
                  <Icon size={17} />
                </button>
              ))}
            </div>
            <div style={{ flex: 1 }} />
          </>
        )}

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Language switcher — always */}
          <div style={{ display: "flex", alignItems: "center", gap: 2, padding: 4, borderRadius: 999, ...glassPanel }}>
            {LANGS.map(l => (
              <button
                key={l.code}
                onClick={() => setLang(l.code)}
                style={{
                  padding: "5px 10px", borderRadius: 999, border: "none", cursor: "pointer",
                  fontSize: "0.72rem", fontWeight: lang === l.code ? 600 : 300,
                  background: lang === l.code ? "#ffffff" : "transparent",
                  color: lang === l.code ? "#1a2030" : "#ffffff",
                  boxShadow: lang === l.code ? "0 2px 8px rgba(20,40,55,0.12)" : "none",
                  fontFamily: "var(--font-sans)", transition: "all 0.18s",
                }}
              >
                {l.label}
              </button>
            ))}
          </div>

          {/* Upload Jira export — always */}
          <input ref={fileRef} type="file" accept=".csv,.xlsx,.xlsm,.html,.htm" onChange={onUpload} style={{ display: "none" }} />
          <button
            onClick={() => fileRef.current?.click()}
            title={online ? "Upload Jira export (CSV / XLSX / HTML)" : "Backend offline"}
            style={{ width: 42, height: 42, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", color: online ? "#0c5563" : "#9aa5b4", position: "relative", ...glassCircle }}
          >
            <Upload size={17} className={uploading ? "animate-pulse" : ""} />
            <span style={{ position: "absolute", bottom: 6, right: 7, width: 7, height: 7, borderRadius: "50%", background: online ? "#1f9d57" : "#e53e3e", border: "1.5px solid #cfe0e2" }} />
          </button>

          {/* Search — desktop + tablet */}
          {!isMobile && (
            <div style={{ display: "flex", alignItems: "center", gap: 9, borderRadius: 999, padding: "9px 18px", width: isTablet ? 160 : 210, ...glassPanel }}>
              <Search size={15} color="#52707c" />
              <input placeholder={t("search")} style={{ border: "none", outline: "none", background: "transparent", fontSize: "0.82rem", color: "#1a2030", fontFamily: "var(--font-sans)", width: "100%" }} />
            </div>
          )}

          {/* settings + bell — desktop only */}
          {isDesktop && (
            <>
              <button style={{ width: 42, height: 42, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", color: "#3f5560", ...glassCircle }}>
                <Settings size={17} />
              </button>
              <button style={{ width: 42, height: 42, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", position: "relative", color: "#3f5560", ...glassCircle }}>
                <Bell size={17} />
                <span style={{ position: "absolute", top: 8, right: 9, width: 7, height: 7, borderRadius: "50%", background: "#e53e3e", border: "1.5px solid #cfe0e2" }} />
              </button>
            </>
          )}

          <img
            src="/temur.jpg"
            onError={(e) => { (e.currentTarget as HTMLImageElement).src = "https://ui-avatars.com/api/?name=Temur&background=8a5a2b&color=fff&bold=true"; }}
            alt="Temur"
            style={{ width: 42, height: 42, borderRadius: "50%", objectFit: "cover", border: "2px solid rgba(255,255,255,0.7)", cursor: "pointer", flexShrink: 0 }}
          />
        </div>
      </header>

      {/* ===================== CONTENT ===================== */}
      <main
        style={{
          flex: 1,
          padding: isMobile ? `4px 16px ${ariaOpen ? 16 : 96}px` : `4px ${isTablet ? 20 : 32}px 20px`,
          display: "flex",
          flexDirection: "column",
          gap: GAP,
          minHeight: 0,
        }}
      >
        {/* Title (left) + metrics cluster (right) */}
        <div style={{ display: "flex", alignItems: isMobile ? "flex-start" : "center", justifyContent: "space-between", gap: isMobile ? 14 : 32, flexWrap: isDesktop ? "nowrap" : "wrap", flexDirection: isMobile ? "column" : "row" }}>
          <div style={{ maxWidth: isDesktop ? 560 : "100%", flexShrink: 0 }}>
            <motion.h1 initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} style={{ fontSize: isMobile ? 30 : isTablet ? 40 : 50, fontWeight: 300, color: "#ffffff", letterSpacing: "-1px", margin: 0, lineHeight: 1.05 }}>
              {t("title")}
            </motion.h1>
            <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }} style={{ fontSize: isMobile ? 14 : 19, fontWeight: 300, color: "rgba(255,255,255,0.85)", margin: "8px 0 0 0" }}>
              {t("subtitle")}
            </motion.p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: isMobile ? 22 : 38, flexShrink: 0, flexWrap: "wrap" }}>
            <Metric value={hm ? String(hm[0].value) : "—"} label={t("kpi_total_projects")} />
            <Metric value={hm ? String(hm[1].value) : "—"} label={t("kpi_completed")} />
            <Metric value={hm ? String(hm[2].value) : "—"} label={t("kpi_critical")} />
          </div>
        </div>

        {/* ============ DESKTOP LAYOUT ============ */}
        {isDesktop && (
          <div style={{ display: "grid", gridTemplateColumns: "2.4fr 0.95fr", gap: GAP, flex: 1, minHeight: 0 }}>
            {/* Left region: Wellness|Stress (top) + Best|Healthcare (bottom) */}
            <div style={{ display: "flex", flexDirection: "column", gap: GAP, minHeight: 0 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1.3fr", gap: GAP, flex: "1.5 1 0", minHeight: 0 }}>
                <div style={{ ...card }}><WellnessChart /></div>
                {stressCard()}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "0.9fr 1.5fr", gap: GAP, flex: "1.2 1 0", minHeight: 0 }}>
                <div style={{ ...card }}><BestProjects /></div>
                <div style={{ ...card }}><HealthcareProviders /></div>
              </div>
            </div>

            {/* Right region: Patient Flow (shorter) + Temur (taller) */}
            <div style={{ display: "flex", flexDirection: "column", gap: GAP, minHeight: 0 }}>
              <div style={{ ...card, flex: "1.26 1 0", minHeight: 0 }}><PatientFlowChart /></div>
              <div style={{ flex: "1.44 1 0", minHeight: 0 }}><AriaPanel /></div>
            </div>
          </div>
        )}

        {/* ============ TABLET LAYOUT (2 columns) ============ */}
        {isTablet && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: GAP }}>
            <div style={{ ...card, minHeight: 340 }}><WellnessChart /></div>
            {stressCard({ minHeight: 360 })}
            <div style={{ ...card, minHeight: 320 }}><PatientFlowChart /></div>
            <div style={{ ...card, minHeight: 320 }}><BestProjects /></div>
            <div style={{ ...card, minHeight: 300, gridColumn: "1 / 3" }}><HealthcareProviders /></div>
            <div style={{ minHeight: 360, gridColumn: "1 / 3" }}><AriaPanel /></div>
          </div>
        )}

        {/* ============ MOBILE LAYOUT (single column stack) ============ */}
        {isMobile && (
          <div style={{ display: "flex", flexDirection: "column", gap: GAP }}>
            <div style={{ ...card, minHeight: 340 }}><WellnessChart /></div>
            {stressCard({ minHeight: 420 })}
            <div style={{ ...card, minHeight: 340 }}><PatientFlowChart /></div>
            <div style={{ ...card, minHeight: 280 }}><BestProjects /></div>
            <div style={{ ...card, minHeight: 320 }}><HealthcareProviders /></div>
          </div>
        )}
      </main>

      {/* ============ MOBILE ARIA — floating round button + chat panel ============ */}
      {isMobile && (
        <>
          <AnimatePresence>
            {ariaOpen && (
              <motion.div
                initial={{ opacity: 0, y: 30, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 30, scale: 0.96 }}
                transition={{ duration: 0.22 }}
                style={{ position: "fixed", left: 14, right: 14, bottom: 88, height: "68vh", zIndex: 99, borderRadius: 16, overflow: "hidden", boxShadow: "0 24px 60px rgba(0,0,0,0.35)" }}
              >
                <AriaPanel />
              </motion.div>
            )}
          </AnimatePresence>

          <motion.button
            onClick={() => setAriaOpen(o => !o)}
            whileTap={{ scale: 0.92 }}
            style={{
              position: "fixed", bottom: 20, right: 20, width: 62, height: 62, borderRadius: "50%",
              background: "linear-gradient(165deg, #083A47 0%, #0c5563 50%, #4EB6A6 100%)",
              border: "none", cursor: "pointer", zIndex: 100,
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 10px 28px rgba(8,58,71,0.45)",
            }}
            aria-label="Aria"
          >
            {ariaOpen ? <X size={24} color="#fff" /> : <MessageCircle size={24} color="#fff" />}
          </motion.button>
        </>
      )}
    </div>
  );
}
