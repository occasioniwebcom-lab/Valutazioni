import React, { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { Image } from "expo-image";
import { colors, font, SHOP_LOGO } from "@/src/theme";

export function Logo({ size = 44 }: { size?: number }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <View
        testID="shop-logo-fallback"
        style={[styles.circle, { width: size, height: size, borderRadius: size / 2 }]}
      >
        <Text style={[styles.initials, { fontSize: size * 0.4 }]}>VI</Text>
      </View>
    );
  }
  return (
    <Image
      testID="shop-logo"
      source={{ uri: SHOP_LOGO }}
      style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: colors.surfaceSecondary }}
      contentFit="contain"
      onError={() => setFailed(true)}
    />
  );
}

const styles = StyleSheet.create({
  circle: {
    backgroundColor: colors.brandPrimary,
    alignItems: "center",
    justifyContent: "center",
  },
  initials: { color: colors.onBrandPrimary, fontFamily: font.bold, letterSpacing: 0.5 },
});
