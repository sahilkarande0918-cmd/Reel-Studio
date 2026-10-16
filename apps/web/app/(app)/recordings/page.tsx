import { Mic } from "lucide-react";
import { EmptyState, PageHeader } from "@/components/app/page-header";
import { ProjectGrid } from "@/components/app/project-grid";
import { requireOrg } from "@/lib/supabase/server";
import { NewProjectForm } from "../projects/new-project-form";

const STEPS = ["Upload a class recording", "Hinglish transcript with corrected technical terms", "Ranked 30–60 s highlights", "Edit, brand and export 9:16 reels"];

export default async function RecordingsPage() {
  const { supabase, org } = await requireOrg();
  const { data, error } = await supabase.from("projects").select("id, name, mode, status, updated_at").eq("organization_id", org.id).eq("mode", "recording").order("updated_at", { ascending: false });
  return (
    <div className="space-y-7">
      <PageHeader eyebrow="Recording → Reels" title="Recordings">Upload a programming class and Reel Studio finds the moments worth sharing.</PageHeader>
      <ol className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{STEPS.map((s, i) => <li key={s} className="flex items-center gap-3 rounded-xl border border-line bg-surface px-4 py-3 text-[13px]"><span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-accent/12 text-[11px] font-semibold text-accent ring-1 ring-accent/25">{i + 1}</span>{s}</li>)}</ol>
      {org.role !== "viewer" && <NewProjectForm mode="recording" fixedMode />}
      {error && <p role="alert" className="text-danger">Recordings could not load. Refresh to try again.</p>}
      {data && (data.length ? <ProjectGrid projects={data} /> : <EmptyState icon={<Mic size={26} aria-hidden />} title="No recordings yet">Name a project above, then upload an MP4, MOV, MKV or WebM class recording.</EmptyState>)}
    </div>
  );
}
