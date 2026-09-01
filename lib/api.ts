import { NextResponse } from "next/server";
import { AuthError } from "@/lib/auth";
import { ZodError } from "zod";

export function jsonError(message: string, status = 400) {
  return NextResponse.json({ error: message }, { status });
}

export function handleRouteError(error: unknown) {
  if (error instanceof AuthError) {
    return jsonError(error.message, error.status);
  }
  if (error instanceof ZodError) {
    return jsonError(error.issues[0]?.message ?? "Invalid input", 400);
  }
  if (error instanceof Error && error.message) {
    const known = [
      "Username is taken",
      "Email is already registered",
      "Invalid email or password",
      "Post not found",
      "You cannot follow yourself",
      "User not found",
      "Comment cannot be empty",
      "Comment is too long",
      "Use a JPEG, PNG, or WebP image",
      "Image must be under 8 MB",
    ];
    if (known.includes(error.message)) {
      const status = error.message === "Post not found" ? 404 : 400;
      return jsonError(error.message, status);
    }
  }
  console.error(error);
  return jsonError("Something went wrong", 500);
}
