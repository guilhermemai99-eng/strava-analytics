import { notFound } from "next/navigation";
import { RunDetail } from "@/components/runs/RunDetail";
import { getCurrentUser } from "@/lib/auth";
import { getRunById } from "@/lib/services/runs";

export const dynamic = "force-dynamic";

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const user = await getCurrentUser();
  if (!user) return null;
  const { id } = await params;
  const run = await getRunById(id, user.id);
  if (!run) notFound();
  return <RunDetail run={run} viewerId={user.id} />;
}
