import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";

const API = (import.meta as any).env?.VITE_API_URL || "http://localhost:8077";

interface PortfolioState {
  data: any | null;          // { widgets, kpis, meta }
  loading: boolean;
  online: boolean;
  meta: any | null;
  refresh: () => void;
  upload: (file: File) => Promise<any>;
  ask: (q: string) => Promise<any>;
  pmBoard: (period: string) => Promise<any>;
}

const Ctx = createContext<PortfolioState>({
  data: null, loading: true, online: false, meta: null,
  refresh: () => {}, upload: async () => ({}), ask: async () => ({}),
  pmBoard: async () => ({ rows: [] }),
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

  const upload = useCallback(async (file: File) => {
    const r = await fetch(`${API}/api/upload?filename=${encodeURIComponent(file.name)}`, {
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

  return (
    <Ctx.Provider value={{ data, loading, online, meta, refresh, upload, ask, pmBoard }}>
      {children}
    </Ctx.Provider>
  );
}

export const usePortfolio = () => useContext(Ctx);
