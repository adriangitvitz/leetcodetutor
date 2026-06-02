import { notFound } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { StudyView } from "@/components/StudyView";
import { ApiError, api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ProblemPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const decoded = decodeURIComponent(slug);

  let resolved;
  try {
    resolved = await api.resolveProblem(decoded);
  } catch (err) {
    if (err instanceof ApiError && (err.status === 404 || err.status === 403)) notFound();
    throw err;
  }

  return (
    <AppShell problemTitle={resolved.problem.title}>
      <StudyView problem={resolved.problem} source={resolved.source} />
    </AppShell>
  );
}
