import { logoutAction } from "@/app/(auth)/login/actions";
import { Button } from "@/components/ui/Button";
import styles from "./settings.module.css";

export default function SettingsPage() {
  return (
    <section className={styles.page}>
      <h1 className={styles.title}>SETTINGS</h1>
      <p className={styles.body}>
        Profile editing ships with the Profile phase. You can sign out now.
      </p>
      <form action={logoutAction}>
        <Button type="submit">Log out</Button>
      </form>
    </section>
  );
}
