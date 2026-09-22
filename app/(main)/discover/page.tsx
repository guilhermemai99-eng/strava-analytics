import { EmptyState } from "@/components/ui/EmptyState";
import { RunCard } from "@/components/runs/RunCard";
import { getCurrentUser } from "@/lib/auth";
import { listUpcomingRuns } from "@/lib/services/runs";
import styles from "./discover.module.css";

export const dynamic = "force-dynamic";

export default async function DiscoverPage() {
  const user = await getCurrentUser();
  if (!user) return null;
  const runs = await listUpcomingRuns(user.id);

  return (
    <section className={styles.page}>
      <h1 className={styles.title}>DISCOVER</h1>
      {runs.length === 0 ? (
        <EmptyState
          title="No public runs yet"
          body="Upcoming runs and the people going will land here."
        />
      ) : (
        runs.map((run) => <RunCard key={run.id} run={run} />)
      )}
    </section>
  );
}
