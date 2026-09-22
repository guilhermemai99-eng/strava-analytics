export const AVATAR_SIZES = ["xs", "sm", "md", "lg", "xl"] as const;
export type AvatarSize = (typeof AVATAR_SIZES)[number];

export const AVATAR_PIXELS: Record<AvatarSize, number> = {
  xs: 64,
  sm: 64,
  md: 128,
  lg: 256,
  xl: 512,
};

export function avatarFolder(userId: string, generation?: string) {
  return generation
    ? `/uploads/avatars/${userId}/${generation}`
    : `/uploads/avatars/${userId}`;
}

export function avatarSrc(
  avatarUrl: string | null | undefined,
  size: AvatarSize = "md",
) {
  if (!avatarUrl) return null;
  if (avatarUrl.startsWith("http://") || avatarUrl.startsWith("https://")) {
    return avatarUrl;
  }
  if (avatarUrl.startsWith("/uploads/avatars/")) {
    const folder = avatarUrl.replace(/\/w\d+\.webp$/, "");
    return `${folder}/w${AVATAR_PIXELS[size]}.webp`;
  }
  return avatarUrl;
}
