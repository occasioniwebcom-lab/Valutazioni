import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { Image } from "expo-image";
import { Feather } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";
import { colors, font, fontSize, radius, spacing } from "@/src/theme";
import { formatEuro } from "@/src/format";
import { Skeleton } from "./Skeleton";

export type PriceState = {
  nuovo?: number | null;
  usato?: number | null;
  buyback?: number | null;
  platform?: string | null;
  status: "loading" | "done" | "failed";
};

function PriceMini({ label, value }: { label: string; value?: number | null }) {
  return (
    <View style={styles.mini}>
      <Text style={styles.miniLabel}>{label}</Text>
      <Text style={styles.miniValue} numberOfLines={1}>{formatEuro(value)}</Text>
    </View>
  );
}

export function GameResultRow({
  title,
  image,
  price,
  added,
  onAdd,
  onRetry,
}: {
  title: string;
  image?: string | null;
  price: PriceState;
  added: boolean;
  onAdd: () => void;
  onRetry: () => void;
}) {
  const loading = price.status === "loading";
  const failed = price.status === "failed";

  return (
    <View style={styles.row} testID="game-result-row">
      <Image
        source={image ? { uri: image } : undefined}
        style={styles.cover}
        contentFit="cover"
        transition={150}
        placeholder={undefined}
      />
      <View style={styles.platformCol}>
        {price.platform ? (
          <View style={styles.platformBadge} testID="platform-badge">
            <Text style={styles.platformText} numberOfLines={2}>{price.platform}</Text>
          </View>
        ) : null}
      </View>
      <View style={styles.mid}>
        <Text style={styles.title} numberOfLines={2}>{title}</Text>

        {loading ? (
          <View style={styles.prices}>
            <Skeleton width={44} height={28} />
            <Skeleton width={44} height={28} />
            <Skeleton width={64} height={30} style={{ borderRadius: radius.pill }} />
          </View>
        ) : failed ? (
          <Pressable onPress={onRetry} style={styles.retry} testID="row-retry">
            <Feather name="refresh-cw" size={12} color={colors.warning} />
            <Text style={styles.retryText}>Prezzi non trovati · Riprova</Text>
          </Pressable>
        ) : (
          <View style={styles.prices}>
            <PriceMini label="Nuovo" value={price.nuovo} />
            <PriceMini label="Usato" value={price.usato} />
            <View style={styles.buybackPill} testID="buyback-pill">
              <Text style={styles.buybackLabel}>Valutazione</Text>
              <Text style={styles.buybackValue} numberOfLines={1}>{formatEuro(price.buyback)}</Text>
            </View>
          </View>
        )}
      </View>

      <Pressable
        testID="add-to-quote-button"
        disabled={loading}
        onPress={() => {
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
          onAdd();
        }}
        style={[styles.addBtn, added && styles.addBtnActive, loading && styles.addBtnDisabled]}
      >
        <Feather name={added ? "check" : "plus"} size={18} color={added ? colors.onBrandPrimary : colors.brandPrimary} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    gap: spacing.sm,
    alignItems: "center",
    backgroundColor: colors.surfaceSecondary,
  },
  cover: {
    width: 72,
    height: 96,
    borderRadius: radius.sm,
    backgroundColor: colors.surfaceTertiary,
  },
  platformCol: { width: 46, alignItems: "center", justifyContent: "center" },
  platformBadge: {
    backgroundColor: colors.surfaceTertiary,
    borderColor: colors.borderStrong,
    borderWidth: 1,
    borderRadius: radius.sm,
    paddingHorizontal: 6,
    paddingVertical: 4,
    alignItems: "center",
  },
  platformText: { fontFamily: font.semibold, fontSize: 11, color: colors.onSurfaceTertiary, textAlign: "center" },
  mid: { flex: 1 },
  title: { fontFamily: font.medium, fontSize: fontSize.base, color: colors.onSurface, lineHeight: 18 },
  prices: { flexDirection: "row", alignItems: "flex-end", flexWrap: "wrap", gap: spacing.sm, rowGap: 6, marginTop: spacing.sm },
  mini: { minWidth: 40 },
  miniLabel: { fontFamily: font.regular, fontSize: 9, color: colors.muted, marginBottom: 1 },
  miniValue: { fontFamily: font.mono, fontSize: 11, color: colors.onSurfaceTertiary },
  buybackPill: {
    backgroundColor: colors.brandTertiary,
    borderRadius: radius.md,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
  },
  buybackLabel: { fontFamily: font.semibold, fontSize: 9, color: colors.onBrandTertiary, textTransform: "uppercase", letterSpacing: 0.3 },
  buybackValue: { fontFamily: font.monoSemibold, fontSize: 14, color: colors.brandPrimary },
  retry: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: spacing.sm, paddingVertical: 2 },
  retryText: { fontFamily: font.medium, fontSize: 12, color: colors.warning },
  addBtn: {
    width: 38,
    height: 38,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surface,
  },
  addBtnActive: { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary },
  addBtnDisabled: { opacity: 0.4 },
});
