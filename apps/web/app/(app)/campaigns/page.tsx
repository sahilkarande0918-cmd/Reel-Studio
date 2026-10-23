import Link from "next/link";
import { Megaphone } from "lucide-react";
import { EmptyState, PageHeader } from "@/components/app/page-header";
import { NewCampaign } from "@/components/campaigns/new-campaign";
import { requireOrg } from "@/lib/supabase/server";

export default async function CampaignsPage() {
  const { supabase, org } = await requireOrg();
  const { data } = await supabase.from("campaigns").select("id, code, business, language, status, created_at").eq("organization_id", org.id).order("created_at", { ascending: false });
  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Business" title="Campaigns">Describe a local business once. The AI plans a Reels campaign (hooks, scripts, captions, CTAs and a posting plan), turns each idea into an edit, and tracks real clicks and inquiries.</PageHeader>
      {org.role !== "viewer" && <NewCampaign orgId={org.id} />}
      <section>
        <h2 className="mb-4 text-[17px] font-semibold tracking-[-.02em]">Your campaigns</h2>
        {data?.length ? <ul className="grid gap-3 md:grid-cols-2">{data.map((c) => <li key={c.id}><Link href={`/campaigns/${c.id}`} className="studio-panel block p-4 hover:border-accent">
          <p className="text-[15px] font-semibold">{(c.business as { name: string }).name}</p>
          <p className="mt-1 text-[12px] text-muted">{c.code} · {c.language} · {c.status} · {new Date(c.created_at).toLocaleDateString()}</p></Link></li>)}</ul>
          : <EmptyState icon={<Megaphone size={26} aria-hidden />} title="No campaigns yet">Fill in the business details above to plan the first one.</EmptyState>}
      </section>
    </div>
  );
}
