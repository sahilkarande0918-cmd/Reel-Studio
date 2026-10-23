"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Clapperboard, Download, Film } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch, useBackend } from "@/lib/backend";
import { CaptionPicker, type CaptionChoice } from "./caption-picker";
import { StylePicker, type StylePreset } from "./style-picker";
import { createClient } from "@/lib/supabase/client";

type Render = {
  id: string;
  status: "queued" | "rendering" | "ready" | "failed" | "cancelled";
  quality: string;
  job_id: string | null;
  duration_s: number | null;
  size_bytes: number | null;
  render_s: number | null;
  error: string | null;
  created_at: string;
  job: { progress: number; current_stage: string | null; status: string; result: { timing?: Timing } | null } | null;
};

type Timing = { ok: boolean | null; audio_offset_ms?: number; words_on_speech?: number; words?: number; error?: string };

const STAGES: Record<string, string> = {
  queued: "Waiting for the processing machine",
  compose: "Compiling the timeline",
  lint: "Checking the composition",
  render: "Rendering frames",
  verify: "Verifying the MP4",
  sync_check: "Checking caption and audio timing",
};
const QUALITY = { draft: "Draft (fast)", looks: "Standard", delivery: "Delivery (best)" } as const;

/** Render a selected highlight to MP4; progress is live via Realtime, results play inline. */
export function Renders({ highlightId, projectId, selected, canEdit, onSelect }: {
  highlightId: string; projectId: string; selected: boolean; canEdit: boolean;
  /** Marks the highlight selected first, so "Create reel" is one click. */
  onSelect?: () => Promise<boolean>;
}) {
  const qc = useQueryClient();
  const backend = useBackend();
  const base = backend.data?.state === "online" ? backend.data.url : null;
  const [quality, setQuality] = useState<keyof typeof QUALITY>("looks");
  // "" = the brand kit's caption look; otherwise one of the 100 presets
  const [caption, setCaption] = useState<CaptionChoice>({ on: true, preset: "", overrides: {} });
  const [style, setStyle] = useState<StylePreset>("focus");
  const [kitChoice, setKitChoice] = useState<string>(""); // "" = organisation default, "none" = no branding
  const kits = useQuery({
    queryKey: ["brand-kit-names", projectId],
    staleTime: 60_000,
    queryFn: async () => {
      const sb = createClient();
      const { data: project, error: pe } = await sb.from("projects").select("organization_id").eq("id", projectId).single();
      if (pe) throw pe;
      const { data, error } = await sb.from("brand_kits").select("id, name, is_default").eq("organization_id", project.organization_id).order("created_at");
      if (error) throw error;
      return data as { id: string; name: string; is_default: boolean }[];
    },
  });
  const defaultKit = kits.data?.find((k) => k.is_default);
  const [error, setError] = useState<string | null>(null);
  const key = ["renders", highlightId];

  const renders = useQuery({
    queryKey: key,
    queryFn: async () => {
      const { data, error } = await createClient()
        .from("render_jobs")
        .select("id, status, quality, job_id, duration_s, size_bytes, render_s, error, created_at, job:jobs(progress, current_stage, status, result)")
        .eq("highlight_id", highlightId)
        .order("created_at", { ascending: false })
        .limit(3);
      if (error) throw error;
      return data as unknown as Render[];
    },
    refetchInterval: (q) => (q.state.data?.some((r) => r.status === "queued" || r.status === "rendering") ? 3000 : false),
  });
  useEffect(() => {
    const sb = createClient();
    const ch = sb.channel(`renders:${highlightId}`)
      .on("postgres_changes", { event: "*", schema: "public", table: "render_jobs", filter: `highlight_id=eq.${highlightId}` }, () => qc.invalidateQueries({ queryKey: key }))
      .on("postgres_changes", { event: "UPDATE", schema: "public", table: "jobs", filter: `project_id=eq.${projectId}` }, () => qc.invalidateQueries({ queryKey: key }))
      .subscribe();
    return () => { sb.removeChannel(ch); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highlightId, projectId]);

  const latest = renders.data?.[0];
  const urls = useQuery({
    queryKey: ["render-urls", latest?.id, base],
    enabled: !!base && latest?.status === "ready",
    staleTime: 60 * 60 * 1000,
    queryFn: async () => {
      const r = await apiFetch(base!, `/renders/${latest!.id}/urls`);
      if (!r.ok) throw new Error("link refused");
      const u = await r.json();
      const abs = (p: string) => `${base!.replace(/\/$/, "")}${p}`;
      return { video: abs(u.video), thumb: abs(u.thumb), download: abs(u.download) };
    },
  });

  async function render() {
    setError(null);
    if (!base) return setError("The processing backend is offline.");
    if (!selected && !(await onSelect?.())) return setError("Select this highlight to render it.");
    const r = await apiFetch(base, `/highlights/${highlightId}/render`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quality, brand_kit_id: kitChoice || null, style, captions: caption.on, caption_preset: caption.preset || null, caption_overrides: caption.overrides }),
    });
    if (!r.ok) setError((await r.json()).detail ?? `Render refused (${r.status})`);
    qc.invalidateQueries({ queryKey: key });
  }

  // fetch + blob instead of a link: a navigation through a dev tunnel gets its interstitial page
  async function download(request: Promise<Response>, name: string) {
    const r = await request.catch(() => null);
    if (!r?.ok) return setError("Download failed. Is the processing backend online?");
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(await r.blob()), download: name });
    a.click();
    URL.revokeObjectURL(a.href);
  }

  const busy = latest?.status === "queued" || latest?.status === "rendering";
  return (
    <div className="space-y-3 border-t border-line pt-4">
      <div className="flex flex-wrap items-center gap-3 text-[13px]">
        <h3 className="mr-auto text-[15px] font-semibold">Export reel</h3>
        {canEdit && (
          <>
            <label className="text-muted">
              Brand{" "}
              <select value={kitChoice} onChange={(e) => setKitChoice(e.target.value)}
                className="ml-1 max-w-[180px] rounded-lg border border-line bg-[var(--bg)] px-2 py-1.5 text-ink outline-none focus-visible:ring-2 focus-visible:ring-accent">
                <option value="">{defaultKit ? `${defaultKit.name} (default)` : "Default (none set)"}</option>
                {kits.data?.filter((k) => !k.is_default).map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
                <option value="none">No branding</option>
              </select>
            </label>
            <label className="text-muted">
              Quality{" "}
              <select value={quality} onChange={(e) => setQuality(e.target.value as keyof typeof QUALITY)}
                className="ml-1 rounded-lg border border-line bg-[var(--bg)] px-2 py-1.5 text-ink outline-none focus-visible:ring-2 focus-visible:ring-accent">
                {Object.entries(QUALITY).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </label>
            <button type="button" onClick={render} disabled={(!selected && !onSelect) || busy || !base}
              className="flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 font-semibold text-accent-ink hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50">
              <Film size={14} aria-hidden /> {selected ? "Render MP4" : "Create reel"}
            </button>
          </>
        )}
      </div>
      {canEdit && <StylePicker value={style} onChange={setStyle} name="render-style" />}
      {canEdit && <CaptionPicker value={caption} onChange={setCaption} />}
      {!selected && <p className="text-[13px] text-muted">{onSelect ? "Create reel selects this highlight and renders it with the brand, quality and style above." : "Select this highlight to render it."}</p>}
      {selected && !base && <p className="text-[13px] text-muted">Rendering needs the processing backend online.</p>}
      {error && <p className="text-[13px] text-danger">{error}</p>}
      {latest && busy && (
        <div className="space-y-1.5" aria-live="polite">
          <div className="flex justify-between text-[13px]">
            <span>{STAGES[latest.job?.current_stage ?? "queued"] ?? latest.job?.current_stage}</span>
            <span className="tabular-nums text-muted">{Math.round((latest.job?.progress ?? 0) * 100)}%</span>
          </div>
          <progress className="h-2 w-full accent-[var(--accent)]" value={latest.job?.progress ?? 0} max={1} />
        </div>
      )}
      {latest?.status === "failed" && <p className="text-[13px] text-danger">Render failed: {latest.error}</p>}
      {latest?.status === "cancelled" && <p className="text-[13px] text-muted">Render cancelled.</p>}
      {latest?.status === "ready" && (
        <div className="flex flex-wrap items-start gap-4">
          {urls.data ? (
            <video src={urls.data.video} poster={urls.data.thumb} controls playsInline preload="metadata"
              className="w-[216px] rounded-[6px] bg-black" style={{ aspectRatio: "9 / 16" }} />
          ) : (
            <div className="grid w-[216px] place-items-center rounded-[6px] bg-surface-2 text-[13px] text-muted" style={{ aspectRatio: "9 / 16" }}>
              {base ? "Loading…" : "Backend offline"}
            </div>
          )}
          <div className="space-y-2 text-[13px]">
            <p className="tabular-nums text-muted">
              1080×1920 · {latest.duration_s?.toFixed(1)} s · {((latest.size_bytes ?? 0) / 1024 ** 2).toFixed(1)} MB · {QUALITY[latest.quality as keyof typeof QUALITY] ?? latest.quality}
              {latest.render_s ? ` · rendered in ${Math.round(latest.render_s)} s` : ""}
            </p>
            {urls.data && (
              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={() => download(fetch(urls.data.download, { headers: { "X-Tunnel-Skip-AntiPhishing-Page": "true" } }), `reel-${latest.id.slice(0, 8)}.mp4`)}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-surface-2 px-3 py-1.5 hover:bg-surface-3">
                  <Download size={14} aria-hidden /> Download MP4
                </button>
                {(["srt", "vtt"] as const).map((f) => (
                  <button key={f} type="button" onClick={() => download(apiFetch(base!, `/renders/${latest.id}/captions?format=${f}`), `reel-${latest.id.slice(0, 8)}.${f}`)}
                    className="rounded-lg bg-surface-2 px-3 py-1.5 uppercase hover:bg-surface-3">
                    {f}
                  </button>
                ))}
                <Link href={`/editor/${latest.id}`} className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 font-semibold text-accent-ink hover:brightness-110">
                  <Clapperboard size={14} aria-hidden /> Open in editor
                </Link>
              </div>
            )}
            <TimingNote timing={latest.job?.result?.timing} />
          </div>
        </div>
      )}
    </div>
  );
}

function TimingNote({ timing }: { timing?: Timing }) {
  if (!timing) return null;
  if (timing.ok === null) return <p className="text-[13px] text-muted">Timing check could not run: {timing.error}</p>;
  const pct = Math.round((timing.words_on_speech ?? 0) * 100);
  return (
    <p className={`max-w-[46ch] text-[13px] ${timing.ok ? "text-muted" : "text-danger"}`}>
      {timing.ok ? "Timing check passed" : "Timing check: review before publishing"} · audio offset {timing.audio_offset_ms} ms vs the
      source · {pct}% of {timing.words} caption words fall on speech
    </p>
  );
}
