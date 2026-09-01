import { NextRequest, NextResponse } from "next/server";
import { getCurrentUser } from "@/lib/auth";
import { handleRouteError, jsonError } from "@/lib/api";
import { updateProfile } from "@/lib/services/users";
import { saveImageUpload } from "@/lib/storage";
import { prisma } from "@/lib/db";

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
        const avatarUrl = await saveImageUpload(file);
        const updated = await prisma.user.update({
          where: { id: user.id },
          data: { avatarUrl },
          select: {
            id: true,
            email: true,
            name: true,
            username: true,
            bio: true,
            city: true,
            avatarUrl: true,
          },
        });
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
