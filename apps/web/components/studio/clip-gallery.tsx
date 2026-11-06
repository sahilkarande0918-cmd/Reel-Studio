"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, LoaderCircle, Play } from "lucide-react";
import { useState } from "react";
import { apiFetch, useBackend } from "@/lib/backend";
import { Enhance4K, type Hd } from "./enhance-4k";

type Clip = {
  highlight_id: string; title: string; start_s: number; end_s: number; status: string; score: number | null; topic: string | null;
  render: { id: string; status: string; error: string | null; duration_s: number | null } | null;
  job: { status: string; current_stage: string | null; progress?: number | null } | null;
  hd: Hd | null;
};

const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

async function save(url: string, name: string) {
  const r = await fetch(url, { headers: { "X-Tunnel-Skip-AntiPhishing-Page": "true" } });
  if (!r.ok) throw new Error("download failed");
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(await r.blob()), download: name });
  a.click();
  URL.revokeObjectURL(a.href);
}

function Card({ c, base, recordingId }: { c: Clip; base: string; recordingId: string }) {
  const qc = useQueryClient();
  const [play, setPlay] = useState(false);
  const ready = c.render?.status === "ready";
  const urls = useQuery({
    queryKey: ["render-urls", c.render?.id, base], enabled: ready, staleTime: 3600_000,
    queryFn: async () => {
      const u = await (await apiFetch(base, `/renders/${c.render!.id}/urls`)).json();
      const abs = (p: string) => `${base.replace(/\/$/, "")}${p}`;
      return { video: abs(u.video), thumb: abs(u.thumb), download: abs(u.download) };
    },
  });
  const working = c.render && ["queued", "rendering"].includes(c.render.status);
  return (
    <li className="overflow-hidden rounded-xl border border-line bg-surface">
      <div className="relative aspect-[9/16] bg-[#141810]">
        {ready && urls.data ? (play
          ? <video src={urls.data.video} className="h-full w-full object-contain" controls autoPlay playsInline />
          : <button type="button" className="group h-full w-full" onClick={() => setPlay(true)} aria-label={`Play ${c.title}`}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={urls.data.thumb} alt="" className="h-full w-full object-cover" />
              <span className="absolute inset-0 grid place-items-center bg-black/0 transition group-hover:bg-black/30"><Play size={34} className="text-white opacity-80" /></span>
            </button>)
          : <div className="grid h-full place-items-center p-4 text-center text-[12px] text-white/70">
              {working ? <span className="flex flex-col items-center gap-2"><LoaderCircle className="animate-spin" size={22} />{c.job?.current_stage?.replaceAll("_", " ") ?? c.render!.status}</span>
                : c.render?.status === "failed" ? <span className="text-danger">Render failed</span> : "Not rendered"}
            </div>}
        {c.score != null && <span className="absolute left-2 top-2 rounded-md bg-black/70 px-1.5 py-0.5 text-[11px] font-bold text-white" title="Editorial score (a ranking aid, not a view prediction)">{Math.round(c.score)}</span>}
        <span className="absolute right-2 top-2 rounded-md bg-black/70 px-1.5 py-0.5 text-[11px] tabular-nums text-white">{fmt(c.end_s - c.start_s)}</span>
      </div>
      <div className="space-y-2 p-3">
        <p className="line-clamp-2 text-[13px] font-semibold leading-5">{c.title}</p>
        <p className="text-[11px] text-muted">{fmt(c.start_s)}–{fmt(c.end_s)}{c.topic ? ` · ${c.topic}` : ""}</p>
        {ready && urls.data && <button type="button" onClick={() => save(urls.data!.download, `${c.title.slice(0, 40).replace(/[^\w -]/g, "")}.mp4`)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-line px-2.5 py-1.5 text-[11px] font-semibold text-accent hover:bg-surface-2"><Download size={13} />Download</button>}
        {ready && <Enhance4K base={base} reelId={c.render!.id} hd={c.hd} compact name={c.title.slice(0, 40).replace(/[^\w -]/g, "")}
          onQueued={() => qc.invalidateQueries({ queryKey: ["batch", recordingId] })} />}
      </div>
    </li>
  );
}

/** All clips of a recording as an OpusClip-style results grid: real render state per clip, preview, download, ZIP. */
export function ClipGallery({ recordingId }: { recordingId: string }) {
  const backend = useBackend();
  const base = backend.data?.state === "online" ? backend.data.url : null;
  const [error, setError] = useState<string | null>(null);
  const batch = useQuery({
    queryKey: ["batch", recordingId, base], enabled: !!base,
    queryFn: async () => (await (await apiFetch(base!, `/recordings/${recordingId}/batch`)).json()) as { clips: Clip[] },
    refetchInterval: (q) => (q.state.data?.clips.some((c) => [c.render?.status, c.hd?.status].some((s) => s === "queued" || s === "rendering")) ? 4000 : 15000),
  });
  const clips = (batch.data?.clips ?? []).filter((c) => c.render).sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  if (!base || !clips.length) return null;
  const ready = clips.filter((c) => c.render?.status === "ready").length;
  async function zip() {
    setError(null);
    try {
      const u = await (await apiFetch(base!, `/recordings/${recordingId}/batch-zip-url`)).json();
      await save(`${base!.replace(/\/$/, "")}${u.url}`, `clips-${recordingId.slice(0, 8)}.zip`);
    } catch { setError("ZIP download failed. Is the engine online?"); }
  }
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="text-[20px]">Your clips <span className="text-[13px] text-muted">{ready} of {clips.length} ready</span></h2>
        <button type="button" onClick={zip} disabled={!ready} className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-2 text-[12px] font-semibold text-white hover:bg-forest disabled:opacity-50">
          <Download size={14} />Download all (ZIP)</button>
      </div>
      {error && <p className="text-[12px] text-danger">{error}</p>}
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5">{clips.map((c) => <Card key={c.highlight_id} c={c} base={base} recordingId={recordingId} />)}</ul>
    </section>
  );
}
