import { NextRequest, NextResponse } from "next/server";
import { getCurrentUser } from "@/lib/auth";
import { handleRouteError, jsonError } from "@/lib/api";
import { followUser, unfollowUser } from "@/lib/services/follows";

type Ctx = { params: Promise<{ username: string }> };

export async function POST(_request: NextRequest, context: Ctx) {
  try {
    const { username } = await context.params;
    const user = await getCurrentUser();
    if (!user) return jsonError("Sign in required", 401);
    const result = await followUser(user.id, username);
    return NextResponse.json(result);
  } catch (error) {
    return handleRouteError(error);
  }
}

export async function DELETE(_request: NextRequest, context: Ctx) {
  try {
    const { username } = await context.params;
    const user = await getCurrentUser();
    if (!user) return jsonError("Sign in required", 401);
    const result = await unfollowUser(user.id, username);
    return NextResponse.json(result);
  } catch (error) {
    return handleRouteError(error);
  }
}
