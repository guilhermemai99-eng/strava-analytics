import { NextRequest, NextResponse } from "next/server";
import { getCurrentUser } from "@/lib/auth";
import { handleRouteError, jsonError } from "@/lib/api";
import { deletePost, getPost, updatePost } from "@/lib/services/posts";

type Ctx = { params: Promise<{ id: string }> };

export async function GET(_request: NextRequest, context: Ctx) {
  try {
    const { id } = await context.params;
    const user = await getCurrentUser();
    const post = await getPost(id, user?.id ?? null);
    return NextResponse.json({ post });
  } catch (error) {
    return handleRouteError(error);
  }
}

export async function PATCH(request: NextRequest, context: Ctx) {
  try {
    const { id } = await context.params;
    const user = await getCurrentUser();
    if (!user) return jsonError("Sign in required", 401);
    const body = await request.json();
    const post = await updatePost(id, user.id, body);
    return NextResponse.json({ post });
  } catch (error) {
    return handleRouteError(error);
  }
}

export async function DELETE(_request: NextRequest, context: Ctx) {
  try {
    const { id } = await context.params;
    const user = await getCurrentUser();
    if (!user) return jsonError("Sign in required", 401);
    await deletePost(id, user.id);
    return NextResponse.json({ ok: true });
  } catch (error) {
    return handleRouteError(error);
  }
}
