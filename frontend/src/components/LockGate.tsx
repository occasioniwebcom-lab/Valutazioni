import React, { useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";

import { colors, font, fontSize, radius, spacing } from "@/src/theme";
import { Logo } from "@/src/components/Logo";
import { useLock } from "@/src/store/lock";

export function LockGate({ children }: { children: React.ReactNode }) {
  const { loading, hasPin, unlocked, unlock } = useLock();
  const insets = useSafeAreaInsets();
  const [value, setValue] = useState("");
  const [error, setError] = useState(false);

  if (loading) return null;
  if (!hasPin || unlocked) return <>{children}</>;

  const attempt = (v: string) => {
    if (!unlock(v)) {
      setError(true);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error).catch(() => {});
      setValue("");
    }
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top + spacing["2xl"] }]} testID="lock-screen">
      <Logo size={64} />
      <Text style={styles.title}>Codice di accesso</Text>
      <Text style={styles.sub}>Inserisci il tuo codice per continuare</Text>

      <View style={styles.dots}>
        {Array.from({ length: Math.max(4, value.length) }).map((_, i) => (
          <View key={i} style={[styles.dot, i < value.length && styles.dotFilled]} />
        ))}
      </View>

      <TextInput
        testID="lock-input"
        style={styles.input}
        value={value}
        onChangeText={(t) => {
          setError(false);
          const clean = t.replace(/[^0-9]/g, "").slice(0, 8);
          setValue(clean);
        }}
        keyboardType="number-pad"
        secureTextEntry
        autoFocus
        maxLength={8}
        returnKeyType="done"
        onSubmitEditing={() => attempt(value)}
        placeholder="••••"
        placeholderTextColor={colors.muted}
      />

      {error && (
        <Text style={styles.error} testID="lock-error">Codice errato, riprova</Text>
      )}

      <Pressable
        testID="lock-unlock-button"
        style={[styles.btn, value.length < 4 && styles.btnDisabled]}
        disabled={value.length < 4}
        onPress={() => attempt(value)}
      >
        <Feather name="unlock" size={18} color={colors.onBrandPrimary} />
        <Text style={styles.btnText}>Sblocca</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface, alignItems: "center", paddingHorizontal: spacing.xl, gap: spacing.md },
  title: { fontFamily: font.bold, fontSize: fontSize.xl, color: colors.onSurface, marginTop: spacing.md },
  sub: { fontFamily: font.regular, fontSize: fontSize.base, color: colors.muted, textAlign: "center" },
  dots: { flexDirection: "row", gap: spacing.md, marginTop: spacing.lg, height: 16, alignItems: "center" },
  dot: { width: 12, height: 12, borderRadius: 6, backgroundColor: colors.surfaceTertiary, borderWidth: 1, borderColor: colors.borderStrong },
  dotFilled: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
  input: {
    marginTop: spacing.lg, width: 200, textAlign: "center", letterSpacing: 8,
    backgroundColor: colors.surfaceTertiary, borderRadius: radius.md, paddingVertical: spacing.md,
    fontFamily: font.monoSemibold, fontSize: fontSize.xl, color: colors.onSurface,
  },
  error: { fontFamily: font.medium, fontSize: fontSize.base, color: colors.error, marginTop: spacing.xs },
  btn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm,
    marginTop: spacing.lg, backgroundColor: colors.brandPrimary, borderRadius: radius.md,
    paddingVertical: spacing.lg, paddingHorizontal: spacing["2xl"], minWidth: 200,
  },
  btnDisabled: { opacity: 0.4 },
  btnText: { fontFamily: font.semibold, fontSize: fontSize.lg, color: colors.onBrandPrimary },
});
