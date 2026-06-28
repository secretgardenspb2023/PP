"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import * as auth from "@/lib/auth";

type AuthState = {
  user: auth.User | null;
  token: string | null;
  loading: boolean;
  signIn: (email: string, password: string, captchaToken?: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
  applySession: (access: string, user: auth.User) => void;
};

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<auth.User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadFromRefresh = useCallback(async () => {
    try {
      const { access } = await auth.refresh();
      setToken(access);
      setUser(await auth.me(access));
    } catch {
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadFromRefresh();
  }, [loadFromRefresh]);

  const signIn = useCallback(async (email: string, password: string, captchaToken?: string) => {
    const { access } = await auth.login(email, password, captchaToken);
    setToken(access);
    setUser(await auth.me(access));
  }, []);

  const signOut = useCallback(async () => {
    await auth.logout();
    setToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    if (token) setUser(await auth.me(token));
  }, [token]);

  // Завести сессию из уже полученных токена и профиля (напр. после подтверждения
  // email — refresh-cookie уже выставлен бэкендом, повторный вход не нужен).
  const applySession = useCallback((access: string, u: auth.User) => {
    setToken(access);
    setUser(u);
    setLoading(false);
  }, []);

  return (
    <Ctx.Provider value={{ user, token, loading, signIn, signOut, refreshUser, applySession }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
