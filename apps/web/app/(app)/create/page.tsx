import { Wand2 } from "lucide-react";
import { EmptyState, PageHeader } from "@/components/app/page-header";
import { ProjectGrid } from "@/components/app/project-grid";
import { requireOrg } from "@/lib/supabase/server";
import { NewProjectForm } from "../projects/new-project-form";

export default async function CreatePage() {
  const { supabase, org } = await requireOrg();
  const { data, error } = await supabase.from("projects").select("id, name, mode, status, updated_at").eq("organization_id", org.id).eq("mode", "edit").order("updated_at", { ascending: false });
  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Prompt → Edit" title="Create">Upload raw clips, add a song or a reference reel if you like, and describe the edit. An AI director plans it on the beat and renders a finished MP4 on your machine.</PageHeader>
      {org.role !== "viewer" && <NewProjectForm mode="edit" fixedMode />}
      <section>
        <h2 className="mb-4 text-[17px] font-semibold tracking-[-.02em]">Your edits</h2>
        {error && <p role="alert" className="text-danger">Projects could not load. Refresh to try again.</p>}
        {data && (data.length ? <ProjectGrid projects={data} /> : <EmptyState icon={<Wand2 size={26} aria-hidden />} title="No edits yet">Name a project above, then upload your clips.</EmptyState>)}
      </section>
    </div>
  );
}
