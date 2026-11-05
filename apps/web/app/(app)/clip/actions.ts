"use server";

import { revalidatePath } from "next/cache";
import { requireOrg } from "@/lib/supabase/server";

/** A recording project for one "Clip long video" run (RLS decides whether this role may create it). */
export async function createClipProject(name: string): Promise<{ id?: string; error?: string }> {
  const clean = name.trim().slice(0, 120) || "Clips";
  const { supabase, org, userId } = await requireOrg();
  const { data, error } = await supabase.from("projects")
    .insert({ organization_id: org.id, name: clean, mode: "recording", created_by: userId }).select("id").single();
  if (error) return { error: error.code === "42501" ? "Your role cannot create projects here." : error.message };
  revalidatePath("/projects");
  revalidatePath("/dashboard");
  return { id: data.id as string };
}
