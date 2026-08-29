import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import { AppState, AppStateStatus } from "react-native";
import { storage } from "@/src/utils/storage";

const PIN_KEY = "app_pin_v1";

type Ctx = {
  loading: boolean;
  hasPin: boolean;
  unlocked: boolean;
  unlock: (pin: string) => boolean;
  setPin: (pin: string) => Promise<void>;
  disablePin: () => Promise<void>;
};

const LockContext = createContext<Ctx | null>(null);

export function LockProvider({ children }: { children: React.ReactNode }) {
  const [pin, setPinState] = useState<string | null>(null);
  const [unlocked, setUnlocked] = useState(false);
  const [loading, setLoading] = useState(true);
  const pinRef = useRef<string | null>(null);

  useEffect(() => {
    (async () => {
      const stored = await storage.secureGet(PIN_KEY, "");
      const p = stored && String(stored).length > 0 ? String(stored) : null;
      pinRef.current = p;
      setPinState(p);
      setUnlocked(!p); // no pin => app open
      setLoading(false);
    })();
  }, []);

  // Re-lock when the app goes to background (requires PIN again on return).
  useEffect(() => {
    const sub = AppState.addEventListener("change", (state: AppStateStatus) => {
      if ((state === "background" || state === "inactive") && pinRef.current) {
        setUnlocked(false);
      }
    });
    return () => sub.remove();
  }, []);

  const unlock = useCallback((entered: string) => {
    if (pinRef.current && entered === pinRef.current) {
      setUnlocked(true);
      return true;
    }
    return false;
  }, []);

  const setPin = useCallback(async (newPin: string) => {
    await storage.secureSet(PIN_KEY, newPin);
    pinRef.current = newPin;
    setPinState(newPin);
    setUnlocked(true);
  }, []);

  const disablePin = useCallback(async () => {
    await storage.secureRemove(PIN_KEY);
    pinRef.current = null;
    setPinState(null);
    setUnlocked(true);
  }, []);

  return (
    <LockContext.Provider value={{ loading, hasPin: !!pin, unlocked, unlock, setPin, disablePin }}>
      {children}
    </LockContext.Provider>
  );
}

export function useLock() {
  const ctx = useContext(LockContext);
  if (!ctx) throw new Error("useLock must be used within LockProvider");
  return ctx;
}
