import Link from "next/link";
import { ArrowRight, CalendarClock, CheckCircle2, Code2, Film, FolderOpen, Mic, Send, Workflow } from "lucide-react";
import { EmptyState, PageHeader } from "@/components/app/page-header";
import { ProjectGrid } from "@/components/app/project-grid";
import { requireOrg } from "@/lib/supabase/server";

const JOB_LABEL: Record<string, string> = { transcribe: "Transcription", analyze: "Highlight analysis", render: "Render", generate: "Topic video", publish: "Instagram post", insights: "Analytics sync" };

function ago(iso: string) {
  const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m} min ago`;
  if (m < 1440) return `${Math.round(m / 60)} h ago`;
  return new Date(iso).toLocaleDateString("en", { month: "short", day: "numeric" });
}

export default async function DashboardPage() {
  const { supabase, org } = await requireOrg();
  const q = (t: string) => supabase.from(t).select("id", { count: "exact", head: true }).eq("organization_id", org.id);
  const [projects, videos, ready, published, active, activity, upcoming] = await Promise.all([
    supabase.from("projects").select("id, name, mode, status, updated_at").eq("organization_id", org.id).order("updated_at", { ascending: false }).limit(6),
    q("render_jobs"),
    q("render_jobs").eq("status", "ready"),
    q("publish_jobs").eq("status", "published"),
    q("jobs").in("status", ["queued", "running"]),
    supabase.from("jobs").select("id, project_id, job_type, status, current_stage, progress, created_at, projects(name)").eq("organization_id", org.id).order("created_at", { ascending: false }).limit(7),
    supabase.from("publish_jobs").select("id, caption, scheduled_at, status, projects(name)").eq("organization_id", org.id).in("status", ["scheduled", "processing", "publishing"]).order("scheduled_at").limit(4),
  ]);
  const stats = [
    { label: "Videos created", result: videos, icon: Film, hint: "All renders" },
    { label: "Completed renders", result: ready, icon: CheckCircle2, hint: "Ready to download" },
    { label: "Published posts", result: published, icon: Send, hint: "On Instagram" },
    { label: "Processing now", result: active, icon: Workflow, hint: "Queued or running" },
  ];
  const canEdit = org.role !== "viewer";
  return (
    <div className="space-y-8">
      <PageHeader eyebrow={org.name} title="Dashboard">Turn class recordings and topics into reels, then share them on Instagram.</PageHeader>

      <div className="grid gap-4 md:grid-cols-2">
        {[
          { href: "/recordings", icon: Mic, cta: "Upload recording", title: "Recording → Reels", body: "Upload a class. We transcribe the Hinglish, find the best 30–60 s moments and frame them for phones." },
          { href: "/topics", icon: Code2, cta: "Create from topic", title: "Topic → Video", body: "Type a topic like “JSON vs XML”. Get a narrated 45 s explainer with animated code and captions." },
        ].map(({ href, icon: Icon, cta, title, body }) => <Link key={href} href={href} className="studio-panel group relative flex items-start gap-5 overflow-hidden p-6 transition-[border-color,transform] duration-200 hover:-translate-y-0.5 hover:border-accent/60">
          <span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-accent/12 text-accent ring-1 ring-accent/25"><Icon size={22} strokeWidth={1.8} aria-hidden /></span>
          <span className="min-w-0"><h2 className="text-[19px] font-semibold tracking-[-.02em]">{title}</h2>
          <p className="mt-1.5 max-w-[50ch] text-[13.5px] leading-6 text-muted">{body}</p>
          <span className="mt-4 inline-flex items-center gap-2 text-[13px] font-semibold text-accent">{canEdit ? cta : "Open"} <ArrowRight size={15} className="transition-transform group-hover:translate-x-1" aria-hidden /></span></span>
        </Link>)}
      </div>

      <dl className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {stats.map(({ label, result, icon: Icon, hint }) => <div key={label} className="studio-panel p-5">
          <div className="flex items-center justify-between"><dt className="text-[12.5px] font-semibold text-muted">{label}</dt><Icon size={18} className="text-accent" strokeWidth={1.7} aria-hidden /></div>
          <dd className="mt-3 text-[34px] font-semibold leading-none tracking-[-.04em] tabular-nums">{result.error ? "—" : result.count ?? 0}</dd>
          <p className={`mt-2 text-[11.5px] ${result.error ? "text-danger" : "text-muted"}`}>{result.error ? "Could not load" : hint}</p>
        </div>)}
      </dl>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <section className="min-w-0">
          <div className="mb-4 flex items-center justify-between gap-3"><h2 className="text-[17px] font-semibold tracking-[-.02em]">Recent projects</h2><Link href="/projects" className="flex items-center gap-1 text-[12.5px] font-semibold text-muted hover:text-accent">All projects <ArrowRight size={14} aria-hidden /></Link></div>
          {projects.error ? <p role="alert" className="studio-panel p-6 text-[14px] text-danger">Projects could not load. Refresh to try again.</p>
            : projects.data?.length ? <ProjectGrid projects={projects.data} />
            : <EmptyState icon={<FolderOpen size={26} aria-hidden />} title="No projects yet" action={canEdit && <Link href="/projects#new-project" className="studio-button">Create your first project</Link>}>Start with a class recording or a topic. Scripts, clips and finished videos stay together in each project.</EmptyState>}
        </section>

        <aside className="space-y-6">
          <section className="studio-panel p-5">
            <div className="flex items-center justify-between"><h2 className="text-[15px] font-semibold">Upcoming posts</h2><Link href="/publishing" className="text-[12px] font-semibold text-muted hover:text-accent">Publish</Link></div>
            {upcoming.error ? <p className="mt-4 text-[13px] text-danger">Could not load the schedule.</p>
              : !upcoming.data?.length ? <p className="mt-4 flex gap-3 text-[13px] leading-6 text-muted"><CalendarClock size={18} className="mt-0.5 shrink-0 text-accent" aria-hidden />Nothing scheduled. Pick a finished reel on the Publish page to schedule it for Instagram.</p>
              : <ul className="mt-3 divide-y divide-line">{upcoming.data.map((p) => <li key={p.id} className="py-3">
                <p className="truncate text-[13px] font-semibold">{(p.projects as unknown as { name: string } | null)?.name ?? "Reel"}</p>
                <p className="mt-0.5 text-[12px] text-muted">{new Date(p.scheduled_at).toLocaleString("en", { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })} · {p.status}</p>
              </li>)}</ul>}
          </section>
          <section className="studio-panel p-5">
            <h2 className="text-[15px] font-semibold">Recent activity</h2>
            {activity.error ? <p role="alert" className="mt-4 text-[13px] text-danger">Activity could not load.</p>
              : !activity.data?.length ? <p className="mt-4 text-[13px] leading-6 text-muted">No processing yet. Upload a recording or generate a topic video to see progress here.</p>
              : <ol className="mt-3 space-y-1">{activity.data.map((job) => {
                const live = ["queued", "running"].includes(job.status);
                const href = job.job_type === "insights" ? "/analytics" : job.job_type === "publish" ? "/publishing" : job.project_id ? `/projects/${job.project_id}` : "/projects";
                return <li key={job.id}><Link href={href} className="-mx-2 flex gap-3 rounded-lg px-2 py-2.5 hover:bg-surface-2">
                  <span aria-hidden className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${job.status === "failed" ? "bg-danger" : live ? "animate-pulse bg-signal" : job.status === "succeeded" ? "bg-success" : "bg-line"}`} />
                  <span className="min-w-0 flex-1">
                    <span className="flex justify-between gap-2 text-[13px] font-semibold"><span className="truncate">{JOB_LABEL[job.job_type] ?? job.job_type}</span><span className="shrink-0 text-[11px] font-normal text-muted">{ago(job.created_at)}</span></span>
                    <span className="block truncate text-[12px] text-muted">{(job.projects as unknown as { name: string } | null)?.name ?? "Workspace"} · {job.status === "failed" ? "failed" : live ? `${Math.round(job.progress * 100)}%` : job.status}</span>
                  </span>
                </Link></li>;
              })}</ol>}
          </section>
        </aside>
      </div>
    </div>
  );
}
