"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { apiFetch, useBackend } from "@/lib/backend";

export type Look = {
  id: string; font: string; uppercase?: boolean; italic?: boolean; sizeScale?: number; tracking?: number; color: string; active: string;
  chip?: string; stroke?: number; strokeColor?: string; shadow?: "none" | "soft" | "hard" | "long"; glow?: number;
  highlight?: "fill" | "chip" | "karaoke" | "underline" | "scale" | "none"; entrance?: string; box?: boolean; position?: "lower" | "middle" | "upper";
};
export type Preset = { id: string; name: string; family: string; look: Look };
export type CaptionChoice = { on: boolean; preset: string; overrides: Partial<Pick<Look, "color" | "active" | "sizeScale" | "position">> };

// The same bundled OFL files the renderer uses (public/caption-fonts), so the preview typeface matches the export.
const FONT_FILES: Record<string, string> = {
  Archivo: "archivo-800.woff2", Poppins: "poppins-700.woff2", "Noto Sans": "noto-sans-700.woff2", "JetBrains Mono": "jetbrains-mono-700.woff2",
  "Fira Code": "fira-code-600.woff2", Fraunces: "fraunces-600.woff2", "Bebas Neue": "bebas-neue-400.ttf", Caveat: "caveat-700.ttf",
  "Press Start 2P": "press-start-2p-400.ttf",
};
const FONT_CSS = Object.entries(FONT_FILES).map(([f, file]) => `@font-face{font-family:"cap-${f}";src:url(/caption-fonts/${file});font-display:swap}`).join("");
const BRAND = { accent: "#C8E06B", text: "#FFFFFF", bg: "#141810" };
const tok = (c?: string) => (c === "accent" ? BRAND.accent : c === "text" ? BRAND.text : c === "bg" ? BRAND.bg : c);
const SHADOW = { none: "", soft: "0 2px 12px rgba(0,0,0,.75)", hard: "4px 4px 0 rgba(0,0,0,.85)", long: "5px 5px 0 rgba(0,0,0,.6), 10px 10px 0 rgba(0,0,0,.3)" };

/** Live preview: the second word is "being spoken", styled with the preset's highlight; brand tokens use sample colours. */
function Sample({ look, size = 22 }: { look: Look; size?: number }) {
  const active = tok(look.active)!, color = tok(look.color)!;
  const shadows = [SHADOW[look.shadow ?? "soft"], look.glow ? `0 0 ${look.glow / 3}px ${active}` : ""].filter(Boolean).join(",") || "none";
  const base: React.CSSProperties = {
    fontFamily: `"cap-${look.font}", sans-serif`, fontStyle: look.italic ? "italic" : "normal", fontSize: size * (look.sizeScale ?? 1),
    textTransform: look.uppercase ? "uppercase" : "none", letterSpacing: `${look.tracking ?? 0}em`, color, textShadow: shadows,
    WebkitTextStroke: look.stroke ? `${look.stroke / 4}px ${tok(look.strokeColor) ?? "#000"}` : undefined, paintOrder: "stroke fill",
    padding: "0 4px", borderRadius: 6, display: "inline-block",
  };
  const hi = look.highlight ?? "fill";
  const on: React.CSSProperties = hi === "chip" ? { background: tok(look.chip) ?? active, color: "#111" }
    : hi === "underline" ? { boxShadow: `inset 0 -0.16em 0 ${active}` } : hi === "scale" ? { color: active, transform: "scale(1.15)" }
    : hi === "none" ? {} : { color: active };
  const words = ["Make", "it", "move"];
  return <span className={`flex flex-wrap justify-center gap-x-1 ${look.box ? "rounded-lg bg-black/70 px-2 py-1" : ""}`}>
    {words.map((w, i) => <span key={w} style={{ ...base, ...(i === 1 || (hi === "karaoke" && i < 1) ? on : {}) }}
      className={look.entrance && look.entrance !== "none" && i === 2 ? "animate-pulse" : ""}>{w}</span>)}
  </span>;
}

export function CaptionPicker({ value, onChange, needsSpeech }: { value: CaptionChoice; onChange: (c: CaptionChoice) => void; needsSpeech?: string }) {
  const backend = useBackend();
  const base = backend.data?.state === "online" ? backend.data.url : null;
  const presets = useQuery({
    queryKey: ["caption-presets", base], enabled: !!base, staleTime: 3600_000,
    queryFn: async () => { const r = await apiFetch(base!, "/captions/presets"); if (!r.ok) throw new Error("presets unavailable"); return (await r.json()) as Preset[]; },
  });
  const families = useMemo(() => [...new Set((presets.data ?? []).map((p) => p.family))], [presets.data]);
  const current = presets.data?.find((p) => p.id === value.preset);
  const [family, setFamily] = useState<string | null>(null);
  const fam = family ?? current?.family ?? families[0];
  const set = (patch: Partial<CaptionChoice>) => onChange({ ...value, ...patch });
  return (
    <div className="space-y-3 rounded-xl border border-line bg-surface p-4">
      <style>{FONT_CSS}</style>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[13px] font-semibold">Captions</p>
        <div role="radiogroup" aria-label="Captions" className="inline-flex rounded-full border border-line p-0.5 text-[12px]">
          {[["Off", false], ["On", true]].map(([l, v]) => <button key={String(l)} type="button" role="radio" aria-checked={value.on === v} onClick={() => set({ on: v as boolean })}
            className={`rounded-full px-3 py-1 ${value.on === v ? "bg-accent text-accent-ink" : "text-muted"}`}>{l as string}</button>)}
        </div>
      </div>
      {!value.on && <p className="text-[12px] text-muted">Off: nothing is burned into the video. Transcript and word timing are kept, so captions can be turned on later.</p>}
      {value.on && needsSpeech && <p className="text-[12px] text-muted">{needsSpeech}</p>}
      {value.on && (presets.isLoading ? <p className="text-[12px] text-muted">Loading the 100 caption styles…</p> : presets.error ? <p className="text-[12px] text-danger">Caption styles need the processing machine online.</p> : <>
        <div className="flex gap-1.5 overflow-x-auto pb-1">{families.map((f) => <button key={f} type="button" onClick={() => setFamily(f)}
          className={`shrink-0 rounded-full border px-3 py-1 text-[11px] ${f === fam ? "border-accent bg-accent/10 font-semibold" : "border-line text-muted"}`}>{f}</button>)}</div>
        <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">{(presets.data ?? []).filter((p) => p.family === fam).map((p) => <li key={p.id}>
          <button type="button" onClick={() => set({ preset: p.id, overrides: {} })} aria-pressed={value.preset === p.id}
            className={`flex h-24 w-full flex-col items-center justify-center gap-2 overflow-hidden rounded-lg bg-[#23281d] p-2 ring-2 ${value.preset === p.id ? "ring-accent" : "ring-transparent hover:ring-line"}`}>
            <Sample look={p.look} />
            <span className="text-[10px] text-white/70">{p.name}{p.look.entrance && p.look.entrance !== "none" ? ` · ${p.look.entrance}` : ""}</span>
          </button></li>)}</ul>
        {current && <div className="grid gap-3 sm:grid-cols-4">
          <label className="studio-label">Text colour<input type="color" className="h-9 w-full rounded" value={value.overrides.color ?? tok(current.look.color)} onChange={(e) => set({ overrides: { ...value.overrides, color: e.target.value } })} /></label>
          <label className="studio-label">Highlight colour<input type="color" className="h-9 w-full rounded" value={value.overrides.active ?? tok(current.look.active)} onChange={(e) => set({ overrides: { ...value.overrides, active: e.target.value } })} /></label>
          <label className="studio-label">Size<input type="range" min={0.6} max={1.6} step={0.05} value={value.overrides.sizeScale ?? current.look.sizeScale ?? 1} onChange={(e) => set({ overrides: { ...value.overrides, sizeScale: Number(e.target.value) } })} /></label>
          <label className="studio-label">Position<select className="studio-input" value={value.overrides.position ?? current.look.position ?? "lower"} onChange={(e) => set({ overrides: { ...value.overrides, position: e.target.value as Look["position"] } })}>
            <option value="lower">Lower (safe zone)</option><option value="middle">Middle</option><option value="upper">Upper</option></select></label>
        </div>}
      </>)}
    </div>
  );
}
