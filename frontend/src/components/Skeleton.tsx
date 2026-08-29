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
      <Skeleton width={48} height={48} style={{ borderRadius: radius.sm }} />
      <View style={styles.mid}>
        <Skeleton width="80%" height={13} />
        <Skeleton width="55%" height={13} style={{ marginTop: 6 }} />
        <View style={styles.prices}>
          <Skeleton width={52} height={26} />
          <Skeleton width={52} height={26} />
          <Skeleton width={64} height={26} style={{ borderRadius: radius.pill }} />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", padding: 12, gap: 12, alignItems: "flex-start" },
  mid: { flex: 1 },
  prices: { flexDirection: "row", gap: 10, marginTop: 10 },
});
