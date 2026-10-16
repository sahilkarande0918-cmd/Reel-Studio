"use client";

import { Clapperboard, Crosshair, Stamp, Zap } from "lucide-react";

export type StylePreset = "focus" | "energy" | "story" | "signature";

const STYLES = [
  { id: "focus", name: "Focus", body: "Clean captions, code first", icon: Crosshair },
  { id: "energy", name: "Energy", body: "Bold captions, quick cuts", icon: Zap },
  { id: "story", name: "Story", body: "Cinematic fades, slow push-ins", icon: Clapperboard },
  { id: "signature", name: "Signature", body: "Branded boxes and lower third", icon: Stamp },
] as const;

/** Creative preset sent with render/generate requests; the compiler applies it to the MP4. */
export function StylePicker({ value, onChange, name = "style", compact }: { value: StylePreset; onChange: (v: StylePreset) => void; name?: string; compact?: boolean }) {
  return <fieldset>
    {!compact && <legend className="mb-2 text-[12px] font-medium text-muted">Style</legend>}
    <div className={`grid grid-cols-2 gap-2 ${compact ? "" : "lg:grid-cols-4"}`}>
      {STYLES.map(({ id, name: label, body, icon: Icon }) => <label key={id} className={`flex cursor-pointer items-start gap-2.5 rounded-xl border p-3 transition-colors ${value === id ? "border-accent bg-accent/8" : "border-line hover:border-[#3a404e]"}`}>
        <input type="radio" name={name} value={id} checked={value === id} onChange={() => onChange(id)} className="sr-only" />
        <Icon size={16} className={`mt-0.5 shrink-0 ${value === id ? "text-accent" : "text-muted"}`} aria-hidden />
        <span><span className="block text-[13px] font-semibold">{label}</span><span className="block text-[11.5px] leading-4 text-muted">{body}</span></span>
      </label>)}
    </div>
  </fieldset>;
}
