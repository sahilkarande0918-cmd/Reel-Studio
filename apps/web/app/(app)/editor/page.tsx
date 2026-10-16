import Link from "next/link";
import { Clapperboard, PencilLine } from "lucide-react";
import { EmptyState, PageHeader } from "@/components/app/page-header";
import { RenderThumb } from "@/components/editor/render-thumb";
import { requireOrg } from "@/lib/supabase/server";

export default async function EditorIndex() {
  const { supabase, org } = await requireOrg();
  const [{ data: renders, error }, { data: drafts }] = await Promise.all([
    supabase.from("render_jobs").select("id, project_id, duration_s, created_at, parent_render_id, projects(name, mode)").eq("organization_id", org.id).eq("status", "ready").order("created_at", { ascending: false }).limit(48),
    supabase.from("timeline_drafts").select("base_render_id, updated_at").eq("organization_id", org.id),
  ]);
  const drafted = new Map((drafts ?? []).map((d) => [d.base_render_id, d.updated_at]));
  return <div className="space-y-7">
    <PageHeader eyebrow="Creative editor" title="Editor">Open any finished video to trim, split, re-caption, add text and code, change the style, then render a new MP4.</PageHeader>
    {error && <p role="alert" className="text-danger">Videos could not load. Refresh to try again.</p>}
    {renders && !renders.length && <EmptyState icon={<Clapperboard size={26} aria-hidden />} title="Nothing to edit yet" action={<Link href="/dashboard" className="studio-button">Create a video</Link>}>Render a highlight from a recording or generate a topic video, then open it here.</EmptyState>}
    {!!renders?.length && <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
      {renders.map((r) => { const p = r.projects as unknown as { name: string; mode: string } | null; const d = drafted.get(r.id); return <Link key={r.id} href={`/editor/${r.id}`} className="group overflow-hidden rounded-xl border border-line bg-surface transition-colors hover:border-accent/60">
        <RenderThumb renderId={r.id} />
        <div className="p-3">
          <p className="truncate text-[13px] font-semibold group-hover:text-accent">{p?.name ?? "Video"}</p>
          <p className="mt-0.5 text-[11px] text-muted">{r.duration_s?.toFixed(0)} s · {r.parent_render_id ? "edited" : p?.mode === "topic" ? "topic video" : "reel"} · {new Date(r.created_at).toLocaleDateString("en", { month: "short", day: "numeric" })}</p>
          {d && <p className="mt-1.5 flex items-center gap-1 text-[11px] text-accent"><PencilLine size={12} aria-hidden />Draft saved</p>}
        </div>
      </Link>; })}
    </div>}
  </div>;
}
