"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { createClient } from "@/lib/supabase/client";

export type Job = {
  id: string;
  job_type: string;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  progress: number;
  current_stage: string | null;
  error: string | null;
  attempts: number;
  result: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

/** Latest jobs of a project, kept live through Supabase Realtime (RLS limits rows to members). */
export function useProjectJobs(projectId: string) {
  const qc = useQueryClient();
  const key = ["jobs", projectId];
  useEffect(() => {
    const sb = createClient();
    const ch = sb
      .channel(`jobs:${projectId}:${crypto.randomUUID()}`) // one channel per hook use: a second .on() on a subscribed channel throws
      .on("postgres_changes", { event: "*", schema: "public", table: "jobs", filter: `project_id=eq.${projectId}` }, () =>
        qc.invalidateQueries({ queryKey: key }),
      )
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "source_recordings", filter: `project_id=eq.${projectId}` },
        () => qc.invalidateQueries({ queryKey: ["recording", projectId] }),
      )
      .subscribe();
    return () => {
      sb.removeChannel(ch);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);
  return useQuery({
    queryKey: key,
    queryFn: async () => {
      const { data, error } = await createClient()
        .from("jobs")
        .select("id, job_type, status, progress, current_stage, error, attempts, result, created_at, updated_at")
        .eq("project_id", projectId)
        .neq("job_type", "render") // render progress lives with its highlight (components/studio/renders.tsx)
        .order("created_at", { ascending: false })
        .limit(5);
      if (error) throw error;
      return data as Job[];
    },
    refetchInterval: (q) => (q.state.data?.some((j) => j.status === "running" || j.status === "queued") ? 5000 : false),
  });
}
