"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import * as auth from "@/lib/auth";

type AuthState = {
  user: auth.User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
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

  const signIn = useCallback(async (email: string, password: string) => {
    const { access } = await auth.login(email, password);
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

  return (
    <Ctx.Provider value={{ user, loading, signIn, signOut, refreshUser }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
