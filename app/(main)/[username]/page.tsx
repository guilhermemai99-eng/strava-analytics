import { Avatar } from "@/components/ui/Avatar";
import { FollowButton } from "@/components/profile/FollowButton";
import { PostCard } from "@/components/feed/PostCard";
import { getCurrentUser } from "@/lib/auth";
import { isFollowing } from "@/lib/services/follows";
import { getPostsByUsername } from "@/lib/services/posts";
import { getUserByUsername } from "@/lib/services/users";
import { notFound } from "next/navigation";
import styles from "./username.module.css";

type Props = {
  params: Promise<{ username: string }>;
};

export default async function UserProfilePage({ params }: Props) {
  const { username } = await params;
  const profile = await getUserByUsername(username);
  if (!profile) notFound();
  const viewer = await getCurrentUser();
  const posts = await getPostsByUsername(profile.username, viewer?.id ?? null);
  const following =
    viewer && viewer.id !== profile.id
      ? await isFollowing(viewer.id, profile.id)
      : false;

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <Avatar name={profile.name} src={profile.avatarUrl} size="lg" />
        <div>
          <h1 className={styles.name}>{profile.name}</h1>
          <p className={styles.handle}>@{profile.username}</p>
          {profile.city ? <p className={styles.meta}>{profile.city}</p> : null}
          {profile.bio ? <p className={styles.bio}>{profile.bio}</p> : null}
          <p className={styles.counts}>
            {profile._count.followers} followers · {profile._count.following}{" "}
            following
          </p>
          {viewer && viewer.id !== profile.id ? (
            <FollowButton username={profile.username} initialFollowing={following} />
          ) : null}
        </div>
      </header>
      {posts.map((post) => (
        <PostCard key={post.id} post={post} />
      ))}
    </section>
  );
}
