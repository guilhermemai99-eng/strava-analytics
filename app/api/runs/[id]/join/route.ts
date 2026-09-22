import { NextResponse } from "next/server";
import { getCurrentUser } from "@/lib/auth";
import { handleRouteError, jsonError } from "@/lib/api";
import { joinRun, leaveRun } from "@/lib/services/runs";

export const dynamic = "force-dynamic";

export async function POST(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  try {
    const user = await getCurrentUser();
    if (!user) return jsonError("Sign in required", 401);
    const { id } = await context.params;
    const run = await joinRun(id, user.id);
    return NextResponse.json({ run });
  } catch (error) {
    return handleRouteError(error);
  }
}

export async function DELETE(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  try {
    const user = await getCurrentUser();
    if (!user) return jsonError("Sign in required", 401);
    const { id } = await context.params;
    const run = await leaveRun(id, user.id);
    return NextResponse.json({ run });
  } catch (error) {
    return handleRouteError(error);
  }
}
