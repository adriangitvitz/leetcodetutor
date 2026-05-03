import { NextRequest } from "next/server";
import { LEETAPI_URL } from "@/lib/api";

export const runtime = "nodejs";

export async function GET(req: NextRequest) {
  const provider = req.nextUrl.searchParams.get("provider") ?? "openrouter";
  const r = await fetch(`${LEETAPI_URL}/models?provider=${encodeURIComponent(provider)}`, {
    cache: "no-store",
  });
  return new Response(r.body, {
    status: r.status,
    headers: { "content-type": r.headers.get("content-type") ?? "application/json" },
  });
}
