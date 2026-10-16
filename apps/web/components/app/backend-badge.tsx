"use client";

import { useBackend } from "@/lib/backend";

/** Compact status of the local GPU worker that does transcription, generation and rendering. */
export function BackendBadge() {
  const { data, isLoading } = useBackend();
  const online = data?.state === "online";
  const label = isLoading ? "Checking engine" : online ? "Engine online" : "Engine offline";
  const tip = isLoading ? "Checking the processing machine…" : online ? "The processing machine is connected." : `The processing machine is offline. ${data?.state === "offline" ? data.reason : ""} Saved work is safe; processing resumes when it reconnects.`;
  return (
    <span title={tip} aria-label={tip} className="inline-flex items-center gap-2 whitespace-nowrap rounded-full border border-line bg-surface px-3 py-1.5 text-[12px] font-medium text-muted">
      <span aria-hidden className={`relative h-2 w-2 rounded-full ${isLoading ? "bg-muted" : online ? "bg-success" : "bg-danger"}`}>
        {online && <span className="absolute inset-0 animate-ping rounded-full bg-success opacity-60 motion-reduce:hidden" />}
      </span>
      <span className="hidden sm:inline">{label}</span>
    </span>
  );
}
