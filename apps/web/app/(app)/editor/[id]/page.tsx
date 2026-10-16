import { notFound } from "next/navigation";
import { parseComposition } from "@reel-studio/timeline-schema";
import { Editor } from "@/components/editor/editor";
import { requireOrg } from "@/lib/supabase/server";

export default async function EditorPage({ params }: PageProps<"/editor/[id]">) {
  const { id } = await params;
  const { supabase, org } = await requireOrg();
  const [{ data: render }, { data: draft }] = await Promise.all([
    supabase.from("render_jobs").select("id, organization_id, project_id, timeline, projects(name)").eq("id", id).maybeSingle(),
    supabase.from("timeline_drafts").select("timeline, updated_at").eq("base_render_id", id).maybeSingle(),
  ]);
  if (!render || render.organization_id !== org.id) notFound();
  let initial, restored = null;
  try {
    initial = parseComposition(render.timeline);
    if (draft) restored = { timeline: parseComposition(draft.timeline), updated_at: draft.updated_at };
  } catch {
    return <p role="alert" className="studio-panel p-6 text-danger">This video uses an older timeline format that the editor cannot open. Render it again from its project.</p>;
  }
  return <Editor renderId={render.id} projectId={render.project_id} orgId={org.id} projectName={(render.projects as unknown as { name: string } | null)?.name ?? "Project"}
    initial={initial} draft={restored} canEdit={org.role !== "viewer"} />;
}
