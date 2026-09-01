"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import styles from "./AuthScreen.module.css";

export function AuthScreen() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    const path = mode === "login" ? "/api/auth/login" : "/api/auth/register";
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setPending(false);
    if (!response.ok) {
      const data = (await response.json()) as { error?: string };
      setError(data.error ?? "Could not continue");
      return;
    }
    router.push("/");
    router.refresh();
  }

  return (
    <main className={styles.screen}>
      <div className={styles.brand}>
        <h1 className={styles.wordmark}>PULSE</h1>
        <p className={styles.tagline}>
          Find your pace.
          <br />
          Find your people.
        </p>
      </div>

      <form className={styles.form} onSubmit={(event) => void onSubmit(event)}>
        {mode === "register" ? (
          <>
            <Field label="Name" name="name" required autoComplete="name" />
            <Field
              label="Username"
              name="username"
              required
              autoComplete="username"
              placeholder="joana"
            />
          </>
        ) : null}
        <Field
          label="Email"
          name="email"
          type="email"
          required
          autoComplete="email"
        />
        <Field
          label="Password"
          name="password"
          type="password"
          required
          autoComplete={mode === "login" ? "current-password" : "new-password"}
        />
        {error ? <p className={styles.error}>{error}</p> : null}
        <Button type="submit" block disabled={pending}>
          {mode === "login" ? "Enter" : "Create account"}
        </Button>
      </form>

      <p className={styles.switch}>
        {mode === "login" ? "New here?" : "Already running with PULSE?"}{" "}
        <button
          type="button"
          onClick={() => {
            setError(null);
            setMode(mode === "login" ? "register" : "login");
          }}
        >
          {mode === "login" ? "Create an account" : "Sign in"}
        </button>
      </p>
    </main>
  );
}
