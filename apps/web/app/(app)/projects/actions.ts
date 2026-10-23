"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireOrg } from "@/lib/supabase/server";

export type ProjectFormState = { error?: string; notice?: string } | undefined;

export async function createProject(_: ProjectFormState, form: FormData): Promise<ProjectFormState> {
  const name = String(form.get("name") ?? form.get("topic") ?? "").trim().slice(0, 120);
  const mode = String(form.get("mode") ?? "");
  if (!name || name.length > 120) return { error: "Give the project a name (up to 120 characters)." };
  // Topic → Video is retired (old topic projects stay readable); new projects are Recording → Reels or Prompt → Edit.
  if (mode !== "recording" && mode !== "edit") return { error: "Choose a mode." };
  const { supabase, org, userId } = await requireOrg();
  // RLS decides whether this role may create projects in this workspace.
  const { data, error } = await supabase.from("projects").insert({ organization_id: org.id, name, mode, created_by: userId }).select("id").single();
  if (error) return { error: error.code === "42501" ? "Your role cannot create projects here." : error.message };
  revalidatePath("/projects");
  revalidatePath("/dashboard");
  revalidatePath("/create");
  redirect(`/projects/${data.id}`);
}
