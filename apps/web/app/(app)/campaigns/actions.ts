"use server";

import { redirect } from "next/navigation";
import { requireOrg } from "@/lib/supabase/server";

/** Turns a campaign Reel idea into a real project: Prompt → Edit (clips) or Recording → Reels (talking video). */
export async function createFromIdea(campaignId: string, reelKey: string, mode: "edit" | "recording", title: string) {
  if (!/^[a-z0-9-]{1,20}$/.test(reelKey)) throw new Error("bad reel");
  const { supabase, org, userId } = await requireOrg();
  const { data, error } = await supabase.from("projects").insert({
    organization_id: org.id, name: title.slice(0, 120) || "Campaign reel", mode, created_by: userId, campaign_id: campaignId, campaign_reel: reelKey,
  }).select("id").single();
  if (error) throw new Error(error.code === "42501" ? "Your role cannot create projects here." : error.message);
  redirect(`/projects/${data.id}`);
}
