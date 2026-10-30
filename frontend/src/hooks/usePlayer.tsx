import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError, tokenStore } from "../api/client";
import type { Profile } from "../api/types";

interface PlayerCtx {
  profile: Profile | null;
  loading: boolean;
  error: string | null;
  login: (name: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
  setProfile: (p: Profile) => void;
}

const Ctx = createContext<PlayerCtx | null>(null);

export function PlayerProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!tokenStore.get()) { setLoading(false); return; }
    try {
      setProfile(await api.me());
      setError(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) tokenStore.clear();
      else setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const login = async (name: string) => {
    const r = await api.guestLogin(name);
    tokenStore.set(r.token);
    setProfile(r.profile);
  };

  const logout = () => { tokenStore.clear(); setProfile(null); };

  return (
    <Ctx.Provider value={{ profile, loading, error, login, logout, refresh, setProfile }}>{children}</Ctx.Provider>
  );
}

export function usePlayer() {
  const c = useContext(Ctx);
  if (!c) throw new Error("usePlayer outside provider");
  return c;
}
