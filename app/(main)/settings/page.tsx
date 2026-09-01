"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import styles from "./settings.module.css";

export default function SettingsPage() {
  const router = useRouter();

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <section className={styles.page}>
      <h1 className={styles.title}>SETTINGS</h1>
      <p className={styles.body}>
        Profile editing ships with the Profile phase. You can sign out now.
      </p>
      <Button onClick={() => void logout()}>Log out</Button>
    </section>
  );
}
