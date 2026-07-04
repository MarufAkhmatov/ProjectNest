import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import { X, Plus, KeyRound, Trash2, Shield, User, ChevronDown, AudioLines, Check } from "lucide-react";
import { usePortfolio } from "../portfolio";
import { useI18n } from "../i18n";
import { usePopupOpenSignal, useTemurBesidePad } from "../popup";

const ROLE_COLORS: Record<string, { bg: string; color: string }> = {
  admin: { bg: "#e8f0fe", color: "#1a56db" },
  pm:    { bg: "var(--surface2)", color: "var(--text-muted)" },
};

type User = { username: string; name: string; role: string };
type ResetState = { pass: string; loading: boolean; done: boolean; err: string };

export function AdminPanel({ onClose }: { onClose: () => void }) {
  usePopupOpenSignal(true);
  const pad = useTemurBesidePad();
  const { t, tf } = useI18n();
  const { adminUsers, adminAddUser, adminResetPassword, adminDeleteUser, voiceStatus, setOpenAIKey } = usePortfolio();

  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  // OpenAI voice key (for Temur's ChatGPT voice bridge)
  const [keyInput, setKeyInput] = useState("");
  const [keySet, setKeySet] = useState(false);
  const [keyBusy, setKeyBusy] = useState(false);
  const [keySaved, setKeySaved] = useState(false);
  useEffect(() => { voiceStatus().then(s => setKeySet(!!s?.has_key)).catch(() => {}); }, [voiceStatus]);
  const saveKey = async () => {
    if (!keyInput.trim().startsWith("sk-")) return;
    setKeyBusy(true);
    const r = await setOpenAIKey(keyInput.trim());
    setKeyBusy(false);
    if (r?.ok) { setKeySet(true); setKeySaved(true); setKeyInput(""); setTimeout(() => setKeySaved(false), 2500); }
  };

  // Add-user form state
  const [showAdd, setShowAdd] = useState(false);
  const [newUser, setNewUser] = useState({ username: "", name: "", password: "", role: "pm" });
  const [addErr, setAddErr] = useState("");
  const [addOk, setAddOk] = useState(false);
  const [addLoading, setAddLoading] = useState(false);

  // Per-row reset/delete state
  const [resets, setResets] = useState<Record<string, ResetState>>({});
  const [deleting, setDeleting] = useState<Record<string, boolean>>({});

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const r = await adminUsers();
      setUsers(r.users || []);
    } finally {
      setLoading(false);
    }
  }, [adminUsers]);

  useEffect(() => { reload(); }, [reload]);

  const handleAdd = async () => {
    if (!newUser.username.trim() || !newUser.password.trim() || !newUser.name.trim()) {
      setAddErr(t("admin_err_required")); return;
    }
    setAddLoading(true); setAddErr("");
    const r = await adminAddUser({ ...newUser, username: newUser.username.trim(), name: newUser.name.trim(), password: newUser.password.trim() });
    setAddLoading(false);
    if (r.ok) {
      setAddOk(true); setNewUser({ username: "", name: "", password: "", role: "pm" }); setShowAdd(false);
      setTimeout(() => setAddOk(false), 2500);
      reload();
    } else {
      setAddErr(r.error === "user already exists" ? t("admin_err_exists") : r.error || "error");
    }
  };

  const startReset = (u: User) => {
    setResets(p => ({ ...p, [u.username]: { pass: "", loading: false, done: false, err: "" } }));
  };

  const handleReset = async (username: string) => {
    const s = resets[username];
    if (!s?.pass.trim()) return;
    setResets(p => ({ ...p, [username]: { ...p[username], loading: true, err: "" } }));
    const r = await adminResetPassword(username, s.pass.trim());
    if (r.ok) {
      setResets(p => ({ ...p, [username]: { ...p[username], loading: false, done: true } }));
      setTimeout(() => setResets(p => { const n = { ...p }; delete n[username]; return n; }), 2000);
    } else {
      setResets(p => ({ ...p, [username]: { ...p[username], loading: false, err: r.error || "error" } }));
    }
  };

  const handleDelete = async (u: User) => {
    if (!window.confirm(tf("admin_delete_confirm", { name: u.name || u.username }))) return;
    setDeleting(p => ({ ...p, [u.username]: true }));
    const r = await adminDeleteUser(u.username);
    setDeleting(p => ({ ...p, [u.username]: false }));
    if (r.ok) { reload(); }
    else { alert(r.error === "cannot delete the last admin" ? t("admin_err_last_admin") : r.error || "error"); }
  };

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "8px 11px", borderRadius: 8, border: "1px solid var(--divider)",
    background: "var(--surface2)", color: "var(--text)", fontSize: "0.83rem",
    fontFamily: "var(--font-sans)", outline: "none", boxSizing: "border-box",
  };
  const btnStyle = (primary?: boolean): React.CSSProperties => ({
    padding: "7px 14px", borderRadius: 8, border: "none", cursor: "pointer",
    fontSize: "0.8rem", fontWeight: 500, fontFamily: "var(--font-sans)",
    background: primary ? "#0c5563" : "var(--surface2)",
    color: primary ? "#fff" : "var(--text)",
  });

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      style={{ position: "fixed", inset: 0, zIndex: 400, background: "rgba(0,0,0,0.55)", display: "flex", alignItems: "center", justifyContent: "center", padding: 16, ...pad }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <motion.div
        initial={{ opacity: 0, y: 18, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 18, scale: 0.97 }}
        transition={{ duration: 0.22 }}
        style={{ background: "var(--card)", borderRadius: 18, width: "100%", maxWidth: 680, maxHeight: "88vh",
          display: "flex", flexDirection: "column", overflow: "hidden", boxShadow: "0 24px 64px rgba(0,0,0,0.35)" }}
      >
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "18px 22px 14px", borderBottom: "1px solid var(--divider)", flexShrink: 0 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: "#e8f0fe", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Shield size={18} color="#1a56db" />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text)" }}>{t("admin_title")}</div>
            <div style={{ fontSize: "0.76rem", color: "var(--text-muted)", marginTop: 1 }}>{t("admin_subtitle")}</div>
          </div>
          <button onClick={onClose} style={{ width: 32, height: 32, borderRadius: 8, border: "none", background: "var(--surface2)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)" }}>
            <X size={16} />
          </button>
        </div>

        {/* Toolbar */}
        <div style={{ padding: "12px 22px", borderBottom: "1px solid var(--divider)", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{users.length} {t("admin_col_user").toLowerCase()}</span>
          <button
            onClick={() => { setShowAdd(v => !v); setAddErr(""); setAddOk(false); }}
            style={{ ...btnStyle(true), display: "flex", alignItems: "center", gap: 6 }}
          >
            <Plus size={14} /> {t("admin_add")}
          </button>
        </div>

        {/* Add user form */}
        <AnimatePresence>
          {showAdd && (
            <motion.div
              initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.18 }}
              style={{ overflow: "hidden", flexShrink: 0 }}
            >
              <div style={{ padding: "16px 22px", borderBottom: "1px solid var(--divider)", background: "var(--surface2)" }}>
                <div style={{ fontSize: "0.84rem", fontWeight: 600, color: "var(--text)", marginBottom: 12 }}>{t("admin_add_title")}</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <div>
                    <label style={{ fontSize: "0.74rem", color: "var(--text-muted)", display: "block", marginBottom: 4 }}>{t("admin_field_user")}</label>
                    <input style={inputStyle} value={newUser.username} onChange={e => setNewUser(p => ({ ...p, username: e.target.value }))} placeholder="m.axmatov@ipakyulibank.uz" />
                  </div>
                  <div>
                    <label style={{ fontSize: "0.74rem", color: "var(--text-muted)", display: "block", marginBottom: 4 }}>{t("admin_field_name")}</label>
                    <input style={inputStyle} value={newUser.name} onChange={e => setNewUser(p => ({ ...p, name: e.target.value }))} placeholder="M. Axmatov" />
                  </div>
                  <div>
                    <label style={{ fontSize: "0.74rem", color: "var(--text-muted)", display: "block", marginBottom: 4 }}>{t("admin_field_pass")}</label>
                    <input style={inputStyle} type="password" value={newUser.password} onChange={e => setNewUser(p => ({ ...p, password: e.target.value }))} placeholder="••••••" />
                  </div>
                  <div>
                    <label style={{ fontSize: "0.74rem", color: "var(--text-muted)", display: "block", marginBottom: 4 }}>{t("admin_field_role")}</label>
                    <div style={{ position: "relative" }}>
                      <select style={{ ...inputStyle, appearance: "none", paddingRight: 28 }}
                        value={newUser.role} onChange={e => setNewUser(p => ({ ...p, role: e.target.value }))}>
                        <option value="pm">{t("admin_role_pm")}</option>
                        <option value="admin">{t("admin_role_admin")}</option>
                      </select>
                      <ChevronDown size={13} style={{ position: "absolute", right: 9, top: "50%", transform: "translateY(-50%)", pointerEvents: "none", color: "var(--text-muted)" }} />
                    </div>
                  </div>
                </div>
                {addErr && <div style={{ marginTop: 8, fontSize: "0.78rem", color: "#e0574f" }}>{addErr}</div>}
                {addOk && <div style={{ marginTop: 8, fontSize: "0.78rem", color: "#1f9d57" }}>{t("admin_ok_added")}</div>}
                <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                  <button style={btnStyle(true)} onClick={handleAdd} disabled={addLoading}>{addLoading ? "…" : t("admin_save")}</button>
                  <button style={btnStyle()} onClick={() => { setShowAdd(false); setAddErr(""); }}>{t("admin_cancel")}</button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* User list */}
        <div style={{ flex: 1, overflowY: "auto", padding: "0 22px 16px" }}>
          {loading ? (
            <div style={{ padding: 32, textAlign: "center", color: "var(--text-muted)", fontSize: "0.84rem" }}>Loading…</div>
          ) : (
            users.map((u, i) => {
              const rc = ROLE_COLORS[u.role] || ROLE_COLORS.pm;
              const rst = resets[u.username];
              return (
                <div key={u.username} style={{ flexShrink: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "13px 0", borderBottom: i < users.length - 1 ? "1px solid var(--divider)" : "none" }}>
                    {/* Avatar placeholder */}
                    <div style={{ width: 36, height: 36, borderRadius: "50%", background: "var(--surface2)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <User size={16} color="var(--text-muted)" />
                    </div>
                    {/* Info */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: "0.84rem", fontWeight: 600, color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{u.name || u.username}</div>
                      <div style={{ fontSize: "0.74rem", color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{u.username}</div>
                    </div>
                    {/* Role badge */}
                    <span style={{ padding: "3px 9px", borderRadius: 99, fontSize: "0.7rem", fontWeight: 600, background: rc.bg, color: rc.color, flexShrink: 0 }}>
                      {u.role === "admin" ? t("admin_role_admin") : t("admin_role_pm")}
                    </span>
                    {/* Actions */}
                    <button
                      onClick={() => rst ? setResets(p => { const n = { ...p }; delete n[u.username]; return n; }) : startReset(u)}
                      title={t("admin_reset")}
                      style={{ width: 30, height: 30, borderRadius: 7, border: "none", background: rst ? "#fef3c7" : "var(--surface2)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", color: rst ? "#b45309" : "var(--text-muted)", flexShrink: 0 }}
                    >
                      <KeyRound size={14} />
                    </button>
                    <button
                      onClick={() => handleDelete(u)}
                      disabled={deleting[u.username]}
                      title={t("admin_delete")}
                      style={{ width: 30, height: 30, borderRadius: 7, border: "none", background: "var(--surface2)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", color: "#e0574f", flexShrink: 0 }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>

                  {/* Inline reset form */}
                  <AnimatePresence>
                    {rst && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.14 }}
                        style={{ overflow: "hidden" }}
                      >
                        <div style={{ padding: "10px 0 14px 48px", display: "flex", alignItems: "center", gap: 8 }}>
                          <input
                            type="password"
                            placeholder={t("admin_new_pass")}
                            value={rst.pass}
                            onChange={e => setResets(p => ({ ...p, [u.username]: { ...p[u.username], pass: e.target.value, err: "" } }))}
                            onKeyDown={e => e.key === "Enter" && handleReset(u.username)}
                            style={{ ...inputStyle, width: 200 }}
                            autoFocus
                          />
                          <button style={btnStyle(true)} onClick={() => handleReset(u.username)} disabled={rst.loading}>
                            {rst.loading ? "…" : rst.done ? "✓ " + t("admin_ok_reset") : t("admin_confirm")}
                          </button>
                          {rst.err && <span style={{ fontSize: "0.76rem", color: "#e0574f" }}>{rst.err}</span>}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })
          )}
        </div>

        {/* OpenAI voice key — powers Temur's spoken (ChatGPT) voice bridge */}
        <div style={{ padding: "14px 22px", borderTop: "1px solid var(--divider)", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <AudioLines size={16} color="#10a37f" />
            <span style={{ fontSize: "0.84rem", fontWeight: 600, color: "var(--text)" }}>{t("voice_key_title")}</span>
            {keySet && <span style={{ fontSize: "0.68rem", fontWeight: 700, color: "#1f9d57", display: "flex", alignItems: "center", gap: 3 }}><Check size={12} /> {t("voice_key_set")}</span>}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <input type="password" value={keyInput} onChange={e => setKeyInput(e.target.value)}
              placeholder={keySet ? "sk-…  (" + t("voice_key_replace") + ")" : "sk-…"}
              style={{ flex: 1, padding: "8px 11px", borderRadius: 8, border: "1px solid var(--divider)", background: "var(--surface2)", color: "var(--text)", fontSize: "0.8rem", fontFamily: "var(--font-sans)", outline: "none" }} />
            <button onClick={saveKey} disabled={keyBusy || !keyInput.trim().startsWith("sk-")}
              style={{ padding: "8px 14px", borderRadius: 8, border: "none", cursor: keyInput.trim().startsWith("sk-") ? "pointer" : "default", background: "#10a37f", color: "#fff", fontSize: "0.8rem", fontWeight: 700, opacity: keyInput.trim().startsWith("sk-") ? 1 : 0.5 }}>
              {keyBusy ? "…" : keySaved ? "✓" : t("admin_save")}
            </button>
          </div>
          <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginTop: 6 }}>{t("voice_key_hint")}</div>
        </div>
      </motion.div>
    </motion.div>
  );
}
