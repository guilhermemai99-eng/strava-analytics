"use server";

import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { createPost } from "@/lib/services/posts";
import { saveImageUpload } from "@/lib/storage";
import { PostVisibility } from "@prisma/client";

export type ComposeState = { error?: string } | null;

export async function createPostAction(
  _prev: ComposeState,
  formData: FormData,
): Promise<ComposeState> {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  try {
    const image = formData.get("image");
    let imageUrl: string | null = null;
    if (image instanceof File && image.size > 0) {
      imageUrl = await saveImageUpload(image);
    }

    const hours = Number(formData.get("hours") || 0);
    const minutes = Number(formData.get("minutes") || 0);
    const seconds = Number(formData.get("seconds") || 0);
    const visibilityValue = String(formData.get("visibility") || "public");
    const visibility =
      visibilityValue === "followers" || visibilityValue === "private"
        ? visibilityValue
        : "public";

    await createPost(user.id, {
      caption: String(formData.get("caption") || "") || null,
      distanceKm: Number(formData.get("distanceKm")),
      durationSeconds: hours * 3600 + minutes * 60 + seconds,
      occurredAt: new Date(String(formData.get("occurredAt"))),
      city: String(formData.get("city") || "") || null,
      isPr: formData.get("isPr") === "on" || formData.get("isPr") === "true",
      visibility: visibility as PostVisibility,
      imageUrl,
    });
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Could not post",
    };
  }

  redirect("/");
}
