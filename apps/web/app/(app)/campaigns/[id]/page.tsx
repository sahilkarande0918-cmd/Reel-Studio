import { notFound } from "next/navigation";
import { CampaignView } from "@/components/campaigns/campaign-view";
import { requireOrg } from "@/lib/supabase/server";

export default async function CampaignPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { supabase, org } = await requireOrg();
  const { data } = await supabase.from("campaigns").select("id, organization_id").eq("id", id).maybeSingle();
  if (!data || data.organization_id !== org.id) notFound();
  return <CampaignView id={id} orgId={org.id} canEdit={org.role !== "viewer"} siteUrl={process.env.NEXT_PUBLIC_SITE_URL ?? ""} />;
}
