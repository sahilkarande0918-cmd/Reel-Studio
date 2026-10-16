"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Clapperboard, Code2, Download, Film, LoaderCircle, Mic, Pencil, Plus, RefreshCw, Sparkles, Trash2, Wand2, X } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { apiErrorMessage, apiFetch, useBackend } from "@/lib/backend";
import { friendlyError } from "@/lib/friendly-error";
import { useProjectJobs } from "@/lib/realtime";
import { StylePicker, type StylePreset } from "./style-picker";
import { createClient } from "@/lib/supabase/client";

type Scene = { title: string; narration: string; code: string; code_language: "json" | "xml" | "python" | "text" };
type Storyboard = { title: string; scenes: Scene[] };
type Generation = { id: string; status: string; topic: string; settings: Record<string, unknown> | null; storyboard: Storyboard | null; render_id: string | null; job_id: string | null; error: string | null; created_at: string };

const STEPS = [
  { key: "storyboard", label: "Script", icon: Sparkles },
  { key: "narration", label: "Voiceover", icon: Mic },
  { key: "render", label: "Render", icon: Film },
  { key: "done", label: "Ready", icon: Check },
];
const STAGE_TEXT: Record<string, string> = { queued: "Waiting for the processing machine", storyboard: "Writing the script and code examples", narration: "Recording the voiceover and syncing captions", render: "Rendering your video", done: "Your video is ready" };
const ACTIVE = ["queued", "generating", "rendering"];

async function responseJson(r: Response) {
  const body = await r.json().catch(() => null);
  if (!r.ok) throw new Error(apiErrorMessage(body, r.status));
  if (body === null) throw new Error("The processing machine returned an invalid response.");
  return body;
}

function stepIndex(g: Generation | undefined, stage: string | null | undefined) {
  if (!g) return -1;
  if (g.status === "ready") return 4;
  if (g.status === "rendering" || stage === "render" || stage?.startsWith("render")) return 2;
  if (stage === "narration") return 1;
  return 0;
}

export function TopicStudio({ projectId, canEdit }: { projectId: string; canEdit: boolean }) {
  const backend = useBackend();
  const base = backend.data?.state === "online" ? backend.data.url : null;
  const qc = useQueryClient();
  const jobs = useProjectJobs(projectId);
  const params = useSearchParams();
  const [typed, setTopic] = useState<string | null>(params.get("topic"));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Storyboard | null>(null);
  const [style, setStyle] = useState<StylePreset>("focus");
  const generations = useQuery<Generation[]>({
    queryKey: ["generations", projectId, base], enabled: !!base,
    queryFn: async () => responseJson(await apiFetch(base!, `/projects/${projectId}/generations`)),
    refetchInterval: (q) => q.state.data?.some((g) => ACTIVE.includes(g.status)) ? 3000 : 15000,
  });
  const kits = useQuery({
    queryKey: ["brand-kit-names", projectId],
    queryFn: async () => {
      const sb = createClient();
      const { data: project, error: pe } = await sb.from("projects").select("organization_id").eq("id", projectId).single();
      if (pe) throw pe;
      const { data, error } = await sb.from("brand_kits").select("id, name, is_default").eq("organization_id", project.organization_id).order("created_at");
      if (error) throw error;
      return data as { id: string; name: string; is_default: boolean }[];
    }, staleTime: 60_000,
  });
  const latest = generations.data?.find((g) => g.id === selectedId) ?? generations.data?.[0];
  const job = jobs.data?.find((j) => j.id === latest?.job_id);
  const topic = typed ?? latest?.topic ?? "";
  const busy = submitting || !!generations.data?.some((g) => ACTIVE.includes(g.status));
  const step = stepIndex(latest, job?.current_stage);
  const failed = latest && ["failed", "cancelled"].includes(latest.status);
  const rawError = latest?.error || job?.error;

  async function start(body: Record<string, unknown>) {
    if (!base || !canEdit) return;
    setError(null); setSubmitting(true);
    try {
      const result = await responseJson(await apiFetch(base, `/projects/${projectId}/generate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }));
      setSelectedId(result.generation_id); setDraft(null);
      await Promise.all([qc.invalidateQueries({ queryKey: ["generations", projectId] }), qc.invalidateQueries({ queryKey: ["jobs", projectId] })]);
    } catch (e) { setError(e instanceof Error ? e.message : "The request failed. Please try again."); }
    finally { setSubmitting(false); }
  }
  function generate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const v = new FormData(event.currentTarget);
    void start({ topic: topic.trim(), audience: v.get("audience"), language: "en", tone: v.get("tone"), difficulty: v.get("difficulty"), voice: v.get("voice"), duration_s: Number(v.get("duration_s")), quality: v.get("quality"), brand_kit_id: v.get("brand_kit_id") || null, style });
  }
  function renderEdited() {
    if (!latest?.settings || !draft) return;
    const settings = { ...latest.settings }; delete settings.storyboard;
    void start({ ...settings, topic: latest.topic, storyboard: draft });
  }

  return (
    <div className="space-y-6">
      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_400px]">
        <form onSubmit={generate} className="studio-panel p-5 sm:p-6">
          <h2 className="text-[18px] font-semibold tracking-[-.02em]">What should the video explain?</h2>
          <fieldset disabled={!canEdit || submitting} className="mt-4 space-y-5 disabled:opacity-70">
            <label className="block"><span className="sr-only">Topic</span><textarea value={topic} onChange={(e) => setTopic(e.target.value)} name="topic" minLength={3} maxLength={500} required rows={3} placeholder="Explain JSON vs XML with a simple example. Show how the same data looks in both formats." className="studio-input resize-y !rounded-xl !p-4 !text-[17px] !leading-7" /></label>
            <div className="flex flex-wrap gap-2">{["JSON vs XML", "Python lists vs tuples", "How HTTP requests work"].map((example) => <button key={example} type="button" onClick={() => setTopic(example)} className="rounded-full border border-line px-3 py-1.5 text-[12px] text-muted transition-colors hover:border-accent hover:text-accent">{example}</button>)}</div>
            <StylePicker value={style} onChange={setStyle} />
            <div className="grid gap-4 sm:grid-cols-3">
              <label className="studio-label">Voice (English)<select name="voice" className="studio-input"><option value="af_heart">Heart · warm female</option><option value="af_bella">Bella · bright female</option><option value="am_adam">Adam · calm male</option></select></label>
              <label className="studio-label">Duration<select name="duration_s" defaultValue="45" className="studio-input"><option value="30">30 seconds</option><option value="45">45 seconds</option><option value="60">60 seconds</option></select></label>
              <label className="studio-label">Brand kit<select name="brand_kit_id" className="studio-input"><option value="">Workspace default</option>{kits.data?.map((kit) => <option key={kit.id} value={kit.id}>{kit.name}{kit.is_default ? " (default)" : ""}</option>)}<option value="none">No branding</option></select></label>
            </div>
            <details className="group rounded-xl border border-line px-4 py-3">
              <summary className="cursor-pointer list-none text-[13px] font-medium text-muted group-open:text-ink">Advanced settings <span className="text-[11.5px]">· audience, level, tone, quality</span></summary>
            <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <label className="studio-label">Audience<input name="audience" defaultValue="Beginners learning to code" required maxLength={120} className="studio-input" /></label>
              <label className="studio-label">Level<select name="difficulty" className="studio-input"><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></label>
              <label className="studio-label">Tone<select name="tone" className="studio-input"><option value="clear">Clear & focused</option><option value="conversational">Conversational</option><option value="energetic">Energetic</option></select></label>
              <label className="studio-label">Quality<select name="quality" defaultValue="looks" className="studio-input"><option value="draft">Draft · fastest</option><option value="looks">Standard</option><option value="delivery">Best</option></select></label>
            </div>
            </details>
          </fieldset>
          <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5">
            <span className="flex items-center gap-1.5 text-[12px] text-muted"><Mic size={14} aria-hidden /> Runs on your own machine · 1080×1920 MP4</span>
            {canEdit && <button type="submit" disabled={!base || busy || topic.trim().length < 3} className="studio-button !px-5 !py-3">{busy ? <LoaderCircle size={16} className="animate-spin" aria-hidden /> : <Wand2 size={16} aria-hidden />}{busy ? "Generating…" : latest ? "Generate new version" : "Generate video"}</button>}
          </div>
          {!canEdit && <p className="mt-3 text-[12px] text-muted">You have view access. An editor can generate videos.</p>}
          {!base && <p className="mt-3 text-[12px] text-muted">{backend.isLoading ? "Connecting to the processing machine…" : "The processing machine is offline. Your project is saved; generate when it is back online."}</p>}
          {error && <p role="alert" className="mt-3 rounded-lg bg-danger/10 ring-1 ring-danger/25 px-3 py-2 text-[13px] text-danger">{error}</p>}
        </form>

        <section className="studio-panel overflow-hidden">
          <div className="flex items-center justify-between border-b border-line px-5 py-3.5"><h2 className="text-[14px] font-semibold">Preview</h2>{latest && <span className="text-[12px] text-muted">{STAGE_TEXT[job?.current_stage ?? ""] ?? (latest.status === "ready" ? STAGE_TEXT.done : latest.status)}</span>}</div>
          {latest && !failed && <ol className="grid grid-cols-4 gap-1 border-b border-line px-5 py-4" aria-label="Generation progress">{STEPS.map((s, i) => {
            const done = step > i || (i === 3 && step === 4); const now = step === i && busy;
            return <li key={s.key} className="flex flex-col items-center gap-1.5 text-center">
              <span className={`grid h-8 w-8 place-items-center rounded-full transition-colors ${done ? "bg-success/15 text-success" : now ? "bg-accent text-accent-ink" : "bg-surface-2 text-muted"}`}>{now ? <LoaderCircle size={15} className="animate-spin" aria-hidden /> : done ? <Check size={15} aria-hidden /> : <s.icon size={15} aria-hidden />}</span>
              <span className={`text-[11px] ${done || now ? "font-semibold text-ink" : "text-muted"}`}>{s.label}</span>
            </li>;
          })}</ol>}
          {latest && busy && job && <div className="px-5 pt-4"><div className="h-1.5 overflow-hidden rounded-full bg-surface-2"><div className="h-full rounded-full bg-accent transition-[width] duration-700" style={{ width: `${Math.max(3, Math.round(job.progress * 100))}%` }} /></div><p className="mt-1.5 text-right text-[11px] tabular-nums text-muted">{Math.round(job.progress * 100)}% · usually 3–5 minutes</p></div>}
          {failed && rawError && <FriendlyFailure raw={rawError} />}
          {latest?.render_id && latest.status === "ready" ? <TopicExport renderId={latest.render_id} base={base} /> : <div className="p-6"><div className="mx-auto flex aspect-[9/16] max-h-[380px] flex-col justify-between rounded-2xl bg-[var(--canvas)] p-6 text-[var(--canvas-ink)]"><Code2 size={28} strokeWidth={1.4} aria-hidden /><div><p className="text-[10px] uppercase tracking-[.18em] opacity-60">{busy ? "Working on it" : "Nothing rendered yet"}</p><p className="mt-3 text-[22px] font-semibold leading-tight tracking-[-.03em]">{latest?.storyboard?.title ?? (topic || "Your topic, explained in under a minute.")}</p></div><span className="text-[11px] opacity-60">Script → Voice → Code → Reel</span></div></div>}
        </section>
      </div>

      <section className="studio-panel p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><h2 className="text-[18px] font-semibold tracking-[-.02em]">Script & storyboard</h2><p className="mt-1 text-[13px] text-muted">{draft ? "Edit the narration and code, then re-record and render. Code is checked before anything is rendered." : "Each scene pairs narration with a code card in the video."}</p></div>
          <div className="flex flex-wrap items-center gap-2">
            {!!generations.data?.length && !draft && <label><span className="sr-only">Version</span><select className="studio-input !w-auto !py-2" value={latest?.id ?? ""} onChange={(e) => setSelectedId(e.target.value)}>{generations.data.map((g, i) => <option key={g.id} value={g.id}>Version {generations.data!.length - i} · {g.status}</option>)}</select></label>}
            {!draft && <button type="button" aria-label="Refresh" disabled={!base || generations.isFetching} onClick={() => generations.refetch()} className="rounded-lg border border-line p-2.5 text-muted hover:text-ink disabled:opacity-40"><RefreshCw size={15} className={generations.isFetching ? "animate-spin" : ""} aria-hidden /></button>}
            {canEdit && latest?.storyboard && !draft && <button type="button" disabled={busy} onClick={() => setDraft(structuredClone(latest.storyboard!))} className="studio-button studio-button-secondary"><Pencil size={15} aria-hidden />Edit script</button>}
            {draft && <><button type="button" onClick={() => setDraft(null)} className="studio-button studio-button-secondary"><X size={15} aria-hidden />Discard</button><button type="button" disabled={!base || busy} onClick={renderEdited} className="studio-button">{submitting ? <LoaderCircle size={15} className="animate-spin" aria-hidden /> : <Film size={15} aria-hidden />}Record & render edits</button></>}
            {latest?.render_id && latest.status === "ready" && !draft && <Link href={`/editor/${latest.render_id}`} className="studio-button studio-button-secondary"><Clapperboard size={15} aria-hidden />Open in editor</Link>}
          </div>
        </div>
        {generations.error && <p role="alert" className="mt-4 text-[13px] text-danger">Could not load versions. {friendlyError(generations.error.message).title}</p>}
        {draft ? <StoryboardEditor board={draft} onChange={setDraft} /> : latest?.storyboard?.scenes?.length ? <div className="mt-6 grid gap-4 lg:grid-cols-2">{latest.storyboard.scenes.map((scene, i) => <article key={i} className="rounded-xl border border-line p-4">
          <div className="flex items-baseline gap-3"><span className="text-[12px] font-semibold tabular-nums text-accent">{String(i + 1).padStart(2, "0")}</span><h3 className="text-[15px] font-semibold">{scene.title}</h3></div>
          <p className="mt-2 text-[13.5px] leading-6 text-muted">{scene.narration}</p>
          {scene.code && <div className="mt-3 min-w-0 rounded-lg bg-[var(--canvas)] p-3.5 text-[var(--canvas-ink)]"><span className="text-[10px] font-semibold uppercase tracking-wider opacity-60">{scene.code_language}</span><pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words font-mono text-[12px] leading-5 [font-variant-ligatures:none]"><code>{scene.code}</code></pre></div>}
        </article>)}</div> : <div className="mt-5 rounded-xl bg-surface-2 p-6 text-[13.5px] leading-6 text-muted">{busy ? "The script appears here as soon as it is written (about a minute)." : "Generate a video to see the scene-by-scene script and code. You can then edit any scene and re-render."}</div>}
      </section>
    </div>
  );
}

function StoryboardEditor({ board, onChange }: { board: Storyboard; onChange: (b: Storyboard) => void }) {
  const set = (i: number, patch: Partial<Scene>) => onChange({ ...board, scenes: board.scenes.map((s, j) => j === i ? { ...s, ...patch } : s) });
  const words = board.scenes.reduce((n, s) => n + s.narration.split(/\s+/).filter(Boolean).length, 0);
  return <div className="mt-6 space-y-4">
    <label className="studio-label">Video title<input value={board.title} maxLength={120} onChange={(e) => onChange({ ...board, title: e.target.value })} className="studio-input" /></label>
    {board.scenes.map((s, i) => <fieldset key={i} className="grid gap-4 rounded-xl border border-line p-4 lg:grid-cols-2">
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2"><legend className="text-[12px] font-semibold text-accent">Scene {i + 1}</legend>{board.scenes.length > 2 && <button type="button" onClick={() => onChange({ ...board, scenes: board.scenes.filter((_, j) => j !== i) })} className="flex items-center gap-1 text-[12px] text-muted hover:text-danger"><Trash2 size={13} aria-hidden />Remove</button>}</div>
        <label className="studio-label">Title<input value={s.title} maxLength={80} onChange={(e) => set(i, { title: e.target.value })} className="studio-input" /></label>
        <label className="studio-label">Narration<textarea value={s.narration} rows={5} maxLength={1500} onChange={(e) => set(i, { narration: e.target.value })} className="studio-input resize-y leading-6" /></label>
      </div>
      <div className="space-y-3">
        <label className="studio-label">Code type<select value={s.code_language} onChange={(e) => set(i, { code_language: e.target.value as Scene["code_language"] })} className="studio-input"><option value="json">JSON</option><option value="xml">XML</option><option value="python">Python</option><option value="text">Plain text</option></select></label>
        <label className="studio-label">Code shown on screen<textarea value={s.code} rows={8} maxLength={2500} spellCheck={false} onChange={(e) => set(i, { code: e.target.value })} className="studio-input resize-y !bg-[var(--canvas)] font-mono !text-[12.5px] leading-5 !text-[var(--canvas-ink)] [font-variant-ligatures:none]" /></label>
      </div>
    </fieldset>)}
    <div className="flex flex-wrap items-center justify-between gap-3">
      {board.scenes.length < 6 && <button type="button" onClick={() => onChange({ ...board, scenes: [...board.scenes, { title: "New scene", narration: "", code: "", code_language: "text" }] })} className="studio-button studio-button-secondary"><Plus size={15} aria-hidden />Add scene</button>}
      <span className="text-[12px] text-muted">{words} spoken words ≈ {Math.round(words / 2.8)} seconds</span>
    </div>
  </div>;
}

function FriendlyFailure({ raw }: { raw: string }) {
  const f = friendlyError(raw);
  return <div role="alert" className="m-5 rounded-xl bg-danger/10 ring-1 ring-danger/25 p-4 text-[13px]">
    <p className="font-semibold text-danger">{f.title}</p><p className="mt-1 leading-5 text-ink/80">{f.hint}</p>
    <details className="mt-2 text-[11.5px] text-muted"><summary className="cursor-pointer">Technical details</summary><p className="mt-1 break-words font-mono">{raw.slice(0, 600)}</p></details>
  </div>;
}

function TopicExport({ renderId, base }: { renderId: string; base: string | null }) {
  const [error, setError] = useState<string | null>(null);
  const render = useQuery({ queryKey: ["topic-render", renderId], queryFn: async () => {
    const { data, error } = await createClient().from("render_jobs").select("id,status,duration_s,size_bytes,error").eq("id", renderId).single();
    if (error) throw error;
    return data;
  }, refetchInterval: (q) => ["ready", "failed", "cancelled"].includes(q.state.data?.status ?? "") ? false : 3000 });
  const urls = useQuery<{ video: string; thumb: string; download: string }>({ queryKey: ["render-urls", renderId, base], enabled: !!base && render.data?.status === "ready", staleTime: 60 * 60 * 1000,
    queryFn: async () => {
      const data = await responseJson(await apiFetch(base!, `/renders/${renderId}/urls`));
      const b = base!.replace(/\/$/, "");
      return { video: `${b}${data.video}`, thumb: `${b}${data.thumb}`, download: `${b}${data.download}` };
    },
  });
  async function download(format: "mp4" | "srt" | "vtt") {
    setError(null);
    try {
      const r = format === "mp4" ? await fetch(urls.data!.download, { headers: { "X-Tunnel-Skip-AntiPhishing-Page": "true" } }) : await apiFetch(base!, `/renders/${renderId}/captions?format=${format}`);
      if (!r.ok) throw new Error("Download failed. Check that the processing machine is online and try again.");
      const url = URL.createObjectURL(await r.blob());
      Object.assign(document.createElement("a"), { href: url, download: `topic-${renderId.slice(0, 8)}.${format}` }).click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) { setError(e instanceof Error ? e.message : "Download failed."); }
  }
  return <div className="p-5">
    {urls.data ? <video controls playsInline preload="metadata" src={urls.data.video} poster={urls.data.thumb} className="mx-auto aspect-[9/16] max-h-[520px] w-full rounded-2xl bg-[var(--canvas)]" /> : <div className="flex aspect-[9/16] max-h-[420px] flex-col items-center justify-center gap-3 rounded-2xl bg-surface-2 p-6 text-center"><Film size={30} strokeWidth={1.3} className="text-accent" aria-hidden /><p className="text-[13px] text-muted">{!base ? "Connect the processing machine to play this video." : "Loading your video…"}</p></div>}
    {render.data?.status === "ready" && <p className="mt-3 flex items-center gap-2 text-[12px] text-muted"><Check size={14} className="text-success" aria-hidden />{render.data.duration_s?.toFixed(1)} s · {((render.data.size_bytes ?? 0) / 1024 ** 2).toFixed(1)} MB · 1080×1920</p>}
    {urls.data && <div className="mt-3 flex flex-wrap gap-2"><button type="button" className="studio-button flex-1" onClick={() => download("mp4")}><Download size={15} aria-hidden />Download MP4</button>{(["srt", "vtt"] as const).map((f) => <button key={f} type="button" title={`Download ${f.toUpperCase()} captions`} className="studio-button studio-button-secondary uppercase" onClick={() => download(f)}>{f}</button>)}</div>}
    {(error || render.error || urls.error) && <p role="alert" className="mt-3 text-[12px] text-danger">{error || friendlyError(render.error?.message || urls.error?.message || "").title}</p>}
  </div>;
}
