import { describe, expect, it } from "vitest";
import { duplicate, findItem, moveTo, remove, splitAt, trimTo } from "./edit.ts";
import { parseComposition } from "./index.ts";

const doc = () => parseComposition({
  id: "r", schemaVersion: 1, width: 1080, height: 1920, duration: 13,
  assets: { source: { id: "source", kind: "video", src: "source.mp4", width: 1920, height: 1080, duration: 100 } },
  tracks: [
    { id: "v", kind: "video", items: [{ id: "clip", type: "video", assetId: "source", start: 0, duration: 10, sourceStart: 20, sourceEnd: 30,
      cropKeyframes: [{ t: 0, crop_x: 0, crop_y: 0, crop_width: 608, crop_height: 1080, layout: "crop", region: "a", transition_mode: "start" },
        { t: 6, crop_x: 600, crop_y: 0, crop_width: 608, crop_height: 1080, layout: "crop", region: "b", transition_mode: "ease" }] }] },
    { id: "c", kind: "caption", items: [{ id: "cap", type: "caption", start: 0, duration: 10, words: [{ text: "one", start: 1, end: 2 }, { text: "two", start: 7, end: 8 }] }] },
  ],
  brand: { colors: { background: "#000000", text: "#ffffff", accent: "#f2b544" }, fonts: { body: "Archivo", code: "JetBrains Mono" }, outro: { enabled: true, duration: 3, cta: "Follow" } },
  captionStyle: {}, renderSettings: {},
});

describe("editor operations keep the timeline valid", () => {
  it("splits media, keyframes and captions at the playhead", () => {
    const out = parseComposition(splitAt(doc(), "clip", 4));
    const [a, b] = out.tracks[0].items;
    expect([a.duration, b.start, b.duration]).toEqual([4, 4, 6]);
    if (b.type !== "video") throw new Error();
    expect([b.sourceStart, b.sourceEnd]).toEqual([24, 30]);
    expect(b.cropKeyframes.map((k) => k.t)).toEqual([0, 2]);
    const cut = parseComposition(splitAt(out, "cap", 5)).tracks[1].items;
    expect(cut.map((i) => i.type === "caption" && i.words.map((w) => w.text))).toEqual([["one"], ["two"]]);
  });
  it("trims the head and grows composition with the outro", () => {
    const out = parseComposition(trimTo(doc(), "clip", "start", 2));
    const clip = findItem(out, "clip")!.item;
    expect([clip.start, clip.duration, clip.type === "video" && clip.sourceStart]).toEqual([2, 8, 22]);
    expect(parseComposition(moveTo(out, "cap", 5)).duration).toBe(18);
  });
  it("duplicates after the original and removes cleanly", () => {
    const { doc: d, id } = duplicate(doc(), "clip");
    expect(findItem(d, id)!.item.start).toBe(10);
    expect(parseComposition(remove(d, id)).tracks[0].items).toHaveLength(1);
  });
});
