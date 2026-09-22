"use client";

import { useState } from "react";
import { Avatar } from "@/components/ui/Avatar";
import type { PublicUser } from "@/lib/types";
import styles from "./AvatarStack.module.css";

type Person = Pick<PublicUser, "name" | "avatarUrl"> & {
  username?: string;
  id?: string;
};

type Props = {
  people: Person[];
  max?: number;
  size?: "xs" | "sm";
  onExpand?: () => void;
};

export function AvatarStack({
  people,
  max = 3,
  size = "xs",
  onExpand,
}: Props) {
  const [open, setOpen] = useState(false);
  const shown = people.slice(0, max);
  const rest = Math.max(0, people.length - shown.length);

  function toggle() {
    if (onExpand) {
      onExpand();
      return;
    }
    if (rest > 0) setOpen(true);
  }

  return (
    <>
      <button
        type="button"
        className={styles.stack}
        onClick={toggle}
        disabled={people.length === 0}
        aria-label={
          rest > 0
            ? `${people.length} runners. Show all.`
            : `${people.length} runners`
        }
      >
        {shown.map((person, index) => (
          <span
            key={person.id ?? `${person.name}-${index}`}
            className={styles.slot}
            style={{ zIndex: shown.length - index }}
          >
            <Avatar name={person.name} src={person.avatarUrl} size={size} />
          </span>
        ))}
        {rest > 0 ? <span className={styles.more}>+{rest}</span> : null}
      </button>
      {open ? (
        <div className={styles.overlay} role="dialog" aria-modal="true">
          <div className={styles.sheet}>
            <div className={styles.sheetHead}>
              <p>Going</p>
              <button type="button" onClick={() => setOpen(false)}>
                Close
              </button>
            </div>
            <ul className={styles.list}>
              {people.map((person, index) => (
                <li key={person.id ?? `${person.name}-${index}`}>
                  <Avatar name={person.name} src={person.avatarUrl} size="sm" />
                  <div>
                    <p className={styles.personName}>{person.name}</p>
                    {person.username ? (
                      <p className={styles.handle}>@{person.username}</p>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}
    </>
  );
}
