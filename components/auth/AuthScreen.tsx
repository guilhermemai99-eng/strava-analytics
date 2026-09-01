"use client";

import { useActionState, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { loginAction, registerAction } from "@/app/(auth)/login/actions";
import styles from "./AuthScreen.module.css";

export function AuthScreen() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [loginState, loginFormAction, loginPending] = useActionState(
    loginAction,
    null,
  );
  const [registerState, registerFormAction, registerPending] = useActionState(
    registerAction,
    null,
  );

  const pending = mode === "login" ? loginPending : registerPending;
  const error =
    mode === "login" ? loginState?.error : registerState?.error;

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

      <form
        className={styles.form}
        action={mode === "login" ? loginFormAction : registerFormAction}
      >
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
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "Create an account" : "Sign in"}
        </button>
      </p>
    </main>
  );
}
