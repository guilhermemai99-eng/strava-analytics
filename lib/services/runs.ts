import { prisma } from "@/lib/db";
import { toPublicUser } from "@/lib/services/users";
import type { PublicUser } from "@/lib/types";

const participantSelect = {
  user: {
    select: {
      id: true,
      name: true,
      username: true,
      bio: true,
      city: true,
      avatarUrl: true,
    },
  },
} as const;

function peopleFromRun(run: {
  host: {
    id: string;
    name: string;
    username: string;
    bio: string | null;
    city: string | null;
    avatarUrl: string | null;
  };
  participants: { user: Parameters<typeof toPublicUser>[0] }[];
}): PublicUser[] {
  const seen = new Map<string, PublicUser>();
  seen.set(run.host.id, toPublicUser(run.host));
  for (const row of run.participants) {
    seen.set(row.user.id, toPublicUser(row.user));
  }
  return [...seen.values()];
}

export type RunCardData = {
  id: string;
  title: string;
  startsAt: string;
  city: string;
  locationName: string | null;
  distanceKm: number;
  paceMinSec: number | null;
  paceMaxSec: number | null;
  description: string | null;
  host: PublicUser;
  people: PublicUser[];
  going: boolean;
};

function serialize(
  run: {
    id: string;
    title: string;
    startsAt: Date;
    city: string;
    locationName: string | null;
    distanceKm: number;
    paceMinSec: number | null;
    paceMaxSec: number | null;
    description: string | null;
    host: Parameters<typeof toPublicUser>[0];
    participants: { user: Parameters<typeof toPublicUser>[0] }[];
  },
  viewerId: string | null,
): RunCardData {
  const people = peopleFromRun(run);
  return {
    id: run.id,
    title: run.title,
    startsAt: run.startsAt.toISOString(),
    city: run.city,
    locationName: run.locationName,
    distanceKm: run.distanceKm,
    paceMinSec: run.paceMinSec,
    paceMaxSec: run.paceMaxSec,
    description: run.description,
    host: toPublicUser(run.host),
    people,
    going: Boolean(viewerId && people.some((person) => person.id === viewerId)),
  };
}

const runInclude = {
  host: {
    select: {
      id: true,
      name: true,
      username: true,
      bio: true,
      city: true,
      avatarUrl: true,
    },
  },
  participants: { include: participantSelect },
} as const;

export async function listUpcomingRuns(viewerId: string | null) {
  const runs = await prisma.run.findMany({
    where: { startsAt: { gte: new Date(Date.now() - 60 * 60 * 1000) } },
    include: runInclude,
    orderBy: { startsAt: "asc" },
    take: 50,
  });
  return runs.map((run) => serialize(run, viewerId));
}

export async function getRunById(id: string, viewerId: string | null) {
  const run = await prisma.run.findUnique({
    where: { id },
    include: runInclude,
  });
  if (!run) return null;
  return serialize(run, viewerId);
}

export async function joinRun(runId: string, userId: string) {
  const run = await prisma.run.findUnique({ where: { id: runId } });
  if (!run) throw new Error("Run not found");
  await prisma.runParticipant.upsert({
    where: { runId_userId: { runId, userId } },
    update: {},
    create: { runId, userId },
  });
  return getRunById(runId, userId);
}

export async function leaveRun(runId: string, userId: string) {
  const run = await prisma.run.findUnique({ where: { id: runId } });
  if (!run) throw new Error("Run not found");
  if (run.hostId === userId) {
    return getRunById(runId, userId);
  }
  await prisma.runParticipant.deleteMany({ where: { runId, userId } });
  return getRunById(runId, userId);
}

export async function createRun() {
  throw new Error("Runs ship in the next phase");
}
