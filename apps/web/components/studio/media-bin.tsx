"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Film, ImageIcon, LoaderCircle, Music, Trash2, UploadCloud, Video } from "lucide-react";
import { useEffect, useState } from "react";
import { apiFetch, useBackend } from "@/lib/backend";
import { dismiss, dropHandles, enqueue, onUploadDone, useUploads } from "@/lib/uploads";
import { createClient } from "@/lib/supabase/client";

export type Asset = {
  id: string; kind: "clip" | "image" | "audio" | "reference"; filename: string; status: string; size_bytes: number;
  duration_s: number | null; width: number | null; height: number | null; error: string | null; position: number;
  analysis: { tempo_bpm?: number; drops?: number[]; vlm?: { subject?: string; shot?: string } | null; techniques?: string[]; moments?: unknown[]; pacing?: object } | null;
};
type Kind = Asset["kind"];

const VIDEO = [".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"];
const IMAGE = [".jpg", ".jpeg", ".png", ".webp"];
const AUDIO = [".mp3", ".mpeg", ".wav", ".m4a", ".aac", ".ogg", ".flac"];
const ext = (n: string) => n.slice(n.lastIndexOf(".")).toLowerCase();
const mb = (n: number) => (n >= 1024 ** 3 ? `${(n / 1024 ** 3).toFixed(2)} GB` : `${(n / 1024 ** 2).toFixed(1)} MB`);

export function useAssets(projectId: string) {
  const qc = useQueryClient();
  useEffect(() => {
    const sb = createClient();
    const ch = sb.channel(`assets:${projectId}:${crypto.randomUUID()}`) // one channel per hook instance: Realtime rejects a second .on() on a subscribed channel
      .on("postgres_changes", { event: "*", schema: "public", table: "media_assets", filter: `project_id=eq.${projectId}` }, () => qc.invalidateQueries({ queryKey: ["assets", projectId] }))
      .subscribe();
    return () => { sb.removeChannel(ch); };
  }, [projectId, qc]);
  return useQuery({
    queryKey: ["assets", projectId],
    queryFn: async () => {
      const { data, error } = await createClient().from("media_assets")
        .select("id, kind, filename, status, size_bytes, duration_s, width, height, error, position, analysis")
        .eq("project_id", projectId).neq("status", "uploading").order("position").order("created_at");
      if (error) throw error;
      return data as Asset[];
    },
    refetchInterval: (q) => (q.state.data?.some((a) => a.status === "uploaded" || a.status === "analyzing") ? 4000 : false),
  });
}

function Thumb({ asset, base }: { asset: Asset; base: string | null }) {
  const urls = useQuery({
    queryKey: ["asset-urls", asset.id, base], enabled: !!base && asset.status === "ready" && asset.kind !== "audio", staleTime: 3 * 3600_000,
    queryFn: async () => { const r = await apiFetch(base!, `/assets/${asset.id}/urls`); if (!r.ok) throw new Error(); return r.json() as Promise<{ media: string; thumb: string }>; },
  });
  const [play, setPlay] = useState(false);
  const Icon = asset.kind === "image" ? ImageIcon : asset.kind === "audio" ? Music : Video;
  if (!urls.data || !base) return <div className="grid aspect-[9/16] place-items-center bg-surface-2 text-muted"><Icon size={22} aria-hidden /></div>;
  const root = base.replace(/\/$/, "");
  return play && asset.kind !== "image"
    ? <video src={root + urls.data.media} className="aspect-[9/16] w-full bg-black object-contain" controls autoPlay muted playsInline onEnded={() => setPlay(false)} />
    : <button type="button" onClick={() => setPlay(true)} className="block w-full" aria-label={`Preview ${asset.filename}`}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={root + urls.data.thumb} alt="" className="aspect-[9/16] w-full bg-black object-cover" />
      </button>;
}

export function MediaBin({ projectId, canEdit }: { projectId: string; canEdit: boolean }) {
  const backend = useBackend();
  const base = backend.data?.state === "online" ? backend.data.url : null;
  const qc = useQueryClient();
  const assets = useAssets(projectId);
  // uploads run in the app-wide manager (lib/uploads.ts, two at a time): they continue while you switch sections
  const uploads = useUploads().filter((u) => u.projectId === projectId && u.kind !== "recording" && u.status !== "done")
    .map((u) => ({ key: u.key, name: u.name, sent: u.sent, total: u.size, error: u.status === "error" ? u.error : u.status === "paused" ? "paused — resume from the upload button at the top" : undefined }));
  const [notice, setNotice] = useState<string | null>(null);
  const [drag, setDrag] = useState(false);
  useEffect(() => onUploadDone((u) => {
    if (u.projectId !== projectId || u.kind === "recording") return;
    if (u.duplicate) setNotice(`${u.name} is already in this project; skipped the duplicate.`);
    qc.invalidateQueries({ queryKey: ["assets", projectId] });
  }), [projectId, qc]);

  function add(files: FileList | File[], forced?: Kind, handles: (Parameters<typeof enqueue>[3])[] = []) {
    setNotice(null);
    const list = [...files];
    const rejected: string[] = [];
    list.forEach((f, i) => {
      const e = ext(f.name);
      const kind: Kind | null = forced ?? (VIDEO.includes(e) ? "clip" : IMAGE.includes(e) ? "image" : AUDIO.includes(e) ? "audio" : null);
      const allowed = kind === "reference" ? VIDEO : kind === "audio" ? AUDIO : kind === "image" ? IMAGE : VIDEO;
      if (!kind || !allowed.includes(e)) { rejected.push(f.name); return; }
      enqueue(kind, projectId, f, handles[i]);
    });
    if (rejected.length) setNotice(`Not a supported file: ${rejected.join(", ")}`);
  }

  async function remove(a: Asset) {
    if (!base) return;
    const r = await apiFetch(base, `/assets/${a.id}`, { method: "DELETE" });
    if (!r.ok) setNotice("Could not remove the file.");
    qc.invalidateQueries({ queryKey: ["assets", projectId] });
  }

  const all = assets.data ?? [];
  const visual = all.filter((a) => a.kind === "clip" || a.kind === "image");
  const music = all.find((a) => a.kind === "audio");
  const reference = all.find((a) => a.kind === "reference");
  const total = all.reduce((n, a) => n + a.size_bytes, 0);
  const disabled = !base || !canEdit;

  return (
    <section className="studio-panel space-y-5 p-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><p className="studio-eyebrow mb-2">Your footage</p><h2 className="text-[20px] font-semibold tracking-[-.03em]">Clips, music & reference</h2>
          <p className="mt-1 text-[12px] text-muted">{visual.length} clip{visual.length === 1 ? "" : "s"}/images · {mb(total)} of 40 GB · up to 300 files, 2 GB per clip. Files stay on the processing machine.</p></div>
      </div>
      {canEdit && <label
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); const files = [...e.dataTransfer.files]; const h = dropHandles(e); if (!disabled) void h.then((hs) => add(files, undefined, hs)); }}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-line px-6 py-10 text-center transition-colors ${drag ? "bg-surface-3" : "bg-surface hover:bg-surface-2"} ${disabled ? "pointer-events-none opacity-60" : ""}`}>
        <UploadCloud size={26} className="text-muted" aria-hidden />
        <span className="text-[15px]">Drop any number of clips and images here, or choose files</span>
        <span className="text-[12px] text-muted">MP4, MOV, MKV, WebM · JPG, PNG, WebP · music files dropped here become the soundtrack</span>
        <input type="file" multiple className="sr-only" disabled={disabled} accept={[...VIDEO, ...IMAGE, ...AUDIO].join(",") + ",video/*,image/*,audio/*"} onChange={(e) => { if (e.target.files) add(e.target.files); e.target.value = ""; }} />
      </label>}
      {!base && !backend.isLoading && <p className="text-[13px] text-danger">Uploads go straight to the processing machine, which is offline right now.</p>}
      {notice && <p role="status" className="text-[13px] text-muted">{notice}</p>}
      {uploads.length > 0 && <ul className="space-y-2" aria-live="polite">{uploads.map((u) => <li key={u.key} className="text-[12px]">
        <div className="flex justify-between gap-3"><span className="truncate">{u.name}</span><span className={`tabular-nums ${u.error ? "text-danger" : "text-muted"}`}>{u.error ?? `${mb(u.sent)} / ${mb(u.total)}`}</span></div>
        {!u.error && <progress className="h-1.5 w-full" value={u.sent} max={u.total} />}
        {u.error && <button type="button" className="text-muted hover:text-ink" onClick={() => dismiss(u.key)}>Dismiss</button>}
      </li>)}</ul>}

      <div className="grid gap-3 sm:grid-cols-2">
        <Slot title="Music (optional)" icon={<Music size={16} aria-hidden />} asset={music} accept={AUDIO} disabled={disabled} onPick={(f) => add([f], "audio")} onRemove={remove} canEdit={canEdit}
          detail={music?.analysis?.tempo_bpm ? `${music.analysis.tempo_bpm} BPM${music.analysis.drops?.length ? ` · drop at ${music.analysis.drops[0].toFixed(1)} s` : ""}` : undefined} />
        <Slot title="Reference reel (optional)" icon={<Film size={16} aria-hidden />} asset={reference} accept={VIDEO} disabled={disabled} onPick={(f) => add([f], "reference")} onRemove={remove} canEdit={canEdit}
          detail={reference?.analysis?.techniques?.slice(0, 2).join(" · ")} />
      </div>
      {reference?.status === "ready" && reference.analysis?.pacing && <ReferenceReport a={reference.analysis} />}

      {assets.isLoading ? <p className="text-muted">Loading…</p> : visual.length === 0 ? <p className="text-[13px] text-muted">No clips yet.</p> :
        <ul className="grid grid-cols-3 gap-3 sm:grid-cols-4 lg:grid-cols-6">{visual.map((a, i) => <li key={a.id} className="group min-w-0 overflow-hidden rounded-xl border border-line bg-surface">
          <div className="relative"><Thumb asset={a} base={base} />
            <span className="absolute left-1.5 top-1.5 rounded bg-black/60 px-1.5 py-0.5 text-[10px] font-semibold text-white">{i + 1}</span>
            {(a.status === "uploaded" || a.status === "analyzing") && <span className="absolute inset-x-0 bottom-0 flex items-center gap-1 bg-black/60 px-2 py-1 text-[10px] text-white"><LoaderCircle size={11} className="animate-spin" aria-hidden />Analysing</span>}
          </div>
          <div className="space-y-0.5 p-2 text-[11px]">
            <p className="truncate font-semibold" title={a.filename}>{a.filename}</p>
            <p className="truncate text-muted">{a.status === "failed" ? <span className="text-danger">{a.error}</span> : `${a.duration_s ? `${a.duration_s.toFixed(1)} s · ` : ""}${a.analysis?.vlm?.subject ?? a.kind}`}</p>
            {canEdit && <button type="button" onClick={() => remove(a)} className="inline-flex items-center gap-1 text-muted hover:text-danger"><Trash2 size={11} aria-hidden />Remove</button>}
          </div>
        </li>)}</ul>}
    </section>
  );
}

function Slot({ title, icon, asset, accept, disabled, onPick, onRemove, canEdit, detail }: {
  title: string; icon: React.ReactNode; asset?: Asset; accept: string[]; disabled: boolean; canEdit: boolean;
  onPick: (f: File) => void; onRemove: (a: Asset) => void; detail?: string;
}) {
  return <div className="rounded-xl border border-line bg-surface p-3 text-[12px]">
    <p className="flex items-center gap-2 font-semibold">{icon}{title}</p>
    {asset ? <div className="mt-1.5 space-y-0.5">
      <p className="truncate">{asset.filename}{asset.duration_s ? ` · ${asset.duration_s.toFixed(1)} s` : ""}</p>
      <p className="text-muted">{asset.status === "ready" ? (detail ?? "Analysed") : asset.status === "failed" ? <span className="text-danger">{asset.error}</span> : "Analysing…"}</p>
      {canEdit && <button type="button" onClick={() => onRemove(asset)} className="text-muted hover:text-danger">Remove</button>}
    </div> : <p className="mt-1.5 text-muted">None — {title.startsWith("Music") ? "an original score is generated, or choose No music." : "the director picks the style from your prompt."}</p>}
    {canEdit && <label className={`mt-2 inline-block cursor-pointer font-semibold text-accent ${disabled ? "pointer-events-none opacity-50" : ""}`}>{asset ? "Replace" : "Add"}
      <input type="file" className="sr-only" accept={accept.join(",")} disabled={disabled} onChange={(e) => { const f = e.target.files?.[0]; if (f) onPick(f); e.target.value = ""; }} />
    </label>}
  </div>;
}

/* eslint-disable @typescript-eslint/no-explicit-any -- analysis JSON written by services/reference/analyzer.py */
/** What the analyzer measured in the reference reel: the evidence the director's style transfer uses. */
function ReferenceReport({ a }: { a: any }) {
  const dur = a.meta?.duration_s || 1;
  const cuts: { t: number; kind: string }[] = a.transitions ?? [];
  const kinds = cuts.reduce((m: Record<string, number>, c) => ({ ...m, [c.kind]: (m[c.kind] ?? 0) + 1 }), {});
  const bs = a.beat_sync ?? {};
  const pct = (x: number) => `${Math.round(x * 100)}%`;
  const rows: [string, string][] = [
    ["Pacing", `${a.pacing.shots} shots · ${a.pacing.cuts_per_min} cuts/min · median shot ${a.pacing.median_shot_s} s`],
    ["Beat sync", bs.tempo_bpm ? `${bs.tempo_bpm} BPM · ${pct(bs.cuts_within_60ms ?? 0)} of cuts within 60 ms of a beat (median ${bs.median_abs_offset_ms} ms)` : "No music beat detected"],
    ["Transitions", Object.entries(kinds).map(([k, n]) => `${k} ×${n}`).join(" · ") || "—"],
    ["Flashes", `${(a.flashes ?? []).length} white/black hit frames`],
    ["Camera", a.motion ? `zoom-in ${pct(a.motion.zoom_in_share)} · zoom-out ${pct(a.motion.zoom_out_share)} of shots · peak motion ${a.motion.peak_flow}` : "—"],
    ["Text", a.text ? `on-screen text in ${pct(a.text.frames_with_text)} of sampled shots` : "—"],
    ["Layout", a.layout ? `framed cards/screens in ${pct(a.layout.panel_shots)} of shots · split layouts in ${pct(a.layout.split_shots)}` : "not measured (re-upload to analyse)"],
  ];
  return (
    <details className="rounded-xl border border-line bg-surface p-4 text-[12px]">
      <summary className="cursor-pointer font-semibold">Reference style report <span className="font-normal text-muted">· measured from the reel, used by the director</span></summary>
      <ul className="mt-3 list-disc space-y-0.5 pl-4">{(a.techniques ?? []).map((t: string) => <li key={t}>{t}</li>)}</ul>
      <dl className="mt-3 grid gap-x-4 gap-y-1 sm:grid-cols-[110px_1fr]">{rows.map(([k, v]) => <div key={k} className="contents"><dt className="text-muted">{k}</dt><dd>{v}</dd></div>)}</dl>
      <div className="relative mt-4 h-8 rounded bg-surface-2" aria-label="Cuts (tall marks) and beats (short marks) across the reel">
        {(a.music?.beats ?? []).map((b: number) => <span key={`b${b}`} className="absolute bottom-0 h-2 w-px bg-muted/60" style={{ left: `${(b / dur) * 100}%` }} />)}
        {cuts.map((c) => <span key={`c${c.t}`} title={`${c.t.toFixed(2)} s · ${c.kind}`} className="absolute inset-y-0 w-0.5 bg-accent" style={{ left: `${(c.t / dur) * 100}%` }} />)}
      </div>
      <p className="mt-1 text-[11px] text-muted">Tall marks: cuts · short marks: beats · {dur.toFixed(1)} s</p>
      {a.colour?.palette && <div className="mt-3 flex gap-1">{a.colour.palette.map((c: string) => <span key={c} title={c} className="h-6 w-6 rounded ring-1 ring-line" style={{ background: c }} />)}</div>}
    </details>
  );
}
