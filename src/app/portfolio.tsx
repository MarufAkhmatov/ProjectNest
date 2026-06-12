import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";

const API = (import.meta as any).env?.VITE_API_URL || "http://localhost:8077";

interface PortfolioState {
  data: any | null;          // { widgets, kpis, meta }
  loading: boolean;
  online: boolean;
  meta: any | null;
  refresh: () => void;
  upload: (file: File, mode?: "replace" | "merge") => Promise<any>;
  ask: (q: string) => Promise<any>;
  pmBoard: (period: string) => Promise<any>;
  notifications: () => Promise<any>;
  dataQuality: () => Promise<any>;
  drill: (params: Record<string, string>) => Promise<any>;
  issueDetail: (key: string) => Promise<any>;
}

const Ctx = createContext<PortfolioState>({
  data: null, loading: true, online: false, meta: null,
  refresh: () => {}, upload: async () => ({}), ask: async () => ({}),
  pmBoard: async () => ({ rows: [] }), notifications: async () => ({ epics: [], tasks: [] }),
  dataQuality: async () => ({ fields: [] }), drill: async () => ({ issues: [] }),
  issueDetail: async () => ({ found: false }),
});

export function PortfolioProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [online, setOnline] = useState(false);
  const [meta, setMeta] = useState<any | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/dashboard`);
      const j = await r.json();
      setOnline(true);
      if (j.has_data) { setData(j); setMeta(j.meta); }
      else { setData(null); setMeta(null); }
    } catch {
      setOnline(false);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const upload = useCallback(async (file: File, mode: "replace" | "merge" = "replace") => {
    const r = await fetch(`${API}/api/upload?filename=${encodeURIComponent(file.name)}&mode=${mode}`, {
      method: "POST", body: file,
    });
    const j = await r.json();
    await refresh();
    return j;
  }, [refresh]);

  const ask = useCallback(async (q: string) => {
    try {
      const r = await fetch(`${API}/api/aria`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      return await r.json();
    } catch {
      return { answer: "ARIA backend is offline. Start the backend (python backend/server.py).", source: "system" };
    }
  }, []);

  const pmBoard = useCallback(async (period: string) => {
    try {
      const r = await fetch(`${API}/api/pm-leaderboard?period=${encodeURIComponent(period)}`);
      return await r.json();
    } catch {
      return { rows: [] };
    }
  }, []);

  const notifications = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/notifications`);
      return await r.json();
    } catch {
      return { epics: [], tasks: [] };
    }
  }, []);

  const dataQuality = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/data-quality`);
      return await r.json();
    } catch {
      return { fields: [] };
    }
  }, []);

  const drill = useCallback(async (params: Record<string, string>) => {
    try {
      const qs = new URLSearchParams(params).toString();
      const r = await fetch(`${API}/api/issues?${qs}`);
      return await r.json();
    } catch {
      return { issues: [] };
    }
  }, []);

  const issueDetail = useCallback(async (key: string) => {
    try {
      const r = await fetch(`${API}/api/issue?key=${encodeURIComponent(key)}`);
      return await r.json();
    } catch {
      return { found: false };
    }
  }, []);

  return (
    <Ctx.Provider value={{ data, loading, online, meta, refresh, upload, ask, pmBoard, notifications, dataQuality, drill, issueDetail }}>
      {children}
    </Ctx.Provider>
  );
}

export const usePortfolio = () => useContext(Ctx);
