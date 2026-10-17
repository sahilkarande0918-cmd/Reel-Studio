"use client";

import { useRef } from "react";
import { Captions, Code2, Film, Music, Type } from "lucide-react";
import type { Composition } from "@reel-studio/timeline-schema";
import { itemEnd, moveTo, trimTo, type Item } from "@reel-studio/timeline-schema/edit";

const KIND = {
  video: { label: "Video", icon: Film, cls: "bg-[#2c3a52] border-[#4a6a9a]" },
  audio: { label: "Audio", icon: Music, cls: "bg-[#21403a] border-[#3f8a76]" },
  caption: { label: "Captions", icon: Captions, cls: "bg-[#433a22] border-[#a88a3c]" },
  text: { label: "Text", icon: Type, cls: "bg-[#3d2c3a] border-[#8c5a80]" },
  overlay: { label: "Overlay", icon: Code2, cls: "bg-[#24363f] border-[#3f7f96]" },
} as const;

export const fmt = (t: number) => `${Math.floor(t / 60)}:${(t % 60).toFixed(1).padStart(4, "0")}`;

function label(i: Item) {
  if (i.type === "caption") return i.words.map((w) => w.text).join(" ") || "Captions";
  if (i.type === "text") return i.text;
  if (i.type === "code") return i.title || i.language;
  if (i.type === "video" || i.type === "audio") return `${i.assetId} · ${i.sourceStart.toFixed(1)}–${i.sourceEnd.toFixed(1)} s${i.volume === 0 ? " · muted" : ""}`;
  return "";
}

export function TimelinePanel({ doc, time, zoom, selected, onSelect, onSeek, onLive, onCommit }: {
  doc: Composition; time: number; zoom: number; selected: string | null;
  onSelect: (id: string | null) => void; onSeek: (t: number) => void;
  onLive: (d: Composition) => void; onCommit: () => void;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const width = Math.max(doc.duration + 4, 20) * zoom;
  const step = zoom > 90 ? 1 : zoom > 40 ? 2 : zoom > 18 ? 5 : 10;
  const edges = doc.tracks.flatMap((t) => t.items.flatMap((i) => [i.start, itemEnd(i)]));

  function snap(t: number, self: Item) {
    const own = new Set([self.start, itemEnd(self)]);
    const near = [time, 0, ...edges.filter((e) => !own.has(e))].find((c) => Math.abs(c - t) * zoom < 7);
    return near ?? Math.round(t * 30) / 30;
  }
  function timeAt(clientX: number) {
    const box = scroller.current!.getBoundingClientRect();
    return Math.max(0, Math.min(doc.duration, (clientX - box.left + scroller.current!.scrollLeft - 96) / zoom));
  }
  function scrub(e: React.PointerEvent) {
    onSeek(timeAt(e.clientX));
    const move = (ev: PointerEvent) => onSeek(timeAt(ev.clientX));
    const up = () => { removeEventListener("pointermove", move); removeEventListener("pointerup", up); };
    addEventListener("pointermove", move); addEventListener("pointerup", up);
  }
  function drag(e: React.PointerEvent, item: Item, mode: "move" | "start" | "end") {
    e.stopPropagation(); e.preventDefault();
    onSelect(item.id);
    const x0 = e.clientX, base = doc, s0 = item.start, e0 = itemEnd(item);
    const asset = item.type === "video" || item.type === "audio" ? doc.assets[item.assetId]?.duration : undefined;
    let moved = false;
    const move = (ev: PointerEvent) => {
      const dt = (ev.clientX - x0) / zoom;
      if (!moved && Math.abs(ev.clientX - x0) < 3) return;
      moved = true;
      onLive(mode === "move" ? moveTo(base, item.id, snap(s0 + dt, item)) : mode === "start" ? trimTo(base, item.id, "start", snap(s0 + dt, item)) : trimTo(base, item.id, "end", snap(e0 + dt, item), { assetDuration: asset }));
    };
    const up = () => { removeEventListener("pointermove", move); removeEventListener("pointerup", up); if (moved) onCommit(); };
    addEventListener("pointermove", move); addEventListener("pointerup", up);
  }

  return <div ref={scroller} className="relative h-full overflow-auto" onPointerDown={(e) => { if (e.target === e.currentTarget) onSelect(null); }}>
    <div style={{ width: width + 96 }} className="relative min-h-full">
      <div onPointerDown={scrub} className="sticky top-0 z-20 flex h-7 cursor-ew-resize border-b border-line bg-[var(--rail)]">
        <div className="sticky left-0 z-10 w-24 shrink-0 bg-[var(--rail)]" />
        <div className="relative flex-1">
          {Array.from({ length: Math.ceil(width / zoom / step) + 1 }, (_, i) => i * step).map((s) => <span key={s} style={{ left: s * zoom }} className="absolute top-0 h-full border-l border-line pl-1 text-[10px] leading-7 tabular-nums text-muted">{fmt(s)}</span>)}
        </div>
      </div>
      {doc.tracks.map((track) => {
        const k = KIND[track.kind]; const Icon = k.icon;
        return <div key={track.id} className="flex h-12 border-b border-line/70">
          <div className="sticky left-0 z-10 flex w-24 shrink-0 items-center gap-1.5 border-r border-line bg-[var(--rail)] px-2.5 text-[11px] font-medium text-muted"><Icon size={13} aria-hidden />{k.label}</div>
          <div className="relative flex-1" onPointerDown={(e) => { if (e.target === e.currentTarget) { onSelect(null); scrub(e); } }}>
            {track.items.map((item) => {
              const on = item.id === selected;
              return <div key={item.id} role="button" tabIndex={0} aria-label={`${k.label} item at ${fmt(item.start)}`} aria-pressed={on}
                onPointerDown={(e) => drag(e, item, "move")} onKeyDown={(e) => { if (e.key === "Enter") onSelect(item.id); }}
                style={{ left: item.start * zoom, width: Math.max(6, item.duration * zoom) }}
                className={`group absolute inset-y-1.5 cursor-grab overflow-hidden rounded-md border text-[11px] text-[#e8e8ec] active:cursor-grabbing ${k.cls} ${on ? "ring-2 ring-[#E8D9A8]" : "hover:brightness-125"}`}>
                <span className="pointer-events-none block truncate px-2.5 leading-[34px]">{label(item)}</span>
                <span onPointerDown={(e) => drag(e, item, "start")} className="absolute inset-y-0 left-0 w-2 cursor-ew-resize bg-white/0 group-hover:bg-white/25" />
                <span onPointerDown={(e) => drag(e, item, "end")} className="absolute inset-y-0 right-0 w-2 cursor-ew-resize bg-white/0 group-hover:bg-white/25" />
              </div>;
            })}
          </div>
        </div>;
      })}
      <div className="pointer-events-none absolute bottom-0 top-0 z-30 w-px bg-[#E8D9A8]" style={{ left: 96 + time * zoom }}>
        <span className="absolute -left-[5px] top-0 h-0 w-0 border-x-[5px] border-t-[7px] border-x-transparent border-t-[#E8D9A8]" />
      </div>
    </div>
  </div>;
}
