import React, { useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Feather } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";

import { colors, font, fontSize, radius, spacing } from "@/src/theme";
import { changePassword } from "@/src/api";
import { useAuth } from "@/src/store/auth";

export default function ImpostazioniScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { signOut } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  const submit = async () => {
    setMsg(null);
    if (next.length < 4) { setMsg({ type: "err", text: "La nuova password deve avere almeno 4 caratteri" }); return; }
    if (next !== confirm) { setMsg({ type: "err", text: "Le due password non coincidono" }); return; }
    setBusy(true);
    try {
      await changePassword(current, next);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
      setMsg({ type: "ok", text: "Password cambiata. Effettua di nuovo l'accesso." });
      setTimeout(() => signOut(), 1200);
    } catch (e: any) {
      setMsg({ type: "err", text: e?.message || "Errore" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top }]} testID="impostazioni-screen">
      <View style={styles.header}>
        <Pressable testID="close-settings" onPress={() => router.back()} hitSlop={8} style={styles.iconBtn}>
          <Feather name="chevron-left" size={24} color={colors.onSurface} />
        </Pressable>
        <Text style={styles.h1}>Impostazioni</Text>
        <View style={{ width: 32 }} />
      </View>

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={insets.top}>
        <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }} keyboardShouldPersistTaps="handled">
          <Text style={styles.sectionTitle}>Cambia password</Text>

          <TextInput testID="current-password" style={styles.input} value={current} onChangeText={setCurrent}
            placeholder="Password attuale" placeholderTextColor={colors.muted} secureTextEntry autoCapitalize="none" />
          <TextInput testID="new-password" style={styles.input} value={next} onChangeText={setNext}
            placeholder="Nuova password" placeholderTextColor={colors.muted} secureTextEntry autoCapitalize="none" />
          <TextInput testID="confirm-password" style={styles.input} value={confirm} onChangeText={setConfirm}
            placeholder="Conferma nuova password" placeholderTextColor={colors.muted} secureTextEntry autoCapitalize="none" />

          {msg ? <Text style={[styles.msg, msg.type === "err" ? styles.msgErr : styles.msgOk]} testID="settings-msg">{msg.text}</Text> : null}

          <Pressable testID="save-password" style={[styles.btn, busy && { opacity: 0.6 }]} disabled={busy} onPress={submit}>
            {busy ? <ActivityIndicator color={colors.onBrandPrimary} /> : <Text style={styles.btnText}>Salva nuova password</Text>}
          </Pressable>

          <Pressable testID="logout-button" style={styles.logoutBtn} onPress={() => { Haptics.selectionAsync().catch(() => {}); signOut(); }}>
            <Feather name="log-out" size={18} color={colors.error} />
            <Text style={styles.logoutText}>Esci</Text>
          </Pressable>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: spacing.md, paddingVertical: spacing.md,
    borderBottomColor: colors.border, borderBottomWidth: 1,
  },
  iconBtn: { width: 32, height: 32, alignItems: "center", justifyContent: "center" },
  h1: { fontFamily: font.bold, fontSize: fontSize.xl, color: colors.onSurface },
  sectionTitle: { fontFamily: font.semibold, fontSize: fontSize.base, color: colors.onSurfaceTertiary, marginBottom: spacing.xs },
  input: {
    backgroundColor: colors.surfaceTertiary, borderRadius: radius.md,
    paddingHorizontal: spacing.md, paddingVertical: spacing.md,
    fontFamily: font.regular, fontSize: fontSize.lg, color: colors.onSurface,
  },
  msg: { fontFamily: font.medium, fontSize: fontSize.base, marginTop: spacing.xs },
  msgErr: { color: colors.error },
  msgOk: { color: colors.brandPrimary },
  btn: { backgroundColor: colors.brandPrimary, borderRadius: radius.md, paddingVertical: spacing.lg, alignItems: "center", marginTop: spacing.sm },
  btnText: { fontFamily: font.semibold, fontSize: fontSize.lg, color: colors.onBrandPrimary },
  logoutBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm, paddingVertical: spacing.lg, marginTop: spacing.xl },
  logoutText: { fontFamily: font.semibold, fontSize: fontSize.base, color: colors.error },
});
