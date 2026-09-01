import { z } from "zod";
import { prisma } from "@/lib/db";
import {
  createSession,
  hashPassword,
  verifyPassword,
  SESSION_COOKIE,
  sessionCookieOptions,
} from "@/lib/auth";
import { RESERVED_USERNAMES } from "@/lib/format";

const usernameSchema = z
  .string()
  .trim()
  .toLowerCase()
  .min(3, "Username must be at least 3 characters")
  .max(24, "Username must be at most 24 characters")
  .regex(/^[a-z0-9_]+$/, "Use lowercase letters, numbers, and underscores")
  .refine((value) => !RESERVED_USERNAMES.has(value), "That username is reserved");

export const registerSchema = z.object({
  email: z.string().trim().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  name: z.string().trim().min(1, "Name is required").max(80),
  username: usernameSchema,
});

export const loginSchema = z.object({
  email: z.string().trim().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

export async function registerUser(input: z.infer<typeof registerSchema>) {
  const data = registerSchema.parse(input);
  const email = data.email.toLowerCase();
  const username = data.username.toLowerCase();

  const existingEmail = await prisma.user.findUnique({ where: { email } });
  if (existingEmail) {
    throw new Error("Email is already registered");
  }
  const existingUsername = await prisma.user.findUnique({ where: { username } });
  if (existingUsername) {
    throw new Error("Username is taken");
  }

  const user = await prisma.user.create({
    data: {
      email,
      passwordHash: await hashPassword(data.password),
      name: data.name,
      username,
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

  const session = await createSession(user.id);
  return { user, session };
}

export async function loginUser(input: z.infer<typeof loginSchema>) {
  const data = loginSchema.parse(input);
  const user = await prisma.user.findUnique({
    where: { email: data.email.toLowerCase() },
  });
  if (!user) {
    throw new Error("Invalid email or password");
  }
  if (!user.passwordHash) {
    throw new Error("This account uses Google or Apple. Continue with that instead.");
  }
  if (!(await verifyPassword(data.password, user.passwordHash))) {
    throw new Error("Invalid email or password");
  }
  const session = await createSession(user.id);
  return {
    user: {
      id: user.id,
      email: user.email,
      name: user.name,
      username: user.username,
      bio: user.bio,
      city: user.city,
      avatarUrl: user.avatarUrl,
    },
    session,
  };
}

export { SESSION_COOKIE, sessionCookieOptions };
