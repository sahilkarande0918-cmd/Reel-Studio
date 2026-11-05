"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Power } from "lucide-react";
import { useState } from "react";
import { apiFetch, useBackend } from "@/lib/backend";

type EngineState = { processing: boolean; paused_at?: string | null; can_switch: boolean };

/** Dashboard on/off switch for the processing engine (apps/api/app/api/engine.py). "Off" pauses the worker: no GPU,
 * renders or AI run and new jobs wait; the engine keeps answering so this button can turn it back on. A computer that
 * is shut down (or an engine stopped with the desktop button) cannot be reached from the website. */
export function EngineSwitch() {
  const qc = useQueryClient();
  const backend = useBackend();
  const base = backend.data?.state === "online" ? backend.data.url : null;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const engine = useQuery({
    queryKey: ["engine", base],
    enabled: !!base,
    refetchInterval: 15_000,
    queryFn: async () => {
      const r = await apiFetch(base!, "/engine");
      if (!r.ok) throw new Error(`Engine state unavailable (${r.status})`);
      return (await r.json()) as EngineState;
    },
  });

  async function flip(processing: boolean) {
    if (!base) return;
    if (!processing && !window.confirm("Turn the engine off? Running jobs stop now and continue when you turn it back on.")) return;
    setBusy(true);
    setError(null);
    try {
      const r = await apiFetch(base, "/engine", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ processing }),
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(typeof body.detail === "string" ? body.detail : `Refused (${r.status})`);
      qc.setQueryData(["engine", base], body);
      qc.invalidateQueries({ queryKey: ["backend"] });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reach the engine");
    } finally {
      setBusy(false);
    }
  }

  const checking = backend.isLoading || (!!base && engine.isLoading);
  const on = !!base && engine.data?.processing !== false;
  const state = checking ? "checking" : !base ? "off" : on ? "on" : "paused";
  const text = {
    checking: "Checking the processing computer…",
    on: "On. Transcription, AI clipping and rendering run on the processing computer.",
    paused: "Off. Nothing is processed and the GPU is free; new jobs wait in the queue until you turn it on.",
    off: "Not reachable. The processing computer is asleep or shut down, or the engine was stopped there. Turn it on with the “Reel Studio Engine (on-off)” button on that computer’s desktop.",
  }[state];

  return (
    <section className="rounded-2xl border border-line bg-surface p-5 shadow-sm" aria-live="polite">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Power size={18} className="text-sage" aria-hidden />
          <h2 className="font-serif text-[20px] text-ink">Engine</h2>
        </div>
        <span className="inline-flex items-center gap-2 text-[11px] font-semibold text-muted">
          <span aria-hidden className={`h-2 w-2 rounded-full ${state === "on" ? "bg-success" : state === "checking" ? "bg-muted" : "bg-danger"}`} />
          {state === "on" ? "On" : state === "paused" ? "Off" : state === "off" ? "Unreachable" : "…"}
        </span>
      </div>
      <p className="mt-3 text-[12px] leading-6 text-muted">{text}</p>
      {base && engine.data?.can_switch && (
        <button type="button" disabled={busy} onClick={() => flip(!on)}
          className={`mt-4 inline-flex items-center gap-2 rounded-lg px-4 py-2 text-[12px] font-semibold transition disabled:opacity-60 ${on ? "border border-line text-ink hover:bg-surface-2" : "bg-accent text-white hover:bg-forest"}`}>
          <Power size={14} aria-hidden />{busy ? "Switching…" : on ? "Turn engine off" : "Turn engine on"}
        </button>
      )}
      {base && engine.data && !engine.data.can_switch && <p className="mt-3 text-[11px] text-muted">Only a workspace owner or admin can turn the engine on or off.</p>}
      {error && <p role="alert" className="mt-3 text-[12px] text-danger">{error}</p>}
    </section>
  );
}
