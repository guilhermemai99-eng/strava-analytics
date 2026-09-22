import assert from "node:assert/strict";
import { test } from "node:test";
import { AVATAR_PIXELS, avatarFolder, avatarSrc } from "../lib/avatar";

test("resolves local avatar folders to size-specific webp files", () => {
  const folder = avatarFolder("user123", "abc123");
  assert.equal(folder, "/uploads/avatars/user123/abc123");
  assert.equal(avatarSrc(folder, "xs"), "/uploads/avatars/user123/abc123/w64.webp");
  assert.equal(avatarSrc(`${folder}/w512.webp`, "lg"), "/uploads/avatars/user123/abc123/w256.webp");
  assert.equal(AVATAR_PIXELS.md, 128);
});

test("keeps remote oauth photos unchanged", () => {
  const google = "https://lh3.googleusercontent.com/a/photo";
  assert.equal(avatarSrc(google, "sm"), google);
});

test("falls back to null without a photo", () => {
  assert.equal(avatarSrc(null, "md"), null);
  assert.equal(avatarSrc(undefined), null);
});
