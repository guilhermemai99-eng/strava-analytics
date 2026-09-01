import { z } from "zod";
import { prisma } from "@/lib/db";
import { RESERVED_USERNAMES } from "@/lib/format";
import type { PublicUser } from "@/lib/types";

export const updateProfileSchema = z.object({
  name: z.string().trim().min(1).max(80).optional(),
  username: z
    .string()
    .trim()
    .min(3)
    .max(24)
    .regex(/^[a-z0-9_]+$/)
    .refine((value) => !RESERVED_USERNAMES.has(value))
    .optional(),
  bio: z.string().trim().max(160).nullable().optional(),
  city: z.string().trim().max(80).nullable().optional(),
  preferredPaceSecPerKm: z.number().int().positive().nullable().optional(),
  preferredDistanceKm: z.number().positive().nullable().optional(),
});

export function toPublicUser(user: {
  id: string;
  name: string;
  username: string;
  bio: string | null;
  city: string | null;
  avatarUrl: string | null;
}): PublicUser {
  return {
    id: user.id,
    name: user.name,
    username: user.username,
    bio: user.bio,
    city: user.city,
    avatarUrl: user.avatarUrl,
  };
}

export async function getUserByUsername(username: string) {
  return prisma.user.findUnique({
    where: { username: username.toLowerCase() },
    select: {
      id: true,
      name: true,
      username: true,
      bio: true,
      city: true,
      avatarUrl: true,
      createdAt: true,
      _count: { select: { followers: true, following: true, posts: true } },
    },
  });
}

export async function updateProfile(
  userId: string,
  input: z.infer<typeof updateProfileSchema>,
) {
  const data = updateProfileSchema.parse(input);
  if (data.username) {
    const taken = await prisma.user.findFirst({
      where: { username: data.username, NOT: { id: userId } },
    });
    if (taken) throw new Error("Username is taken");
  }
  return prisma.user.update({
    where: { id: userId },
    data: {
      name: data.name,
      username: data.username,
      bio: data.bio,
      city: data.city,
      preferredPaceSecPerKm: data.preferredPaceSecPerKm,
      preferredDistanceKm: data.preferredDistanceKm,
    },
    select: {
      id: true,
      email: true,
      name: true,
      username: true,
      bio: true,
      city: true,
      avatarUrl: true,
    },
  });
}
