"use client";

import { useActionState, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Field, TextArea } from "@/components/ui/Field";
import { createPostAction } from "@/app/(main)/compose/actions";
import styles from "./ComposeForm.module.css";

export function ComposeForm() {
  const [state, formAction, pending] = useActionState(createPostAction, null);
  const [preview, setPreview] = useState<string | null>(null);

  return (
    <form className={styles.form} action={formAction}>
      <h1 className={styles.title}>POST A RUN</h1>
      <label className={styles.file}>
        Photo
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
      {state?.error ? <p className={styles.error}>{state.error}</p> : null}
      <Button type="submit" disabled={pending} block>
        Share run
      </Button>
    </form>
  );
}
