"use client";

import { UploadCloud } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useBackend } from "@/lib/backend";
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
