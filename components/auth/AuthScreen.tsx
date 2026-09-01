"use client";

import { useActionState, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { loginAction, registerAction } from "@/app/(auth)/login/actions";
import styles from "./AuthScreen.module.css";

type Props = {
  oauthError?: string | null;
};

function GoogleMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62Z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.71H.96v2.33A9 9 0 0 0 9 18Z"
      />
      <path
        fill="#FBBC05"
        d="M3.97 10.71A5.41 5.41 0 0 1 3.69 9c0-.6.1-1.17.28-1.71V4.96H.96A9 9 0 0 0 0 9c0 1.45.35 2.82.96 4.04l3.01-2.33Z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .96 4.96l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58Z"
      />
    </svg>
  );
}

function AppleMark() {
  return (
    <svg width="16" height="18" viewBox="0 0 16 18" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12.7 9.4c.02 2.3 2.02 3.07 2.04 3.08-.02.06-.32 1.09-1.05 2.16-.63.92-1.29 1.84-2.32 1.86-1.01.02-1.34-.6-2.5-.6-1.16 0-1.52.58-2.48.62-1 .04-1.76-.99-2.4-1.91C2.67 12.7 1.5 9.3 2.86 6.98c.67-1.16 1.87-1.89 3.17-1.91 1-.02 1.93.67 2.5.67.56 0 1.73-.83 2.92-.71.5.02 1.9.2 2.8 1.52-.07.04-1.67.98-1.65 2.85ZM10.9 4.2c.54-.66.91-1.57.81-2.48-.78.03-1.73.52-2.29 1.18-.5.58-.94 1.5-.82 2.39.87.07 1.76-.44 2.3-1.09Z"
      />
    </svg>
  );
}

export function AuthScreen({ oauthError }: Props) {
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
  const error = mode === "login" ? loginState?.error : registerState?.error;

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

      <div className={styles.oauth}>
        {oauthError ? <p className={styles.error}>{oauthError}</p> : null}
        <Button href="/api/auth/google" variant="google" block>
          <GoogleMark />
          Continue with Google
        </Button>
        <Button href="/api/auth/apple" variant="apple" block>
          <AppleMark />
          Continue with Apple
        </Button>
      </div>

      <p className={styles.divider}>
        <span>or use email</span>
      </p>

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
