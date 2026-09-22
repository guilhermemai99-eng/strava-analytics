import { mkdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { randomBytes } from "node:crypto";
import sharp from "sharp";
import { AVATAR_PIXELS, avatarFolder } from "@/lib/avatar";

const UPLOAD_DIR = path.join(process.cwd(), "public", "uploads");
const ALLOWED = new Set(["image/jpeg", "image/png", "image/webp"]);
const MAX_BYTES = 8 * 1024 * 1024;
const AVATAR_QUALITY = 84;

function extensionFor(type: string) {
  if (type === "image/png") return "png";
  if (type === "image/webp") return "webp";
  return "jpg";
}

async function readValidatedBuffer(file: File) {
  if (!ALLOWED.has(file.type)) {
    throw new Error("Use a JPEG, PNG, or WebP image");
  }
  if (file.size > MAX_BYTES) {
    throw new Error("Image must be under 8 MB");
  }
  const buffer = Buffer.from(await file.arrayBuffer());
  let metadata;
  try {
    metadata = await sharp(buffer).metadata();
  } catch {
    throw new Error("Use a JPEG, PNG, or WebP image");
  }
  if (!metadata.format || !["jpeg", "png", "webp"].includes(metadata.format)) {
    throw new Error("Use a JPEG, PNG, or WebP image");
  }
  return buffer;
}

export async function saveImageUpload(file: File) {
  const buffer = await readValidatedBuffer(file);
  const ext = extensionFor(file.type);
  const name = `${randomBytes(16).toString("hex")}.${ext}`;
  await mkdir(UPLOAD_DIR, { recursive: true });
  await writeFile(path.join(UPLOAD_DIR, name), buffer);
  return `/uploads/${name}`;
}

function avatarUserDir(userId: string) {
  if (!/^[a-zA-Z0-9_-]+$/.test(userId)) {
    throw new Error("Invalid avatar path");
  }
  return path.join(process.cwd(), "public", "uploads", "avatars", userId);
}

export async function saveAvatarUpload(userId: string, file: File) {
  const buffer = await readValidatedBuffer(file);
  const generation = randomBytes(8).toString("hex");
  const userAbs = avatarUserDir(userId);
  const folderAbs = path.join(userAbs, generation);
  await rm(userAbs, { recursive: true, force: true });
  await mkdir(folderAbs, { recursive: true });

  const square = sharp(buffer).rotate().resize(512, 512, {
    fit: "cover",
    position: "centre",
  });

  const sizes = [...new Set(Object.values(AVATAR_PIXELS))] as number[];
  await Promise.all(
    sizes.map(async (pixels) => {
      const out = await square
        .clone()
        .resize(pixels, pixels, { fit: "cover" })
        .webp({ quality: AVATAR_QUALITY });
      await writeFile(path.join(folderAbs, `w${pixels}.webp`), await out.toBuffer());
    }),
  );

  return avatarFolder(userId, generation);
}

export async function deleteAvatarFiles(avatarUrl: string | null | undefined) {
  if (!avatarUrl?.startsWith("/uploads/avatars/")) return;
  const parts = avatarUrl.replace(/\/w\d+\.webp$/, "").replace(/^\//, "").split("/");
  if (parts[0] !== "uploads" || parts[1] !== "avatars" || !parts[2]) return;
  if (!/^[a-zA-Z0-9_-]+$/.test(parts[2])) return;
  await rm(avatarUserDir(parts[2]), { recursive: true, force: true });
}