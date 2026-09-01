import { cookies } from "next/headers";
import { oauthRedirectUri, redirectHomeWithSession, redirectToLoginError } from "@/lib/oauth";
import { loginWithOAuth } from "@/lib/services/oauth";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const url = new URL(request.url);
  if (url.searchParams.get("error")) {
    return redirectToLoginError("google_denied");
  }

  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const jar = await cookies();
  const expected = jar.get("pulse_oauth_state")?.value;
  const verifier = jar.get("pulse_oauth_verifier")?.value;
  jar.delete("pulse_oauth_state");
  jar.delete("pulse_oauth_verifier");

  if (!code || !state || !expected || state !== expected || !verifier) {
    return redirectToLoginError("google_invalid");
  }

  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
  if (!clientId || !clientSecret) {
    return redirectToLoginError("google_not_configured");
  }

  const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: clientId,
      client_secret: clientSecret,
      redirect_uri: oauthRedirectUri("google"),
      grant_type: "authorization_code",
      code_verifier: verifier,
    }),
  });

  if (!tokenRes.ok) return redirectToLoginError("google_token");
  const tokens = (await tokenRes.json()) as { access_token?: string };
  if (!tokens.access_token) return redirectToLoginError("google_token");

  const profileRes = await fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });
  if (!profileRes.ok) return redirectToLoginError("google_profile");

  const profile = (await profileRes.json()) as {
    sub?: string;
    email?: string;
    name?: string;
    picture?: string;
  };

  if (!profile.sub || !profile.email) {
    return redirectToLoginError("google_profile");
  }

  try {
    const session = await loginWithOAuth({
      provider: "google",
      providerAccountId: profile.sub,
      email: profile.email,
      name: profile.name ?? profile.email.split("@")[0] ?? "Runner",
      avatarUrl: profile.picture,
    });
    return redirectHomeWithSession(session.token, session.expiresAt);
  } catch (error) {
    console.error(error);
    return redirectToLoginError("google_failed");
  }
}
