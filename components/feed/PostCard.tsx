"use client";

import Link from "next/link";
import { useState } from "react";
import { Avatar } from "@/components/ui/Avatar";
import { PrBadge } from "@/components/ui/Badge";
import { formatDistance, formatDuration, formatPace } from "@/lib/format";
import type { FeedPost, PostComment } from "@/lib/types";
import { downloadShareImage } from "@/components/feed/shareImage";
import styles from "./PostCard.module.css";

type Props = {
  post: FeedPost;
};

export function PostCard({ post }: Props) {
  const [liked, setLiked] = useState(post.likedByMe);
  const [likeCount, setLikeCount] = useState(post.likeCount);
  const [comments, setComments] = useState<PostComment[] | null>(null);
  const [commentCount, setCommentCount] = useState(post.commentCount);
  const [hidden, setHidden] = useState(Boolean(post.hiddenAt));
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  if (hidden && post.isMine) {
    return (
      <article className={styles.card}>
        <div className={styles.header}>
          <p className={styles.meta}>This run is hidden from your feed.</p>
          <button
            className={styles.action}
            type="button"
            onClick={() => void hide(false)}
          >
            Undo
          </button>
        </div>
      </article>
    );
  }

  async function toggleLike() {
    const next = !liked;
    setLiked(next);
    setLikeCount((count) => count + (next ? 1 : -1));
    const response = await fetch(`/api/posts/${post.id}/like`, {
      method: next ? "POST" : "DELETE",
    });
    if (!response.ok) {
      setLiked(!next);
      setLikeCount((count) => count + (next ? -1 : 1));
    }
  }

  async function loadComments() {
    const response = await fetch(`/api/posts/${post.id}/comments`);
    if (!response.ok) return;
    const data = (await response.json()) as { comments: PostComment[] };
    setComments(data.comments);
  }

  async function submitComment(event: React.FormEvent) {
    event.preventDefault();
    if (!draft.trim() || busy) return;
    setBusy(true);
    const response = await fetch(`/api/posts/${post.id}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body: draft }),
    });
    setBusy(false);
    if (!response.ok) return;
    const comment = (await response.json()) as PostComment;
    setComments((current) => [...(current ?? []), comment]);
    setCommentCount((count) => count + 1);
    setDraft("");
  }

  async function hide(nextHidden: boolean) {
    const response = await fetch(`/api/posts/${post.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hidden: nextHidden }),
    });
    if (response.ok) setHidden(nextHidden);
  }

  return (
    <article className={styles.card}>
      <header className={styles.header}>
        <Avatar name={post.author.name} src={post.author.avatarUrl} />
        <div className={styles.identity}>
          <Link href={`/${post.author.username}`} className={styles.name}>
            {post.author.name}
          </Link>
          <span className={styles.meta}>
            @{post.author.username}
            {post.city ? ` · ${post.city}` : ""}
          </span>
        </div>
      </header>

      {post.imageUrl ? (
        // User photos are local uploads.
        // eslint-disable-next-line @next/next/no-img-element
        <img src={post.imageUrl} alt="" className={styles.photo} />
      ) : (
        <div className={styles.fallback} />
      )}

      <div className={styles.metrics}>
        <div className={styles.primaryMetrics}>
          <span className={styles.stat}>{formatDistance(post.distanceKm)}</span>
          <span className={styles.stat}>
            {formatDuration(post.durationSeconds)}
          </span>
        </div>
        <div className={styles.pace}>
          {formatPace(post.distanceKm, post.durationSeconds)}
        </div>
        {post.isPr ? (
          <div className={styles.badgeRow}>
            <PrBadge />
          </div>
        ) : null}
      </div>

      {post.caption ? <p className={styles.caption}>{post.caption}</p> : null}

      <div className={styles.actions}>
        <button
          type="button"
          className={`${styles.action} ${liked ? styles.liked : ""}`}
          onClick={() => void toggleLike()}
          aria-label={liked ? "Unlike" : "Like"}
        >
          {liked ? "♥" : "♡"} {likeCount}
        </button>
        <button
          type="button"
          className={styles.action}
          onClick={() => void loadComments()}
        >
          💬 {commentCount}
        </button>
        <button
          type="button"
          className={styles.action}
          onClick={() =>
            void downloadShareImage({
              distanceKm: post.distanceKm,
              durationSeconds: post.durationSeconds,
              isPr: post.isPr,
            })
          }
        >
          Share
        </button>
        {post.isMine ? (
          <button
            type="button"
            className={`${styles.action} ${styles.menu}`}
            onClick={() => void hide(true)}
          >
            Hide
          </button>
        ) : null}
      </div>

      {comments ? (
        <div className={styles.comments}>
          {comments.map((comment) => (
            <p key={comment.id} className={styles.comment}>
              <Avatar
                name={comment.author.name}
                src={comment.author.avatarUrl}
                size="xs"
              />
              <span>
                <span className={styles.commentAuthor}>{comment.author.name}</span>
                {comment.body}
              </span>
            </p>
          ))}
          <form className={styles.composer} onSubmit={(event) => void submitComment(event)}>
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Write a comment"
              maxLength={280}
            />
            <button type="submit">Post</button>
          </form>
        </div>
      ) : null}
    </article>
  );
}
