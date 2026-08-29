import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { router } from "expo-router";
import { Feather } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";

import { colors, font, fontSize, radius, spacing } from "@/src/theme";
import { Logo } from "@/src/components/Logo";
import { useAuth } from "@/src/store/auth";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { token, ready, signIn } = useAuth();
  const insets = useSafeAreaInsets();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const prevToken = useRef<string | null>(null);

  // After logging in from a logged-out state, always land on the main screen
  // (deterministic on web, where the browser URL could otherwise be restored to
  // a deep route like /impostazioni). Does NOT fire on token refresh while authed.
  useEffect(() => {
    if (!prevToken.current && token) {
      setTimeout(() => { try { router.replace("/cerca"); } catch { /* noop */ } }, 0);
    }
    prevToken.current = token;
  }, [token]);

  if (!ready) return null;
  if (token) return <>{children}</>;

  const submit = async () => {
    if (!password || busy) return;
    setBusy(true);
    setError("");
    try {
      await signIn(password);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    } catch (e: any) {
      setError(e?.message || "Password errata");
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error).catch(() => {});
      setPassword("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={[styles.inner, { paddingTop: insets.top + spacing["2xl"] }]} testID="login-screen">
        <Logo size={72} />
        <Text style={styles.title}>Valutazioni</Text>
        <Text style={styles.sub}>Inserisci la password per accedere</Text>

        <View style={styles.inputBox}>
          <Feather name="lock" size={18} color={colors.muted} />
          <TextInput
            testID="password-input"
            style={styles.input}
            value={password}
            onChangeText={(t) => { setError(""); setPassword(t); }}
            placeholder="Password"
            placeholderTextColor={colors.muted}
            secureTextEntry
            autoCapitalize="none"
            autoCorrect={false}
            returnKeyType="go"
            onSubmitEditing={submit}
          />
        </View>

        {error ? <Text style={styles.error} testID="login-error">{error}</Text> : null}

        <Pressable testID="login-button" style={[styles.btn, (!password || busy) && styles.btnDisabled]} disabled={!password || busy} onPress={submit}>
          {busy ? <ActivityIndicator color={colors.onBrandPrimary} /> : (
            <>
              <Feather name="log-in" size={18} color={colors.onBrandPrimary} />
              <Text style={styles.btnText}>Accedi</Text>
            </>
          )}
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  inner: { flex: 1, alignItems: "center", paddingHorizontal: spacing.xl, gap: spacing.md },
  title: { fontFamily: font.bold, fontSize: fontSize["2xl"], color: colors.onSurface, marginTop: spacing.md },
  sub: { fontFamily: font.regular, fontSize: fontSize.base, color: colors.muted, textAlign: "center" },
  inputBox: {
    flexDirection: "row", alignItems: "center", gap: spacing.sm, width: "100%",
    backgroundColor: colors.surfaceTertiary, borderRadius: radius.md,
    paddingHorizontal: spacing.md, marginTop: spacing.lg,
  },
  input: { flex: 1, fontFamily: font.regular, fontSize: fontSize.lg, color: colors.onSurface, paddingVertical: spacing.md },
  error: { fontFamily: font.medium, fontSize: fontSize.base, color: colors.error, marginTop: spacing.xs },
  btn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm,
    marginTop: spacing.lg, width: "100%", backgroundColor: colors.brandPrimary,
    borderRadius: radius.md, paddingVertical: spacing.lg,
  },
  btnDisabled: { opacity: 0.4 },
  btnText: { fontFamily: font.semibold, fontSize: fontSize.lg, color: colors.onBrandPrimary },
});
