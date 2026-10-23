import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { InquiryForm } from "./inquiry-form";

/** Public inquiry form for a campaign link: what a visitor sends becomes a real inquiry record for the business. */
export default async function InquiryPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  if (!/^[a-z0-9]{6,16}$/.test(slug)) notFound();
  const { data } = await (await createClient()).rpc("link_info", { p_slug: slug });
  const info = data as { business: string | null; offer: string | null } | null;
  if (!info) notFound();
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 bg-[#FCF9F4] px-6 py-12 text-[#1F2618]">
      <div>
        <p className="text-[12px] font-semibold uppercase tracking-[.12em] text-[#5B6B45]">Enquiry</p>
        <h1 className="mt-2 font-serif text-[32px] leading-tight">{info.business ?? "Send a message"}</h1>
        {info.offer && <p className="mt-2 text-[15px] text-[#4A5240]">{info.offer}</p>}
      </div>
      <InquiryForm slug={slug} />
      <p className="text-[11px] text-[#7A7F70]">Your message goes only to {info.business ?? "this business"}. Sent through Reel Studio.</p>
    </main>
  );
}
