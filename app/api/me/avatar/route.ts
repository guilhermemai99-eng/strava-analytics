import { NextResponse } from "next/server";
import { getCurrentUser } from "@/lib/auth";
import { handleRouteError, jsonError } from "@/lib/api";
import { prisma } from "@/lib/db";
import { clearAvatar, setAvatar } from "@/lib/services/users";
import { deleteAvatarFiles, saveAvatarUpload } from "@/lib/storage";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const user = await getCurrentUser();
    if (!user) return jsonError("Sign in required", 401);

    const form = await request.formData();
    const file = form.get("avatar");
    if (!(file instanceof File) || file.size === 0) {
      return jsonError("Choose a photo", 400);
    }

    const avatarUrl = await saveAvatarUpload(user.id, file);
    const updated = await setAvatar(user.id, avatarUrl);
    return NextResponse.json({ user: updated });
  } catch (error) {
    return handleRouteError(error);
  }
}

export async function DELETE() {
  try {
    const user = await getCurrentUser();
    if (!user) return jsonError("Sign in required", 401);
    const current = await prisma.user.findUnique({
      where: { id: user.id },
      select: { avatarUrl: true },
    });
    await deleteAvatarFiles(current?.avatarUrl);
    const updated = await clearAvatar(user.id);
    return NextResponse.json({ user: updated });
  } catch (error) {
    return handleRouteError(error);
  }
}
