import { NextRequest, NextResponse } from "next/server";
import { getCurrentUser } from "@/lib/auth";
import { handleRouteError, jsonError } from "@/lib/api";
import { setAvatar, updateProfile } from "@/lib/services/users";
import { saveAvatarUpload } from "@/lib/storage";

export async function GET() {
  try {
    const user = await getCurrentUser();
    if (!user) return jsonError("Sign in required", 401);
    return NextResponse.json({ user });
  } catch (error) {
    return handleRouteError(error);
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const user = await getCurrentUser();
    if (!user) return jsonError("Sign in required", 401);

    const contentType = request.headers.get("content-type") ?? "";
    if (contentType.includes("multipart/form-data")) {
      const form = await request.formData();
      const file = form.get("avatar");
      if (file instanceof File && file.size > 0) {
        const avatarUrl = await saveAvatarUpload(user.id, file);
        const updated = await setAvatar(user.id, avatarUrl);
        return NextResponse.json({ user: updated });
      }
    }

    const body = await request.json();
    const updated = await updateProfile(user.id, body);
    return NextResponse.json({ user: updated });
  } catch (error) {
    return handleRouteError(error);
  }
}
