import { NextRequest, NextResponse } from "next/server";
import { getCurrentUser } from "@/lib/auth";
import { handleRouteError, jsonError } from "@/lib/api";
import { addComment, listComments } from "@/lib/services/posts";

type Ctx = { params: Promise<{ id: string }> };

export async function GET(_request: NextRequest, context: Ctx) {
  try {
    const { id } = await context.params;
    const user = await getCurrentUser();
    if (!user) return jsonError("Sign in required", 401);
    const comments = await listComments(id);
    return NextResponse.json({ comments });
  } catch (error) {
    return handleRouteError(error);
  }
}

export async function POST(request: NextRequest, context: Ctx) {
  try {
    const { id } = await context.params;
    const user = await getCurrentUser();
    if (!user) return jsonError("Sign in required", 401);
    const body = await request.json();
    const comment = await addComment(id, user.id, String(body.body ?? ""));
    return NextResponse.json(comment, { status: 201 });
  } catch (error) {
    return handleRouteError(error);
  }
}
