"use client";

import { Link2, UploadCloud } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { apiFetch, useBackend } from "@/lib/backend";
import { useProjectJobs } from "@/lib/realtime";
import { dropHandles, enqueue, onUploadDone, useUploads } from "@/lib/uploads";

const ACCEPT = [".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"];
const MAX_BYTES = 4 * 1024 ** 3;
type State =
  | { phase: "idle" }
  | { phase: "uploading"; name: string; sent: number; total: number; rate: number }
  | { phase: "validating"; name: string }
  | { phase: "error"; message: string };

function fmtBytes(n: number) {
  return n >= 1024 ** 3 ? `${(n / 1024 ** 3).toFixed(2)} GB` : `${(n / 1024 ** 2).toFixed(1)} MB`;
}

export function Uploader({ projectId, onDone }: { projectId: string; onDone: () => void }) {
  const backend = useBackend();
  const [state, setState] = useState<State>({ phase: "idle" });
  const [drag, setDrag] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const online = backend.data?.state === "online";

  // the upload itself runs in the app-wide manager (lib/uploads.ts): it continues while you switch sections
  const mine = useUploads().find((u) => u.kind === "recording" && u.projectId === projectId && u.status !== "done");
  useEffect(() => onUploadDone((u) => { if (u.kind === "recording" && u.projectId === projectId) onDone(); }), [projectId, onDone]);
  // what the drop zone shows: the live upload when there is one, else a local validation message
  const view: State = !mine ? state
    : mine.status === "validating" ? { phase: "validating", name: mine.name }
    : mine.status === "error" ? { phase: "error", message: mine.error ?? "Upload failed" }
    : mine.status === "paused" ? { phase: "error", message: `Upload of ${mine.name} paused at ${fmtBytes(mine.sent)}. Resume it from the upload button at the top, or drop the same file again.` }
    : { phase: "uploading", name: mine.name, sent: mine.sent, total: mine.size, rate: 0 };

  // paste a YouTube link: the engine downloads it itself (no download + upload round trip through this browser)
  const [link, setLink] = useState("");
  const [rights, setRights] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);
  const jobs = useProjectJobs(projectId);
  const importJob = jobs.data?.find((j) => j.job_type === "import_url");
  const importing = importJob && (importJob.status === "queued" || importJob.status === "running");
  async function importLink() {
    setLinkError(null);
    if (!rights) return setLinkError("Confirm that you own this video or have permission to clip it.");
    const r = await apiFetch(backend.data?.state === "online" ? backend.data.url : "", "/recordings/import", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId, url: link.trim(), rights_confirmed: rights }),
    }).catch(() => null);
    if (!r?.ok) {
      const d = r ? (await r.json().catch(() => ({}))).detail : null;
      return setLinkError(typeof d === "string" ? d : "The engine could not start the import.");
    }
    setLink("");
    jobs.refetch();
  }

  function upload(file: File, handle?: Parameters<typeof enqueue>[3]) {
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!ACCEPT.includes(ext)) return setState({ phase: "error", message: `Unsupported type ${ext}. Use ${ACCEPT.join(", ")}.` });
    if (file.size > MAX_BYTES) return setState({ phase: "error", message: "Files up to 4 GB are supported." });
    setState({ phase: "idle" });
    enqueue("recording", projectId, file, handle);
  }

  const busy = view.phase === "uploading" || view.phase === "validating";
  return (
    <div className="space-y-3">
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          const f = e.dataTransfer.files[0];
          const handles = dropHandles(e); // must be read inside the drop event
          if (f && online && !busy) void handles.then((h) => upload(f, h[0]));
        }}
        className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-[6px] px-6 py-14 text-center transition-colors ${
          drag ? "bg-surface-3" : "bg-surface hover:bg-surface-2"
        } ${!online || busy ? "pointer-events-none opacity-60" : ""}`}
      >
        <UploadCloud size={28} aria-hidden className="text-muted" />
        <span className="text-[16px]">Drop a class recording here, or choose a file</span>
        <span className="text-[13px] text-muted">MP4, MOV, MKV, WebM, AVI · up to 4 GB and 4 hours · stays on the processing machine</span>
        <input
          ref={input}
          type="file"
          accept={ACCEPT.join(",") + ",video/*"}
          className="sr-only"
          disabled={!online || busy}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) upload(f);
            e.target.value = "";
          }}
        />
      </label>
      <div className="space-y-2 rounded-[6px] bg-surface p-4">
        <p className="flex items-center gap-2 text-[14px]"><Link2 size={15} aria-hidden /> Or paste a YouTube link</p>
        <div className="flex flex-wrap gap-2">
          <input type="url" value={link} onChange={(e) => setLink(e.target.value)} placeholder="https://www.youtube.com/watch?v=…"
            disabled={!online || busy || !!importing} aria-label="YouTube link"
            className="min-w-[240px] flex-1 rounded-[4px] bg-surface-2 px-3 py-2 text-[14px] text-ink outline-none focus-visible:ring-2 focus-visible:ring-accent" />
          <button type="button" onClick={importLink} disabled={!online || busy || !!importing || !link.trim()}
            className="rounded-[4px] bg-accent px-4 py-2 text-[13px] font-semibold text-accent-ink hover:brightness-110 disabled:opacity-50">
            {importing ? "Importing…" : "Import"}
          </button>
        </div>
        <label className="flex items-start gap-2 text-[12px] text-muted">
          <input type="checkbox" checked={rights} onChange={(e) => setRights(e.target.checked)} className="mt-0.5" />
          I own this video or have permission to clip and repost it.
        </label>
        <p className="text-[12px] text-muted">The processing computer downloads it directly (up to 1080p, 4 hours), then transcription and clip finding start automatically. You can leave this page meanwhile.</p>
        {importing && (
          <div className="space-y-1" aria-live="polite">
            <p className="text-[13px] text-muted">{importJob.status === "queued" ? "Waiting for the engine…" : importJob.current_stage === "validate" ? "Checking the video…" : `Downloading on the engine · ${Math.round((importJob.progress ?? 0) * 100)}%`}</p>
            <progress className="h-2 w-full accent-[var(--accent)]" value={importJob.progress ?? 0} max={1} />
          </div>
        )}
        {importJob?.status === "failed" && <p role="alert" className="text-[13px] text-danger">Import failed: {importJob.error}</p>}
        {linkError && <p role="alert" className="text-[13px] text-danger">{linkError}</p>}
      </div>
      {!online && !backend.isLoading && (
        <p className="text-[14px] text-danger">
          Uploads go straight to the processing backend, which is offline right now.
          {backend.data?.state === "offline" && ` ${backend.data.reason}`}
        </p>
      )}
      {view.phase === "uploading" && (
        <div className="space-y-1.5" aria-live="polite">
          <div className="flex justify-between text-[13px]">
            <span className="truncate">{view.name}</span>
            <span className="tabular-nums text-muted">
              {fmtBytes(view.sent)} / {fmtBytes(view.total)}
              {" · continues if you switch sections"}
            </span>
          </div>
          <progress className="h-2 w-full accent-[var(--accent)]" value={view.sent} max={view.total} />
        </div>
      )}
      {view.phase === "validating" && <p className="text-[14px] text-muted">Checking the file with FFprobe…</p>}
      {view.phase === "error" && (
        <p role="alert" className="text-[14px] text-danger">
          {view.message}
        </p>
      )}
    </div>
  );
}
