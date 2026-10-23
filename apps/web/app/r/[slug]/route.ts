import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

/** Tracked CTA link: records one real click (no IP or identity stored) and redirects to the business's destination. */
export async function GET(request: NextRequest, { params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  if (!/^[a-z0-9]{6,16}$/.test(slug)) return new NextResponse("Not found", { status: 404 });
  const ua = request.headers.get("user-agent") ?? "";
  const device = /Mobi|Android|iPhone/i.test(ua) ? "mobile" : /Windows|Macintosh|Linux|CrOS/i.test(ua) ? "desktop" : "other";
  let referrer: string | null = null;
  try { referrer = request.headers.get("referer") ? new URL(request.headers.get("referer")!).host : null; } catch { /* malformed */ }
  const { data, error } = await (await createClient()).rpc("track_click", { p_slug: slug, p_referrer: referrer, p_device: device });
  if (error || typeof data !== "string" || !data.startsWith("https://")) return new NextResponse("This link is no longer active.", { status: 404 });
  return NextResponse.redirect(data, { status: 302, headers: { "Cache-Control": "no-store" } });
}
