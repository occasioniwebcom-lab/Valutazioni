import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { login as apiLogin, setAuthToken, setOnUnauthorized } from "@/src/api";

const KEY = "auth_token_v1";

type Ctx = {
  token: string | null;
  ready: boolean;
  signIn: (password: string) => Promise<void>;
  signOut: () => void;
};

const AuthContext = createContext<Ctx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  const signOut = useCallback(() => {
    setToken(null);
    setAuthToken(null);
    AsyncStorage.removeItem(KEY).catch(() => {});
  }, []);

  useEffect(() => {
    setOnUnauthorized(() => signOut());
    (async () => {
      try {
        const t = await AsyncStorage.getItem(KEY);
        if (t) { setAuthToken(t); setToken(t); }
      } catch {
        // ignore
      } finally {
        setReady(true);
      }
    })();
    return () => setOnUnauthorized(null);
  }, [signOut]);

  const signIn = useCallback(async (password: string) => {
    const t = await apiLogin(password);
    setAuthToken(t);
    setToken(t);
    await AsyncStorage.setItem(KEY, t);
  }, []);

  return (
    <AuthContext.Provider value={{ token, ready, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
