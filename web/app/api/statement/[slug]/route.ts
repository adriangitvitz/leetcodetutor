import { NextRequest, NextResponse } from "next/server";
import { LEETAPI_URL } from "@/lib/api";

export const runtime = "nodejs";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params;
  const search = req.nextUrl.search;
  const r = await fetch(`${LEETAPI_URL}/problems/${slug}/statement${search}`, {
    cache: "no-store",
  });
  return new Response(r.body, {
    status: r.status,
    headers: { "content-type": r.headers.get("content-type") ?? "application/json" },
  });
}
