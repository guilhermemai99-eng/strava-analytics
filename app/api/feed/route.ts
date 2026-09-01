import { NextResponse } from "next/server";
import { getCurrentUser } from "@/lib/auth";
import { handleRouteError, jsonError } from "@/lib/api";
import { getFeed } from "@/lib/services/posts";

export async function GET() {
  try {
    const user = await getCurrentUser();
    if (!user) return jsonError("Sign in required", 401);
    const posts = await getFeed(user.id);
    return NextResponse.json({ posts });
  } catch (error) {
    return handleRouteError(error);
  }
}
