"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Avatar } from "@/components/ui/Avatar";
import type { SessionUser } from "@/lib/auth";
import styles from "./AppShell.module.css";

const NAV = [
  { href: "/", label: "Home" },
  { href: "/runs", label: "Runs" },
  { href: "/discover", label: "Discover" },
  { href: "/profile", label: "Profile" },
];

export function AppShell({
  children,
  user,
}: {
  children: React.ReactNode;
  user: SessionUser;
}) {
  const pathname = usePathname();

  function isActive(href: string) {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  }

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <Link href="/" className={styles.wordmark}>
          PULSE
        </Link>
        <div className={styles.headerActions}>
          <Link href="/profile" className={styles.headerAvatar} aria-label="Your profile">
            <Avatar name={user.name} src={user.avatarUrl} size="sm" eager />
          </Link>
          <Link href="/compose" className={styles.plus} aria-label="Post a run">
            +
          </Link>
        </div>
      </header>

      <aside className={styles.rail}>
        <div className={styles.brandBlock}>
          <Link href="/" className={styles.railWordmark}>
            PULSE
          </Link>
          <p className={styles.tagline}>
            Find your pace.
            <br />
            Find your people.
          </p>
        </div>
        <nav className={styles.railNav}>
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.railItem} ${
                isActive(item.href) ? styles.railActive : ""
              }`}
            >
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>
        <Link href="/profile" className={styles.railUser}>
          <Avatar name={user.name} src={user.avatarUrl} size="sm" eager />
          <span>
            <strong>{user.name}</strong>
            <em>@{user.username}</em>
          </span>
        </Link>
        <Link href="/compose" className={styles.plus}>
          +
        </Link>
      </aside>

      <div className={styles.content}>{children}</div>

      <nav className={styles.nav} aria-label="Primary">
        {NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`${styles.item} ${isActive(item.href) ? styles.active : ""}`}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
