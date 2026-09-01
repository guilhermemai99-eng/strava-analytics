import { createHash, randomBytes } from "node:crypto";
import { NextResponse } from "next/server";
import { SESSION_COOKIE, sessionCookieOptions } from "@/lib/auth";

export function appUrl() {
  if (process.env.APP_URL) {
    return process.env.APP_URL.replace(/\/$/, "");
  }
  if (process.env.RAILWAY_PUBLIC_DOMAIN) {
    return `https://${process.env.RAILWAY_PUBLIC_DOMAIN}`;
  }
  return "http://localhost:3000";
}

export function oauthRedirectUri(provider: "google" | "apple") {
  return `${appUrl()}/api/auth/${provider}/callback`;
}

export function googleConfigured() {
  return Boolean(
    process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET,
  );
}

export function appleConfigured() {
  return Boolean(
    process.env.APPLE_CLIENT_ID &&
      process.env.APPLE_TEAM_ID &&
      process.env.APPLE_KEY_ID &&
      process.env.APPLE_PRIVATE_KEY,
  );
}

export function randomOAuthValue() {
  return randomBytes(32).toString("hex");
}

export function pkceChallenge(verifier: string) {
  return createHash("sha256").update(verifier).digest("base64url");
}

export function createPkce() {
  const verifier = randomOAuthValue();
  return { verifier, challenge: pkceChallenge(verifier) };
}

export function oauthCookieOptions() {
  const secure = process.env.NODE_ENV === "production";
  return {
    httpOnly: true as const,
    sameSite: (secure ? "none" : "lax") as "none" | "lax",
    secure,
    path: "/",
    maxAge: 10 * 60,
  };
}

export function redirectToLoginError(code: string) {
  return NextResponse.redirect(
    new URL(`/login?error=${encodeURIComponent(code)}`, appUrl()),
  );
}

export function redirectHomeWithSession(token: string, expiresAt: Date) {
  const response = NextResponse.redirect(new URL("/", appUrl()));
  response.cookies.set(
    SESSION_COOKIE,
    token,
    sessionCookieOptions(expiresAt),
  );
  return response;
}
