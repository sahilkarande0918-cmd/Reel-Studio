import { ClipStudio } from "@/components/clip/clip-studio";
import { requireOrg } from "@/lib/supabase/server";

export const metadata = { title: "Clip long video · Reel Studio" };

export default async function ClipPage() {
  const { supabase, org } = await requireOrg();
  const { data: kits } = await supabase.from("brand_kits").select("id, name, is_default").eq("organization_id", org.id).order("created_at");
  return <ClipStudio canEdit={org.role !== "viewer"} kits={kits ?? []} />;
}
