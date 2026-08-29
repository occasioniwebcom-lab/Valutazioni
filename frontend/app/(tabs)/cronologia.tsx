import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  SectionList,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useFocusEffect } from "expo-router";
import { Image } from "expo-image";
import { Feather } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";

import { colors, font, fontSize, radius, spacing } from "@/src/theme";
import { HistoryItem, getHistory, clearHistory } from "@/src/api";
import { formatEuro, dateLabel } from "@/src/format";
import { usePreventivo } from "@/src/store/preventivo";

type Section = { title: string; data: HistoryItem[] };

function groupByDate(items: HistoryItem[]): Section[] {
  const map = new Map<string, HistoryItem[]>();
  for (const it of items) {
    const label = dateLabel(it.viewed_at);
    if (!map.has(label)) map.set(label, []);
    map.get(label)!.push(it);
  }
  return Array.from(map.entries()).map(([title, data]) => ({ title, data }));
}

export default function CronologiaScreen() {
  const insets = useSafeAreaInsets();
  const { add, has } = usePreventivo();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setError("");
      const data = await getHistory();
      setItems(data);
    } catch (e: any) {
      setError(e?.message || "Errore di rete");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const onClear = useCallback(async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    setItems([]);
    try {
      await clearHistory();
    } catch {
      // ignore, will reload on focus
    }
  }, []);

  const sections = groupByDate(items);

  const renderItem = useCallback(({ item }: { item: HistoryItem }) => (
    <View style={styles.row} testID="history-row">
      <Image source={item.image ? { uri: item.image } : undefined} style={styles.cover} contentFit="cover" transition={150} />
      <View style={styles.mid}>
        <Text style={styles.title} numberOfLines={2}>{item.title}</Text>
        <View style={styles.buybackPill}>
          <Text style={styles.buybackLabel}>Valutazione</Text>
          <Text style={styles.buybackValue}>{formatEuro(item.buyback)}</Text>
        </View>
      </View>
      <Pressable
        testID="history-add-button"
        onPress={() => {
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
          add({ url: item.url, title: item.title, image: item.image, nuovo: item.nuovo, usato: item.usato, buyback: item.buyback });
        }}
        style={[styles.addBtn, has(item.url) && styles.addBtnActive]}
      >
        <Feather name={has(item.url) ? "check" : "plus"} size={18} color={has(item.url) ? colors.onBrandPrimary : colors.brandPrimary} />
      </Pressable>
    </View>
  ), [add, has]);

  return (
    <View style={[styles.container, { paddingTop: insets.top }]} testID="cronologia-screen">
      <View style={styles.header}>
        <View>
          <Text style={styles.h1}>Cronologia</Text>
          <Text style={styles.sub}>Giochi valutati di recente</Text>
        </View>
        {items.length > 0 && (
          <Pressable testID="clear-history" onPress={onClear} style={styles.clearBtn} hitSlop={8}>
            <Feather name="trash-2" size={16} color={colors.error} />
            <Text style={styles.clearText}>Svuota</Text>
          </Pressable>
        )}
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={colors.brandPrimary} /></View>
      ) : error ? (
        <View style={styles.center} testID="history-error">
          <Feather name="wifi-off" size={34} color={colors.muted} />
          <Text style={styles.centerText}>{error}</Text>
          <Pressable style={styles.primaryBtn} onPress={load}><Text style={styles.primaryBtnText}>Riprova</Text></Pressable>
        </View>
      ) : items.length === 0 ? (
        <View style={styles.center} testID="history-empty">
          <Feather name="clock" size={36} color={colors.muted} />
          <Text style={styles.centerTitle}>Nessuna cronologia</Text>
          <Text style={styles.centerText}>I giochi che valuti appariranno qui.</Text>
        </View>
      ) : (
        <SectionList
          testID="history-list"
          sections={sections}
          keyExtractor={(item) => item.url}
          renderItem={renderItem}
          renderSectionHeader={({ section }) => (
            <Text style={styles.sectionHeader}>{section.title}</Text>
          )}
          ItemSeparatorComponent={() => <View style={styles.sep} />}
          contentContainerStyle={{ paddingBottom: spacing.xl }}
          stickySectionHeadersEnabled={false}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor={colors.brandPrimary} />
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: spacing.md,
    borderBottomColor: colors.border, borderBottomWidth: 1,
  },
  h1: { fontFamily: font.bold, fontSize: fontSize["2xl"], color: colors.onSurface },
  sub: { fontFamily: font.regular, fontSize: fontSize.sm, color: colors.muted, marginTop: 2 },
  clearBtn: { flexDirection: "row", alignItems: "center", gap: 6, paddingVertical: 6, paddingHorizontal: 10, borderRadius: radius.sm },
  clearText: { fontFamily: font.medium, fontSize: fontSize.sm, color: colors.error },
  sectionHeader: {
    fontFamily: font.semibold, fontSize: fontSize.sm, color: colors.onSurfaceTertiary,
    paddingHorizontal: spacing.lg, paddingTop: spacing.lg, paddingBottom: spacing.sm,
    textTransform: "uppercase", letterSpacing: 0.4,
  },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, paddingHorizontal: spacing.lg, paddingVertical: spacing.md, backgroundColor: colors.surfaceSecondary },
  cover: { width: 48, height: 48, borderRadius: radius.sm, backgroundColor: colors.surfaceTertiary },
  mid: { flex: 1, gap: spacing.sm },
  title: { fontFamily: font.medium, fontSize: fontSize.base, color: colors.onSurface, lineHeight: 18 },
  buybackPill: { alignSelf: "flex-start", flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: colors.brandTertiary, borderRadius: radius.md, paddingHorizontal: spacing.sm, paddingVertical: 4 },
  buybackLabel: { fontFamily: font.semibold, fontSize: 9, color: colors.onBrandTertiary, textTransform: "uppercase", letterSpacing: 0.3 },
  buybackValue: { fontFamily: font.monoSemibold, fontSize: 14, color: colors.brandPrimary },
  addBtn: { width: 40, height: 40, borderRadius: radius.md, borderWidth: 1, borderColor: colors.borderStrong, alignItems: "center", justifyContent: "center", backgroundColor: colors.surface },
  addBtnActive: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
  sep: { height: 1, backgroundColor: colors.divider, marginLeft: 76 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: spacing.sm },
  centerTitle: { fontFamily: font.semibold, fontSize: fontSize.lg, color: colors.onSurface },
  centerText: { fontFamily: font.regular, fontSize: fontSize.base, color: colors.muted, textAlign: "center", lineHeight: 20 },
  primaryBtn: { marginTop: spacing.md, backgroundColor: colors.brandPrimary, paddingHorizontal: spacing.xl, paddingVertical: spacing.md, borderRadius: radius.md },
  primaryBtnText: { fontFamily: font.semibold, fontSize: fontSize.base, color: colors.onBrandPrimary },
});
