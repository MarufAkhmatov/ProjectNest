import { useState, useEffect, useMemo, useRef, type ReactNode } from "react";
import { Loader2, Eye, EyeOff, User, Lock, Smartphone } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import QRCode from "qrcode";
import { useI18n, LANGS } from "../i18n";
import { useBreakpoint } from "../useBreakpoint";

const API = (import.meta as any).env?.VITE_API_URL ?? "";

type Focus = "user" | "pass" | null;
type Mood = "idle" | "sad" | "happy";

/* ============================================================================
 *  OwlMascot — a cute owl that reacts to the login form (Dribbble-style):
 *   • watches & pans its eyes as you type the username
 *   • covers its eyes with both wings when you type the password
 *   • peeks again the moment you reveal the password
 *   • blinks on idle, shakes its head on a wrong password, beams on success
 * ========================================================================== */
function OwlMascot({ focus, typed, mood, cover, size = 230 }: {
  focus: Focus; typed: number; mood: Mood; cover: boolean; size?: number;
}) {
  const [blink, setBlink] = useState(false);

  // Idle blinking — paused while the eyes are already covered/closed.
  useEffect(() => {
    if (cover) return;
    let alive = true;
    const loop = () => {
      const next = 2200 + Math.random() * 2600;
      return window.setTimeout(() => {
        if (!alive) return;
        setBlink(true);
        window.setTimeout(() => setBlink(false), 140);
        timer = loop();
      }, next);
    };
    let timer = loop();
    return () => { alive = false; window.clearTimeout(timer); };
  }, [cover]);

  // Pupils pan left→right (and look down) as the username is typed.
  const look = useMemo(() => {
    if (focus === "user") {
      const f = Math.min(1, typed / 22);
      return { x: -6 + f * 12, y: 6 };
    }
    return { x: 0, y: 0 };
  }, [focus, typed]);

  const eyesClosed = cover || blink;
  const teal = "#0c5563", tealLite = "#15788b", cream = "#fdf3e3";
  const wingFill = "#0a4954";

  // Wing rest vs. cover (eye-covering) poses.
  const leftWing = cover ? { x: 40, y: -46, rotate: -34 } : { x: 0, y: 0, rotate: 10 };
  const rightWing = cover ? { x: -40, y: -46, rotate: 34 } : { x: 0, y: 0, rotate: -10 };

  return (
    <motion.svg
      width={size} height={size} viewBox="0 0 220 240"
      animate={mood === "sad"
        ? { x: [0, -7, 7, -5, 5, 0], rotate: [0, -1, 1, 0] }
        : { y: [0, -5, 0] }}
      transition={mood === "sad"
        ? { duration: 0.5 }
        : { duration: 3.4, repeat: Infinity, ease: "easeInOut" }}
      style={{ overflow: "visible" }}
    >
      <defs>
        <radialGradient id="owlBody" cx="50%" cy="38%" r="70%">
          <stop offset="0%" stopColor={tealLite} />
          <stop offset="100%" stopColor={teal} />
        </radialGradient>
        <linearGradient id="owlBranch" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#8a5a2b" />
          <stop offset="100%" stopColor="#6e4621" />
        </linearGradient>
      </defs>

      {/* branch (the "nest" wink) */}
      <rect x="22" y="206" width="176" height="15" rx="7.5" fill="url(#owlBranch)" />
      <ellipse cx="60" cy="206" rx="15" ry="6" fill="#3f9d5d" opacity="0.85" />
      <ellipse cx="166" cy="207" rx="13" ry="5" fill="#3f9d5d" opacity="0.7" />

      {/* feet gripping the branch */}
      <g fill="#e8a13c">
        <path d="M88 198 v12 M82 210 h12 M88 210 l-5 6 M88 210 l5 6" stroke="#e8a13c" strokeWidth="4" strokeLinecap="round" />
        <path d="M132 198 v12 M126 210 h12 M132 210 l-5 6 M132 210 l5 6" stroke="#e8a13c" strokeWidth="4" strokeLinecap="round" />
      </g>

      {/* ear tufts */}
      <path d="M70 44 L60 14 L92 38 Z" fill={teal} />
      <path d="M150 44 L160 14 L128 38 Z" fill={teal} />

      {/* body */}
      <path d="M110 30 C58 30 40 78 40 122 C40 176 70 204 110 204 C150 204 180 176 180 122 C180 78 162 30 110 30 Z" fill="url(#owlBody)" />
      {/* belly panel */}
      <path d="M110 96 C84 96 74 120 74 146 C74 178 90 198 110 198 C130 198 146 178 146 146 C146 120 136 96 110 96 Z" fill={cream} opacity="0.95" />

      {/* eye discs */}
      <g>
        <circle cx="80" cy="104" r="32" fill="#fff" />
        <circle cx="140" cy="104" r="32" fill="#fff" />
        <circle cx="80" cy="104" r="32" fill="none" stroke={teal} strokeWidth="3" opacity="0.25" />
        <circle cx="140" cy="104" r="32" fill="none" stroke={teal} strokeWidth="3" opacity="0.25" />

        {/* pupils (tracking) */}
        {!eyesClosed && (
          <>
            <motion.g animate={{ x: look.x, y: look.y }} transition={{ type: "spring", stiffness: 250, damping: 18 }}>
              <circle cx="80" cy="104" r="13" fill="#1a2b30" />
              <circle cx="85" cy="99" r="4.5" fill="#fff" />
            </motion.g>
            <motion.g animate={{ x: look.x, y: look.y }} transition={{ type: "spring", stiffness: 250, damping: 18 }}>
              <circle cx="140" cy="104" r="13" fill="#1a2b30" />
              <circle cx="145" cy="99" r="4.5" fill="#fff" />
            </motion.g>
          </>
        )}

        {/* happy eyes (curved arcs) on success */}
        {mood === "happy" && (
          <g stroke="#1a2b30" strokeWidth="5" fill="none" strokeLinecap="round">
            <path d="M66 108 q14 -16 28 0" />
            <path d="M126 108 q14 -16 28 0" />
          </g>
        )}

        {/* closed-eye lids (blink / cover) */}
        {eyesClosed && mood !== "happy" && (
          <g stroke="#1a2b30" strokeWidth="5" strokeLinecap="round">
            <line x1="64" y1="106" x2="96" y2="106" />
            <line x1="124" y1="106" x2="156" y2="106" />
          </g>
        )}
      </g>

      {/* beak */}
      <path d="M110 124 l-11 12 q11 9 22 0 Z" fill="#e8a13c" />

      {/* cheeks */}
      <circle cx="58" cy="138" r="9" fill="#f6a6a0" opacity={mood === "sad" ? 0.4 : 0.7} />
      <circle cx="162" cy="138" r="9" fill="#f6a6a0" opacity={mood === "sad" ? 0.4 : 0.7} />

      {/* wings — rest at the sides, rise up to cover the eyes for the password */}
      <motion.g
        style={{ originX: "55px", originY: "150px" }}
        animate={leftWing}
        transition={{ type: "spring", stiffness: 180, damping: 16 }}
      >
        <path d="M48 110 C26 120 24 160 44 178 C54 166 58 140 60 118 Z" fill={wingFill} />
      </motion.g>
      <motion.g
        style={{ originX: "165px", originY: "150px" }}
        animate={rightWing}
        transition={{ type: "spring", stiffness: 180, damping: 16 }}
      >
        <path d="M172 110 C194 120 196 160 176 178 C166 166 162 140 160 118 Z" fill={wingFill} />
      </motion.g>
    </motion.svg>
  );
}

/** Gates the whole app behind a login. Checks the session on mount; shows the
 *  animated login screen until authenticated, then renders the app. */
export function AuthGate({ children }: { children: ReactNode }) {
  const { t, lang, setLang } = useI18n();
  const bp = useBreakpoint();
  const isMobile = bp === "mobile";
  const [state, setState] = useState<"loading" | "in" | "out">("loading");
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [focus, setFocus] = useState<Focus>(null);
  const [showPass, setShowPass] = useState(false);
  const [mood, setMood] = useState<Mood>("idle");
  const [qr, setQr] = useState("");        // QR data-URL for the LAN address
  const [lanUrl, setLanUrl] = useState("");
  const moodTimer = useRef<number | undefined>(undefined);

  useEffect(() => {
    fetch(`${API}/api/me`, { credentials: "same-origin" })
      .then((r) => r.json())
      .then((j) => setState(j.authed ? "in" : "out"))
      .catch(() => setState("out"));
  }, []);

  // Build a QR that points at this PC's LAN address so a phone on the same
  // Wi-Fi can scan it and open the app — no tunnel needed.
  useEffect(() => {
    fetch(`${API}/api/lan`, { credentials: "same-origin" })
      .then((r) => r.json())
      .then((j) => {
        if (!j?.url) return;
        setLanUrl(j.url);
        QRCode.toDataURL(j.url, { margin: 1, width: 240, color: { dark: "#0c5563", light: "#ffffff" } })
          .then(setQr).catch(() => {});
      })
      .catch(() => {});
  }, []);

  useEffect(() => () => window.clearTimeout(moodTimer.current), []);

  const flashMood = (m: Mood, ms: number) => {
    setMood(m);
    window.clearTimeout(moodTimer.current);
    moodTimer.current = window.setTimeout(() => setMood("idle"), ms);
  };

  const submit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (busy || !u || !p) return;
    setBusy(true); setErr("");
    try {
      const r = await fetch(`${API}/api/login`, {
        method: "POST", headers: { "Content-Type": "application/json" }, credentials: "same-origin",
        body: JSON.stringify({ username: u, password: p }),
      });
      const j = await r.json();
      if (j.ok) { setMood("happy"); setTimeout(() => setState("in"), 650); }
      else { setErr(t("login_error")); flashMood("sad", 1200); }
    } catch {
      setErr(t("login_error")); flashMood("sad", 1200);
    } finally {
      setBusy(false);
    }
  };

  if (state === "in") return <>{children}</>;

  const wrap = (inner: ReactNode) => (
    <div style={{
      minHeight: "100vh", width: "100%",
      background: "radial-gradient(1200px 600px at 70% -10%, #1d6f7f 0%, var(--bg) 55%)",
      display: "flex", alignItems: "center", justifyContent: "center", padding: 18,
      fontFamily: "var(--font-sans)",
    }}>{inner}</div>
  );

  if (state === "loading") {
    return wrap(<Loader2 size={26} color="#fff" className="animate-spin" />);
  }

  const cover = focus === "pass" && !showPass;

  /* ---------- the cute hero (owl on a soft gradient) ---------- */
  const hero = (
    <div style={{
      position: "relative", flex: isMobile ? "none" : 1,
      background: "linear-gradient(160deg, #19808f 0%, #0c5563 60%, #073e47 100%)",
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      padding: isMobile ? "26px 20px 14px" : "40px 32px", overflow: "hidden",
      minHeight: isMobile ? 200 : "auto",
    }}>
      {/* floating bubbles for depth */}
      {[
        { s: 120, top: -30, left: -30, o: 0.10 },
        { s: 70, top: 60, left: "70%", o: 0.12 },
        { s: 40, top: "75%", left: 30, o: 0.10 },
      ].map((b, i) => (
        <motion.div key={i}
          animate={{ y: [0, -14, 0] }}
          transition={{ duration: 5 + i, repeat: Infinity, ease: "easeInOut", delay: i * 0.6 }}
          style={{ position: "absolute", top: b.top as any, left: b.left as any, width: b.s, height: b.s, borderRadius: "50%", background: "#fff", opacity: b.o }}
        />
      ))}

      <OwlMascot focus={focus} typed={u.length} mood={mood} cover={cover} size={isMobile ? 150 : 230} />

      {!isMobile && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
          style={{ textAlign: "center", marginTop: 22, color: "#fff" }}>
          <div style={{ fontSize: "1.5rem", fontWeight: 700, letterSpacing: "-0.5px" }}>
            {u.trim() ? `${t("login_welcome_user")}, ${u.split("@")[0]}!` : t("login_hero_title")}
          </div>
          <div style={{ fontSize: "0.84rem", opacity: 0.82, marginTop: 6, maxWidth: 280 }}>{t("login_hero_sub")}</div>
        </motion.div>
      )}

      {/* QR → open on phone (same Wi-Fi, no tunnel). Desktop/tablet only. */}
      {!isMobile && qr && (
        <motion.div initial={{ opacity: 0, scale: 0.92 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.3 }}
          title={lanUrl}
          style={{ position: "absolute", bottom: 22, left: 22, display: "flex", alignItems: "center", gap: 12,
            background: "rgba(255,255,255,0.12)", backdropFilter: "blur(8px)", WebkitBackdropFilter: "blur(8px)",
            border: "1px solid rgba(255,255,255,0.2)", borderRadius: 16, padding: 12, maxWidth: 250 }}>
          <img src={qr} alt="QR" width={76} height={76} style={{ borderRadius: 10, background: "#fff", padding: 4, flexShrink: 0 }} />
          <div style={{ color: "#fff" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.82rem", fontWeight: 700 }}>
              <Smartphone size={14} /> {t("qr_title")}
            </div>
            <div style={{ fontSize: "0.68rem", opacity: 0.82, marginTop: 3, lineHeight: 1.35 }}>{t("qr_hint")}</div>
          </div>
        </motion.div>
      )}
    </div>
  );

  const inputWrap: React.CSSProperties = {
    display: "flex", alignItems: "center", gap: 9, padding: "0 12px",
    borderRadius: 12, background: "var(--surface2)", transition: "box-shadow .18s, border-color .18s",
  };
  const inputBase: React.CSSProperties = {
    flex: 1, padding: "12px 0", border: "none", background: "transparent",
    color: "var(--text)", fontSize: "0.9rem", outline: "none",
  };
  const ringStyle = (active: boolean): React.CSSProperties => ({
    border: `1.5px solid ${active ? "#19808f" : "var(--divider)"}`,
    boxShadow: active ? "0 0 0 4px #19808f22" : "none",
  });

  /* ---------- the form side ---------- */
  const formSide = (
    <form onSubmit={submit} style={{
      width: isMobile ? "100%" : 380, padding: isMobile ? "22px 24px 26px" : "44px 40px",
      display: "flex", flexDirection: "column", gap: 16, background: "var(--card)",
    }}>
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
          <img src="/ipak-logo.svg" alt="IPAK" style={{ width: 30, height: 30, objectFit: "contain" }}
            onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }} />
          <span style={{ fontSize: "1.45rem", fontWeight: 700, color: "var(--text)", letterSpacing: "-0.5px" }}>{t("login_title")}</span>
        </div>
        <div style={{ fontSize: "0.78rem", color: "var(--muted)" }}>{t("login_subtitle")}</div>
      </div>

      <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <span style={{ fontSize: "0.72rem", color: "var(--soft)", fontWeight: 600 }}>{t("login_user")}</span>
        <div style={{ ...inputWrap, ...ringStyle(focus === "user") }}>
          <User size={16} color={focus === "user" ? "#19808f" : "var(--soft)"} />
          <input value={u} onChange={(e) => setU(e.target.value)} autoFocus autoComplete="username"
            onFocus={() => setFocus("user")} onBlur={() => setFocus((f) => f === "user" ? null : f)}
            style={inputBase} />
        </div>
      </label>

      <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <span style={{ fontSize: "0.72rem", color: "var(--soft)", fontWeight: 600 }}>{t("login_pass")}</span>
        <div style={{ ...inputWrap, ...ringStyle(focus === "pass") }}>
          <Lock size={16} color={focus === "pass" ? "#19808f" : "var(--soft)"} />
          <input value={p} onChange={(e) => setP(e.target.value)} type={showPass ? "text" : "password"} autoComplete="current-password"
            onFocus={() => setFocus("pass")} onBlur={() => setFocus((f) => f === "pass" ? null : f)}
            style={inputBase} />
          <button type="button" tabIndex={-1} title={showPass ? t("login_hide") : t("login_show")}
            onClick={() => setShowPass((s) => !s)}
            style={{ border: "none", background: "transparent", cursor: "pointer", color: "var(--soft)", display: "flex", padding: 4 }}>
            {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
      </label>

      <AnimatePresence>
        {err && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
            style={{ fontSize: "0.76rem", color: "#e0574f", fontWeight: 600 }}>
            {err}
          </motion.div>
        )}
      </AnimatePresence>

      <motion.button type="submit" disabled={busy || !u || !p}
        whileTap={{ scale: 0.97 }}
        style={{
          marginTop: 2, padding: "12px", borderRadius: 12, border: "none",
          cursor: busy || !u || !p ? "default" : "pointer",
          background: "linear-gradient(135deg, #19808f, #0c5563)", color: "#fff",
          fontSize: "0.9rem", fontWeight: 700, opacity: busy || !u || !p ? 0.55 : 1,
          display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
          boxShadow: "0 8px 20px #0c556340",
        }}>
        {busy && <Loader2 size={15} className="animate-spin" />}
        {busy ? t("login_signing") : t("login_submit")}
      </motion.button>

      <div style={{ display: "flex", justifyContent: "center", gap: 4, marginTop: 2 }}>
        {LANGS.map((l) => (
          <button type="button" key={l.code} onClick={() => setLang(l.code)}
            style={{ padding: "4px 12px", borderRadius: 999, border: "none", cursor: "pointer", fontSize: "0.72rem",
              fontWeight: lang === l.code ? 700 : 400, background: lang === l.code ? "#0c5563" : "var(--surface2)", color: lang === l.code ? "#fff" : "var(--soft)" }}>
            {l.label}
          </button>
        ))}
      </div>
    </form>
  );

  return wrap(
    <motion.div
      initial={{ opacity: 0, y: 24, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      style={{
        width: isMobile ? 400 : 880, maxWidth: "96vw",
        display: "flex", flexDirection: isMobile ? "column" : "row",
        borderRadius: 24, overflow: "hidden", background: "var(--card)",
        boxShadow: "0 40px 100px rgba(0,0,0,0.45)",
      }}>
      {hero}{formSide}
    </motion.div>
  );
}
