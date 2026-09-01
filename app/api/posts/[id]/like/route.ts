import { NextRequest, NextResponse } from "next/server";
import { getCurrentUser } from "@/lib/auth";
import { handleRouteError, jsonError } from "@/lib/api";
import { toggleLike } from "@/lib/services/posts";
import { prisma } from "@/lib/db";

type Ctx = { params: Promise<{ id: string }> };

export async function POST(_request: NextRequest, context: Ctx) {
  try {
    const { id } = await context.params;
    const user = await getCurrentUser();
    if (!user) return jsonError("Sign in required", 401);
    const existing = await prisma.postLike.findUnique({
      where: { postId_userId: { postId: id, userId: user.id } },
    });
    if (!existing) {
      await toggleLike(id, user.id);
    }
    return NextResponse.json({ liked: true });
  } catch (error) {
    return handleRouteError(error);
  }
}

export async function DELETE(_request: NextRequest, context: Ctx) {
  try {
    const { id } = await context.params;
    const user = await getCurrentUser();
    if (!user) return jsonError("Sign in required", 401);
    const existing = await prisma.postLike.findUnique({
      where: { postId_userId: { postId: id, userId: user.id } },
    });
    if (existing) {
      await toggleLike(id, user.id);
    }
    return NextResponse.json({ liked: false });
  } catch (error) {
    return handleRouteError(error);
  }
}
