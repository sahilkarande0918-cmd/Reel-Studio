"use client";

import { UploadCloud, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useBackend } from "@/lib/backend";
import { dismiss, resume, setUploadBase, useUploads } from "@/lib/uploads";

const mb = (n: number) => (n >= 1024 ** 3 ? `${(n / 1024 ** 3).toFixed(2)} GB` : `${(n / 1024 ** 2).toFixed(1)} MB`);

/** Top-bar upload status on every page: uploads keep running while you move around the app, and uploads interrupted
 * by a refresh are offered again here (see lib/uploads.ts). Hidden when nothing is uploading. */
export function UploadTray() {
  const backend = useBackend();
  const url = backend.data?.state === "online" ? backend.data.url : "";
  useEffect(() => { setUploadBase(url); }, [url]);
  const list = useUploads();
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState<Record<string, string>>({});
  const picker = useRef<HTMLInputElement>(null);
  const pickFor = useRef<string | null>(null);
  if (!list.length) return null;

  const running = list.filter((u) => u.status === "uploading" || u.status === "queued" || u.status === "validating");
  const waiting = list.filter((u) => u.status === "paused" || u.status === "error");
  const sent = running.reduce((n, u) => n + u.sent, 0), total = running.reduce((n, u) => n + u.size, 0);
  const label = running.length ? `Uploading ${running.length} · ${total ? Math.floor((sent / total) * 100) : 0}%`
    : waiting.length ? `${waiting.length} upload${waiting.length === 1 ? "" : "s"} paused` : "Uploads done";

  async function go(key: string, file?: File) {
    const m = await resume(key, file);
    setMsg((x) => ({ ...x, [key]: m ?? "" }));
    if (m && !file) { pickFor.current = key; picker.current?.click(); }
  }

  return (
    <div className="relative">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open}
        className={`inline-flex items-center gap-2 whitespace-nowrap rounded-full border px-3 py-1.5 text-[12px] font-medium ${waiting.length && !running.length ? "border-accent text-accent" : "border-line text-muted"} bg-surface`}>
        <UploadCloud size={13} aria-hidden /> <span className="hidden sm:inline">{label}</span>
      </button>
      <input ref={picker} type="file" className="sr-only" onChange={(e) => {
        const f = e.target.files?.[0];
        if (f && pickFor.current) void go(pickFor.current, f);
        e.target.value = "";
      }} />
      {open && (
        <div className="absolute right-0 z-50 mt-2 w-[340px] space-y-3 rounded-xl border border-line bg-surface p-4 text-[12px] shadow-xl">
          <p className="text-muted">Uploads continue while you switch sections. Refreshing or closing the tab pauses them; resume here.</p>
          {list.map((u) => (
            <div key={u.key} className="space-y-1">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-medium">{u.name}</span>
                {(u.status === "paused" || u.status === "error") && (
                  <span className="flex shrink-0 gap-2">
                    <button type="button" className="font-semibold text-accent hover:underline" onClick={() => go(u.key)}>Resume</button>
                    <button type="button" aria-label={`Forget ${u.name}`} className="text-muted hover:text-ink" onClick={() => dismiss(u.key)}><X size={13} /></button>
                  </span>
                )}
              </div>
              <progress className="h-1.5 w-full accent-[var(--accent)]" value={u.sent} max={u.size || 1} />
              <p className={u.status === "error" ? "text-danger" : "text-muted"}>
                {u.status === "done" ? (u.duplicate ? "Already in the project (duplicate skipped)" : "Uploaded — processing on the engine")
                  : u.status === "validating" ? "Checking the file…"
                  : u.status === "paused" ? `Paused at ${mb(u.sent)} of ${mb(u.size)}`
                  : u.status === "error" ? u.error
                  : `${mb(u.sent)} of ${mb(u.size)}${u.status === "queued" ? " · waiting" : ""}`}
              </p>
              {msg[u.key] && <p className="text-accent">{msg[u.key]}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
