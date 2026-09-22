"use client";

import { useState } from "react";
import { avatarSrc, type AvatarSize } from "@/lib/avatar";
import styles from "./Avatar.module.css";

type Props = {
  name: string;
  src?: string | null;
  size?: AvatarSize;
  alt?: string;
  className?: string;
  eager?: boolean;
};

function PersonMark() {
  return (
    <svg
      className={styles.mark}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="12" cy="8" r="3.4" fill="currentColor" />
      <path
        d="M5.2 19.2c.7-3.4 3.4-5.2 6.8-5.2s6.1 1.8 6.8 5.2"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function Avatar({
  name,
  src,
  size = "md",
  alt,
  className,
  eager = false,
}: Props) {
  const resolved = avatarSrc(src, size);
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const showPhoto = Boolean(resolved) && failedSrc !== resolved;
  const label = alt ?? name;

  return (
    <span
      className={[styles.avatar, styles[size], className ?? ""]
        .filter(Boolean)
        .join(" ")}
      title={name}
    >
      {showPhoto ? (
        // Local + remote avatars (Google) both use a plain img so broken files can fall back.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={resolved!}
          alt={label}
          className={styles.image}
          loading={eager ? "eager" : "lazy"}
          decoding="async"
          onError={() => {
            if (resolved) setFailedSrc(resolved);
          }}
        />
      ) : (
        <PersonMark />
      )}
    </span>
  );
}
