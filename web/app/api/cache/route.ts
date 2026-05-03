import { LEETAPI_URL } from "@/lib/api";

export const runtime = "nodejs";

export async function GET() {
  const r = await fetch(`${LEETAPI_URL}/cache`, { cache: "no-store" });
  return new Response(r.body, {
    status: r.status,
    headers: { "content-type": r.headers.get("content-type") ?? "application/json" },
  });
}
