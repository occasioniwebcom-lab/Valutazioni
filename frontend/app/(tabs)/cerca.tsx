import React, { useCallback, useMemo, useRef, useState } from "react";
import {
  FlatList,
  Keyboard,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";

import { colors, font, fontSize, radius, spacing } from "@/src/theme";
import { GameRow, searchGames, fetchProduct } from "@/src/api";
import { GameResultRow, PriceState } from "@/src/components/GameResultRow";
import { SkeletonRow } from "@/src/components/Skeleton";
import { usePreventivo } from "@/src/store/preventivo";

type SearchState = "idle" | "loading" | "error" | "done";
const CONCURRENCY = 3;

export default function CercaScreen() {
  const insets = useSafeAreaInsets();
  const { add, has } = usePreventivo();

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GameRow[]>([]);
  const [state, setState] = useState<SearchState>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [prices, setPrices] = useState<Record<string, PriceState>>({});
  const [onlyGames, setOnlyGames] = useState(true);
  const tokenRef = useRef(0);

  const filtered = useMemo(
    () => (onlyGames ? results.filter((r) => r.is_game) : results),
    [onlyGames, results],
  );

  const setPrice = useCallback((url: string, p: PriceState) => {
    setPrices((prev) => ({ ...prev, [url]: p }));
  }, []);

  const loadOne = useCallback(async (row: GameRow, token: number) => {
    try {
      const res = await fetchProduct(row.url, row.title, row.image);
      if (token !== tokenRef.current) return;
      setPrice(row.url, {
        nuovo: res.nuovo,
        usato: res.usato,
        buyback: res.buyback,
        status: res.ok ? "done" : "failed",
      });
    } catch {
      if (token !== tokenRef.current) return;
      setPrice(row.url, { status: "failed" });
    }
  }, [setPrice]);

  const runQueue = useCallback(async (rows: GameRow[], token: number) => {
    let idx = 0;
    const worker = async () => {
      while (idx < rows.length && token === tokenRef.current) {
        const row = rows[idx++];
        await loadOne(row, token);
      }
    };
    await Promise.all(Array.from({ length: CONCURRENCY }, worker));
  }, [loadOne]);

  const runSearch = useCallback(async () => {
    const q = query.trim();
    if (!q) return;
    Keyboard.dismiss();
    const token = ++tokenRef.current;
    setState("loading");
    setErrorMsg("");
    setResults([]);
    setPrices({});
    try {
      const data = await searchGames(q);
      if (token !== tokenRef.current) return;
      setResults(data.results);
      setState("done");
      const init: Record<string, PriceState> = {};
      data.results.forEach((r) => {
        init[r.url] = r.priced
          ? { nuovo: r.nuovo, usato: r.usato, buyback: r.buyback, status: "done" }
          : { status: "loading" };
      });
      setPrices(init);
      const pending = data.results.filter((r) => !r.priced);
      runQueue(pending, token);
    } catch (e: any) {
      if (token !== tokenRef.current) return;
      setState("error");
      setErrorMsg(e?.message || "Errore di rete");
    }
  }, [query, runQueue]);

  const onRetry = useCallback((row: GameRow) => {
    setPrice(row.url, { status: "loading" });
    loadOne(row, tokenRef.current);
  }, [loadOne, setPrice]);

  const onAdd = useCallback((row: GameRow) => {
    const p = prices[row.url];
    add({
      url: row.url,
      title: row.title,
      image: row.image,
      nuovo: p?.nuovo ?? null,
      usato: p?.usato ?? null,
      buyback: p?.buyback ?? null,
    });
  }, [add, prices]);

  const renderItem = useCallback(({ item }: { item: GameRow }) => {
    const p = prices[item.url] || { status: "loading" as const };
    return (
      <GameResultRow
        title={item.title}
        image={item.image}
        price={p}
        added={has(item.url)}
        onAdd={() => onAdd(item)}
        onRetry={() => onRetry(item)}
      />
    );
  }, [prices, has, onAdd, onRetry]);

  return (
    <View style={[styles.container, { paddingTop: insets.top }]} testID="cerca-screen">
      <View style={styles.header}>
        <Text style={styles.h1}>Valutazioni</Text>
        <Text style={styles.sub}>Cerca un gioco e leggi la valutazione buyback</Text>
        <View style={styles.searchBox}>
          <Feather name="search" size={18} color={colors.muted} />
          <TextInput
            testID="search-input"
            style={styles.input}
            placeholder="Titolo del gioco…"
            placeholderTextColor={colors.muted}
            value={query}
            onChangeText={setQuery}
            returnKeyType="search"
            autoCorrect={false}
            onSubmitEditing={runSearch}
          />
          {query.length > 0 && (
            <Pressable testID="clear-search" onPress={() => setQuery("")} hitSlop={8}>
              <Feather name="x-circle" size={18} color={colors.muted} />
            </Pressable>
          )}
          <Pressable
            testID="search-button"
            onPress={() => {
              Haptics.selectionAsync().catch(() => {});
              runSearch();
            }}
            style={styles.goBtn}
          >
            <Feather name="arrow-right" size={18} color={colors.onBrandPrimary} />
          </Pressable>
        </View>

        {state === "done" && results.length > 0 && (
          <View style={styles.chipsRow}>
            <Pressable
              testID="chip-solo-giochi"
              onPress={() => setOnlyGames(true)}
              style={[styles.chip, onlyGames && styles.chipActive]}
            >
              <Feather name="disc" size={13} color={onlyGames ? colors.onBrandPrimary : colors.onSurfaceTertiary} />
              <Text style={[styles.chipText, onlyGames && styles.chipTextActive]}>Solo giochi</Text>
            </Pressable>
            <Pressable
              testID="chip-tutti"
              onPress={() => setOnlyGames(false)}
              style={[styles.chip, !onlyGames && styles.chipActive]}
            >
              <Text style={[styles.chipText, !onlyGames && styles.chipTextActive]}>Tutti</Text>
            </Pressable>
          </View>
        )}
      </View>

      {state === "loading" && (
        <View testID="loading-list">
          {Array.from({ length: 7 }).map((_, i) => (
            <SkeletonRow key={i} />
          ))}
        </View>
      )}

      {state === "error" && (
        <View style={styles.center} testID="error-state">
          <Feather name="wifi-off" size={36} color={colors.muted} />
          <Text style={styles.centerTitle}>Ricerca non riuscita</Text>
          <Text style={styles.centerText}>{errorMsg}</Text>
          <Pressable style={styles.primaryBtn} onPress={runSearch} testID="retry-search">
            <Text style={styles.primaryBtnText}>Riprova</Text>
          </Pressable>
        </View>
      )}

      {state === "idle" && (
        <View style={styles.center} testID="idle-state">
          <View style={styles.idleIcon}>
            <Feather name="search" size={30} color={colors.brandPrimary} />
          </View>
          <Text style={styles.centerTitle}>Inizia una ricerca</Text>
          <Text style={styles.centerText}>Scrivi il titolo o parte del titolo per vedere{"\n"}nuovo, usato e valutazione.</Text>
        </View>
      )}

      {state === "done" && results.length === 0 && (
        <View style={styles.center} testID="empty-state">
          <Feather name="inbox" size={36} color={colors.muted} />
          <Text style={styles.centerTitle}>Nessun risultato</Text>
          <Text style={styles.centerText}>Prova con un altro titolo.</Text>
        </View>
      )}

      {state === "done" && results.length > 0 && filtered.length === 0 && (
        <View style={styles.center} testID="only-accessories-state">
          <Feather name="package" size={36} color={colors.muted} />
          <Text style={styles.centerTitle}>Solo accessori trovati</Text>
          <Text style={styles.centerText}>Nessun videogioco tra i risultati.</Text>
          <Pressable style={styles.primaryBtn} onPress={() => setOnlyGames(false)} testID="show-all-button">
            <Text style={styles.primaryBtnText}>Mostra tutti i risultati</Text>
          </Pressable>
        </View>
      )}

      {state === "done" && filtered.length > 0 && (
        <FlatList
          testID="results-list"
          data={filtered}
          keyExtractor={(item) => item.url}
          renderItem={renderItem}
          ItemSeparatorComponent={() => <View style={styles.sep} />}
          contentContainerStyle={{ paddingBottom: spacing.xl }}
          keyboardShouldPersistTaps="handled"
          ListHeaderComponent={
            <Text style={styles.count}>
              {filtered.length} {filtered.length === 1 ? "risultato" : "risultati"}
              {onlyGames ? " · solo giochi" : ""}
            </Text>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  header: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.md,
    backgroundColor: colors.surface,
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
  },
  h1: { fontFamily: font.bold, fontSize: fontSize["2xl"], color: colors.onSurface },
  sub: { fontFamily: font.regular, fontSize: fontSize.sm, color: colors.muted, marginTop: 2 },
  searchBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.surfaceTertiary,
    borderRadius: radius.md,
    paddingLeft: spacing.md,
    paddingRight: spacing.xs,
    paddingVertical: spacing.xs,
    marginTop: spacing.md,
  },
  input: {
    flex: 1,
    fontFamily: font.regular,
    fontSize: fontSize.lg,
    color: colors.onSurface,
    paddingVertical: spacing.sm,
  },
  goBtn: {
    width: 36,
    height: 36,
    borderRadius: radius.sm,
    backgroundColor: colors.brandPrimary,
    alignItems: "center",
    justifyContent: "center",
  },
  chipsRow: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.md },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    height: 36,
    flexShrink: 0,
    paddingHorizontal: spacing.md,
    borderRadius: radius.pill,
    backgroundColor: colors.surfaceTertiary,
  },
  chipActive: { backgroundColor: colors.brandPrimary },
  chipText: { fontFamily: font.medium, fontSize: fontSize.sm, color: colors.onSurfaceTertiary },
  chipTextActive: { color: colors.onBrandPrimary },
  count: {
    fontFamily: font.medium,
    fontSize: fontSize.sm,
    color: colors.muted,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.sm,
  },
  sep: { height: 1, backgroundColor: colors.divider, marginLeft: 76 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: spacing.sm },
  idleIcon: {
    width: 72, height: 72, borderRadius: 36, backgroundColor: colors.brandTertiary,
    alignItems: "center", justifyContent: "center", marginBottom: spacing.sm,
  },
  centerTitle: { fontFamily: font.semibold, fontSize: fontSize.lg, color: colors.onSurface },
  centerText: { fontFamily: font.regular, fontSize: fontSize.base, color: colors.muted, textAlign: "center", lineHeight: 20 },
  primaryBtn: {
    marginTop: spacing.md, backgroundColor: colors.brandPrimary,
    paddingHorizontal: spacing.xl, paddingVertical: spacing.md, borderRadius: radius.md,
  },
  primaryBtnText: { fontFamily: font.semibold, fontSize: fontSize.base, color: colors.onBrandPrimary },
});
