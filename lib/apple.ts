import { createHash } from "node:crypto";
import { SignJWT, createRemoteJWKSet, jwtVerify, importPKCS8 } from "jose";

const APPLE_ISS = "https://appleid.apple.com";

export async function appleClientSecret() {
  const pem = (process.env.APPLE_PRIVATE_KEY ?? "").replace(/\\n/g, "\n");
  const key = await importPKCS8(pem, "ES256");
  return new SignJWT({})
    .setProtectedHeader({
      alg: "ES256",
      kid: process.env.APPLE_KEY_ID,
    })
    .setIssuer(process.env.APPLE_TEAM_ID!)
    .setSubject(process.env.APPLE_CLIENT_ID!)
    .setAudience(APPLE_ISS)
    .setIssuedAt()
    .setExpirationTime("1h")
    .sign(key);
}

export async function verifyAppleIdToken(idToken: string, nonce?: string) {
  const JWKS = createRemoteJWKSet(new URL(`${APPLE_ISS}/auth/keys`));
  const { payload } = await jwtVerify(idToken, JWKS, {
    issuer: APPLE_ISS,
    audience: process.env.APPLE_CLIENT_ID,
  });
  if (nonce && payload.nonce) {
    const hashed = createHash("sha256").update(nonce).digest("hex");
    if (payload.nonce !== nonce && payload.nonce !== hashed) {
      throw new Error("Invalid Apple nonce");
    }
  }
  return payload;
}
