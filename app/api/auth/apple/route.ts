import { NextResponse } from "next/server";
import {
  appleConfigured,
  createPkce,
  oauthCookieOptions,
  oauthRedirectUri,
  randomOAuthValue,
  redirectToLoginError,
} from "@/lib/oauth";

export const dynamic = "force-dynamic";

export async function GET() {
  if (!appleConfigured()) {
    return redirectToLoginError("apple_not_configured");
  }

  const state = randomOAuthValue();
  const nonce = randomOAuthValue();
  const { verifier, challenge } = createPkce();

  const url = new URL("https://appleid.apple.com/auth/authorize");
  url.searchParams.set("client_id", process.env.APPLE_CLIENT_ID!);
  url.searchParams.set("redirect_uri", oauthRedirectUri("apple"));
  url.searchParams.set("response_type", "code");
  url.searchParams.set("response_mode", "form_post");
  url.searchParams.set("scope", "name email");
  url.searchParams.set("state", state);
  url.searchParams.set("nonce", nonce);
  url.searchParams.set("code_challenge", challenge);
  url.searchParams.set("code_challenge_method", "S256");

  const response = NextResponse.redirect(url);
  const cookies = oauthCookieOptions();
  response.cookies.set("pulse_oauth_state", state, cookies);
  response.cookies.set("pulse_oauth_verifier", verifier, cookies);
  response.cookies.set("pulse_oauth_nonce", nonce, cookies);
  response.headers.set("Cache-Control", "no-store");
  return response;
}
