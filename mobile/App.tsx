import { StatusBar } from "expo-status-bar";
import { ActivityIndicator, Platform, StyleSheet, View } from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { WebView } from "react-native-webview";
import Constants from "expo-constants";
import { useMemo, useState } from "react";

const DEFAULT_PULSE_URL =
  "https://web-production-c4ff9.up.railway.app/dashboard";

export default function App() {
  const pulseUrl = useMemo(() => {
    const fromEnv = process.env.EXPO_PUBLIC_PULSE_URL;
    const fromExtra = Constants.expoConfig?.extra?.pulseUrl;
    return (fromEnv || fromExtra || DEFAULT_PULSE_URL).trim();
  }, []);

  const [loading, setLoading] = useState(true);

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.root} edges={["top", "left", "right"]}>
        <StatusBar style="light" />
        <WebView
          source={{ uri: pulseUrl }}
          style={styles.webview}
          originWhitelist={["https://*", "http://*"]}
          sharedCookiesEnabled
          thirdPartyCookiesEnabled
          allowsBackForwardNavigationGestures
          pullToRefreshEnabled={Platform.OS === "android"}
          onLoadStart={() => setLoading(true)}
          onLoadEnd={() => setLoading(false)}
          onError={() => setLoading(false)}
          applicationNameForUserAgent={`PulseExpo/${Constants.expoConfig?.version || "1.0.0"}`}
        />
        {loading ? (
          <View style={styles.loader} pointerEvents="none">
            <ActivityIndicator size="large" color="#b8f25a" />
          </View>
        ) : null}
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#070908",
  },
  webview: {
    flex: 1,
    backgroundColor: "#070908",
  },
  loader: {
    ...StyleSheet.absoluteFill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(7, 9, 8, 0.72)",
  },
});
