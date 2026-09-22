import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { PostCard } from "@/components/feed/PostCard";
import { RunCard } from "@/components/runs/RunCard";
import type { RunCardData } from "@/lib/services/runs";
import type { FeedPost } from "@/lib/types";
import styles from "./FeedList.module.css";

export function FeedList({
  posts,
  runs = [],
}: {
  posts: FeedPost[];
  runs?: RunCardData[];
}) {
  const upcoming = runs.slice(0, 3);

  if (posts.length === 0 && upcoming.length === 0) {
    return (
      <EmptyState
        title="NO RUNS YET"
        body="Share a run, or follow people whose pace feels like yours."
      >
        <Button href="/compose">Post a run</Button>
      </EmptyState>
    );
  }

  return (
    <div className={styles.page}>
      <p className={styles.title}>HOME</p>
      {upcoming.length > 0 ? (
        <section className={styles.upcoming} aria-label="Upcoming social runs">
          {upcoming.map((run) => (
            <RunCard key={run.id} run={run} />
          ))}
        </section>
      ) : null}
      {posts.map((post) => (
        <PostCard key={post.id} post={post} />
      ))}
    </div>
  );
}
