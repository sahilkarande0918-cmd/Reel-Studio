"use client";

import type { Composition } from "@reel-studio/timeline-schema";
import type { Item } from "@reel-studio/timeline-schema/edit";
import { Volume2, VolumeX } from "lucide-react";

type Patch = (patch: Partial<Item>, key?: string) => void;
const TRANSITIONS = [["none", "None (style default)"], ["fade", "Fade"], ["slide", "Slide"], ["zoom", "Zoom"]] as const;

export function Num({ label, value, onChange, step = 0.1, min, max, suffix }: { label: string; value: number; onChange: (v: number) => void; step?: number; min?: number; max?: number; suffix?: string }) {
  return <label className="studio-label">{label}{suffix && <span className="sr-only"> ({suffix})</span>}
    <input type="number" value={Number.isFinite(value) ? Math.round(value * 1000) / 1000 : 0} step={step} min={min} max={max}
      onChange={(e) => { const v = parseFloat(e.target.value); if (Number.isFinite(v)) onChange(v); }} className="studio-input !py-2 tabular-nums" />
  </label>;
}

function Range({ label, value, onChange, min, max, step, display }: { label: string; value: number; onChange: (v: number) => void; min: number; max: number; step: number; display: string }) {
  return <label className="studio-label"><span className="flex justify-between">{label}<span className="tabular-nums text-ink">{display}</span></span>
    <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(parseFloat(e.target.value))} className="accent-[var(--accent)]" />
  </label>;
}

export function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="space-y-3 border-b border-line px-4 py-4"><h3 className="text-[11px] font-semibold uppercase tracking-[.1em] text-muted">{title}</h3>{children}</section>;
}

export function ItemProperties({ doc, item, onPatch }: { doc: Composition; item: Item; onPatch: Patch }) {
  const visual = item.type === "video" || item.type === "text" || item.type === "code";
  return <>
    <Section title="Timing">
      <div className="grid grid-cols-2 gap-3">
        <Num label="Start (s)" value={item.start} min={0} onChange={(v) => onPatch({ start: Math.max(0, v) }, "start")} />
        {item.type === "video" || item.type === "audio"
          ? <Num label="Length (s)" value={item.duration} min={0.2} onChange={(v) => onPatch({ duration: Math.max(0.2, v) } as Partial<Item>, "duration")} />
          : <Num label="Length (s)" value={item.duration} min={0.2} onChange={(v) => onPatch({ duration: Math.max(0.2, v) }, "duration")} />}
      </div>
      {visual && <label className="studio-label">Transition<select className="studio-input !py-2" value={"transition" in item ? item.transition : "none"} onChange={(e) => onPatch({ transition: e.target.value } as Partial<Item>)}>{TRANSITIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>}
    </Section>
    {(item.type === "video" || item.type === "audio") && <Section title="Audio">
      <div className="flex items-center gap-3">
        <button type="button" onClick={() => onPatch({ volume: item.volume === 0 ? 1 : 0 } as Partial<Item>)} aria-label={item.volume === 0 ? "Unmute" : "Mute"} className="studio-button studio-button-secondary !px-2.5">{item.volume === 0 ? <VolumeX size={15} aria-hidden /> : <Volume2 size={15} aria-hidden />}</button>
        <div className="flex-1"><Range label="Volume" value={item.volume} min={0} max={2} step={0.05} display={`${Math.round(item.volume * 100)}%`} onChange={(v) => onPatch({ volume: v } as Partial<Item>, "volume")} /></div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Num label="Fade in (s)" value={item.fadeIn} min={0} onChange={(v) => onPatch({ fadeIn: Math.max(0, v) } as Partial<Item>, "fadeIn")} />
        <Num label="Fade out (s)" value={item.fadeOut} min={0} onChange={(v) => onPatch({ fadeOut: Math.max(0, v) } as Partial<Item>, "fadeOut")} />
      </div>
      <p className="text-[11px] leading-4 text-muted">Source {item.sourceStart.toFixed(2)}–{item.sourceEnd.toFixed(2)} s. Drag the clip edges on the timeline to trim.</p>
    </Section>}
    {item.type === "video" && <CropSection doc={doc} item={item} onPatch={onPatch} />}
    {item.type === "text" && <Section title="Text overlay">
      <label className="studio-label">Text<textarea rows={3} value={item.text} maxLength={2000} onChange={(e) => onPatch({ text: e.target.value || " " } as Partial<Item>, "text")} className="studio-input resize-y" /></label>
      <div className="grid grid-cols-3 gap-3">
        <Num label="X" step={10} value={item.x} onChange={(v) => onPatch({ x: v } as Partial<Item>, "x")} />
        <Num label="Y" step={10} value={item.y} onChange={(v) => onPatch({ y: v } as Partial<Item>, "y")} />
        <Num label="Size" step={2} min={12} max={200} value={item.fontSize} onChange={(v) => onPatch({ fontSize: Math.round(Math.min(200, Math.max(12, v))) } as Partial<Item>, "fs")} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <label className="studio-label">Colour<input type="color" value={item.color ?? doc.brand.colors.text} onChange={(e) => onPatch({ color: e.target.value } as Partial<Item>, "color")} className="h-9 w-full cursor-pointer rounded-lg border border-line bg-transparent" /></label>
        <label className="studio-label">Align<select className="studio-input !py-2" value={item.align} onChange={(e) => onPatch({ align: e.target.value } as Partial<Item>)}><option value="left">Left</option><option value="center">Centre</option><option value="right">Right</option></select></label>
      </div>
      <label className="flex items-center gap-2 text-[12.5px]"><input type="checkbox" checked={item.box} onChange={(e) => onPatch({ box: e.target.checked } as Partial<Item>)} className="accent-[var(--accent)]" />Background box for legibility</label>
    </Section>}
    {item.type === "code" && <Section title="Code card">
      <label className="studio-label">Title<input value={item.title} maxLength={120} onChange={(e) => onPatch({ title: e.target.value } as Partial<Item>, "title")} className="studio-input !py-2" /></label>
      <label className="studio-label">Language<select className="studio-input !py-2" value={item.language} onChange={(e) => onPatch({ language: e.target.value } as Partial<Item>)}>{["json", "xml", "javascript", "typescript", "python", "sql", "html", "css", "text"].map((l) => <option key={l}>{l}</option>)}</select></label>
      <label className="studio-label">Code<textarea rows={8} spellCheck={false} value={item.code} onChange={(e) => onPatch({ code: e.target.value } as Partial<Item>, "code")} className="studio-input resize-y font-mono !text-[12px] [font-variant-ligatures:none]" /></label>
      <Num label="Typing animation (s)" value={item.typingDuration} min={0} onChange={(v) => onPatch({ typingDuration: Math.max(0, v) } as Partial<Item>, "typing")} />
    </Section>}
    {item.type === "caption" && <CaptionWords item={item} onPatch={onPatch} />}
  </>;
}

function CropSection({ doc, item, onPatch }: { doc: Composition; item: Extract<Item, { type: "video" }>; onPatch: Patch }) {
  const asset = doc.assets[item.assetId];
  const k0 = item.cropKeyframes[0];
  const maxX = Math.max(0, (asset?.width ?? 1920) - k0.crop_width);
  function shift(x: number) {
    const d = Math.round(x) - k0.crop_x;
    onPatch({ cropKeyframes: item.cropKeyframes.map((k) => ({ ...k, crop_x: Math.max(0, Math.min((asset?.width ?? 1920) - k.crop_width, k.crop_x + d)) })) } as Partial<Item>, "crop");
  }
  return <Section title="Framing (9:16 crop)">
    <Range label="Horizontal position" value={k0.crop_x} min={0} max={maxX} step={4} display={`${k0.crop_x}px`} onChange={shift} />
    <p className="text-[11px] leading-4 text-muted">{item.cropKeyframes.length > 1 ? `Smart framing follows the code in ${item.cropKeyframes.length} moves; this shifts all of them.` : "One fixed frame."}</p>
    {item.cropKeyframes.length > 1 && <button type="button" onClick={() => onPatch({ cropKeyframes: [{ ...k0, t: 0, transition_mode: "manual" }] } as Partial<Item>)} className="studio-button studio-button-secondary w-full">Lock to a fixed frame</button>}
  </Section>;
}

function CaptionWords({ item, onPatch }: { item: Extract<Item, { type: "caption" }>; onPatch: Patch }) {
  const set = (i: number, w: Partial<(typeof item.words)[number]>, key: string) => onPatch({ words: item.words.map((x, j) => j === i ? { ...x, ...w } : x) } as Partial<Item>, key);
  const nudge = (d: number) => onPatch({ words: item.words.map((w) => ({ ...w, start: Math.max(0, Math.round((w.start + d) * 1000) / 1000), end: Math.max(0.05, Math.round((w.end + d) * 1000) / 1000) })) } as Partial<Item>);
  return <Section title={`Caption words (${item.words.length})`}>
    <div className="flex items-center justify-between text-[12px] text-muted">Shift all<span className="flex gap-1">{[-0.1, 0.1].map((d) => <button key={d} type="button" onClick={() => nudge(d)} className="rounded-md border border-line px-2 py-1 text-ink hover:bg-surface-2">{d > 0 ? "+" : "−"}0.1 s</button>)}</span></div>
    <div className="max-h-[340px] space-y-1 overflow-y-auto pr-1">
      {item.words.map((w, i) => <div key={i} className="grid grid-cols-[1fr_58px_58px] gap-1">
        <input aria-label={`Word ${i + 1}`} value={w.text} onChange={(e) => set(i, { text: e.target.value || "·" }, `w${i}`)} className={`studio-input !px-2 !py-1.5 !text-[12.5px] ${w.isCode ? "font-mono text-accent" : ""}`} />
        <input aria-label={`Word ${i + 1} start`} type="number" step={0.05} value={w.start} onChange={(e) => set(i, { start: Math.max(0, +e.target.value) }, `s${i}`)} className="studio-input !px-1.5 !py-1.5 !text-[11.5px] tabular-nums" />
        <input aria-label={`Word ${i + 1} end`} type="number" step={0.05} value={w.end} onChange={(e) => set(i, { end: Math.max(0, +e.target.value) }, `e${i}`)} className="studio-input !px-1.5 !py-1.5 !text-[11.5px] tabular-nums" />
      </div>)}
    </div>
    <p className="text-[11px] leading-4 text-muted">Times are seconds from the start of this caption block.</p>
  </Section>;
}
