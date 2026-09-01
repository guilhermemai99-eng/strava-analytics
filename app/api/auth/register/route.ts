import { NextRequest, NextResponse } from "next/server";
import { handleRouteError } from "@/lib/api";
import { registerUser, SESSION_COOKIE, sessionCookieOptions } from "@/lib/services/auth";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { user, session } = await registerUser(body);
    const response = NextResponse.json({ user });
    response.cookies.set(
      SESSION_COOKIE,
      session.token,
      sessionCookieOptions(session.expiresAt),
    );
    return response;
  } catch (error) {
    return handleRouteError(error);
  }
}
