import { cookies } from "next/headers";
import { appleClientSecret, verifyAppleIdToken } from "@/lib/apple";
import {
  oauthRedirectUri,
  redirectHomeWithSession,
  redirectToLoginError,
} from "@/lib/oauth";
import { loginWithOAuth } from "@/lib/services/oauth";

export const dynamic = "force-dynamic";

type AppleUserName = {
  name?: { firstName?: string; lastName?: string };
};

async function finishApple(form: FormData) {
  if (form.get("error")) {
    return redirectToLoginError("apple_denied");
  }

  const code = String(form.get("code") ?? "");
  const state = String(form.get("state") ?? "");
  const jar = await cookies();
  const expected = jar.get("pulse_oauth_state")?.value;
  const verifier = jar.get("pulse_oauth_verifier")?.value;
  const nonce = jar.get("pulse_oauth_nonce")?.value;
  jar.delete("pulse_oauth_state");
  jar.delete("pulse_oauth_verifier");
  jar.delete("pulse_oauth_nonce");

  if (!code || !state || !expected || state !== expected || !verifier) {
    return redirectToLoginError("apple_invalid");
  }

  if (!process.env.APPLE_CLIENT_ID) {
    return redirectToLoginError("apple_not_configured");
  }

  let clientSecret: string;
  try {
    clientSecret = await appleClientSecret();
  } catch {
    return redirectToLoginError("apple_not_configured");
  }

  const tokenRes = await fetch("https://appleid.apple.com/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: process.env.APPLE_CLIENT_ID,
      client_secret: clientSecret,
      code,
      grant_type: "authorization_code",
      redirect_uri: oauthRedirectUri("apple"),
      code_verifier: verifier,
    }),
  });

  if (!tokenRes.ok) return redirectToLoginError("apple_token");
  const tokens = (await tokenRes.json()) as { id_token?: string };
  if (!tokens.id_token) return redirectToLoginError("apple_token");

  let sub = "";
  let email: string | undefined;
  try {
    const payload = await verifyAppleIdToken(tokens.id_token, nonce);
    sub = String(payload.sub ?? "");
    email = typeof payload.email === "string" ? payload.email : undefined;
  } catch {
    return redirectToLoginError("apple_token");
  }

  let name = "Runner";
  const userRaw = form.get("user");
  if (typeof userRaw === "string" && userRaw) {
    try {
      const parsed = JSON.parse(userRaw) as AppleUserName;
      const full = `${parsed.name?.firstName ?? ""} ${parsed.name?.lastName ?? ""}`.trim();
      if (full) name = full;
    } catch {
      /* Apple only sends the name on the first authorization. */
    }
  }

  if (!sub || !email) return redirectToLoginError("apple_email");

  try {
    const session = await loginWithOAuth({
      provider: "apple",
      providerAccountId: sub,
      email,
      name,
    });
    return redirectHomeWithSession(session.token, session.expiresAt);
  } catch (error) {
    console.error(error);
    return redirectToLoginError("apple_failed");
  }
}

export async function POST(request: Request) {
  return finishApple(await request.formData());
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const form = new FormData();
  for (const [key, value] of url.searchParams.entries()) {
    form.set(key, value);
  }
  return finishApple(form);
}
