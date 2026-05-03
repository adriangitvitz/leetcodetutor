import { AppShell } from "@/components/AppShell";
import { Catalog } from "@/components/Catalog";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const { items } = await api.listProblems({ limit: 50 });
  return (
    <AppShell totalCount={items.length}>
      <Catalog problems={items} />
    </AppShell>
  );
}
