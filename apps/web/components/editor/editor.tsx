"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, Copy, Download, Film, Image as ImageIcon, LoaderCircle, Music, Pause, Play, Redo2, RotateCcw, Scissors, Trash2, Type, Undo2, ZoomIn, ZoomOut, Code2, Captions, Palette } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Composition } from "@reel-studio/timeline-schema";
import { addItem, duplicate, findItem, newId, normalize, remove, splitAt, update, type Item } from "@reel-studio/timeline-schema/edit";
import { apiErrorMessage, apiFetch, useBackend } from "@/lib/backend";
import { friendlyError } from "@/lib/friendly-error";
import { createClient } from "@/lib/supabase/client";
import { StylePicker, type StylePreset } from "@/components/studio/style-picker";
import { ItemProperties, Num, Section } from "./properties";
import { fmt, TimelinePanel } from "./timeline-panel";
import { usePreview } from "./use-preview";

type Props = { renderId: string; projectId: string; orgId: string; projectName: string; initial: Composition; draft: { timeline: Composition; updated_at: string } | null; canEdit: boolean };
type Hist = { past: Composition[]; doc: Composition; future: Composition[]; key?: string; at: number };

export function Editor({ renderId, projectId, orgId, projectName, initial, draft, canEdit }: Props) {
  const backend = useBackend();
  const base = backend.data?.state === "online" ? backend.data.url : null;
  const [h, setH] = useState<Hist>({ past: [], doc: draft?.timeline ?? initial, future: [], at: 0 });
  const [live, setLive] = useState<Composition | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [zoom, setZoom] = useState(28);
  const [tab, setTab] = useState<"media" | "text" | "captions" | "brand">("media");
  const [saved, setSaved] = useState<string>(draft ? "Draft restored" : "All changes saved");
  const [message, setMessage] = useState<string | null>(null);
  const frame = useRef<HTMLIFrameElement>(null);
  const stage = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.25);
  const doc = live ?? h.doc;
  const timeRef = useRef(0);
  useEffect(() => { timeRef.current = time; }, [time]);
  const preview = usePreview(base, renderId, h.doc, timeRef);
  const post = (type: string, extra: object = {}) => frame.current?.contentWindow?.postMessage({ type, ...extra }, "*");
  const sel = selected ? findItem(doc, selected)?.item ?? null : null;

  const commit = useCallback((next: Composition, key?: string) => {
    setH((s) => {
      const merge = key && s.key === key && Date.now() - s.at < 1200;
      return { past: merge ? s.past : [...s.past.slice(-80), s.doc], doc: next, future: [], key, at: Date.now() };
    });
  }, []);
  const undo = useCallback(() => setH((s) => s.past.length ? { past: s.past.slice(0, -1), doc: s.past[s.past.length - 1], future: [s.doc, ...s.future], at: 0 } : s), []);
  const redo = useCallback(() => setH((s) => s.future.length ? { past: [...s.past, s.doc], doc: s.future[0], future: s.future.slice(1), at: 0 } : s), []);

  // Autosave the draft (RLS: editors only) so it reopens after a reload or on another device.
  const opened = useRef(h.doc);
  useEffect(() => {
    if (!canEdit || h.doc === opened.current) return;
    setSaved("Saving…");
    const t = setTimeout(async () => {
      const { error } = await createClient().from("timeline_drafts").upsert({ organization_id: orgId, project_id: projectId, base_render_id: renderId, timeline: h.doc }, { onConflict: "base_render_id" });
      setSaved(error ? "Not saved — retrying on next change" : `Saved · ${new Date().toLocaleTimeString()}`);
    }, 1200);
    return () => clearTimeout(t);
  }, [h.doc, canEdit, orgId, projectId, renderId]);

  // Preview iframe <-> editor clock.
  useEffect(() => {
    const on = (e: MessageEvent) => {
      if (e.source !== frame.current?.contentWindow) return;
      const m = e.data || {};
      if (m.type === "rs-time") { setTime(m.t); setPlaying(m.playing); }
      if (m.type === "rs-ready") frame.current?.contentWindow?.postMessage({ type: "rs-seek", t: timeRef.current }, "*");
    };
    addEventListener("message", on);
    return () => removeEventListener("message", on);
  }, []);
  const seek = useCallback((t: number) => { setTime(t); post("rs-seek", { t }); }, []);
  const toggle = useCallback(() => post(playing ? "rs-pause" : "rs-play"), [playing]);

  useEffect(() => {
    const el = stage.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setScale(Math.min(e.contentRect.height / doc.height, e.contentRect.width / doc.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, [doc.height, doc.width]);

  const act = useCallback((name: "split" | "delete" | "duplicate") => {
    if (!canEdit) return;
    if (!selected) return setMessage("Select a clip on the timeline first.");
    if (name === "split") { const next = splitAt(h.doc, selected, time); if (next === h.doc) setMessage("Move the playhead inside the selected clip to split it."); else commit(next); }
    if (name === "delete") { commit(remove(h.doc, selected)); setSelected(null); }
    if (name === "duplicate") { const r = duplicate(h.doc, selected); commit(r.doc); setSelected(r.id); }
  }, [canEdit, selected, h.doc, time, commit]);

  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(tag)) return;
      const mod = e.ctrlKey || e.metaKey;
      if (e.code === "Space") { e.preventDefault(); toggle(); }
      else if (mod && e.key.toLowerCase() === "z") { e.preventDefault(); if (e.shiftKey) redo(); else undo(); }
      else if (mod && e.key.toLowerCase() === "y") { e.preventDefault(); redo(); }
      else if (mod && e.key.toLowerCase() === "d") { e.preventDefault(); act("duplicate"); }
      else if (e.key === "s" || e.key === "S") act("split");
      else if (e.key === "Delete" || e.key === "Backspace") act("delete");
      else if (e.key === "ArrowLeft" || e.key === "ArrowRight") { e.preventDefault(); seek(Math.max(0, Math.min(doc.duration, time + (e.key === "ArrowLeft" ? -1 : 1) * (e.shiftKey ? 1 : 1 / 30)))); }
      else if (e.key === "Escape") setSelected(null);
    };
    addEventListener("keydown", key);
    return () => removeEventListener("keydown", key);
  }, [toggle, undo, redo, act, seek, time, doc.duration]);

  const patch = (p: Partial<Item>, key?: string) => selected && commit(update(h.doc, selected, p), key ? `${selected}:${key}` : undefined);
  const setDoc = (p: Partial<Composition>, key?: string) => commit(normalize({ ...h.doc, ...p }), key);

  function addText() {
    const id = newId("text");
    commit(addItem(h.doc, "text", { id, type: "text", start: Math.round(time * 10) / 10, duration: 3, text: "Your text", x: 80, y: 220, fontSize: 72, align: "left", box: true, transition: "fade" }));
    setSelected(id);
  }
  function addCode() {
    const id = newId("code");
    commit(addItem(h.doc, "overlay", { id, type: "code", start: Math.round(time * 10) / 10, duration: 4, language: "python", title: "Example", code: "print(\"hello\")", typingDuration: 1, changes: [], transition: "zoom" }));
    setSelected(id);
  }
  function addMedia(assetId: string) {
    const a = h.doc.assets[assetId];
    const id = newId(a.kind);
    const len = Math.min(a.duration ?? 5, 5);
    const media = { id, assetId, start: Math.round(time * 10) / 10, duration: len, sourceStart: 0, sourceEnd: len, volume: 1, fadeIn: 0, fadeOut: 0 };
    if (a.kind === "audio") commit(addItem(h.doc, "audio", { ...media, type: "audio" }));
    else {
      const k = (h.doc.tracks.flatMap((t) => t.items).find((i) => i.type === "video" && i.assetId === assetId) as Extract<Item, { type: "video" }> | undefined)?.cropKeyframes[0];
      const w = Math.round(((a.height ?? 1080) * 9) / 16);
      commit(addItem(h.doc, "video", { ...media, type: "video", transition: "none", cropKeyframes: [k ? { ...k, t: 0 } : { t: 0, crop_x: Math.max(0, Math.round(((a.width ?? 1920) - w) / 2)), crop_y: 0, crop_width: w, crop_height: a.height ?? 1080, layout: "crop", region: "centre", transition_mode: "start" }] }));
    }
    setSelected(id);
  }
  async function applyBrand(kitId: string) {
    if (!base) return setMessage("The processing machine is offline.");
    const r = await apiFetch(base, `/renders/${renderId}/brand`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ brand_kit_id: kitId || null }) });
    const body = await r.json().catch(() => null);
    if (!r.ok) return setMessage(apiErrorMessage(body, r.status));
    const assets = { ...h.doc.assets };
    delete assets.logo;
    if (body.logoAsset) assets.logo = body.logoAsset;
    commit(normalize({ ...h.doc, assets, brand: body.brand, captionStyle: { ...h.doc.captionStyle, preset: body.captionPreset } }));
  }

  const kits = useQuery({ queryKey: ["brand-kit-names", orgId], queryFn: async () => (await createClient().from("brand_kits").select("id, name, is_default").eq("organization_id", orgId).order("created_at")).data ?? [] });
  const captionItems = doc.tracks.flatMap((t) => t.items).filter((i): i is Extract<Item, { type: "caption" }> => i.type === "caption");

  return <div className="-mx-4 -my-7 flex h-[calc(100svh-56px)] flex-col text-[var(--rail-ink)] sm:-mx-6 lg:-mx-8">
    {/* top bar */}
    <div className="flex h-12 shrink-0 items-center gap-3 border-b border-line bg-[var(--rail)] px-3">
      <Link href={`/projects/${projectId}`} className="flex items-center gap-1 rounded-md px-2 py-1.5 text-[12.5px] text-muted hover:bg-white/10 hover:text-[var(--rail-ink)]"><ChevronLeft size={15} aria-hidden />{projectName}</Link>
      <span className="hidden text-[12px] text-muted md:inline" aria-live="polite">{saved}</span>
      <div className="ml-auto flex items-center gap-1">
        <IconBtn label="Undo (Ctrl+Z)" onClick={undo} disabled={!h.past.length}><Undo2 size={16} /></IconBtn>
        <IconBtn label="Redo (Ctrl+Shift+Z)" onClick={redo} disabled={!h.future.length}><Redo2 size={16} /></IconBtn>
        {draft && <IconBtn label="Revert to the original render" onClick={() => { commit(initial); setSelected(null); }}><RotateCcw size={16} /></IconBtn>}
      </div>
    </div>
    {message && <div role="status" className="flex items-center justify-between gap-3 border-b border-line bg-accent/10 px-4 py-2 text-[12.5px]"><span>{message}</span><button type="button" onClick={() => setMessage(null)} className="text-muted hover:text-[var(--rail-ink)]">Dismiss</button></div>}

    <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[260px_minmax(0,1fr)_320px]">
      {/* left: assets */}
      <aside className="hidden min-h-0 flex-col border-r border-line bg-[var(--rail)] lg:flex">
        <div className="grid grid-cols-4 border-b border-line p-1">{([["media", Film, "Media"], ["text", Type, "Add"], ["captions", Captions, "Script"], ["brand", Palette, "Brand"]] as const).map(([id, Icon, l]) => <button key={id} type="button" onClick={() => setTab(id)} className={`flex flex-col items-center gap-1 rounded-md py-2 text-[10.5px] ${tab === id ? "bg-white/10 text-[var(--rail-ink)]" : "text-muted hover:text-[var(--rail-ink)]"}`}><Icon size={16} aria-hidden />{l}</button>)}</div>
        <div className="min-h-0 flex-1 overflow-y-auto p-3 text-[12.5px]">
          {tab === "media" && <div className="space-y-2">
            <p className="text-[11px] text-muted">Media in this video. Add a copy at the playhead.</p>
            {Object.values(doc.assets).filter((a) => a.kind === "video" || a.kind === "audio").map((a) => <button key={a.id} type="button" disabled={!canEdit} onClick={() => addMedia(a.id)} className="flex w-full items-center gap-3 rounded-lg border border-white/10 bg-white/5 p-2.5 text-left hover:border-[#3a404e]">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-white/10 text-[#C9D2BD]">{a.kind === "video" ? <Film size={16} aria-hidden /> : <Music size={16} aria-hidden />}</span>
              <span className="min-w-0"><span className="block truncate font-medium">{a.id === "source" ? "Class recording" : a.id}</span><span className="text-[11px] text-muted">{a.kind}{a.duration ? ` · ${fmt(a.duration)}` : ""}</span></span>
            </button>)}
            {Object.values(doc.assets).some((a) => a.kind === "image") && <p className="flex items-center gap-1.5 pt-2 text-[11px] text-muted"><ImageIcon size={13} aria-hidden />Logo is placed by the brand kit.</p>}
          </div>}
          {tab === "text" && <div className="space-y-2">
            <AddBtn icon={Type} title="Text overlay" body="Title, label or call to action" onClick={addText} disabled={!canEdit} />
            <AddBtn icon={Code2} title="Code card" body="Animated, typed code panel" onClick={addCode} disabled={!canEdit} />
          </div>}
          {tab === "captions" && <div className="space-y-3">
            <p className="text-[11px] text-muted">Click a word to jump there. Edit words in the caption block&apos;s properties.</p>
            {captionItems.map((c) => <p key={c.id} className="leading-6">{c.words.map((w, i) => <button key={i} type="button" onClick={() => { seek(c.start + w.start); setSelected(c.id); }} className={`mr-1 rounded px-0.5 hover:bg-white/10 ${time >= c.start + w.start && time < c.start + w.end ? "bg-accent/25 text-ink" : w.isCode ? "font-mono text-accent" : "text-[var(--rail-ink)]/85"}`}>{w.text}</button>)}</p>)}
            {!captionItems.length && <p className="text-muted">No captions in this video.</p>}
          </div>}
          {tab === "brand" && <div className="space-y-4">
            <label className="studio-label">Brand kit<select className="studio-input !py-2" defaultValue="" disabled={!canEdit} onChange={(e) => e.target.value !== "" && applyBrand(e.target.value === "default" ? "" : e.target.value)}><option value="" disabled>Apply a kit…</option><option value="default">Workspace default</option>{kits.data?.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}<option value="none">No branding</option></select></label>
            <p className="text-[11px] leading-4 text-muted">Applies colours, fonts, logo, watermark, intro and outro from the kit.</p>
            <label className="flex items-center gap-2"><input type="checkbox" className="accent-[var(--accent)]" checked={doc.brand.intro.enabled} disabled={!canEdit} onChange={(e) => setDoc({ brand: { ...h.doc.brand, intro: { ...h.doc.brand.intro, enabled: e.target.checked } } })} />Intro card</label>
            <label className="flex items-center gap-2"><input type="checkbox" className="accent-[var(--accent)]" checked={doc.brand.outro.enabled} disabled={!canEdit} onChange={(e) => setDoc({ brand: { ...h.doc.brand, outro: { ...h.doc.brand.outro, enabled: e.target.checked } } })} />Outro card</label>
            <label className="flex items-center gap-2"><input type="checkbox" className="accent-[var(--accent)]" checked={doc.brand.watermark.enabled} disabled={!canEdit} onChange={(e) => setDoc({ brand: { ...h.doc.brand, watermark: { ...h.doc.brand.watermark, enabled: e.target.checked } } })} />Watermark</label>
          </div>}
        </div>
      </aside>

      {/* centre: preview */}
      <section className="flex min-h-0 flex-col bg-[var(--canvas)]">
        <div ref={stage} className="relative min-h-[260px] flex-1 overflow-hidden">
          <div className="absolute left-1/2 top-1/2" style={{ width: doc.width * scale, height: doc.height * scale, transform: "translate(-50%, -50%)" }}>
            {preview.html ? <iframe ref={frame} title="Video preview" srcDoc={preview.html} sandbox="allow-scripts allow-same-origin" style={{ width: doc.width, height: doc.height, transform: `scale(${scale})`, transformOrigin: "0 0" }} className="pointer-events-none rounded-sm border-0 bg-black" />
              : <div className="grid h-full w-full place-items-center rounded-lg border border-line bg-surface text-center text-[12.5px] text-muted"><span className="px-4">{!base ? (backend.isLoading ? "Connecting to the processing machine…" : "Preview needs the processing machine online. Edits still autosave.") : preview.error ? friendlyError(preview.error).title : "Building preview…"}</span></div>}
            {preview.loading && <LoaderCircle size={16} className="absolute right-2 top-2 animate-spin text-muted" aria-label="Updating preview" />}
          </div>
        </div>
        {preview.error && <p role="alert" className="border-t border-line bg-danger/10 px-4 py-2 text-[12px] text-danger">{preview.error}</p>}
        <div className="flex h-11 shrink-0 items-center justify-center gap-3 border-t border-line bg-[var(--rail)] text-[12px]">
          <IconBtn label={playing ? "Pause (Space)" : "Play (Space)"} onClick={toggle} disabled={!preview.html}>{playing ? <Pause size={17} /> : <Play size={17} />}</IconBtn>
          <span className="tabular-nums text-muted"><span className="text-ink">{fmt(time)}</span> / {fmt(doc.duration)}</span>
        </div>
      </section>

      {/* right: properties + export */}
      <aside className="min-h-0 overflow-y-auto border-l border-line bg-[var(--rail)]">
        {sel ? <>
          <div className="flex items-center justify-between border-b border-line px-4 py-3"><h2 className="text-[13px] font-semibold capitalize">{sel.type === "code" ? "Code card" : sel.type} clip</h2><button type="button" onClick={() => setSelected(null)} className="text-[12px] text-muted hover:text-[var(--rail-ink)]">Done</button></div>
          <fieldset disabled={!canEdit}><ItemProperties doc={doc} item={sel} onPatch={patch} /></fieldset>
        </> : <fieldset disabled={!canEdit}>
          <Section title="Style"><StylePicker value={(doc.stylePreset ?? "focus") as StylePreset} onChange={(v) => setDoc({ stylePreset: v })} name="editor-style" compact /></Section>
          <Section title="Captions">
            <label className="studio-label">Caption look<select className="studio-input !py-2" value={doc.captionStyle.preset} onChange={(e) => setDoc({ captionStyle: { ...h.doc.captionStyle, preset: e.target.value as Composition["captionStyle"]["preset"] } })}><option value="highlight-word">Highlight word</option><option value="karaoke">Karaoke</option><option value="boxed">Boxed</option></select></label>
            <div className="grid grid-cols-2 gap-3">
              <Num label="Font size" step={2} min={24} max={120} value={doc.captionStyle.fontSize} onChange={(v) => setDoc({ captionStyle: { ...h.doc.captionStyle, fontSize: Math.round(Math.min(120, Math.max(24, v))) } }, "cfs")} />
              <Num label="Chars per line" step={1} min={10} max={60} value={doc.captionStyle.maxCharsPerLine} onChange={(v) => setDoc({ captionStyle: { ...h.doc.captionStyle, maxCharsPerLine: Math.round(Math.min(60, Math.max(10, v))) } }, "ccl")} />
            </div>
            <label className="studio-label">Position<select className="studio-input !py-2" value={doc.captionStyle.safeTop < 700 ? "top" : doc.captionStyle.safeTop < 1100 ? "middle" : "bottom"} onChange={(e) => { const [safeTop, safeBottom] = e.target.value === "top" ? [260, 560] : e.target.value === "middle" ? [810, 1110] : [1350, 1650]; setDoc({ captionStyle: { ...h.doc.captionStyle, safeTop, safeBottom } }); }}><option value="top">Top</option><option value="middle">Middle</option><option value="bottom">Bottom (safe zone)</option></select></label>
            <div className="grid grid-cols-2 gap-3">
              <label className="studio-label">Body font<select className="studio-input !py-2" value={doc.brand.fonts.body} onChange={(e) => setDoc({ brand: { ...h.doc.brand, fonts: { ...h.doc.brand.fonts, body: e.target.value as Composition["brand"]["fonts"]["body"] } } })}>{["Archivo", "Poppins", "Noto Sans"].map((f) => <option key={f}>{f}</option>)}</select></label>
              <label className="studio-label">Code font<select className="studio-input !py-2" value={doc.brand.fonts.code} onChange={(e) => setDoc({ brand: { ...h.doc.brand, fonts: { ...h.doc.brand.fonts, code: e.target.value as Composition["brand"]["fonts"]["code"] } } })}>{["JetBrains Mono", "Fira Code"].map((f) => <option key={f}>{f}</option>)}</select></label>
            </div>
          </Section>
          <ExportSection base={base} renderId={renderId} doc={h.doc} canEdit={canEdit} />
        </fieldset>}
      </aside>
    </div>

    {/* bottom: timeline */}
    <div className="flex h-[260px] shrink-0 flex-col border-t border-line bg-[var(--rail)]">
      <div className="flex h-10 shrink-0 items-center gap-1 border-b border-line px-2">
        <IconBtn label="Split at playhead (S)" onClick={() => act("split")} disabled={!canEdit}><Scissors size={15} /></IconBtn>
        <IconBtn label="Duplicate (Ctrl+D)" onClick={() => act("duplicate")} disabled={!canEdit}><Copy size={15} /></IconBtn>
        <IconBtn label="Delete (Del)" onClick={() => act("delete")} disabled={!canEdit}><Trash2 size={15} /></IconBtn>
        <span className="mx-2 h-5 w-px bg-line" />
        <span className="hidden text-[11px] text-muted sm:inline">Drag clips to move · drag edges to trim · Space plays</span>
        <div className="ml-auto flex items-center gap-2">
          <IconBtn label="Zoom out" onClick={() => setZoom((z) => Math.max(6, z / 1.4))}><ZoomOut size={15} /></IconBtn>
          <input type="range" aria-label="Timeline zoom" min={6} max={200} value={zoom} onChange={(e) => setZoom(+e.target.value)} className="w-24 accent-[var(--accent)]" />
          <IconBtn label="Zoom in" onClick={() => setZoom((z) => Math.min(200, z * 1.4))}><ZoomIn size={15} /></IconBtn>
        </div>
      </div>
      <div className="min-h-0 flex-1">
        <TimelinePanel doc={doc} time={time} zoom={zoom} selected={selected} onSelect={setSelected} onSeek={seek} onLive={canEdit ? setLive : () => {}} onCommit={() => { if (live) commit(live); setLive(null); }} />
      </div>
    </div>
  </div>;
}

function IconBtn({ label, onClick, disabled, children }: { label: string; onClick: () => void; disabled?: boolean; children: React.ReactNode }) {
  return <button type="button" title={label} aria-label={label} onClick={onClick} disabled={disabled} className="grid h-8 w-8 place-items-center rounded-md text-muted transition-colors hover:bg-white/10 hover:text-[var(--rail-ink)] disabled:opacity-35 disabled:hover:bg-transparent">{children}</button>;
}

function AddBtn({ icon: Icon, title, body, onClick, disabled }: { icon: typeof Type; title: string; body: string; onClick: () => void; disabled?: boolean }) {
  return <button type="button" onClick={onClick} disabled={disabled} className="flex w-full items-center gap-3 rounded-lg border border-white/10 bg-white/5 p-3 text-left transition-colors hover:border-accent/60">
    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-white/10 text-[#C9D2BD]"><Icon size={16} aria-hidden /></span>
    <span><span className="block font-medium">{title}</span><span className="text-[11px] text-muted">{body}</span></span>
  </button>;
}

function ExportSection({ base, renderId, doc, canEdit }: { base: string | null; renderId: string; doc: Composition; canEdit: boolean }) {
  const [quality, setQuality] = useState<"draft" | "looks" | "delivery">("looks");
  const [job, setJob] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const out = useQuery({
    queryKey: ["edit-render", job], enabled: !!job,
    queryFn: async () => (await createClient().from("render_jobs").select("id,status,error,duration_s,size_bytes,job:jobs(progress,current_stage)").eq("id", job!).single()).data,
    refetchInterval: (q) => ["ready", "failed", "cancelled"].includes(q.state.data?.status ?? "") ? false : 2500,
  });
  const urls = useQuery({
    queryKey: ["render-urls", job, base], enabled: !!base && out.data?.status === "ready",
    queryFn: async () => { const r = await apiFetch(base!, `/renders/${job}/urls`); if (!r.ok) throw new Error("Video links unavailable"); const u = await r.json(); const b = base!.replace(/\/$/, ""); return { video: b + u.video, download: b + u.download }; },
  });
  async function render() {
    if (!base) return;
    setBusy(true); setError(null);
    try {
      const r = await apiFetch(base, `/renders/${renderId}/edit`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ timeline: doc, quality }) });
      const body = await r.json().catch(() => null);
      if (!r.ok) throw new Error(apiErrorMessage(body, r.status));
      setJob(body.render_id);
    } catch (e) { setError(e instanceof Error ? e.message : "Render failed to start."); }
    finally { setBusy(false); }
  }
  async function download() {
    const r = await fetch(urls.data!.download, { headers: { "X-Tunnel-Skip-AntiPhishing-Page": "true" } });
    if (!r.ok) return setError("Download failed. Check the processing machine.");
    const href = URL.createObjectURL(await r.blob());
    Object.assign(document.createElement("a"), { href, download: `edit-${job!.slice(0, 8)}.mp4` }).click();
    setTimeout(() => URL.revokeObjectURL(href), 1000);
  }
  const j = out.data?.job as unknown as { progress: number; current_stage: string | null } | null;
  const active = out.data && !["ready", "failed", "cancelled"].includes(out.data.status);
  return <Section title="Export">
    <label className="studio-label">Quality<select className="studio-input !py-2" value={quality} onChange={(e) => setQuality(e.target.value as typeof quality)}><option value="draft">Draft · fastest</option><option value="looks">Standard</option><option value="delivery">Best</option></select></label>
    {canEdit && <button type="button" onClick={render} disabled={!base || busy || !!active} className="studio-button w-full">{busy || active ? <LoaderCircle size={15} className="animate-spin" aria-hidden /> : <Film size={15} aria-hidden />}{active ? "Rendering…" : "Render MP4 with edits"}</button>}
    {!base && <p className="text-[11.5px] text-muted">Rendering needs the processing machine online.</p>}
    {active && <div><div className="h-1.5 overflow-hidden rounded-full bg-surface-2"><div className="h-full rounded-full bg-signal transition-[width] duration-700" style={{ width: `${Math.max(3, Math.round((j?.progress ?? 0) * 100))}%` }} /></div><p className="mt-1 text-[11px] text-muted">{j?.current_stage?.replaceAll("_", " ") ?? "queued"} · {Math.round((j?.progress ?? 0) * 100)}%</p></div>}
    {out.data?.status === "failed" && <p role="alert" className="text-[12px] text-danger">{friendlyError(out.data.error ?? "").title}</p>}
    {urls.data && <div className="space-y-2">
      <video src={urls.data.video} controls playsInline className="mx-auto aspect-[9/16] w-40 rounded-lg bg-black" />
      <p className="text-center text-[11px] text-muted">{out.data?.duration_s?.toFixed(1)} s · {((out.data?.size_bytes ?? 0) / 1024 ** 2).toFixed(1)} MB</p>
      <button type="button" onClick={download} className="studio-button studio-button-secondary w-full"><Download size={15} aria-hidden />Download MP4</button>
      <Link href={`/editor/${job}`} className="block text-center text-[12px] text-accent hover:underline">Keep editing this version</Link>
    </div>}
    {error && <p role="alert" className="text-[12px] text-danger">{error}</p>}
  </Section>;
}
