import { prisma } from "@/lib/db";
import { createSession } from "@/lib/auth";
import { usernameFromSeed } from "@/lib/format";

export type OAuthProfile = {
  provider: "google" | "apple";
  providerAccountId: string;
  email: string;
  name: string;
  avatarUrl?: string | null;
};

export async function loginWithOAuth(profile: OAuthProfile) {
  const email = profile.email.trim().toLowerCase();
  if (!email) {
    throw new Error("This account did not share an email address");
  }

  const existingAccount = await prisma.oAuthAccount.findUnique({
    where: {
      provider_providerAccountId: {
        provider: profile.provider,
        providerAccountId: profile.providerAccountId,
      },
    },
  });

  let userId = existingAccount?.userId;

  if (!userId) {
    const byEmail = await prisma.user.findUnique({ where: { email } });
    if (byEmail) {
      userId = byEmail.id;
    } else {
      const user = await prisma.user.create({
        data: {
          email,
          name: profile.name.trim() || email.split("@")[0],
          username: await uniqueUsername(email.split("@")[0]),
          avatarUrl: profile.avatarUrl ?? null,
          passwordHash: null,
        },
      });
      userId = user.id;
    }

    await prisma.oAuthAccount.create({
      data: {
        provider: profile.provider,
        providerAccountId: profile.providerAccountId,
        userId,
      },
    });
  }

  if (profile.avatarUrl) {
    await prisma.user.updateMany({
      where: { id: userId, avatarUrl: null },
      data: { avatarUrl: profile.avatarUrl },
    });
  }

  return createSession(userId);
}

async function uniqueUsername(seed: string) {
  const base = usernameFromSeed(seed);
  for (let i = 0; i < 50; i += 1) {
    const candidate = i === 0 ? base : `${base.slice(0, 20)}${i}`;
    const taken = await prisma.user.findUnique({ where: { username: candidate } });
    if (!taken) return candidate;
  }
  return `${base.slice(0, 12)}${Date.now().toString(36)}`.slice(0, 24);
}
