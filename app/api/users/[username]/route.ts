import { NextRequest, NextResponse } from "next/server";
import { getCurrentUser } from "@/lib/auth";
import { handleRouteError, jsonError } from "@/lib/api";
import { getUserByUsername } from "@/lib/services/users";

type Ctx = { params: Promise<{ username: string }> };

export async function GET(_request: NextRequest, context: Ctx) {
  try {
    const { username } = await context.params;
    const viewer = await getCurrentUser();
    if (!viewer) return jsonError("Sign in required", 401);
    const profile = await getUserByUsername(username);
    if (!profile) return jsonError("User not found", 404);
    return NextResponse.json({ user: profile });
  } catch (error) {
    return handleRouteError(error);
  }
}
