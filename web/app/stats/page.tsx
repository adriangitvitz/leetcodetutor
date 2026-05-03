import { AppShell } from "@/components/AppShell";
import { StatsView } from "@/components/Stats";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function StatsPage() {
  const stats = await api.getStats(30);
  return (
    <AppShell>
      <StatsView stats={stats} />
    </AppShell>
  );
}
