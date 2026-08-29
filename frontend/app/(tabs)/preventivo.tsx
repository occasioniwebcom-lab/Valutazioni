import React, { useMemo, useState } from "react";
import {
  ActivityIndicator,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Image } from "expo-image";
import { Feather } from "@expo/vector-icons";
import * as Print from "expo-print";
import * as Sharing from "expo-sharing";
import * as Haptics from "expo-haptics";

import { colors, font, fontSize, radius, spacing, shadow, SHOP_LOGO, SHOP_NAME } from "@/src/theme";
import { formatEuro, formatEuroPlain, quoteId } from "@/src/format";
import { usePreventivo, PreventivoItem } from "@/src/store/preventivo";

function buildHtml(items: PreventivoItem[], total: number, id: string, customer: string) {
  const date = new Date().toLocaleDateString("it-IT", { day: "2-digit", month: "long", year: "numeric" });
  const rows = items
    .map(
      (i) => `
      <tr>
        <td class="cov">${i.image ? `<img src="${i.image}" />` : ""}</td>
        <td class="ttl">${i.title.replace(/</g, "&lt;")}</td>
        <td class="val">€ ${formatEuroPlain(i.buyback)}</td>
      </tr>`,
    )
    .join("");
  return `<!DOCTYPE html><html><head><meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    * { box-sizing: border-box; }
    body { font-family: -apple-system, Helvetica, Arial, sans-serif; color: #181C1A; margin: 0; padding: 32px; }
    .head { display: flex; align-items: center; gap: 16px; border-bottom: 2px solid #1F4734; padding-bottom: 16px; }
    .head img { width: 56px; height: 56px; object-fit: contain; border-radius: 8px; }
    .brand { font-size: 20px; font-weight: 700; color: #1F4734; }
    .doc { margin-left: auto; text-align: right; font-size: 12px; color: #3E4C45; }
    .doc b { font-size: 14px; color: #181C1A; }
    h1 { font-size: 22px; margin: 24px 0 4px; }
    .meta { font-size: 13px; color: #3E4C45; margin-bottom: 20px; }
    table { width: 100%; border-collapse: collapse; }
    th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .5px; color: #7A8A82; border-bottom: 1px solid #E6EBE8; padding: 8px 6px; }
    th.val, td.val { text-align: right; }
    td { padding: 10px 6px; border-bottom: 1px solid #F1F4F2; font-size: 14px; vertical-align: middle; }
    td.cov img { width: 40px; height: 40px; object-fit: cover; border-radius: 6px; background: #F1F4F2; }
    td.cov { width: 52px; }
    td.val { font-weight: 700; color: #1F4734; white-space: nowrap; font-variant-numeric: tabular-nums; }
    .total { display: flex; justify-content: space-between; align-items: center; margin-top: 24px; padding: 16px 18px; background: #E3EFE8; border-radius: 12px; }
    .total .lbl { font-size: 14px; font-weight: 600; color: #1A3B2B; }
    .total .amt { font-size: 24px; font-weight: 800; color: #1F4734; }
    .note { margin-top: 20px; font-size: 11px; color: #7A8A82; line-height: 1.5; }
  </style></head>
  <body>
    <div class="head">
      <img src="${SHOP_LOGO}" />
      <div class="brand">${SHOP_NAME}</div>
      <div class="doc">Preventivo n.<br/><b>${id}</b></div>
    </div>
    <h1>Preventivo di valutazione</h1>
    <div class="meta">Data: ${date}${customer ? ` &nbsp;·&nbsp; Cliente: <b>${customer.replace(/</g, "&lt;")}</b>` : ""}</div>
    <table>
      <thead><tr><th></th><th>Titolo</th><th class="val">Valutazione</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <div class="total">
      <span class="lbl">Totale valutazione (${items.length} ${items.length === 1 ? "titolo" : "titoli"})</span>
      <span class="amt">€ ${formatEuroPlain(total)}</span>
    </div>
    <div class="note">Valutazione indicativa basata sui prezzi buyback di riferimento. L'importo definitivo è soggetto a verifica delle condizioni del prodotto in negozio.</div>
  </body></html>`;
}

export default function PreventivoScreen() {
  const insets = useSafeAreaInsets();
  const { items, remove, clear, total } = usePreventivo();
  const [customer, setCustomer] = useState("");
  const [generating, setGenerating] = useState(false);
  const id = useMemo(() => quoteId(), []);

  const onShare = async () => {
    if (items.length === 0) return;
    setGenerating(true);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    try {
      const html = buildHtml(items, total, id, customer.trim());
      if (Platform.OS === "web") {
        await Print.printAsync({ html });
      } else {
        const { uri } = await Print.printToFileAsync({ html });
        if (await Sharing.isAvailableAsync()) {
          await Sharing.shareAsync(uri, { mimeType: "application/pdf", UTI: "com.adobe.pdf", dialogTitle: "Condividi preventivo" });
        }
      }
    } catch {
      // ignore
    } finally {
      setGenerating(false);
    }
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top }]} testID="preventivo-screen">
      <View style={styles.header}>
        <Image source={{ uri: SHOP_LOGO }} style={styles.logo} contentFit="contain" />
        <View style={{ flex: 1 }}>
          <Text style={styles.brand}>{SHOP_NAME}</Text>
          <Text style={styles.docId}>Preventivo n. {id}</Text>
        </View>
        {items.length > 0 && (
          <Pressable testID="clear-preventivo" onPress={() => { Haptics.selectionAsync().catch(() => {}); clear(); }} hitSlop={8} style={styles.clearBtn}>
            <Feather name="trash-2" size={16} color={colors.error} />
          </Pressable>
        )}
      </View>

      {items.length === 0 ? (
        <View style={styles.center} testID="preventivo-empty">
          <View style={styles.emptyIcon}><Feather name="file-text" size={30} color={colors.brandPrimary} /></View>
          <Text style={styles.centerTitle}>Preventivo vuoto</Text>
          <Text style={styles.centerText}>Aggiungi giochi dalla ricerca per{"\n"}creare un preventivo per il cliente.</Text>
        </View>
      ) : (
        <>
          <ScrollView contentContainerStyle={{ paddingBottom: spacing.md }} keyboardShouldPersistTaps="handled">
            <View style={styles.customerBox}>
              <Text style={styles.customerLabel}>Cliente (opzionale)</Text>
              <TextInput
                testID="customer-input"
                style={styles.customerInput}
                placeholder="Nome del cliente"
                placeholderTextColor={colors.muted}
                value={customer}
                onChangeText={setCustomer}
              />
            </View>

            {items.map((item) => (
              <View key={item.url} style={styles.row} testID="preventivo-row">
                <Image source={item.image ? { uri: item.image } : undefined} style={styles.cover} contentFit="cover" transition={150} />
                <View style={styles.mid}>
                  <Text style={styles.title} numberOfLines={2}>{item.title}</Text>
                  <Text style={styles.valLabel}>Valutazione</Text>
                </View>
                <Text style={styles.val}>{formatEuro(item.buyback)}</Text>
                <Pressable testID="remove-item" onPress={() => { Haptics.selectionAsync().catch(() => {}); remove(item.url); }} hitSlop={8} style={styles.removeBtn}>
                  <Feather name="x" size={18} color={colors.muted} />
                </Pressable>
              </View>
            ))}
          </ScrollView>

          <View style={[styles.footer, { paddingBottom: spacing.md }]}>
            <View style={styles.totalBox}>
              <Text style={styles.totalLabel}>Totale valutazione</Text>
              <Text style={styles.totalAmt} testID="preventivo-total">{formatEuro(total)}</Text>
            </View>
            <Pressable testID="share-pdf-button" onPress={onShare} disabled={generating} style={[styles.cta, generating && { opacity: 0.7 }]}>
              {generating ? (
                <ActivityIndicator color={colors.onBrandPrimary} />
              ) : (
                <>
                  <Feather name="share" size={18} color={colors.onBrandPrimary} />
                  <Text style={styles.ctaText}>Condividi PDF</Text>
                </>
              )}
            </Pressable>
          </View>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  header: {
    flexDirection: "row", alignItems: "center", gap: spacing.md,
    paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: spacing.md,
    borderBottomColor: colors.border, borderBottomWidth: 1,
  },
  logo: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.surfaceSecondary },
  brand: { fontFamily: font.bold, fontSize: fontSize.lg, color: colors.brandPrimary },
  docId: { fontFamily: font.mono, fontSize: fontSize.sm, color: colors.muted, marginTop: 1 },
  clearBtn: { padding: 8, borderRadius: radius.sm },
  customerBox: { paddingHorizontal: spacing.lg, paddingTop: spacing.lg, paddingBottom: spacing.sm },
  customerLabel: { fontFamily: font.medium, fontSize: fontSize.sm, color: colors.muted, marginBottom: spacing.xs },
  customerInput: {
    backgroundColor: colors.surfaceTertiary, borderRadius: radius.md,
    paddingHorizontal: spacing.md, paddingVertical: spacing.md,
    fontFamily: font.regular, fontSize: fontSize.lg, color: colors.onSurface,
  },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, paddingHorizontal: spacing.lg, paddingVertical: spacing.md, borderBottomColor: colors.divider, borderBottomWidth: 1 },
  cover: { width: 44, height: 44, borderRadius: radius.sm, backgroundColor: colors.surfaceTertiary },
  mid: { flex: 1 },
  title: { fontFamily: font.medium, fontSize: fontSize.base, color: colors.onSurface, lineHeight: 18 },
  valLabel: { fontFamily: font.regular, fontSize: 10, color: colors.muted, textTransform: "uppercase", letterSpacing: 0.3, marginTop: 3 },
  val: { fontFamily: font.monoSemibold, fontSize: fontSize.lg, color: colors.brandPrimary },
  removeBtn: { width: 28, height: 28, alignItems: "center", justifyContent: "center" },
  footer: {
    borderTopColor: colors.border, borderTopWidth: 1, backgroundColor: colors.surfaceSecondary,
    paddingHorizontal: spacing.lg, paddingTop: spacing.md, gap: spacing.md, ...shadow.raised,
  },
  totalBox: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  totalLabel: { fontFamily: font.semibold, fontSize: fontSize.base, color: colors.onSurface },
  totalAmt: { fontFamily: font.monoSemibold, fontSize: fontSize["2xl"], color: colors.brandPrimary },
  cta: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm,
    backgroundColor: colors.brandPrimary, borderRadius: radius.md, paddingVertical: spacing.lg,
  },
  ctaText: { fontFamily: font.semibold, fontSize: fontSize.lg, color: colors.onBrandPrimary },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: spacing.sm },
  emptyIcon: { width: 72, height: 72, borderRadius: 36, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center", marginBottom: spacing.sm },
  centerTitle: { fontFamily: font.semibold, fontSize: fontSize.lg, color: colors.onSurface },
  centerText: { fontFamily: font.regular, fontSize: fontSize.base, color: colors.muted, textAlign: "center", lineHeight: 20 },
});
