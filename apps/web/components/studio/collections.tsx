"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Layers, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { apiErrorMessage, apiFetch, useBackend } from "@/lib/backend";
import { createClient } from "@/lib/supabase/client";

type Episode = { highlight_id: string; title: string; start_s: number; end_s: number; topic: string; steps: string[]; quote: string; render_id?: string };
type Collection = { id: string; title: string; description: string; topic: string; episodes: Episode[]; edited: boolean };
const ts = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

/** AI clip collections: series grouped by the class's own outline topics; reorder, rename, render all. */
export function Collections({ recordingId, canEdit }: { recordingId: string; canEdit: boolean }) {
  const backend = useBackend();
  const base = backend.data?.state === "online" ? backend.data.url : null;
  const qc = useQueryClient();
  const key = ["collections", recordingId];
  const [msg, setMsg] = useState<string | null>(null);
  const cols = useQuery({
    queryKey: key,
    queryFn: async () => {
      const { data, error } = await createClient().from("clip_collections").select("id, title, description, topic, episodes, edited").eq("recording_id", recordingId).order("created_at");
      if (error) throw error;
      return data as Collection[];
    },
  });
  useEffect(() => {
    const sb = createClient();
    const ch = sb.channel(`collections:${recordingId}:${crypto.randomUUID()}`)
      .on("postgres_changes", { event: "*", schema: "public", table: "clip_collections", filter: `recording_id=eq.${recordingId}` }, () => qc.invalidateQueries({ queryKey: key }))
      .subscribe();
    return () => { sb.removeChannel(ch); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recordingId]);

  async function call(path: string, init: RequestInit, ok: string) {
    if (!base) return setMsg("The processing machine is offline.");
    const r = await apiFetch(base, path, { ...init, headers: { "Content-Type": "application/json" } });
    setMsg(r.ok ? ok : apiErrorMessage(await r.json().catch(() => null), r.status));
    qc.invalidateQueries({ queryKey: key });
  }
  const patch = (c: Collection, body: object) => call(`/collections/${c.id}`, { method: "PATCH", body: JSON.stringify(body) }, "Saved.");
  const move = (c: Collection, i: number, d: number) => {
    const ids = c.episodes.map((e) => e.highlight_id);
    [ids[i], ids[i + d]] = [ids[i + d], ids[i]];
    patch(c, { order: ids });
  };

  return (
    <section className="studio-panel space-y-4 p-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><p className="studio-eyebrow mb-2">Series</p><h2 className="flex items-center gap-2 text-[20px] font-semibold tracking-[-.03em]"><Layers size={18} className="text-accent" aria-hidden />AI clip collections</h2>
          <p className="mt-1 text-[12px] text-muted">Groups this class&apos;s highlights into series by the topics it actually teaches, in teaching order, with timestamps as evidence.</p></div>
        {canEdit && <button type="button" className="studio-button" disabled={!base} onClick={() => call(`/recordings/${recordingId}/collections`, { method: "POST" }, "Collections generated from the lecture outline.")}>{cols.data?.length ? "Regenerate" : "Generate collections"}</button>}
      </div>
      {msg && <p role="status" className="text-[12px] text-muted">{msg}</p>}
      {cols.data?.length === 0 && <p className="text-[13px] text-muted">No collections yet. They need analysed highlights; a topic becomes a series only when the class has two or more clips about it.</p>}
      {cols.data?.map((c) => <article key={c.id} className="space-y-3 rounded-xl border border-line bg-surface p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            {canEdit ? <input className="studio-input !text-[15px] font-semibold" defaultValue={c.title} maxLength={120} onBlur={(e) => e.target.value !== c.title && patch(c, { title: e.target.value })} aria-label="Collection title" /> : <h3 className="text-[15px] font-semibold">{c.title}</h3>}
            <p className="mt-1 text-[12px] text-muted">{c.description}</p>
          </div>
          {canEdit && <button type="button" className="studio-button-secondary rounded-xl px-3 py-2 text-[12px] font-semibold" disabled={!base}
            onClick={() => call(`/collections/${c.id}/render`, { method: "POST", body: JSON.stringify({ quality: "looks", style: "focus", captions: true }) }, `Rendering ${c.episodes.length} episodes with your default brand kit.`)}>Render all ({c.episodes.length})</button>}
        </div>
        <ol className="space-y-2">{c.episodes.map((e, i) => <li key={e.highlight_id} className="flex items-start gap-3 rounded-lg bg-surface-2 p-3 text-[12px]">
          <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-accent text-[11px] font-semibold text-accent-ink">{i + 1}</span>
          <div className="min-w-0 flex-1">
            {canEdit ? <input className="w-full bg-transparent font-semibold outline-none focus:underline" defaultValue={e.title} maxLength={120} aria-label={`Episode ${i + 1} title`}
              onBlur={(ev) => ev.target.value !== e.title && patch(c, { episode_titles: { [e.highlight_id]: ev.target.value } })} /> : <p className="font-semibold">{e.title}</p>}
            <p className="text-muted">{ts(e.start_s)}–{ts(e.end_s)}{e.steps.length ? ` · steps: ${e.steps.join(" → ")}` : ""}</p>
            {e.quote && <p className="mt-1 italic text-muted">“{e.quote}”</p>}
            {e.render_id && <Link href={`/editor/${e.render_id}`} className="mt-1 inline-block font-semibold text-accent">Edit this episode →</Link>}
          </div>
          {canEdit && <div className="flex shrink-0 flex-col gap-1">
            <button type="button" aria-label="Move up" disabled={i === 0} onClick={() => move(c, i, -1)} className="text-muted hover:text-ink disabled:opacity-30"><ArrowUp size={14} /></button>
            <button type="button" aria-label="Move down" disabled={i === c.episodes.length - 1} onClick={() => move(c, i, 1)} className="text-muted hover:text-ink disabled:opacity-30"><ArrowDown size={14} /></button>
            <button type="button" aria-label="Remove from series" onClick={() => patch(c, { order: c.episodes.filter((x) => x.highlight_id !== e.highlight_id).map((x) => x.highlight_id) })} className="text-muted hover:text-danger"><X size={14} /></button>
          </div>}
        </li>)}</ol>
      </article>)}
    </section>
  );
}
