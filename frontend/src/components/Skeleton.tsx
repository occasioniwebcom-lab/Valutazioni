import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, View, ViewStyle } from "react-native";
import { colors, radius } from "@/src/theme";

export function Skeleton({ width, height, style }: { width: number | string; height: number; style?: ViewStyle }) {
  const opacity = useRef(new Animated.Value(0.4)).current;
  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, { toValue: 1, duration: 700, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 0.4, duration: 700, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [opacity]);
  return (
    <Animated.View
      style={[{ width: width as any, height, borderRadius: radius.sm, backgroundColor: colors.surfaceTertiary, opacity }, style]}
    />
  );
}

export function SkeletonRow() {
  return (
    <View style={styles.row} testID="skeleton-row">
      <Skeleton width={72} height={96} style={{ borderRadius: radius.sm }} />
      <Skeleton width={40} height={22} />
      <View style={styles.mid}>
        <Skeleton width="80%" height={13} />
        <Skeleton width="55%" height={13} style={{ marginTop: 6 }} />
        <View style={styles.prices}>
          <Skeleton width={44} height={26} />
          <Skeleton width={44} height={26} />
          <Skeleton width={64} height={26} style={{ borderRadius: radius.pill }} />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", padding: 12, gap: 8, alignItems: "center" },
  mid: { flex: 1 },
  prices: { flexDirection: "row", gap: 8, marginTop: 10, flexWrap: "wrap" },
});
