import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

export type PreventivoItem = {
  url: string;
  title: string;
  image?: string | null;
  nuovo?: number | null;
  usato?: number | null;
  buyback?: number | null;
};

const KEY = "preventivo_items_v1";

type Ctx = {
  items: PreventivoItem[];
  has: (url: string) => boolean;
  add: (item: PreventivoItem) => void;
  remove: (url: string) => void;
  setBuyback: (url: string, value: number | null) => void;
  clear: () => void;
  total: number;
  ready: boolean;
};

const PreventivoContext = createContext<Ctx | null>(null);

export function PreventivoProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<PreventivoItem[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const raw = await AsyncStorage.getItem(KEY);
        if (raw) setItems(JSON.parse(raw));
      } catch {
        // ignore
      } finally {
        setReady(true);
      }
    })();
  }, []);

  useEffect(() => {
    if (ready) AsyncStorage.setItem(KEY, JSON.stringify(items)).catch(() => {});
  }, [items, ready]);

  const has = useCallback((url: string) => items.some((i) => i.url === url), [items]);

  const add = useCallback((item: PreventivoItem) => {
    setItems((prev) => (prev.some((i) => i.url === item.url) ? prev : [item, ...prev]));
  }, []);

  const remove = useCallback((url: string) => {
    setItems((prev) => prev.filter((i) => i.url !== url));
  }, []);

  const setBuyback = useCallback((url: string, value: number | null) => {
    setItems((prev) => prev.map((i) => (i.url === url ? { ...i, buyback: value } : i)));
  }, []);

  const clear = useCallback(() => setItems([]), []);

  const total = items.reduce((sum, i) => sum + (i.buyback ?? 0), 0);

  return (
    <PreventivoContext.Provider value={{ items, has, add, remove, setBuyback, clear, total, ready }}>
      {children}
    </PreventivoContext.Provider>
  );
}

export function usePreventivo() {
  const ctx = useContext(PreventivoContext);
  if (!ctx) throw new Error("usePreventivo must be used within PreventivoProvider");
  return ctx;
}
