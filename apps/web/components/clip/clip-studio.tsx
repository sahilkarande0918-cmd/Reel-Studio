"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AudioLines, Captions, Crop, Film, Globe, Languages, Link2, Palette, Scissors, Smile, Sparkles, Upload, Volume2, Wand2, ZoomIn,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { createClipProject } from "@/app/(app)/clip/actions";
import { FONT_CSS, Sample, type CaptionChoice, type Preset } from "@/components/studio/caption-picker";
import { apiFetch, useBackend } from "@/lib/backend";
import { dropHandles, enqueue } from "@/lib/uploads";

/**
 * "Clip long video": one page, one click. Source (link or file, language, genre, range, ratio, layout, SRT) → recipe
 * (clipping, captions, hook, motion graphics, emojis, B-roll, speech cleanup, audio, SFX, zoom, transitions, colour,
 * dubbing, caption translation, brand kit) → Generate: the engine downloads/receives the video, transcribes, finds the
 * clips and renders every one with this recipe (apps/api: Recipe in recordings.py, _auto_render in workers/analyze.py).
 */
type Ratio = "9:16" | "16:9" | "1:1" | "4:5";
const RATIOS: Ratio[] = ["9:16", "16:9", "1:1", "4:5"];
const BOX: Record<Ratio, [number, number]> = { "9:16": [236, 420], "16:9": [420, 236], "1:1": [320, 320], "4:5": [300, 375] };
const LANGS = [["auto", "Auto"], ["en", "English"], ["hi", "Hindi"], ["hinglish", "Hinglish"]] as const;
const GENRES = [["auto", "Auto"], ["podcast", "Podcast / interview"], ["business", "Business"], ["motivational", "Motivational"],
  ["general", "General"], ["education", "Educational / class"]] as const;
const PICKS = [["auto", "Auto"], ["5", "5 clips"], ["10", "10 clips"], ["15", "15 clips"], ["20", "20 clips"], ["30", "30 clips"]] as const;
const LENGTHS = [["auto", "Auto (0m–3m)"], ["15-30", "15–30 s"], ["30-45", "30–45 s"], ["45-60", "45–60 s"], ["60-90", "60–90 s"],
  ["90-180", "90 s–3 m"]] as const;
const CAPTION_LANGS = [["", "Original"], ["en", "English"], ["hi", "Hindi"], ["hinglish", "Hinglish"], ["mr", "Marathi"], ["bn", "Bengali"],
  ["ta", "Tamil"], ["te", "Telugu"], ["gu", "Gujarati"], ["es", "Spanish"], ["fr", "French"], ["de", "German"], ["pt", "Portuguese"],
  ["it", "Italian"], ["id", "Indonesian"], ["ar", "Arabic"], ["ja", "Japanese"], ["ko", "Korean"], ["zh", "Chinese"], ["ru", "Russian"], ["tr", "Turkish"]] as const;
const DUB_LANGS = [["", "Off"], ["en", "English"], ["hi", "Hindi"], ["es", "Spanish"], ["fr", "French"], ["it", "Italian"],
  ["pt", "Portuguese"], ["ja", "Japanese"], ["zh", "Chinese"]] as const;
const HOOKS = [["classic", "Classic"], ["statement", "Statement"], ["editorial", "Editorial"]] as const;
const secs = (v: string) => { if (!v.trim()) return null; const n = v.split(":").map(Number); return n.some(Number.isNaN) ? null : n.reduce((a, x) => a * 60 + x, 0); };

function Toggle({ on, set, label }: { on: boolean; set: (v: boolean) => void; label: string }) {
  return <button type="button" role="switch" aria-checked={on} aria-label={label} onClick={() => set(!on)}
    className={`relative h-6 w-11 shrink-0 rounded-full transition ${on ? "bg-accent" : "bg-surface-3"}`}>
    <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${on ? "left-[22px]" : "left-0.5"}`} />
  </button>;
}

function Row({ icon: Icon, title, hint, children }: { icon: typeof Film; title: string; hint?: string; children: React.ReactNode }) {
  return <div className="flex flex-wrap items-center justify-between gap-3 py-2.5">
    <div className="flex min-w-0 items-center gap-3"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-surface-2 text-sage"><Icon size={16} aria-hidden /></span>
      <div className="min-w-0"><p className="text-[13px] font-semibold">{title}</p>{hint && <p className="text-[11px] text-muted">{hint}</p>}</div></div>
    <div className="flex items-center gap-2">{children}</div>
  </div>;
}

const select = "rounded-lg border border-line bg-surface px-2.5 py-1.5 text-[12px] text-ink outline-none focus-visible:ring-2 focus-visible:ring-accent";

/** Headline tile / preview in the same three looks the renderer draws (rendering/fast.py _hook). */
function Headline({ style, text, scale = 1 }: { style: string; text: string; scale?: number }) {
  if (style === "statement") return <div style={{ fontFamily: '"cap-Archivo"', color: "#fff", textShadow: "0 3px 10px rgba(0,0,0,.6)", lineHeight: 1.05, fontSize: 20 * scale }}>
    <div style={{ fontSize: 10 * scale }}>{text.split(" ").slice(0, -2).join(" ")}</div><div>{text.split(" ").slice(-2).join(" ")}</div></div>;
  if (style === "editorial") return <div style={{ fontFamily: '"cap-Fraunces"', fontStyle: "italic", color: "#C8E06B", fontSize: 18 * scale, textShadow: "0 2px 8px rgba(0,0,0,.5)", lineHeight: 1.1 }}>{text}</div>;
  return <div style={{ fontFamily: '"cap-Archivo"', background: "#fff", color: "#141414", fontSize: 13 * scale, padding: `${3 * scale}px ${8 * scale}px`, lineHeight: 1.15 }}>{text}</div>;
}

export function ClipStudio({ canEdit, kits }: { canEdit: boolean; kits: { id: string; name: string; is_default: boolean }[] }) {
  const router = useRouter();
  const backend = useBackend();
  const base = backend.data?.state === "online" ? backend.data.url : null;
  const [source, setSource] = useState<"link" | "file">("link");
  const [link, setLink] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const handle = useRef<Parameters<typeof enqueue>[3]>(null);
  const [srt, setSrt] = useState<{ name: string; text: string } | null>(null);
  const [rights, setRights] = useState(false);
  const [lang, setLang] = useState("auto");
  const [genre, setGenre] = useState("auto");
  const [range, setRange] = useState({ start: "", end: "" });
  const [ratio, setRatio] = useState<Ratio>("9:16");
  const [layout, setLayout] = useState("auto");
  const [picks, setPicks] = useState("auto");
  const [length, setLength] = useState("auto");
  const [moments, setMoments] = useState("");
  const [caption, setCaption] = useState<CaptionChoice>({ on: true, preset: "creator-yellow", overrides: {} });
  const [family, setFamily] = useState<string | null>(null);
  const [hook, setHook] = useState({ on: true, style: "classic" });
  const [f, setF] = useState({ motion: true, emojis: false, enhance: true, sfx: false, zoom: true, color: false, progress: false });
  const [broll, setBroll] = useState("none");
  const [pace, setPace] = useState("engaging");
  const [transitions, setTransitions] = useState("auto");
  const [dub, setDub] = useState({ lang: "", voice: "female" });
  const [capLang, setCapLang] = useState("");
  const [kit, setKit] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (k: keyof typeof f) => (v: boolean) => setF({ ...f, [k]: v });

  const presets = useQuery({
    queryKey: ["caption-presets", base], enabled: !!base, staleTime: 3600_000,
    queryFn: async () => (await (await apiFetch(base!, "/captions/presets")).json()) as Preset[],
  });
  const families = [...new Set((presets.data ?? []).map((p) => p.family))];
  const current = presets.data?.find((p) => p.id === caption.preset);
  const fam = family ?? current?.family ?? families[0];

  function recipe() {
    const n = picks === "auto" ? null : Number(picks);
    return {
      language: lang,
      analyze: { profile: genre, count: n, duration: genre === "education" ? "30-60" : length, brief: moments,
        range_start_s: secs(range.start), range_end_s: secs(range.end) },
      render: { engine: "auto", quality: "looks", aspect: ratio, layout, pace, captions: caption.on, caption_preset: caption.preset,
        caption_overrides: caption.overrides, emphasis: true, hook_title: hook.on, hook_style: hook.style, motion: f.motion, emojis: f.emojis,
        broll, enhance_audio: f.enhance, sfx: f.sfx, auto_zoom: f.zoom, transitions, color_correct: f.color, progress_bar: f.progress,
        dub_language: dub.lang || null, dub_voice: dub.voice, caption_language: capLang || null, brand_kit_id: kit || null },
    };
  }

  async function generate() {
    setError(null);
    if (!base) return setError("The engine is off or unreachable. Turn it on from the dashboard first.");
    if (source === "link" && !link.trim()) return setError("Paste a YouTube link.");
    if (source === "file" && !file) return setError("Choose a video file.");
    if (!rights) return setError("Confirm that you own this video or have permission to clip it.");
    setBusy(true);
    try {
      const name = source === "file" ? file!.name.replace(/\.[^.]+$/, "") : `Clips · ${new Date().toLocaleString()}`;
      const p = await createClipProject(name);
      if (!p.id) throw new Error(p.error ?? "Could not create the project");
      const body = { recipe: recipe(), ...(srt ? { srt: srt.text } : {}) };
      if (source === "link") {
        const r = await apiFetch(base, "/recordings/import", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ project_id: p.id, url: link.trim(), rights_confirmed: true, ...body }) });
        if (!r.ok) { const d = (await r.json().catch(() => ({}))).detail; throw new Error(typeof d === "string" ? d : "The engine refused the link"); }
      } else {
        enqueue("recording", p.id, file!, handle.current, body); // continues in the background (top-bar upload tray)
      }
      router.push(`/projects/${p.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  }

  const [bw, bh] = BOX[ratio];
  return (
    <div className="space-y-5">
      <style>{FONT_CSS}</style>
      <header><p className="studio-eyebrow">Clip long video</p><h1 className="mt-1 font-serif text-[30px] leading-tight">One long video in, finished Shorts out.</h1>
        <p className="mt-1 text-[13px] text-muted">Choose the recipe once. The engine finds the best moments and renders every clip with it. Everything runs on your processing computer, free.</p></header>
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_440px]">
        <div className="space-y-5">
          {/* ---------------------------------------------------------------- source */}
          <section className="studio-panel space-y-4 p-5">
            <div className="inline-flex rounded-full border border-line p-0.5 text-[12px]">
              {([["link", "Paste link", Link2], ["file", "Upload file", Upload]] as const).map(([v, l, I]) => <button key={v} type="button" onClick={() => setSource(v)}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 ${source === v ? "bg-accent text-accent-ink" : "text-muted"}`}><I size={13} />{l}</button>)}
            </div>
            {source === "link" ? <input type="url" value={link} onChange={(e) => setLink(e.target.value)} placeholder="https://www.youtube.com/watch?v=…"
              className="studio-input w-full" aria-label="YouTube link" />
              : <label onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); const x = e.dataTransfer.files[0]; const h = dropHandles(e); if (x) { setFile(x); void h.then((hs) => { handle.current = hs[0]; }); } }}
                className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border border-dashed border-line bg-surface px-6 py-8 text-center hover:bg-surface-2">
                <Upload size={22} className="text-muted" aria-hidden /><span className="text-[13px]">{file ? `${file.name} · ${(file.size / 1024 ** 2).toFixed(0)} MB` : "Drop a video here, or choose a file"}</span>
                <input type="file" accept="video/*,.mp4,.mov,.mkv,.webm" className="sr-only" onChange={(e) => { setFile(e.target.files?.[0] ?? null); handle.current = null; }} />
              </label>}
            <div className="grid gap-3 text-[12px] sm:grid-cols-2 lg:grid-cols-4">
              <label className="studio-label">Speech language<select className={select} value={lang} onChange={(e) => setLang(e.target.value)}>{LANGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
              <label className="studio-label">Genre<select className={select} value={genre} onChange={(e) => setGenre(e.target.value)}>{GENRES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
              <label className="studio-label">Adjust range<span className="flex gap-1.5"><input className={`${select} w-full`} placeholder="0:00" value={range.start} onChange={(e) => setRange({ ...range, start: e.target.value })} aria-label="Range start" />
                <input className={`${select} w-full`} placeholder="end" value={range.end} onChange={(e) => setRange({ ...range, end: e.target.value })} aria-label="Range end" /></span></label>
              <label className="studio-label">Subtitles (.srt)<span className="flex items-center gap-2"><label className={`${select} cursor-pointer truncate`}>{srt ? srt.name : "Upload SRT"}
                <input type="file" accept=".srt" className="sr-only" onChange={async (e) => { const x = e.target.files?.[0]; if (x) setSrt({ name: x.name, text: await x.text() }); }} /></label>
                {srt && <button type="button" className="text-muted hover:text-ink" onClick={() => setSrt(null)}>clear</button>}</span></label>
            </div>
            <label className="flex items-start gap-2 text-[12px] text-muted"><input type="checkbox" checked={rights} onChange={(e) => setRights(e.target.checked)} className="mt-0.5" />
              I own this video or have permission to clip and repost it.</label>
          </section>

          {/* ---------------------------------------------------------------- recipe */}
          <section className="studio-panel divide-y divide-line px-5 py-2">
            <div className="py-3"><p className="studio-eyebrow">Recipe</p></div>
            <div className="space-y-3 py-3">
              <Row icon={Scissors} title="Clipping" hint="The AI finds complete, distinct moments; fewer when the video supports fewer">
                <select className={select} value={picks} onChange={(e) => setPicks(e.target.value)} aria-label="AI picks">{PICKS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
                <select className={select} value={length} onChange={(e) => setLength(e.target.value)} aria-label="Clip length">{LENGTHS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
              </Row>
              <textarea rows={2} value={moments} onChange={(e) => setMoments(e.target.value)} maxLength={2000} className="studio-input w-full text-[13px]"
                placeholder="Moments to include (optional): e.g. find moments where we talk about pricing and first customers" />
            </div>
            <div className="space-y-3 py-3">
              <p className="text-[11px] font-bold uppercase tracking-[.14em] text-muted">Essentials</p>
              <Row icon={Captions} title="Captions" hint="Word-synced animated captions"><Toggle on={caption.on} set={(v) => setCaption({ ...caption, on: v })} label="Captions" /></Row>
              {caption.on && <div className="space-y-2">
                <div className="flex gap-1.5 overflow-x-auto pb-1">{families.map((x) => <button key={x} type="button" onClick={() => setFamily(x)}
                  className={`shrink-0 rounded-full border px-3 py-1 text-[11px] ${x === fam ? "border-accent bg-accent/10 font-semibold" : "border-line text-muted"}`}>{x}</button>)}</div>
                {presets.isLoading ? <p className="text-[12px] text-muted">Loading caption styles…</p> : !presets.data ? <p className="text-[12px] text-danger">Caption styles need the engine online.</p> :
                  <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">{presets.data.filter((p) => p.family === fam).map((p) => <li key={p.id}>
                    <button type="button" onClick={() => setCaption({ ...caption, preset: p.id, overrides: {} })} aria-pressed={caption.preset === p.id}
                      className={`flex h-24 w-full flex-col items-center justify-center gap-2 overflow-hidden rounded-lg bg-[#23281d] p-2 ring-2 ${caption.preset === p.id ? "ring-accent" : "ring-transparent hover:ring-line"}`}>
                      <Sample look={p.look} words={["To", "get", "started"]} /><span className="text-[10px] text-white/70">{p.name}</span></button></li>)}</ul>}
              </div>}
              <Row icon={Wand2} title="Auto hook" hint="A headline from the clip's own words for the first seconds"><Toggle on={hook.on} set={(v) => setHook({ ...hook, on: v })} label="Auto hook" /></Row>
              {hook.on && <div className="grid grid-cols-3 gap-2">{HOOKS.map(([v, l]) => <button key={v} type="button" onClick={() => setHook({ ...hook, style: v })} aria-pressed={hook.style === v}
                className={`flex h-24 flex-col items-center justify-between rounded-lg bg-gradient-to-b from-[#3a4a33] to-[#1c2418] p-2 ring-2 ${hook.style === v ? "ring-accent" : "ring-transparent hover:ring-line"}`}>
                <span className="mt-2"><Headline style={v} text="Start creating today" scale={0.8} /></span><span className="text-[10px] text-white/80">{l}</span></button>)}</div>}
              <Row icon={Sparkles} title="Motion graphics" hint="Key-number callouts and a topic lower third"><Toggle on={f.motion} set={set("motion")} label="Motion graphics" /></Row>
              <Row icon={Smile} title="AI emojis" hint="A sticker where a word calls for one"><Toggle on={f.emojis} set={set("emojis")} label="AI emojis" /></Row>
              <Row icon={Film} title="Auto B-roll" hint="Cutaways at key moments (stock video needs a free Pexels key on the engine)">
                <select className={select} value={broll} onChange={(e) => setBroll(e.target.value)} aria-label="Auto B-roll"><option value="none">Off</option><option value="stock">Stock B-roll</option><option value="ai">AI video B-roll (slow)</option></select></Row>
              <Row icon={AudioLines} title="Speech cleanup" hint="Remove pauses and filler words">
                <select className={select} value={pace} onChange={(e) => setPace(e.target.value)} aria-label="Speech cleanup"><option value="original">Off</option><option value="natural">Natural</option><option value="engaging">Remove pauses & filler words</option><option value="fast">Fast</option></select></Row>
              <Row icon={Volume2} title="Enhance audio" hint="Denoise, level and polish the voice"><Toggle on={f.enhance} set={set("enhance")} label="Enhance audio" /></Row>
              <Row icon={Sparkles} title="Auto SFX" hint="Subtle whoosh and impacts on titles and zooms"><Toggle on={f.sfx} set={set("sfx")} label="Auto SFX" /></Row>
            </div>
            <div className="space-y-1 py-3">
              <p className="text-[11px] font-bold uppercase tracking-[.14em] text-muted">Look good</p>
              <Row icon={ZoomIn} title="Auto zoom" hint="Punch-ins on the words that carry the point"><Toggle on={f.zoom} set={set("zoom")} label="Auto zoom" /></Row>
              <Row icon={Crop} title="Auto transitions" hint="Smooth changes between speakers and cuts">
                <select className={select} value={transitions} onChange={(e) => setTransitions(e.target.value)} aria-label="Auto transitions"><option value="none">Off</option><option value="auto">Auto</option><option value="fade">Fade</option><option value="slide">Slide</option><option value="flash">Flash</option></select></Row>
              <Row icon={Palette} title="Auto colour correction"><Toggle on={f.color} set={set("color")} label="Auto colour correction" /></Row>
              <Row icon={Film} title="Progress bar"><Toggle on={f.progress} set={set("progress")} label="Progress bar" /></Row>
            </div>
            <div className="space-y-1 py-3">
              <p className="text-[11px] font-bold uppercase tracking-[.14em] text-muted">Translate</p>
              <Row icon={Globe} title="Voice dubbing" hint="Translated voice, timed to the speaker (built-in voices)">
                <select className={select} value={dub.lang} onChange={(e) => setDub({ ...dub, lang: e.target.value })} aria-label="Dubbing language">{DUB_LANGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
                {dub.lang && <select className={select} value={dub.voice} onChange={(e) => setDub({ ...dub, voice: e.target.value })} aria-label="Dubbing voice"><option value="female">Female voice</option><option value="male">Male voice</option></select>}
              </Row>
              <Row icon={Languages} title="Caption translation">
                <select className={select} value={capLang} onChange={(e) => setCapLang(e.target.value)} aria-label="Caption language" disabled={!!dub.lang}>{CAPTION_LANGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></Row>
            </div>
          </section>
          {error && <p role="alert" className="text-[13px] text-danger">{error}</p>}
        </div>

        {/* ---------------------------------------------------------------- live preview */}
        <aside className="space-y-4 xl:sticky xl:top-20 xl:self-start">
          <section className="studio-panel space-y-4 p-5">
            <div className="flex items-center justify-between gap-2">
              <div className="inline-flex rounded-full border border-line p-0.5 text-[12px]">{RATIOS.map((r) => <button key={r} type="button" onClick={() => setRatio(r)}
                className={`rounded-full px-3 py-1 ${ratio === r ? "bg-accent text-accent-ink" : "text-muted"}`}>{r}</button>)}</div>
              <select className={select} value={layout} onChange={(e) => setLayout(e.target.value)} aria-label="Layout"><option value="auto">Auto layout</option><option value="fill">Fill</option><option value="fit">Fit</option></select>
            </div>
            <div className="grid place-items-center">
              <div className="relative overflow-hidden rounded-2xl bg-gradient-to-b from-[#5b6b4f] via-[#2f3a2a] to-[#151a12] shadow-xl" style={{ width: bw, height: bh }}>
                {layout === "fit" && <div className="absolute inset-x-0 top-1/2 h-[40%] -translate-y-1/2 bg-[#7e8e6f]/60" />}
                <div className="absolute inset-x-0 bottom-0 h-[62%] bg-[radial-gradient(ellipse_at_50%_100%,rgba(255,255,255,.18),transparent_60%)]" aria-hidden />
                {f.progress && <div className="absolute left-0 top-0 h-1 w-2/5 bg-accent" />}
                {hook.on && <div className="absolute inset-x-0 top-[12%] flex justify-center px-3 text-center"><Headline style={hook.style} text="Price on value, not cost" /></div>}
                {f.motion && <div className="absolute left-3 top-[58%] bg-[#141414] px-2 py-1 text-[11px] font-bold text-white" style={{ fontFamily: '"cap-Archivo"' }}>Pricing strategy</div>}
                {f.emojis && <div className="absolute inset-x-0 bottom-[30%] text-center text-[26px]" aria-hidden>💰</div>}
                {caption.on && current && <div className="absolute inset-x-2 bottom-[14%] flex justify-center"><Sample look={current.look} size={Math.round(bw / 11)} words={["Price", "on", "value"]} /></div>}
                {dub.lang && <span className="absolute right-2 top-2 rounded bg-black/60 px-1.5 text-[10px] text-white">Dubbed · {dub.lang}</span>}
              </div>
            </div>
            <label className="studio-label">Brand kit<select className={select} value={kit} onChange={(e) => setKit(e.target.value)}>
              <option value="">Organisation default</option><option value="none">No brand kit</option>{kits.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}</select></label>
            <button type="button" disabled={!canEdit || busy} onClick={generate}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-accent px-4 py-3 text-[14px] font-semibold text-white hover:bg-forest disabled:opacity-60">
              <Scissors size={16} aria-hidden />{busy ? "Starting…" : "Get clips"}</button>
            <p className="text-[11px] leading-5 text-muted">You can close this page: the engine keeps working and the clips appear in the project as they finish.
              Scores are editorial ranking aids, not view predictions. Nothing is published automatically.</p>
          </section>
        </aside>
      </div>
    </div>
  );
}
