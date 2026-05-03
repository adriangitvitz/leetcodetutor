import { notFound } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { CompanyDetail } from "@/components/CompanyDetail";
import { ApiError, api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function CompanyPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  const decoded = decodeURIComponent(name);

  let detail;
  let related: Awaited<ReturnType<typeof api.getCompanyRelated>> = [];
  try {
    [detail, related] = await Promise.all([
      api.getCompany(decoded),
      api.getCompanyRelated(decoded, 8),
    ]);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  return (
    <AppShell problemTitle={detail.name}>
      <CompanyDetail detail={detail} related={related} />
    </AppShell>
  );
}
