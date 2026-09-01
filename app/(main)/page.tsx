import { FeedList } from "@/components/feed/FeedList";
import { getCurrentUser } from "@/lib/auth";
import { getFeed } from "@/lib/services/posts";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const user = await getCurrentUser();
  if (!user) return null;
  const posts = await getFeed(user.id);
  return <FeedList posts={posts} />;
}
