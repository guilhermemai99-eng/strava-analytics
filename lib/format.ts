export function formatDistance(km: number) {
  return `${km.toFixed(2)} KM`;
}

export function formatDuration(totalSeconds: number) {
  const seconds = Math.max(0, Math.round(totalSeconds));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = seconds % 60;
  const pad = (n: number) => n.toString().padStart(2, "0");
  if (hours > 0) {
    return `${pad(hours)}:${pad(minutes)}:${pad(rest)}`;
  }
  return `${pad(minutes)}:${pad(rest)}`;
}

export function paceSecondsPerKm(distanceKm: number, durationSeconds: number) {
  if (distanceKm <= 0) return 0;
  return durationSeconds / distanceKm;
}

export function formatPace(distanceKm: number, durationSeconds: number) {
  const pace = paceSecondsPerKm(distanceKm, durationSeconds);
  const minutes = Math.floor(pace / 60);
  const seconds = Math.round(pace % 60);
  const normalizedMinutes = seconds === 60 ? minutes + 1 : minutes;
  const normalizedSeconds = seconds === 60 ? 0 : seconds;
  return `${normalizedMinutes}:${normalizedSeconds
    .toString()
    .padStart(2, "0")} /KM`;
}

export const RESERVED_USERNAMES = new Set([
  "pulse",
  "admin",
  "login",
  "register",
  "runs",
  "discover",
  "profile",
  "settings",
  "compose",
  "api",
  "feed",
  "uploads",
  "health",
]);
