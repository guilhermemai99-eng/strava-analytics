import { NextResponse } from "next/server";
import {
  createPkce,
  googleConfigured,
  oauthCookieOptions,
  oauthRedirectUri,
  randomOAuthValue,
  redirectToLoginError,
} from "@/lib/oauth";

export const dynamic = "force-dynamic";

export async function GET() {
  if (!googleConfigured()) {
    return redirectToLoginError("google_not_configured");
  }

  const state = randomOAuthValue();
  const { verifier, challenge } = createPkce();
  const url = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  url.searchParams.set("client_id", process.env.GOOGLE_CLIENT_ID!);
  url.searchParams.set("redirect_uri", oauthRedirectUri("google"));
  url.searchParams.set("response_type", "code");
  url.searchParams.set("scope", "openid email profile");
  url.searchParams.set("state", state);
  url.searchParams.set("code_challenge", challenge);
  url.searchParams.set("code_challenge_method", "S256");
  url.searchParams.set("prompt", "select_account");

  const response = NextResponse.redirect(url);
  const cookies = oauthCookieOptions();
  response.cookies.set("pulse_oauth_state", state, cookies);
  response.cookies.set("pulse_oauth_verifier", verifier, cookies);
  response.headers.set("Cache-Control", "no-store");
  return response;
}
