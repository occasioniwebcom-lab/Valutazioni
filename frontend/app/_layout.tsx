import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect } from "react";
import { LogBox } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { useFonts } from "expo-font";

import { useIconFonts } from "@/src/hooks/use-icon-fonts";
import { PreventivoProvider } from "@/src/store/preventivo";
import { AuthProvider } from "@/src/store/auth";
import { AuthGate } from "@/src/components/AuthGate";

// Disable logbox errors etc so that users can see the app
// and agent works as expected.
LogBox.ignoreAllLogs(true);

// Keep the native splash visible from cold start until icon fonts register.
// Required because @expo/vector-icons' componentDidMount fallback fires
// Font.loadAsync against a broken vendor path if any <Icon> mounts before
// the family is registered — which throws on Android Expo Go.
SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const [iconsLoaded, iconsError] = useIconFonts();
  const [fontsLoaded, fontsError] = useFonts({
    Geist: require("../assets/fonts/Geist-400.ttf"),
    "Geist-Medium": require("../assets/fonts/Geist-500.ttf"),
    "Geist-SemiBold": require("../assets/fonts/Geist-600.ttf"),
    "Geist-Bold": require("../assets/fonts/Geist-700.ttf"),
    GeistMono: require("../assets/fonts/GeistMono-400.ttf"),
    "GeistMono-Medium": require("../assets/fonts/GeistMono-500.ttf"),
    "GeistMono-SemiBold": require("../assets/fonts/GeistMono-600.ttf"),
  });

  const iconsReady = iconsLoaded || iconsError;
  const fontsReady = fontsLoaded || fontsError;

  useEffect(() => {
    if (iconsReady && fontsReady) {
      SplashScreen.hideAsync();
    }
  }, [iconsReady, fontsReady]);

  if (!iconsReady || !fontsReady) return null;

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <AuthProvider>
          <PreventivoProvider>
            <StatusBar style="dark" />
            <AuthGate>
              <Stack screenOptions={{ headerShown: false }}>
                <Stack.Screen name="impostazioni" />
              </Stack>
            </AuthGate>
          </PreventivoProvider>
        </AuthProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
