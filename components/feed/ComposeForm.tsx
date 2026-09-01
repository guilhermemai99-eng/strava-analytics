"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Field, TextArea } from "@/components/ui/Field";
import styles from "./ComposeForm.module.css";

export function ComposeForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);
    const form = event.currentTarget;
    const data = new FormData(form);
    const hours = Number(data.get("hours") || 0);
    const minutes = Number(data.get("minutes") || 0);
    const seconds = Number(data.get("seconds") || 0);
    data.set("durationSeconds", String(hours * 3600 + minutes * 60 + seconds));
    data.set("isPr", data.get("isPr") ? "true" : "false");

    const response = await fetch("/api/posts", { method: "POST", body: data });
    setPending(false);
    if (!response.ok) {
      const body = (await response.json()) as { error?: string };
      setError(body.error ?? "Could not post");
      return;
    }
    router.push("/");
    router.refresh();
  }

  return (
    <form className={styles.form} onSubmit={(event) => void onSubmit(event)}>
      <h1 className={styles.title}>POST A RUN</h1>
      <label>
        <input
          type="file"
          name="image"
          accept="image/jpeg,image/png,image/webp"
          onChange={(event) => {
            const file = event.target.files?.[0];
            setPreview(file ? URL.createObjectURL(file) : null);
          }}
        />
      </label>
      {preview ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={preview} alt="" className={styles.preview} />
      ) : null}
      <Field
        label="Distance (km)"
        name="distanceKm"
        type="number"
        step="0.01"
        min="0.01"
        required
      />
      <div className={styles.row}>
        <Field label="Hours" name="hours" type="number" min="0" defaultValue="0" />
        <Field
          label="Minutes"
          name="minutes"
          type="number"
          min="0"
          defaultValue="0"
          required
        />
      </div>
      <Field
        label="Seconds"
        name="seconds"
        type="number"
        min="0"
        defaultValue="0"
      />
      <Field
        label="Date"
        name="occurredAt"
        type="date"
        required
        defaultValue={new Date().toISOString().slice(0, 10)}
      />
      <Field label="City" name="city" placeholder="Porto" />
      <TextArea label="Caption" name="caption" placeholder="Easy miles." />
      <label className={styles.check}>
        <input type="checkbox" name="isPr" />
        This is a PR
      </label>
      <label className={styles.check}>
        Visibility
        <select className={styles.select} name="visibility" defaultValue="public">
          <option value="public">Public</option>
          <option value="followers">Followers</option>
          <option value="private">Only me</option>
        </select>
      </label>
      {error ? <p className={styles.error}>{error}</p> : null}
      <Button type="submit" disabled={pending} block>
        Share run
      </Button>
    </form>
  );
}
