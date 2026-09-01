import { prisma } from "@/lib/db";

export async function followUser(followerId: string, username: string) {
  const target = await prisma.user.findUnique({
    where: { username: username.toLowerCase() },
  });
  if (!target) throw new Error("User not found");
  if (target.id === followerId) throw new Error("You cannot follow yourself");

  await prisma.follow.upsert({
    where: {
      followerId_followingId: {
        followerId,
        followingId: target.id,
      },
    },
    update: {},
    create: { followerId, followingId: target.id },
  });

  return { following: true };
}

export async function unfollowUser(followerId: string, username: string) {
  const target = await prisma.user.findUnique({
    where: { username: username.toLowerCase() },
  });
  if (!target) throw new Error("User not found");

  await prisma.follow.deleteMany({
    where: { followerId, followingId: target.id },
  });

  return { following: false };
}

export async function isFollowing(followerId: string, followingId: string) {
  const row = await prisma.follow.findUnique({
    where: {
      followerId_followingId: { followerId, followingId },
    },
  });
  return Boolean(row);
}
