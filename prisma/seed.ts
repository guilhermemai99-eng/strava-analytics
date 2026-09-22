import { PrismaClient, PostVisibility } from "@prisma/client";
import bcrypt from "bcryptjs";

const prisma = new PrismaClient();

async function main() {
  const passwordHash = await bcrypt.hash("pulse1234", 12);

  const joana = await prisma.user.upsert({
    where: { email: "joana@pulse.run" },
    update: {},
    create: {
      email: "joana@pulse.run",
      passwordHash,
      name: "Joana Silva",
      username: "joana",
      city: "Porto",
      bio: "Sunrise miles. Slow coffee.",
    },
  });

  const marco = await prisma.user.upsert({
    where: { email: "marco@pulse.run" },
    update: {},
    create: {
      email: "marco@pulse.run",
      passwordHash,
      name: "Marco Alves",
      username: "marco",
      city: "Porto",
      bio: "Long runs and longer talks.",
    },
  });

  await prisma.follow.upsert({
    where: {
      followerId_followingId: {
        followerId: marco.id,
        followingId: joana.id,
      },
    },
    update: {},
    create: { followerId: marco.id, followingId: joana.id },
  });

  await prisma.follow.upsert({
    where: {
      followerId_followingId: {
        followerId: joana.id,
        followingId: marco.id,
      },
    },
    update: {},
    create: { followerId: joana.id, followingId: marco.id },
  });

  const existing = await prisma.post.count({ where: { authorId: joana.id } });
  if (existing === 0) {
    await prisma.post.create({
      data: {
        authorId: joana.id,
        caption: "Saturday morning. The city still asleep.",
        distanceKm: 12.42,
        durationSeconds: 3741,
        occurredAt: new Date(),
        city: "Porto",
        isPr: true,
        visibility: PostVisibility.public,
      },
    });
    await prisma.post.create({
      data: {
        authorId: marco.id,
        caption: "Easy shakeout along the river.",
        distanceKm: 8.01,
        durationSeconds: 2520,
        occurredAt: new Date(),
        city: "Porto",
        isPr: false,
        visibility: PostVisibility.public,
      },
    });
  }

  const ines = await prisma.user.upsert({
    where: { email: "ines@pulse.run" },
    update: {},
    create: {
      email: "ines@pulse.run",
      passwordHash,
      name: "Inês Costa",
      username: "ines",
      city: "Porto",
      bio: "Track Tuesdays.",
    },
  });
  const rui = await prisma.user.upsert({
    where: { email: "rui@pulse.run" },
    update: {},
    create: {
      email: "rui@pulse.run",
      passwordHash,
      name: "Rui Mendes",
      username: "rui",
      city: "Porto",
      bio: "Hills before breakfast.",
    },
  });
  const ana = await prisma.user.upsert({
    where: { email: "ana@pulse.run" },
    update: {},
    create: {
      email: "ana@pulse.run",
      passwordHash,
      name: "Ana Rocha",
      username: "ana",
      city: "Porto",
      bio: "Easy pace, long talks.",
    },
  });

  let run = await prisma.run.findFirst({
    where: { hostId: joana.id, title: "Saturday river miles" },
  });
  if (!run) {
    run = await prisma.run.create({
      data: {
        hostId: joana.id,
        title: "Saturday river miles",
        startsAt: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000),
        city: "Porto",
        locationName: "Ribeira",
        distanceKm: 10,
        paceMinSec: 310,
        paceMaxSec: 340,
        description: "Easy catch-up along the Douro.",
      },
    });
  }
  for (const person of [marco, ines, rui, ana]) {
    await prisma.runParticipant.upsert({
      where: { runId_userId: { runId: run.id, userId: person.id } },
      update: {},
      create: { runId: run.id, userId: person.id },
    });
  }
}

main()
  .then(() => prisma.$disconnect())
  .catch(async (error) => {
    console.error(error);
    await prisma.$disconnect();
    process.exit(1);
  });
