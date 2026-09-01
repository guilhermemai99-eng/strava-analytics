/**
 * Strava is a future data source, not the product.
 * Phase 6 will connect accounts and import runs as posts.
 */
export function stravaEnabled() {
  return false;
}

export async function importStravaActivities(): Promise<never> {
  throw new Error("Strava connect is not part of the MVP");
}
