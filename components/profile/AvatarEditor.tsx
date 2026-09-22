"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Avatar } from "@/components/ui/Avatar";
import styles from "./AvatarEditor.module.css";

type Props = {
  name: string;
  src?: string | null;
};

export function AvatarEditor({ name, src }: Props) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const seq = useRef(0);
  const [preview, setPreview] = useState<string | null>(null);
  const [current, setCurrent] = useState(src ?? null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function upload(file: File) {
    setError(null);
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError("Use a JPEG, PNG, or WebP image");
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      setError("Image must be under 8 MB");
      return;
    }
    const id = ++seq.current;
    const local = URL.createObjectURL(file);
    setPreview(local);
    setPending(true);
    const body = new FormData();
    body.set("avatar", file);
    try {
      const response = await fetch("/api/me/avatar", {
        method: "POST",
        body,
      });
      const data = (await response.json()) as {
        user?: { avatarUrl?: string | null };
        error?: string;
      };
      if (id !== seq.current) return;
      if (!response.ok) {
        setPreview(null);
        setError(data.error ?? "Could not upload photo");
        return;
      }
      setCurrent(data.user?.avatarUrl ?? null);
      setPreview(null);
      router.refresh();
    } catch {
      if (id !== seq.current) return;
      setPreview(null);
      setError("Could not upload photo");
    } finally {
      if (id === seq.current) setPending(false);
      URL.revokeObjectURL(local);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function remove() {
    setPending(true);
    setError(null);
    try {
      const response = await fetch("/api/me/avatar", { method: "DELETE" });
      if (!response.ok) {
        const data = (await response.json()) as { error?: string };
        setError(data.error ?? "Could not remove photo");
        return;
      }
      setCurrent(null);
      setPreview(null);
      router.refresh();
    } catch {
      setError("Could not remove photo");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className={styles.wrap}>
      <button
        type="button"
        className={styles.hit}
        onClick={() => inputRef.current?.click()}
        disabled={pending}
        aria-label="Change profile photo"
      >
        <Avatar
          name={name}
          src={preview ?? current}
          size="xl"
          eager
        />
        <span className={styles.badge}>{pending ? "…" : "Edit"}</span>
      </button>
      <input
        ref={inputRef}
        className={styles.input}
        type="file"
        accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void upload(file);
        }}
      />
      {current ? (
        <button
          type="button"
          className={styles.remove}
          onClick={() => void remove()}
          disabled={pending}
        >
          Remove photo
        </button>
      ) : (
        <p className={styles.hint}>Tap the photo to add one from your camera or gallery.</p>
      )}
      {error ? <p className={styles.error}>{error}</p> : null}
    </div>
  );
}
