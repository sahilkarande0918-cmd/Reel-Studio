"use client";

import { createClient } from "@/lib/supabase/client";
import type { Job } from "@/lib/realtime";
import { apiFetch, useBackend } from "@/lib/backend";

const STAGES: Record<string, string> = {
  queued: "Waiting for the processing machine",
  extract_audio: "Extracting and normalising audio",
  transcribe: "Transcribing speech on the local GPU",
  correct_terms: "Correcting technical vocabulary",
  save: "Saving transcript",
  screen_activity: "Measuring on-screen activity",
  ocr: "Reading code on screen (local OCR)",
  screen_terms: "Correcting terms visible on screen",
  outline: "Mapping the class into teaching steps (local LLM)",
  highlights: "Scoring complete explanations",
  llm_judge: "Local LLM checks each highlight stands on its own",
  reframe: "Planning code-aware 9:16 framing",
  done: "Done",
  cancelled: "Cancelled",
};

export function JobProgress({ job, recordingId, onChange }: { job: Job; recordingId: string; onChange: () => void }) {
  const backend = useBackend();
  const active = job.status === "queued" || job.status === "running";
  const pct = Math.round(job.progress * 100);

  async function cancel() {
    const { error } = await createClient().rpc("cancel_job", { job: job.id });
    if (error) alert(error.message);
    onChange();
  }
  async function retry() {
    if (backend.data?.state !== "online") return alert("The processing backend is offline.");
    const r = await apiFetch(backend.data.url, `/recordings/${recordingId}/${job.job_type === "analyze" ? "analyze" : "transcribe"}`, { method: "POST" });
    if (!r.ok) alert((await r.json()).detail ?? "Retry failed");
    onChange();
  }

  return (
    <div className="space-y-2 rounded-[6px] bg-surface p-4" aria-live="polite">
      <div className="flex items-baseline justify-between gap-4 text-[14px]">
        <span>
          {job.status === "failed" ? `${job.job_type === "analyze" ? "Analysis" : "Transcription"} failed` : (STAGES[job.current_stage ?? ""] ?? job.current_stage)}
          {job.status === "queued" && job.attempts > 0 && ` (retry ${job.attempts})`}
        </span>
        <span className="tabular-nums text-muted">{active ? `${pct}%` : job.status}</span>
      </div>
      {active && <progress className="h-2 w-full accent-[var(--accent)]" value={job.progress} max={1} />}
      {job.error && <p className="text-[13px] text-danger">{job.error}</p>}
      {job.status === "succeeded" && job.result && job.job_type === "transcribe" && (
        <p className="text-[13px] text-muted">
          {String(job.result.words)} words · {String(job.result.corrections)} technical terms corrected · transcribed in{" "}
          {String(job.result.processing_s)} s ({String(job.result.realtime_factor)}× real time on {String(job.result.device)})
        </p>
      )}
      <div className="flex gap-4 text-[13px]">
        {active && (
          <button type="button" onClick={cancel} className="text-muted hover:text-danger">
            Cancel
          </button>
        )}
        {(job.status === "failed" || job.status === "cancelled") && (
          <button type="button" onClick={retry} className="text-ink hover:text-accent">
            Retry {job.job_type === "analyze" ? "analysis" : "transcription"}
          </button>
        )}
      </div>
    </div>
  );
}
