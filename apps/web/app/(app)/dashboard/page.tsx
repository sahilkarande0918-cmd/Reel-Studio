import { requireOrg } from "@/lib/supabase/server";
import {
  DashboardView,
  type ProjectCardItem,
  type ProcessingJobItem,
} from "@/components/dashboard/dashboard-view";

const JOB_LABEL: Record<string, string> = {
  transcribe: "Transcription",
  analyze: "Highlight analysis",
  render: "Video rendering",
  generate: "AI topic video",
  publish: "Instagram publishing",
  insights: "Analytics sync",
};

function ago(iso: string) {
  const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  if (m < 1440) return `${Math.round(m / 60)}h ago`;
  return `${Math.round(m / 1440)}d ago`;
}

const SAMPLE_IMAGES = [
  "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&q=80",
  "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=400&q=80",
  "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&q=80",
  "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&q=80",
  "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=400&q=80",
];

export default async function DashboardPage() {
  const { supabase, org } = await requireOrg();

  const [projectsRes, activityRes] = await Promise.all([
    supabase
      .from("projects")
      .select("id, name, mode, status, updated_at")
      .eq("organization_id", org.id)
      .order("updated_at", { ascending: false })
      .limit(5),
    supabase
      .from("jobs")
      .select(
        "id, project_id, job_type, status, current_stage, progress, created_at, projects(name)"
      )
      .eq("organization_id", org.id)
      .order("created_at", { ascending: false })
      .limit(5),
  ]);

  const rawProjects = projectsRes.data || [];
  const rawActivity = activityRes.data || [];

  const projects: ProjectCardItem[] | undefined =
    rawProjects.length > 0
      ? rawProjects.map((p, idx) => ({
          id: p.id,
          title: p.name,
          duration: "0:30",
          timeAgo: `Edited ${ago(p.updated_at)}`,
          bgImage: SAMPLE_IMAGES[idx % SAMPLE_IMAGES.length],
        }))
      : undefined;

  const jobs: ProcessingJobItem[] | undefined =
    rawActivity.length > 0
      ? rawActivity.map((job, idx) => {
          const isComplete = job.status === "succeeded";
          const isRunning = job.status === "running";
          const isQueued = job.status === "queued";
          const pct = Math.round((job.progress || 0) * 100);
          const name =
            (job.projects as unknown as { name: string } | null)?.name ||
            JOB_LABEL[job.job_type] ||
            "Video project";
          return {
            id: job.id,
            title: name,
            desc: isComplete
              ? "Completed • Ready to download."
              : isRunning
              ? `${job.current_stage || "Processing"}...`
              : "Queued for processing.",
            progress: isComplete ? 100 : pct,
            status: job.status,
            timeRemaining: isComplete
              ? `Completed ${ago(job.created_at)}`
              : isQueued
              ? "In queue"
              : `${Math.max(1, 100 - pct)}% left`,
            action: isComplete ? "Download" : isRunning ? "Cancel" : "View",
            img: SAMPLE_IMAGES[idx % SAMPLE_IMAGES.length],
            projectId: job.project_id,
          };
        })
      : undefined;

  return <DashboardView projects={projects} jobs={jobs} />;
}
