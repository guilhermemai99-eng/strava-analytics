import { FeedList } from "@/components/feed/FeedList";
import { getCurrentUser } from "@/lib/auth";
import { getFeed } from "@/lib/services/posts";
import { listUpcomingRuns } from "@/lib/services/runs";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const user = await getCurrentUser();
  if (!user) return null;
  const [posts, runs] = await Promise.all([
    getFeed(user.id),
    listUpcomingRuns(user.id),
  ]);
  return <FeedList posts={posts} runs={runs} />;
}
