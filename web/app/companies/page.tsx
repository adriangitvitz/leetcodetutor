import { AppShell } from "@/components/AppShell";
import { CompaniesView } from "@/components/Companies";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function CompaniesPage() {
    const { items } = await api.listCompanies({ with_topics: true });
    return (
        <AppShell totalCount={items.length}>
          <CompaniesView initial={items} />
        </AppShell>
  );
}
