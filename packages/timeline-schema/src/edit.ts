/**
 * Pure editor operations on a canonical composition. Every function returns a new document and keeps the
 * schema invariants (media duration = sourceEnd - sourceStart, word/keyframe times relative to the item,
 * composition long enough for every item plus the outro card).
 */
import type { Composition } from "./index.ts";

type Track = Composition["tracks"][number];
export type Item = Track["items"][number];
const MIN = 0.2;
const r3 = (n: number) => Math.round(n * 1000) / 1000;
const clone = <T,>(v: T): T => structuredClone(v);
let seq = 0;
export const newId = (prefix: string) => `${prefix}-${Date.now().toString(36)}${(seq++).toString(36)}`;

export const itemEnd = (i: Item) => i.start + i.duration;

export function findItem(doc: Composition, id: string): { track: Track; item: Item; index: number } | null {
  for (const track of doc.tracks) {
    const index = track.items.findIndex((i) => i.id === id);
    if (index >= 0) return { track, item: track.items[index], index };
  }
  return null;
}

/** Composition length follows the content: last item end + outro card. Intro is the gap before the first item. */
export function normalize(doc: Composition): Composition {
  const items = doc.tracks.flatMap((t) => t.items);
  const end = Math.max(MIN, ...items.map(itemEnd));
  const outro = doc.brand.outro?.enabled ? doc.brand.outro.duration : 0;
  return { ...doc, duration: r3(end + outro) };
}

function map(doc: Composition, id: string, fn: (item: Item) => Item | Item[] | null): Composition {
  return normalize({
    ...doc,
    tracks: doc.tracks.map((t) => ({ ...t, items: t.items.flatMap((i) => (i.id === id ? fn(clone(i)) ?? [] : [i])) as Item[] })),
  });
}

/** Shift an item's internal (item-relative) timing after its start moved right by `d` seconds of content. */
function cutHead(item: Item, d: number): Item {
  const next = { ...item, start: r3(item.start + d), duration: r3(item.duration - d) } as Item;
  if (next.type === "video" || next.type === "audio") {
    next.sourceStart = r3(next.sourceStart + d);
    next.fadeIn = Math.min(next.fadeIn ?? 0, next.duration / 2);
  }
  if (next.type === "video") {
    const keys = next.cropKeyframes;
    const before = [...keys].reverse().find((k) => k.t <= d) ?? keys[0];
    next.cropKeyframes = [{ ...before, t: 0 }, ...keys.filter((k) => k.t > d).map((k) => ({ ...k, t: r3(k.t - d) }))];
  }
  if (next.type === "caption")
    next.words = next.words.filter((w) => w.end > d).map((w) => ({ ...w, start: r3(Math.max(0, w.start - d)), end: r3(w.end - d) }));
  if (next.type === "code") {
    const shown = [...next.changes].reverse().find((c) => c.at <= d);
    if (shown) next.code = shown.code;
    next.changes = next.changes.filter((c) => c.at > d).map((c) => ({ ...c, at: r3(c.at - d) }));
    next.typingDuration = shown || d > 0 ? 0 : next.typingDuration;
  }
  return fitInside(next);
}

/** Drop or clamp item-relative timing that now falls after the item's end. */
function fitInside(item: Item): Item {
  const d = item.duration;
  if (item.type === "video" || item.type === "audio") {
    item.sourceEnd = r3(item.sourceStart + d);
    item.fadeIn = Math.min(item.fadeIn ?? 0, d / 2);
    item.fadeOut = Math.min(item.fadeOut ?? 0, d / 2);
  }
  if (item.type === "video") {
    item.cropKeyframes = item.cropKeyframes.filter((k, i) => i === 0 || k.t < d);
  }
  if (item.type === "caption") item.words = item.words.filter((w) => w.start < d).map((w) => ({ ...w, end: r3(Math.min(w.end, d)) }));
  if (item.type === "code") {
    item.typingDuration = Math.min(item.typingDuration, d);
    item.changes = item.changes.filter((c) => c.at + c.typingDuration <= d);
  }
  return item;
}

export function splitAt(doc: Composition, id: string, t: number): Composition {
  const found = findItem(doc, id);
  if (!found) return doc;
  const { item } = found;
  const local = r3(t - item.start);
  if (local < MIN || item.duration - local < MIN) return doc;
  return map(doc, id, (i) => {
    const left = fitInside({ ...clone(i), duration: local } as Item);
    const right = cutHead({ ...clone(i), id: newId(i.type) } as Item, local);
    return [left, right];
  });
}

/** Trim the start (`edge: "start"`) or end of an item to composition time `t`. */
export function trimTo(doc: Composition, id: string, edge: "start" | "end", t: number, limits?: { assetDuration?: number }): Composition {
  return map(doc, id, (i) => {
    if (edge === "end") {
      let duration = r3(Math.max(MIN, t - i.start));
      if ((i.type === "video" || i.type === "audio") && limits?.assetDuration !== undefined)
        duration = Math.min(duration, r3(limits.assetDuration - i.sourceStart));
      return fitInside({ ...i, duration } as Item);
    }
    let d = r3(Math.min(t - i.start, i.duration - MIN));
    if (i.type === "video" || i.type === "audio") d = Math.max(d, -i.sourceStart); // can extend back to the source start
    d = Math.max(d, -i.start);
    if (d >= 0) return cutHead(i, d);
    // extending the head of a media item reveals earlier source; other items just grow
    const grown = { ...i, start: r3(i.start + d), duration: r3(i.duration - d) } as Item;
    if (grown.type === "video" || grown.type === "audio") grown.sourceStart = r3(grown.sourceStart + d);
    if (grown.type === "video") grown.cropKeyframes = [{ ...grown.cropKeyframes[0], t: 0 }, ...grown.cropKeyframes.slice(1).map((k) => ({ ...k, t: r3(k.t - d) }))];
    if (grown.type === "caption") grown.words = grown.words.map((w) => ({ ...w, start: r3(w.start - d), end: r3(w.end - d) }));
    if (grown.type === "code") grown.changes = grown.changes.map((c) => ({ ...c, at: r3(c.at - d) }));
    return fitInside(grown);
  });
}

export function moveTo(doc: Composition, id: string, start: number): Composition {
  return map(doc, id, (i) => ({ ...i, start: r3(Math.max(0, start)) }));
}

export function remove(doc: Composition, id: string): Composition {
  return map(doc, id, () => null);
}

/** Copy placed right after the original on the same track. */
export function duplicate(doc: Composition, id: string): { doc: Composition; id: string } {
  const nid = newId("copy");
  return { doc: map(doc, id, (i) => [i, { ...clone(i), id: nid, start: r3(itemEnd(i)) } as Item]), id: nid };
}

export function update(doc: Composition, id: string, patch: Partial<Item>): Composition {
  return map(doc, id, (i) => fitInside({ ...i, ...patch } as Item));
}

/** Add an item to the first track of `kind` (created if missing). */
export function addItem(doc: Composition, kind: Track["kind"], item: Item): Composition {
  const tracks = clone(doc.tracks);
  const track = tracks.find((t) => t.kind === kind) ?? (tracks.push({ id: newId(kind), kind, items: [] }), tracks[tracks.length - 1]);
  track.items.push(item);
  return normalize({ ...doc, tracks });
}
