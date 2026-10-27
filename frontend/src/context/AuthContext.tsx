// Holds the signed-in user, their company and permissions, and the sign-in actions.
import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { authApi } from "../api/services";
import { tokenStore } from "../api/client";
import type { Permission, SessionUser, TokenResponse } from "../types";

interface AuthValue {
  user: SessionUser | null;
  loading: boolean;
  /** UI convenience only: the API checks every permission again. */
  can: (permission: Permission) => boolean;
  canAny: (permissions: Permission[]) => boolean;
  login: (email: string, password: string, remember?: boolean) => Promise<SessionUser>;
  registerCompany: (data: Parameters<typeof authApi.registerCompany>[0]) => Promise<SessionUser>;
  join: (data: Parameters<typeof authApi.join>[0]) => Promise<SessionUser>;
  applySession: (res: TokenResponse) => void;
  setUser: (user: SessionUser) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [loading, setLoading] = useState<boolean>(!!tokenStore.get());

  // Restore the session on page load.
  useEffect(() => {
    if (!tokenStore.get()) return;
    authApi.me().then(setUser).catch(() => tokenStore.clear()).finally(() => setLoading(false));
  }, []);

  const clearLocal = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  // The API client fires this when the server says the session has ended.
  useEffect(() => {
    window.addEventListener("fixflow:unauthorized", clearLocal);
    return () => window.removeEventListener("fixflow:unauthorized", clearLocal);
  }, [clearLocal]);

  const applySession = useCallback((res: TokenResponse, remember = true) => {
    tokenStore.set(res.access_token, remember);
    setUser(res.user);
  }, []);

  const value = useMemo<AuthValue>(() => {
    const held = new Set(user?.permissions ?? []);
    return {
      user,
      loading,
      can: (p) => held.has(p),
      canAny: (ps) => ps.some((p) => held.has(p)),
      applySession,
      setUser,
      login: async (email, password, remember = true) => {
        const res = await authApi.login(email, password);
        applySession(res, remember);
        return res.user;
      },
      registerCompany: async (data) => {
        const res = await authApi.registerCompany(data);
        applySession(res);
        return res.user;
      },
      join: async (data) => {
        const res = await authApi.join(data);
        applySession(res);
        return res.user;
      },
      logout: async () => {
        await authApi.logout().catch(() => undefined); // revoke the token on the server (FR-005)
        clearLocal();
      },
    };
  }, [user, loading, applySession, clearLocal]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
