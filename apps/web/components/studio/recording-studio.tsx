"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { useProjectJobs } from "@/lib/realtime";
import { JobProgress } from "./job-progress";
import { Highlights } from "./highlights";
import { TranscriptView, loadWords } from "./transcript-view";
import { Uploader } from "./uploader";

type Recording = {
  id: string;
  filename: string;
  status: string;
  size_bytes: number;
  duration_s: number | null;
  width: number | null;
  height: number | null;
  fps: number | null;
  video_codec: string | null;
  audio_codec: string | null;
  error: string | null;
};

export function RecordingStudio({ projectId, canEdit }: { projectId: string; canEdit: boolean }) {
  const qc = useQueryClient();
  const jobs = useProjectJobs(projectId);
  const recording = useQuery({
    queryKey: ["recording", projectId],
    queryFn: async () => {
      const sb = createClient();
      const { data: recs, error } = await sb
        .from("source_recordings")
        .select("id, filename, status, size_bytes, duration_s, width, height, fps, video_codec, audio_codec, error")
        .eq("project_id", projectId)
        .neq("status", "uploading")
        .order("created_at", { ascending: false })
        .limit(10);
      if (error) throw error;
      // Newest usable recording wins; a failed upload only shows when nothing usable exists.
      const rec = recs.find((r) => r.status !== "failed") ?? recs[0];
      if (!rec) return null;
      const { data: tr } = await sb
        .from("transcripts")
        .select("id, model, language, processing_s, duration_s")
        .eq("recording_id", rec.id)
        .order("created_at", { ascending: false })
        .limit(1)
        .maybeSingle();
      return { rec: rec as Recording, transcript: tr };
    },
  });
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["recording", projectId] });
    qc.invalidateQueries({ queryKey: ["jobs", projectId] });
  };

  const progress = useQuery({
    queryKey: ["recording-progress", projectId],
    queryFn: async () => {
      const sb = createClient();
      const [h, r] = await Promise.all([
        sb.from("highlight_candidates").select("id", { count: "exact", head: true }).eq("project_id", projectId).eq("status", "selected"),
        sb.from("render_jobs").select("id").eq("project_id", projectId).eq("status", "ready").order("created_at", { ascending: false }).limit(1).maybeSingle(),
      ]);
      return { selected: (h.count ?? 0) > 0, renderId: r.data?.id as string | undefined };
    },
    refetchInterval: 10000,
  });
  const latestJob = jobs.data?.[0];
  const rec = recording.data?.rec;
  const tr = recording.data?.transcript;
  const words = useQuery({ queryKey: ["words", tr?.id], enabled: !!tr, queryFn: () => loadWords(tr!.id) });

  if (recording.isLoading) return <p className="text-muted">Loading…</p>;
  if (recording.error) return <p role="alert" className="text-danger">Could not load the recording: {recording.error.message}</p>;

  return (
    <div className="space-y-6">
      <ol aria-label="Recording workflow" className="studio-panel grid grid-cols-3 gap-3 p-4 text-[12px] md:grid-cols-6">
        {[
          ["Upload", !!rec && rec.status !== "failed", null],
          ["Analyze", !!tr && jobs.data?.some((j) => j.job_type === "analyze" && j.status === "succeeded"), null],
          ["Select", !!progress.data?.selected, null],
          ["Edit", !!progress.data?.renderId, progress.data?.renderId ? `/editor/${progress.data.renderId}` : null],
          ["Export", !!progress.data?.renderId, null],
          ["Publish", false, progress.data?.renderId ? "/publishing" : null],
        ].map(([label, done, href], i) => {
          const body = <><span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-[11px] font-semibold ${done ? "bg-accent text-accent-ink" : "bg-surface-2 text-muted"}`}>{i + 1}</span><span className={done ? "font-semibold" : "text-muted"}>{label as string}</span></>;
          return <li key={String(label)}>{href ? <Link href={href as string} className="flex items-center gap-2.5 rounded-lg hover:text-accent">{body}</Link> : <span className="flex items-center gap-2.5">{body}</span>}</li>;
        })}
      </ol>
      {(!rec || rec.status === "failed") && canEdit && (
        <>
          {rec?.status === "failed" && <p className="text-[14px] text-danger">Last upload failed: {rec.error}</p>}
          <Uploader projectId={projectId} onDone={refresh} />
        </>
      )}
      {!rec && !canEdit && <p className="text-muted">No recording uploaded yet.</p>}
      {rec && (
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-[13px] text-muted">
          <div><dt className="inline">File </dt><dd className="inline text-ink">{rec.filename}</dd></div>
          {rec.duration_s && <div><dt className="inline">Duration </dt><dd className="inline tabular-nums text-ink">{Math.floor(rec.duration_s / 60)} min {Math.round(rec.duration_s % 60)} s</dd></div>}
          {rec.width && <div><dt className="inline">Video </dt><dd className="inline tabular-nums text-ink">{rec.width}×{rec.height} · {rec.fps} fps · {rec.video_codec}</dd></div>}
          <div><dt className="inline">Audio </dt><dd className="inline text-ink">{rec.audio_codec}</dd></div>
          <div><dt className="inline">Size </dt><dd className="inline tabular-nums text-ink">{(rec.size_bytes / 1024 ** 2).toFixed(1)} MB</dd></div>
          {tr && <div><dt className="inline">Transcript </dt><dd className="inline text-ink">{tr.model} · language {tr.language}</dd></div>}
        </dl>
      )}
      {rec && latestJob && latestJob.status !== "succeeded" && (
        <JobProgress job={latestJob} recordingId={rec.id} onChange={refresh} />
      )}
      {rec && tr && <section className="studio-panel p-5"><div className="mb-5"><p className="studio-eyebrow mb-2">The source material</p><h2 className="text-[20px] font-semibold tracking-[-.03em]">Recording & transcript</h2></div><TranscriptView recordingId={rec.id} transcriptId={tr.id} canEdit={canEdit} /></section>}
      {rec && tr && rec.width && rec.height && <section className="studio-panel p-5"><div className="mb-5"><p className="studio-eyebrow mb-2">The moments that matter</p><h2 className="text-[20px] font-semibold tracking-[-.03em]">Highlights & exports</h2><p className="mt-1 text-[12px] text-muted">Review the suggested clips, adjust framing, then render a reel.</p></div><Highlights recordingId={rec.id} projectId={projectId} srcW={rec.width} srcH={rec.height} canEdit={canEdit} words={words.data ?? []} /></section>}
    </div>
  );
}
