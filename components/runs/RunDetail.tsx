"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Avatar } from "@/components/ui/Avatar";
import { AvatarStack } from "@/components/ui/AvatarStack";
import { Button } from "@/components/ui/Button";
import type { RunCardData } from "@/lib/services/runs";
import styles from "./RunDetail.module.css";

function formatWhen(iso: string) {
  return new Date(iso).toLocaleString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function RunDetail({
  run,
  viewerId,
}: {
  run: RunCardData;
  viewerId: string;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isHost = run.host.id === viewerId;

  async function toggle() {
    setBusy(true);
    setError(null);
    const method = run.going ? "DELETE" : "POST";
    const response = await fetch(`/api/runs/${run.id}/join`, { method });
    setBusy(false);
    if (!response.ok) {
      const data = (await response.json()) as { error?: string };
      setError(data.error ?? "Could not update");
      return;
    }
    router.refresh();
  }

  return (
    <article className={styles.page}>
      <p className={styles.when}>{formatWhen(run.startsAt)}</p>
      <h1 className={styles.title}>{run.title}</h1>
      <p className={styles.meta}>
        {run.distanceKm.toFixed(2)} KM · {run.city}
        {run.locationName ? ` · ${run.locationName}` : ""}
      </p>
      {run.description ? <p className={styles.body}>{run.description}</p> : null}

      <section className={styles.people}>
        <div className={styles.peopleHead}>
          <h2>Going</h2>
          <AvatarStack people={run.people} max={4} />
        </div>
        <ul>
          {run.people.map((person) => (
            <li key={person.id}>
              <Avatar name={person.name} src={person.avatarUrl} size="sm" />
              <div>
                <p className={styles.name}>{person.name}</p>
                <p className={styles.handle}>@{person.username}</p>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {error ? <p className={styles.error}>{error}</p> : null}
      {isHost ? (
        <p className={styles.hostNote}>You’re hosting this run.</p>
      ) : (
        <Button type="button" block disabled={busy} onClick={() => void toggle()}>
          {run.going ? "Leave" : "I’m going"}
        </Button>
      )}
    </article>
  );
}
