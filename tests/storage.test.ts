import assert from "node:assert/strict";
import { rm } from "node:fs/promises";
import path from "node:path";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import sharp from "sharp";
import { avatarSrc } from "../lib/avatar";
import { deleteAvatarFiles, saveAvatarUpload } from "../lib/storage";

test("compresses and squares an uploaded avatar", async () => {
  const png = await sharp({
    create: {
      width: 80,
      height: 40,
      channels: 3,
      background: { r: 214, g: 255, b: 46 },
    },
  })
    .png()
    .toBuffer();
  const file = new File([png], "pic.png", { type: "image/png" });
  const url = await saveAvatarUpload("testuser", file);
  assert.match(url, /^\/uploads\/avatars\/testuser\/[0-9a-f]+$/);
  const md = avatarSrc(url, "md");
  assert.equal(md, `${url}/w128.webp`);
  const stored = await readFile(path.join(process.cwd(), "public", md.slice(1)));
  const meta = await sharp(stored).metadata();
  assert.equal(meta.format, "webp");
  assert.equal(meta.width, 128);
  assert.equal(meta.height, 128);
  await deleteAvatarFiles(url);
  await rm(path.join(process.cwd(), "public", "uploads", "avatars", "testuser"), {
    recursive: true,
    force: true,
  });
});

test("rejects files that are not real images", async () => {
  const file = new File([Buffer.from("not-an-image")], "x.png", { type: "image/png" });
  await assert.rejects(
    () => saveAvatarUpload("baduser", file),
    /JPEG, PNG, or WebP/,
  );
});
