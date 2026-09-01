import assert from "node:assert/strict";
import { test } from "node:test";
import { oauthErrorMessage } from "../lib/oauth-errors";
import {
  appleConfigured,
  createPkce,
  googleConfigured,
  oauthRedirectUri,
  pkceChallenge,
} from "../lib/oauth";

test("maps oauth error codes to login copy", () => {
  assert.equal(
    oauthErrorMessage("google_not_configured"),
    "Google sign-in is not configured yet.",
  );
  assert.equal(
    oauthErrorMessage("apple_not_configured"),
    "Apple sign-in is not configured yet.",
  );
  assert.equal(oauthErrorMessage("nope"), "Could not sign in. Try again.");
  assert.equal(oauthErrorMessage(undefined), null);
});

test("pkce challenge is base64url sha256", () => {
  const { verifier, challenge } = createPkce();
  assert.equal(challenge, pkceChallenge(verifier));
  assert.match(challenge, /^[A-Za-z0-9_-]+$/);
  assert.ok(verifier.length >= 32);
});

test("builds oauth callback URLs from APP_URL", () => {
  const previous = process.env.APP_URL;
  process.env.APP_URL = "https://web-production-867a3.up.railway.app/";
  assert.equal(
    oauthRedirectUri("google"),
    "https://web-production-867a3.up.railway.app/api/auth/google/callback",
  );
  assert.equal(
    oauthRedirectUri("apple"),
    "https://web-production-867a3.up.railway.app/api/auth/apple/callback",
  );
  process.env.APP_URL = previous;
});

test("oauth providers are unconfigured without secrets", () => {
  const google = [
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
  ];
  const apple = [
    process.env.APPLE_CLIENT_ID,
    process.env.APPLE_TEAM_ID,
    process.env.APPLE_KEY_ID,
    process.env.APPLE_PRIVATE_KEY,
  ];
  delete process.env.GOOGLE_CLIENT_ID;
  delete process.env.GOOGLE_CLIENT_SECRET;
  delete process.env.APPLE_CLIENT_ID;
  delete process.env.APPLE_TEAM_ID;
  delete process.env.APPLE_KEY_ID;
  delete process.env.APPLE_PRIVATE_KEY;
  assert.equal(googleConfigured(), false);
  assert.equal(appleConfigured(), false);
  if (google[0]) process.env.GOOGLE_CLIENT_ID = google[0];
  if (google[1]) process.env.GOOGLE_CLIENT_SECRET = google[1];
  if (apple[0]) process.env.APPLE_CLIENT_ID = apple[0];
  if (apple[1]) process.env.APPLE_TEAM_ID = apple[1];
  if (apple[2]) process.env.APPLE_KEY_ID = apple[2];
  if (apple[3]) process.env.APPLE_PRIVATE_KEY = apple[3];
});
