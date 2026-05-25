import { AppShell } from "@/components/AppShell";
import { Catalog } from "@/components/Catalog";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

type Diff = "EASY" | "MEDIUM" | "HARD";
const ALLOWED_DIFF: readonly Diff[] = ["EASY", "MEDIUM", "HARD"];

function parseDiff(raw: string | undefined): Diff | undefined {
  const up = raw?.toUpperCase();
  return (ALLOWED_DIFF as readonly string[]).includes(up ?? "")
    ? (up as Diff)
    : undefined;
}

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ difficulty?: string }>;
}) {
  const { difficulty } = await searchParams;
  const filterDiff = parseDiff(difficulty);

  const { items, total } = await api.listProblems({
    limit: 100,
    difficulty: filterDiff,
  });

  return (
    <AppShell totalCount={total}>
      <Catalog problems={items} initialDifficulty={filterDiff ?? "ALL"} />
    </AppShell>
  );
}
