import Link from "next/link";
import { AvatarStack } from "@/components/ui/AvatarStack";
import type { RunCardData } from "@/lib/services/runs";
import styles from "./RunCard.module.css";

function formatWhen(iso: string) {
  return new Date(iso).toLocaleString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatPaceBand(min: number | null, max: number | null) {
  if (min == null && max == null) return null;
  const fmt = (sec: number) => {
    const minutes = Math.floor(sec / 60);
    const seconds = sec % 60;
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
  };
  if (min != null && max != null) return `${fmt(min)}–${fmt(max)} /KM`;
  return `${fmt((min ?? max)!)} /KM`;
}

export function RunCard({ run }: { run: RunCardData }) {
  const pace = formatPaceBand(run.paceMinSec, run.paceMaxSec);
  return (
    <article className={styles.card}>
      <Link href={`/runs/${run.id}`} className={styles.body}>
        <p className={styles.when}>{formatWhen(run.startsAt)}</p>
        <h2 className={styles.title}>{run.title}</h2>
        <p className={styles.meta}>
          {run.distanceKm.toFixed(1)} KM · {run.city}
          {pace ? ` · ${pace}` : ""}
        </p>
      </Link>
      <div className={styles.people}>
        <AvatarStack people={run.people} max={3} />
      </div>
    </article>
  );
}
