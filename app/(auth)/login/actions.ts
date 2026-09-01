"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import {
  loginUser,
  registerUser,
  SESSION_COOKIE,
  sessionCookieOptions,
} from "@/lib/services/auth";

export type AuthState = { error?: string } | null;

async function setSessionCookie(token: string, expiresAt: Date) {
  const jar = await cookies();
  jar.set(SESSION_COOKIE, token, sessionCookieOptions(expiresAt));
}

export async function loginAction(
  _prev: AuthState,
  formData: FormData,
): Promise<AuthState> {
  try {
    const { session } = await loginUser({
      email: String(formData.get("email") ?? ""),
      password: String(formData.get("password") ?? ""),
    });
    await setSessionCookie(session.token, session.expiresAt);
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Could not continue",
    };
  }
  redirect("/");
}

export async function registerAction(
  _prev: AuthState,
  formData: FormData,
): Promise<AuthState> {
  try {
    const { session } = await registerUser({
      email: String(formData.get("email") ?? ""),
      password: String(formData.get("password") ?? ""),
      name: String(formData.get("name") ?? ""),
      username: String(formData.get("username") ?? ""),
    });
    await setSessionCookie(session.token, session.expiresAt);
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Could not continue",
    };
  }
  redirect("/");
}

export async function logoutAction() {
  const { destroySession, SESSION_COOKIE: name } = await import("@/lib/auth");
  const jar = await cookies();
  await destroySession(jar.get(name)?.value);
  jar.set(name, "", { httpOnly: true, path: "/", expires: new Date(0) });
  redirect("/login");
}
