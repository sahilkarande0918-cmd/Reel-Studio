import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronLeft, Code2, Mic, Wand2 } from "lucide-react";
import { statusTone } from "@/components/app/project-grid";
import { EditStudio } from "@/components/studio/edit-studio";
import { RecordingStudio } from "@/components/studio/recording-studio";
import { TopicStudio } from "@/components/studio/topic-studio";
import { requireOrg } from "@/lib/supabase/server";

export default async function ProjectPage({ params }: PageProps<"/projects/[id]">) {
  const { id } = await params;
  const { supabase, org } = await requireOrg();
  const { data: project } = await supabase.from("projects").select("id, name, mode, status, organization_id, campaign_id, campaign_reel").eq("id", id).maybeSingle();
  if (!project || project.organization_id !== org.id) notFound();
  const topic = project.mode === "topic";
  const edit = project.mode === "edit";
  // a project made from a campaign idea starts with that idea's direction filled in
  let idea: { prompt: string; style: string; duration: number } | undefined;
  if (project.campaign_id) {
    const { data: c } = await supabase.from("campaigns").select("plan").eq("id", project.campaign_id).maybeSingle();
    const r = (c?.plan as { reels?: { key: string; hook: string; script: string; cta: string; style: string; duration_s: number }[] } | null)?.reels?.find((x) => x.key === project.campaign_reel);
    if (r) idea = { prompt: `${r.hook} ${r.script} End with: ${r.cta}`.slice(0, 2000), style: r.style, duration: r.duration_s };
  }
  return (
    <div className="space-y-6">
      <div>
        <Link href={edit ? "/create" : topic ? "/projects?mode=topic" : "/recordings"} className="inline-flex items-center gap-1 text-[13px] font-semibold text-muted hover:text-ink"><ChevronLeft size={15} aria-hidden />{edit ? "Create" : topic ? "Topic videos (retired)" : "Recordings"}</Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-accent/12 text-accent ring-1 ring-accent/25">{edit ? <Wand2 size={19} aria-hidden /> : topic ? <Code2 size={19} aria-hidden /> : <Mic size={19} aria-hidden />}</span>
          <h1 className="studio-heading">{project.name}</h1>
          <span className={`studio-pill ${statusTone(project.status)}`}>{project.status.replaceAll("_", " ")}</span>
        </div>
      </div>
      {edit ? <EditStudio projectId={project.id} canEdit={org.role !== "viewer"} idea={idea} /> : topic ? <TopicStudio projectId={project.id} canEdit={org.role !== "viewer"} /> : <RecordingStudio projectId={project.id} canEdit={org.role !== "viewer"} />}
    </div>
  );
}
