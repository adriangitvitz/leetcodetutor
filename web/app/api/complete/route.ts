import { NextRequest, NextResponse } from "next/server";
import { LEETAPI_URL } from "@/lib/api";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const body = await req.text();
  const r = await fetch(`${LEETAPI_URL}/tutor/complete`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body,
  });
  const text = await r.text();
  if (!r.ok) {
    return new Response(text, {
      status: r.status,
      headers: { "content-type": "application/json" },
    });
  }
  try {
    const parsed = JSON.parse(text) as {
      text: string;
      provider: string;
      model: string;
      request_id: string;
    };
    return NextResponse.json({ ...parsed, requestId: parsed.request_id });
  } catch {
    return new Response(text, { status: 500 });
  }
}
