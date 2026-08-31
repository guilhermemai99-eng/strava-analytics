/** @type {import('expo/config').ExpoConfig} */
export default ({ config }) => ({
  ...config,
  name: "Pulse",
  slug: "pulse",
  scheme: "pulse",
  userInterfaceStyle: "dark",
  extra: {
    pulseUrl:
      process.env.EXPO_PUBLIC_PULSE_URL ||
      "https://web-production-c4ff9.up.railway.app/dashboard",
  },
});
