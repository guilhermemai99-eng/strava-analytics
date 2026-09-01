import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { PostCard } from "@/components/feed/PostCard";
import type { FeedPost } from "@/lib/types";
import styles from "./FeedList.module.css";

export function FeedList({ posts }: { posts: FeedPost[] }) {
  if (posts.length === 0) {
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
      {posts.map((post) => (
        <PostCard key={post.id} post={post} />
      ))}
    </div>
  );
}
