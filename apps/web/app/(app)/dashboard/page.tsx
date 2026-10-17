import { DashboardView, type DashboardJob, type DashboardMetric, type DashboardProject, type DashboardReel } from "@/components/dashboard/dashboard-view";
import { requireOrg } from "@/lib/supabase/server";

export default async function DashboardPage() {
  const { supabase, org } = await requireOrg();
  const [projects, jobs, active, ready, published, renderRows, metricsRows] = await Promise.all([
    supabase.from("projects").select("id,name,mode,status,updated_at").eq("organization_id", org.id).order("updated_at", { ascending: false }).limit(5),
    supabase.from("jobs").select("id,project_id,job_type,status,current_stage,progress,projects(name)").eq("organization_id", org.id).order("created_at", { ascending: false }).limit(5),
    supabase.from("jobs").select("id", { count: "exact", head: true }).eq("organization_id", org.id).in("status", ["running", "queued"]),
    supabase.from("render_jobs").select("id", { count: "exact", head: true }).eq("organization_id", org.id).eq("status", "ready"),
    supabase.from("publish_jobs").select("id", { count: "exact", head: true }).eq("organization_id", org.id).eq("status", "published"),
    supabase.from("render_jobs").select("project_id,duration_s").eq("organization_id", org.id).eq("status", "ready").order("created_at", { ascending: false }).limit(100),
    supabase.from("platform_metrics").select("metrics,media,updated_at").eq("organization_id", org.id).order("updated_at", { ascending: false }).limit(1),
  ]);
  const durations = new Map<string, number>();
  for (const render of renderRows.data ?? []) if (render.project_id && typeof render.duration_s === "number" && !durations.has(render.project_id)) durations.set(render.project_id, render.duration_s);
  const recentProjects: DashboardProject[] = (projects.data ?? []).map((project) => ({ ...project, duration_s: durations.get(project.id) ?? null }));
  const recentJobs: DashboardJob[] = (jobs.data ?? []).map((job) => ({ id: job.id, project_id: job.project_id, job_type: job.job_type, status: job.status, current_stage: job.current_stage, progress: job.progress ?? 0, project_name: (job.projects as unknown as { name: string } | null)?.name ?? null }));
  const latest = metricsRows.data?.[0];
  const metrics = (Array.isArray(latest?.metrics) ? latest.metrics : []) as DashboardMetric[];
  const media = (Array.isArray(latest?.media) ? latest.media : []) as DashboardReel[];
  const reels = media.filter((item) => item.media_product_type === "REELS");
  const topReel = reels.filter((reel) => reel.insights && typeof reel.insights.views === "number").sort((a, b) => (b.insights.views ?? 0) - (a.insights.views ?? 0))[0] ?? reels[0] ?? null;
  return <DashboardView workspaceName={org.name} canEdit={org.role !== "viewer"} projects={recentProjects} jobs={recentJobs} activeCount={active.error ? null : active.count ?? 0} readyCount={ready.error ? null : ready.count ?? 0} publishedCount={published.error ? null : published.count ?? 0} metrics={metrics} metricsUpdatedAt={latest?.updated_at ?? null} topReel={topReel} loadError={Boolean(projects.error || jobs.error || active.error || ready.error || published.error || renderRows.error || metricsRows.error)} />;
}
