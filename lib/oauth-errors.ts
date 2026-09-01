const OAUTH_ERRORS: Record<string, string> = {
  google_not_configured: "Google sign-in is not configured yet.",
  apple_not_configured: "Apple sign-in is not configured yet.",
  google_denied: "Google sign-in was cancelled.",
  apple_denied: "Apple sign-in was cancelled.",
  google_invalid: "Google sign-in expired. Try again.",
  apple_invalid: "Apple sign-in expired. Try again.",
  google_token: "Could not verify the Google sign-in.",
  apple_token: "Could not verify the Apple sign-in.",
  google_profile: "Google did not share an email address.",
  apple_email:
    "Apple did not share an email. Allow email on the Apple screen and try again.",
  google_failed: "Could not finish Google sign-in.",
  apple_failed: "Could not finish Apple sign-in.",
};

export function oauthErrorMessage(code: string | undefined) {
  if (!code) return null;
  return OAUTH_ERRORS[code] ?? "Could not sign in. Try again.";
}
