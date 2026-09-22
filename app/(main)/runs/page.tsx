import { EmptyState } from "@/components/ui/EmptyState";
import { RunCard } from "@/components/runs/RunCard";
import { getCurrentUser } from "@/lib/auth";
import { listUpcomingRuns } from "@/lib/services/runs";
import styles from "./runs.module.css";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const user = await getCurrentUser();
  if (!user) return null;
  const runs = await listUpcomingRuns(user.id);

  return (
    <section className={styles.page}>
      <h1 className={styles.title}>RUNS</h1>
      {runs.length === 0 ? (
        <EmptyState
          title="No upcoming runs"
          body="When someone hosts a run, their crew shows up here."
        />
      ) : (
        runs.map((run) => <RunCard key={run.id} run={run} />)
      )}
    </section>
  );
}
