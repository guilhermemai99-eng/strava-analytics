import { formatDistance, formatDuration, formatPace } from "@/lib/format";

export async function downloadShareImage(input: {
  distanceKm: number;
  durationSeconds: number;
  isPr: boolean;
}) {
  const width = 1080;
  const height = 1920;
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  ctx.fillStyle = "#f5f3ee";
  ctx.fillRect(0, 0, width, height);

  ctx.fillStyle = "#000000";
  ctx.font = "700 72px 'Bebas Neue', Impact, sans-serif";
  ctx.fillText("PULSE", 80, 160);

  ctx.font = "400 160px 'Bebas Neue', Impact, sans-serif";
  ctx.fillText(formatDistance(input.distanceKm), 80, 760);
  ctx.fillText(formatDuration(input.durationSeconds), 80, 930);

  ctx.font = "400 88px 'Bebas Neue', Impact, sans-serif";
  ctx.fillStyle = "#6e6c68";
  ctx.fillText(formatPace(input.distanceKm, input.durationSeconds), 80, 1080);

  if (input.isPr) {
    ctx.fillStyle = "#d6ff2e";
    ctx.fillRect(80, 1160, 280, 88);
    ctx.strokeStyle = "#000000";
    ctx.lineWidth = 6;
    ctx.strokeRect(80, 1160, 280, 88);
    ctx.fillStyle = "#000000";
    ctx.font = "400 56px 'Bebas Neue', Impact, sans-serif";
    ctx.fillText("NEW PR", 110, 1222);
  }

  ctx.fillStyle = "#000000";
  ctx.font = "600 28px 'DM Sans', sans-serif";
  ctx.fillText("FIND YOUR PACE. FIND YOUR PEOPLE.", 80, 1780);

  const url = canvas.toDataURL("image/png");
  const link = document.createElement("a");
  link.href = url;
  link.download = "pulse-run.png";
  link.click();
}
