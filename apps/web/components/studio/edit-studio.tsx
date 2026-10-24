"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clapperboard, Download, LoaderCircle, Wand2, XCircle } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { apiErrorMessage, apiFetch, useBackend } from "@/lib/backend";
import { createClient } from "@/lib/supabase/client";
import { CaptionPicker, type CaptionChoice } from "./caption-picker";
import { MediaBin, useAssets } from "./media-bin";

type Segment = { clip: number; slot: [number, number]; effects: [string, Record<string, number>][]; transition_out: string; reuse: Record<string, number> };
type Generation = {
  id: string; status: string; prompt: string; settings: Record<string, unknown>; error: string | null; created_at: string; render_id: string | null;
  director: { style: string; treatment: string; pacing: string; look: string; reasons: string[]; profile: string; clips: string[]; provenance: { engine: string }; reference_evidence: string[]; on_screen_text: { text: string }[]; graphics: { template: string }[] } | null;
  plan: { bpm: number; duration: number; segments: Segment[]; reused_shots: number } | null;
  qa: { pass?: Record<string, boolean>; storyboard?: string[]; loudness?: { integrated_lufs: number; true_peak_dbtp: number }; hard_cuts?: { beat_offset_ms: number }[] } | null;
  job: { progress: number; current_stage: string | null; status: string } | null;
};

export const STYLES: [string, string][] = [
  ["auto", "Let the AI director decide"], ["phonk", "Phonk / velocity"], ["cinematic", "Cinematic"], ["energetic", "Energetic"],
  ["clean_commercial", "Clean commercial"], ["minimal", "Minimal"], ["educational", "Educational"], ["product_showcase", "Product showcase"],
  ["motion_graphics", "Motion graphics"], ["tech_ad", "Tech / SaaS advertisement"],
];
const STAGE: Record<string, string> = {
  queued: "Waiting for the processing machine", analyze: "Checking clip, music and reference analysis", direct: "AI director is planning the edit",
  voice: "Recording narration", plan: "Placing cuts on the beat", render_base: "Rendering cuts, effects and transitions",
  qa: "Measuring the result", compose: "Compiling text and motion graphics", lint: "Checking the composition", render: "Rendering overlays",
  verify: "Verifying the MP4", sync_check: "Final checks", done: "Ready",
};
const IDEAS = [
  "Make a professional phonk edit",
  "Premium shoe-store reel with velocity ramps, flashes and punch zooms on the beat",
  "Cinematic, slow and moody with smooth transitions",
  "Clean product showcase for Instagram with a call to action",
];
const QA_LABEL: Record<string, string> = { exact_length: "Exact length", cuts_on_frame: "Cuts on frame", cuts_on_beat: "Cuts on beat", transitions_visible: "Transitions visible", no_unplanned_black: "No black gaps", no_frozen_seconds: "No frozen frames", "loudness_-14": "−14 LUFS", "true_peak_<=-1": "True peak ≤ −1 dBTP" };

function useGenerations(projectId: string) {
  const qc = useQueryClient();
  useEffect(() => {
    const sb = createClient();
    const ch = sb.channel(`edits:${projectId}:${crypto.randomUUID()}`)
      .on("postgres_changes", { event: "*", schema: "public", table: "edit_generations", filter: `project_id=eq.${projectId}` }, () => qc.invalidateQueries({ queryKey: ["edits", projectId] }))
      .on("postgres_changes", { event: "*", schema: "public", table: "jobs", filter: `project_id=eq.${projectId}` }, () => qc.invalidateQueries({ queryKey: ["edits", projectId] }))
      .subscribe();
    return () => { sb.removeChannel(ch); };
  }, [projectId, qc]);
  return useQuery({
    queryKey: ["edits", projectId],
    queryFn: async () => {
      const { data, error } = await createClient().from("edit_generations")
        .select("id, status, prompt, settings, error, created_at, render_id, director, plan, qa, job:jobs(progress, current_stage, status)")
        .eq("project_id", projectId).order("created_at", { ascending: false }).limit(10);
      if (error) throw error;
      return data as unknown as Generation[];
    },
    refetchInterval: (q) => (q.state.data?.some((g) => ["queued", "planning", "rendering"].includes(g.status)) ? 4000 : false),
  });
}

export function EditStudio({ projectId, canEdit, idea }: { projectId: string; canEdit: boolean; idea?: { prompt: string; style: string; duration: number } }) {
  const backend = useBackend();
  const base = backend.data?.state === "online" ? backend.data.url : null;
  const qc = useQueryClient();
  const assets = useAssets(projectId);
  const gens = useGenerations(projectId);
  const [prompt, setPrompt] = useState(idea?.prompt ?? "");
  const [duration, setDuration] = useState([10, 15, 20, 30, 45, 60].reduce((a, b) => (Math.abs(b - (idea?.duration ?? 15)) < Math.abs(a - (idea?.duration ?? 15)) ? b : a)));
  const [aspect, setAspect] = useState("9:16");
  const [style, setStyle] = useState(idea?.style ?? "auto");
  const [music, setMusic] = useState<"upload" | "score" | "none">("upload");
  const [useReference, setUseReference] = useState(true);
  const [caption, setCaption] = useState<CaptionChoice>({ on: false, preset: "creator-pop", overrides: {} });
  const [voice, setVoice] = useState("none");
  const [narration, setNarration] = useState("");
  const [language, setLanguage] = useState("en");
  const [quality, setQuality] = useState("looks");
  const [beatOffset, setBeatOffset] = useState(0);
  const [bpm, setBpm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const voices = useQuery({
    queryKey: ["voices", base], enabled: !!base, staleTime: 60_000,
    queryFn: async () => { const r = await apiFetch(base!, "/voices"); if (!r.ok) return [] as { id: string; label: string }[]; return (await r.json()) as { id: string; label: string }[]; },
  });

  const all = assets.data ?? [];
  const hasClips = all.some((a) => (a.kind === "clip" || a.kind === "image") && a.status !== "failed");
  const hasMusic = all.some((a) => a.kind === "audio" && a.status !== "failed");
  const hasReference = all.some((a) => a.kind === "reference" && a.status !== "failed");
  const active = gens.data?.find((g) => ["queued", "planning", "rendering"].includes(g.status));

  async function generate() {
    if (!base) return;
    setBusy(true); setError(null);
    try {
      const r = await apiFetch(base, `/projects/${projectId}/edit`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: prompt.trim() || "Edit it professionally", duration_s: duration, aspect, style, music: hasMusic ? music : music === "upload" ? "score" : music,
          use_reference: useReference, captions: caption.on, caption_preset: caption.preset, caption_overrides: caption.overrides, voice, narration: narration.trim() || null, language, quality, beat_offset_ms: beatOffset, bpm: bpm ? Number(bpm) : null }),
      });
      if (!r.ok) throw new Error(apiErrorMessage(await r.json().catch(() => null), r.status));
      qc.invalidateQueries({ queryKey: ["edits", projectId] });
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); }
  }

  return (
    <div className="space-y-6">
      <MediaBin projectId={projectId} canEdit={canEdit} />
      {canEdit && <section className="studio-panel space-y-5 p-5">
        <div><p className="studio-eyebrow mb-2">Direction</p><h2 className="text-[20px] font-semibold tracking-[-.03em]">Describe the edit</h2></div>
        <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={3} maxLength={2000} placeholder="Create a premium phonk shoe-store Reel with smooth velocity ramps, flashes, motion blur and perfectly timed transitions."
          className="studio-input w-full resize-none !rounded-xl !p-4 !text-[16px] !leading-6" aria-label="Edit instructions" />
        <div className="flex flex-wrap gap-2">{IDEAS.map((i) => <button key={i} type="button" onClick={() => setPrompt(i)} className="rounded-full border border-line px-3 py-1.5 text-[12px] text-muted hover:border-accent/60 hover:text-ink">{i}</button>)}</div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="studio-label">Creative style<select className="studio-input" value={style} onChange={(e) => setStyle(e.target.value)}>{STYLES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
          <label className="studio-label">Duration<select className="studio-input" value={duration} onChange={(e) => setDuration(Number(e.target.value))}>{[10, 15, 20, 30, 45, 60].map((d) => <option key={d} value={d}>{d} seconds</option>)}</select></label>
          <label className="studio-label">Aspect ratio<select className="studio-input" value={aspect} onChange={(e) => setAspect(e.target.value)}>{[["9:16", "9:16 Reel / Short"], ["4:5", "4:5 Feed"], ["1:1", "1:1 Square"], ["16:9", "16:9 Landscape"]].map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
          <label className="studio-label">Music<select className="studio-input" value={music} onChange={(e) => setMusic(e.target.value as typeof music)}>
            <option value="upload" disabled={!hasMusic}>{hasMusic ? "My uploaded track (beat-synced)" : "My track (upload one above)"}</option>
            <option value="score">Original synthesized score</option><option value="none">No music (footage sound)</option></select></label>
          <label className="studio-label">Narration voice<select className="studio-input" value={voice} onChange={(e) => setVoice(e.target.value)}>
            <option value="none">No narration</option>
            {(voices.data ?? [{ id: "kokoro:af_heart", label: "Heart (built-in)" }, { id: "kokoro:af_bella", label: "Bella (built-in)" }, { id: "kokoro:am_adam", label: "Adam (built-in)" }]).map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}</select></label>
          <label className="studio-label">Quality<select className="studio-input" value={quality} onChange={(e) => setQuality(e.target.value)}><option value="draft">Draft (fast)</option><option value="looks">Standard</option><option value="delivery">Delivery (best)</option></select></label>
        </div>
        {voice !== "none" && <label className="studio-label">Narration language<select className="studio-input" value={language} onChange={(e) => setLanguage(e.target.value)}><option value="en">English</option><option value="hi">Hindi</option><option value="hinglish">Hinglish</option></select></label>}
        {voice !== "none" && <label className="studio-label">Narration script (optional — the director writes one if empty)<textarea className="studio-input resize-none" rows={2} maxLength={1500} value={narration} onChange={(e) => setNarration(e.target.value)} /></label>}
        <CaptionPicker value={caption} onChange={setCaption} needsSpeech={voice === "none" ? "Captions follow spoken words: choose a narration voice above, otherwise only the director's short on-screen text appears." : undefined} />
        {music === "upload" && hasMusic && <details className="rounded-xl border border-line bg-surface p-3 text-[13px]">
          <summary className="cursor-pointer font-semibold">Beat grid <span className="font-normal text-muted">· detected {String((all.find((a) => a.kind === "audio")?.analysis as { tempo_bpm?: number } | null)?.tempo_bpm ?? "?")} BPM; correct it if cuts feel early, late or at half speed</span></summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <label className="studio-label">Shift beats ({beatOffset > 0 ? "+" : ""}{beatOffset} ms)<input type="range" min={-500} max={500} step={10} value={beatOffset} onChange={(e) => setBeatOffset(Number(e.target.value))} /></label>
            <label className="studio-label">Force tempo (BPM, optional)<input type="number" min={50} max={220} step={0.1} className="studio-input" placeholder="auto" value={bpm} onChange={(e) => setBpm(e.target.value)} /></label>
          </div>
        </details>}
        {hasReference && <label className="flex items-center gap-2 text-[13px]"><input type="checkbox" checked={useReference} onChange={(e) => setUseReference(e.target.checked)} />Follow the reference reel&apos;s editing rhythm and transitions (never its footage, music or branding)</label>}
        <div className="flex flex-wrap items-center gap-3">
          <button type="button" className="studio-button !px-5 !py-3" disabled={!base || !hasClips || busy || !!active} onClick={generate}>
            {busy ? <LoaderCircle size={16} className="animate-spin" aria-hidden /> : <Wand2 size={16} aria-hidden />}Generate professional edit</button>
          {!hasClips && <span className="text-[12px] text-muted">Upload at least one clip or image first.</span>}
          {active && <span className="text-[12px] text-muted">An edit is in progress.</span>}
          {!base && <span className="text-[12px] text-danger">The processing machine is offline.</span>}
        </div>
        {error && <p role="alert" className="text-[13px] text-danger">{error}</p>}
      </section>}
      <section className="space-y-4">
        <h2 className="text-[17px] font-semibold tracking-[-.02em]">Edits</h2>
        {gens.data?.length === 0 && <p className="text-[13px] text-muted">No edits yet.</p>}
        {gens.data?.map((g) => <GenerationCard key={g.id} g={g} base={base} projectId={projectId} />)}
      </section>
    </div>
  );
}

function GenerationCard({ g, base, projectId }: { g: Generation; base: string | null; projectId: string }) {
  const running = ["queued", "planning", "rendering"].includes(g.status);
  const files = useQuery({
    queryKey: ["edit-files", g.id, base], enabled: !!base && !!g.render_id && g.status === "ready", staleTime: 3 * 3600_000,
    queryFn: async () => {
      const [list, urls] = await Promise.all([apiFetch(base!, `/projects/${projectId}/edits`), apiFetch(base!, `/renders/${g.render_id}/urls`)]);
      const row = list.ok ? ((await list.json()) as { id: string; files?: string }[]).find((x) => x.id === g.id) : undefined;
      return { folder: row?.files, urls: urls.ok ? ((await urls.json()) as { video: string; download: string }) : undefined };
    },
  });
  const root = base?.replace(/\/$/, "") ?? "";
  const d = g.director;
  return (
    <article className="studio-panel space-y-4 p-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0"><p className="text-[14px] font-semibold">“{g.prompt}”</p>
          <p className="mt-1 text-[11px] text-muted">{new Date(g.created_at).toLocaleString()} · {String(g.settings.duration_s)} s · {String(g.settings.aspect)} · music: {String(g.settings.music)}</p></div>
        <span className={`studio-pill ${g.status === "ready" ? "text-accent" : g.status === "failed" ? "text-danger" : ""}`}>{g.status}</span>
      </header>
      {running && g.job && <div aria-live="polite" className="space-y-1.5"><div className="flex justify-between text-[13px]"><span>{STAGE[g.job.current_stage ?? "queued"] ?? g.job.current_stage}</span><span className="tabular-nums text-muted">{Math.round(g.job.progress * 100)}%</span></div><progress className="h-2 w-full" value={g.job.progress} max={1} /></div>}
      {g.error && g.status !== "ready" && <p role="alert" className="text-[13px] text-danger">{g.error}</p>}
      {d && <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="space-y-2 text-[13px]">
          <p><span className="font-semibold">Treatment:</span> {d.treatment}</p>
          <p className="text-muted">Style {d.profile.replaceAll("_", " ")} · pacing {d.pacing.replaceAll("_", " ")} · look {d.look.replaceAll("_", " ")}{g.plan ? ` · ${g.plan.bpm} BPM · ${g.plan.segments.length} shots${g.plan.reused_shots ? ` (${g.plan.reused_shots} reused with new framing)` : ""}` : ""}</p>
          <p className="text-[11px] text-muted">Planned by {d.provenance.engine === "rules" ? `the rule-based director (${(d.provenance as { errors?: string[] }).errors?.some((e) => /unreachable|returned 5/i.test(e)) ? "no AI model answered" : "the AI plan did not pass validation"})` : d.provenance.engine}</p>
          {d.reasons.length > 0 && <ul className="list-disc space-y-0.5 pl-5 text-[12px] text-muted">{d.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>}
          {d.reference_evidence?.length > 0 && <p className="text-[12px] text-muted">From the reference: {d.reference_evidence.join(" · ")}</p>}
        </div>
        {g.qa?.pass && <ul className="grid grid-cols-2 gap-1.5 text-[12px]">{Object.entries(g.qa.pass).map(([k, ok]) => <li key={k} className="flex items-center gap-1.5">{ok ? <CheckCircle2 size={14} className="text-accent" aria-hidden /> : <XCircle size={14} className="text-danger" aria-hidden />}{QA_LABEL[k] ?? k}</li>)}
          {g.qa.loudness && <li className="col-span-2 text-muted">Measured {g.qa.loudness.integrated_lufs} LUFS · {g.qa.loudness.true_peak_dbtp} dBTP</li>}</ul>}
      </div>}
      {g.plan && <div><p className="mb-2 text-[12px] font-semibold">Storyboard</p><ol className="flex gap-2 overflow-x-auto pb-2">{g.plan.segments.map((s, i) => <li key={i} className="w-[92px] shrink-0 text-[10px]">
        {files.data?.folder && g.qa?.storyboard?.[i]
          // eslint-disable-next-line @next/next/no-img-element
          ? <img src={root + files.data.folder + g.qa.storyboard[i]} alt={`Shot ${i + 1}`} className="aspect-[9/16] w-full rounded-md bg-black object-cover" />
          : <div className="aspect-[9/16] w-full rounded-md bg-surface-2" />}
        <p className="mt-1 tabular-nums">{s.slot[0].toFixed(2)}–{s.slot[1].toFixed(2)} s</p>
        <p className="truncate text-muted" title={d?.clips[s.clip]}>{d?.clips[s.clip] ?? `clip ${s.clip + 1}`}</p>
        <p className="truncate text-muted" title={s.effects.map((e) => e[0]).join(", ")}>{s.effects.map((e) => e[0]).filter((e) => !["grade", "vignette", "grain"].includes(e)).join(", ") || "—"}</p>
        {s.transition_out !== "cut" && <p className="truncate text-accent">→ {s.transition_out.replaceAll("_", " ")}</p>}
      </li>)}</ol></div>}
      {g.status === "ready" && g.render_id && <div className="flex flex-wrap items-start gap-4">
        {files.data?.urls ? <video src={root + files.data.urls.video} controls playsInline className="max-h-[520px] w-full max-w-[300px] rounded-xl bg-black" /> : <p className="text-[12px] text-muted">{base ? "Loading preview…" : "Preview needs the processing machine online."}</p>}
        <div className="flex flex-col gap-2">
          {files.data?.urls && <a href={root + files.data.urls.download} className="studio-button"><Download size={15} aria-hidden />Download MP4</a>}
          <Link href={`/editor/${g.render_id}`} className="studio-button-secondary inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-[13px] font-semibold"><Clapperboard size={15} aria-hidden />Open in timeline editor</Link>
          <Link href="/publishing" className="text-[12px] font-semibold text-accent">Publish or schedule →</Link>
        </div>
      </div>}
    </article>
  );
}
