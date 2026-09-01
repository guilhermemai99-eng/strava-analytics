import Link from "next/link";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { getCurrentUser } from "@/lib/auth";
import styles from "./profile.module.css";

export default async function ProfilePage() {
  const user = await getCurrentUser();
  if (!user) return null;

  return (
    <section className={styles.page}>
      <Avatar name={user.name} src={user.avatarUrl} size="lg" />
      <h1 className={styles.name}>{user.name}</h1>
      <p className={styles.handle}>@{user.username}</p>
      {user.city ? <p className={styles.city}>{user.city}</p> : null}
      {user.bio ? <p className={styles.bio}>{user.bio}</p> : null}
      <Button href="/settings" variant="inverse">
        Settings
      </Button>
      <p className={styles.note}>
        Posts and follow lists land with the Profile phase. Your runs already
        appear in Home.
      </p>
      <Link href={`/${user.username}`} className={styles.link}>
        View public profile
      </Link>
    </section>
  );
}
