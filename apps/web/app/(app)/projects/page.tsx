import { FolderOpen } from "lucide-react";
import { EmptyState, PageHeader } from "@/components/app/page-header";
import { ProjectGrid } from "@/components/app/project-grid";
import { requireOrg } from "@/lib/supabase/server";
import { NewProjectForm } from "./new-project-form";

const FILTERS = [["", "All"], ["recording", "Recordings"], ["edit", "Prompt edits"], ["topic", "Topic videos (retired)"]] as const;

export default async function ProjectsPage({ searchParams }: { searchParams: Promise<{ mode?: string; q?: string }> }) {
  const { supabase, org } = await requireOrg();
  const { mode, q } = await searchParams;
  let query = supabase.from("projects").select("id, name, mode, status, updated_at").eq("organization_id", org.id).order("updated_at", { ascending: false });
  if (mode === "recording" || mode === "edit" || mode === "topic") query = query.eq("mode", mode);
  if (q?.trim()) query = query.ilike("name", `%${q.trim().replace(/[%_]/g, "")}%`);
  const { data: projects, error } = await query;
  return (
    <div className="space-y-7">
      <PageHeader eyebrow="Library" title="Projects">Every recording, topic and finished reel in {org.name}.</PageHeader>
      {org.role !== "viewer" && <NewProjectForm key={mode} mode={mode === "edit" ? "edit" : "recording"} />}
      <form className="flex flex-wrap items-center justify-between gap-3" role="search">
        <div className="flex gap-1 rounded-lg bg-surface-2 p-1">{FILTERS.map(([v, label]) => <button key={v} name="mode" value={v} className={`rounded-md px-3 py-1.5 text-[12.5px] font-semibold ${((mode ?? "") === v) ? "bg-surface text-ink shadow-sm" : "text-muted hover:text-ink"}`}>{label}</button>)}</div>
        <label className="w-full sm:w-72"><span className="sr-only">Search projects</span><input name="q" defaultValue={q} placeholder="Search projects…" className="studio-input" /></label>
      </form>
      {error && <p role="alert" className="text-danger">Projects could not load. Refresh to try again.</p>}
      {projects && projects.length === 0 && <EmptyState icon={<FolderOpen size={26} aria-hidden />} title={q || mode ? "No matching projects" : "Your next lesson starts here"}>{q || mode ? "Try another search or filter." : org.role === "viewer" ? "This workspace has no projects yet." : "Name a project above and choose Recording → Reels or Prompt → Edit."}</EmptyState>}
      {!!projects?.length && <ProjectGrid projects={projects} />}
    </div>
  );
}
