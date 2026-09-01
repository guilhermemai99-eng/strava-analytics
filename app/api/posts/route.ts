import { NextRequest, NextResponse } from "next/server";
import { getCurrentUser } from "@/lib/auth";
import { handleRouteError, jsonError } from "@/lib/api";
import { createPost } from "@/lib/services/posts";
import { saveImageUpload } from "@/lib/storage";
import { PostVisibility } from "@prisma/client";

export async function POST(request: NextRequest) {
  try {
    const user = await getCurrentUser();
    if (!user) return jsonError("Sign in required", 401);

    const form = await request.formData();
    const image = form.get("image");
    let imageUrl: string | null = null;
    if (image instanceof File && image.size > 0) {
      imageUrl = await saveImageUpload(image);
    }

    const visibilityValue = String(form.get("visibility") || "public");
    const visibility =
      visibilityValue === "followers" || visibilityValue === "private"
        ? visibilityValue
        : "public";

    const post = await createPost(user.id, {
      caption: String(form.get("caption") || "") || null,
      distanceKm: Number(form.get("distanceKm")),
      durationSeconds: Number(form.get("durationSeconds")),
      occurredAt: new Date(String(form.get("occurredAt"))),
      city: String(form.get("city") || "") || null,
      isPr: String(form.get("isPr")) === "true",
      visibility: visibility as PostVisibility,
      imageUrl,
    });

    return NextResponse.json({ post }, { status: 201 });
  } catch (error) {
    return handleRouteError(error);
  }
}
