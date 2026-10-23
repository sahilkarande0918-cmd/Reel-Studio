/**
 * Canonical timeline — the one document format shared by AI generation (Python emits it), the editor,
 * preview and export. Zod is the source of truth; `timeline.schema.json` is generated from it for Python.
 * Times are seconds on the composition clock unless a field says "source".
 */
import { z } from "zod";

export const SCHEMA_VERSION = 1;

const seconds = z.number().min(0);
const px = z.number().int().min(0);

/** Section 18 crop keyframe; `t` is relative to the item's start. */
export const CropKeyframe = z.object({
  t: seconds,
  crop_x: px,
  crop_y: px,
  crop_width: z.number().int().positive(),
  crop_height: z.number().int().positive(),
  layout: z.enum(["crop", "panel"]),
  region: z.string(),
  transition_mode: z.enum(["start", "hold", "ease", "cut", "manual"]),
});

export const Asset = z.object({
  id: z.string().min(1),
  kind: z.enum(["video", "audio", "image", "font"]),
  /** Path inside the render project directory, never an absolute or user-supplied path. */
  src: z.string().regex(/^[A-Za-z0-9_.-]+$/),
  width: z.number().int().positive().optional(),
  height: z.number().int().positive().optional(),
  duration: seconds.optional(),
});

/** Editor transition on a visual item: animated in at its start and out at its end (0.4 s). */
export const Transition = z.enum(["none", "fade", "slide", "zoom"]);

export const VideoItem = z.object({
  id: z.string().min(1),
  type: z.literal("video"),
  assetId: z.string().min(1),
  start: seconds,
  duration: z.number().positive(),
  sourceStart: seconds,
  sourceEnd: z.number().positive(),
  volume: z.number().min(0).max(3.98).default(1),
  /** Audio fades in seconds at the item's start/end (applied to the mix at those times). */
  fadeIn: seconds.default(0),
  fadeOut: seconds.default(0),
  transition: Transition.default("none"),
  cropKeyframes: z.array(CropKeyframe).min(1),
});

export const CaptionWord = z.object({
  text: z.string().min(1),
  start: seconds,
  end: seconds,
  isCode: z.boolean().default(false),
});

export const CaptionItem = z.object({
  id: z.string().min(1),
  type: z.literal("caption"),
  start: seconds,
  duration: z.number().positive(),
  words: z.array(CaptionWord),
});

export const AudioItem = VideoItem.omit({ cropKeyframes: true, transition: true }).extend({ type: z.literal("audio") });

/** Source text is displayed only. It is never inserted as HTML or executed. */
export const CodeItem = z.object({
  id: z.string().min(1), type: z.literal("code"), start: seconds, duration: z.number().positive(),
  language: z.enum(["json", "xml", "javascript", "typescript", "python", "sql", "html", "css", "text"]),
  title: z.string().max(120).default(""), code: z.string().max(12000),
  typingDuration: seconds.default(2),
  changes: z.array(z.object({ at: seconds, code: z.string().max(12000), typingDuration: seconds })).max(30).default([]),
  transition: Transition.default("none"),
});

export const TextItem = z.object({
  id: z.string().min(1), type: z.literal("text"), start: seconds, duration: z.number().positive(),
  text: z.string().min(1).max(2000), x: z.number().default(80), y: z.number().default(180),
  fontSize: z.number().int().min(12).max(200).default(64),
  color: z.string().regex(/^#[0-9a-fA-F]{6}$/).optional(),
  align: z.enum(["left", "center", "right"]).default("left"),
  /** Solid brand-coloured box behind the text for legibility over video. */
  box: z.boolean().default(false),
  transition: Transition.default("none"),
});

/** Motion-graphics scene or overlay from the template library (apps/api/app/services/rendering/motion.py).
 * `fields` are the template's editable texts; `media` are asset ids (images/clips) shown inside the template. */
export const MotionItem = z.object({
  id: z.string().min(1), type: z.literal("motion"), start: seconds, duration: z.number().positive(),
  template: z.string().regex(/^[a-z_]{2,40}$/),
  fields: z.record(z.string(), z.string().max(400)).default({}),
  media: z.array(z.string().min(1)).max(6).default([]),
  intensity: z.number().min(0).max(1).default(0.6),
});

export const Item = z.discriminatedUnion("type", [VideoItem, CaptionItem, AudioItem, CodeItem, TextItem, MotionItem]);

export const Track = z.object({
  id: z.string().min(1),
  kind: z.enum(["video", "audio", "caption", "text", "overlay"]),
  items: z.array(Item),
});

const color = z.string().regex(/^#[0-9a-fA-F]{6}$/);

/** Fonts bundled with the renderer (SIL OFL); renders never load remote fonts. */
export const BODY_FONTS = ["Archivo", "Poppins", "Noto Sans"] as const;
export const CODE_FONTS = ["JetBrains Mono", "Fira Code"] as const;

/** Snapshot of an institute brand kit, copied into the timeline when a render is requested. */
export const Brand = z.object({
  name: z.string().max(80).default(""),
  handle: z.string().max(40).default(""),
  colors: z.object({ background: color, text: color, accent: color }),
  fonts: z.object({ body: z.enum(BODY_FONTS), code: z.enum(CODE_FONTS) }),
  /** Asset id of the logo image, if the kit has one. */
  logoAssetId: z.string().min(1).optional(),
  watermark: z
    .object({ enabled: z.boolean(), position: z.enum(["top-left", "top-right", "bottom-left", "bottom-right"]) })
    .default({ enabled: false, position: "top-right" }),
  /** Title card before the clip; `title` is already resolved (no template placeholders). */
  intro: z.object({ enabled: z.boolean(), duration: z.number().min(1).max(5), title: z.string().max(80) })
    .default({ enabled: false, duration: 2, title: "" }),
  /** Closing card after the clip. */
  outro: z.object({ enabled: z.boolean(), duration: z.number().min(1).max(6), cta: z.string().max(80) })
    .default({ enabled: false, duration: 3, cta: "" }),
});

export const CaptionStyle = z.object({
  preset: z.enum(["highlight-word", "karaoke", "boxed"]).default("highlight-word"),
  fontSize: z.number().int().min(24).max(120).default(64),
  maxCharsPerLine: z.number().int().min(10).max(60).default(32),
  maxLines: z.number().int().min(1).max(3).default(2),
  /** Lower safe zone for 9:16 platforms (clear of the top bar and the bottom UI). */
  safeTop: px.default(1350),
  safeBottom: px.default(1650),
});

/** Creative direction applied by the compiler: Focus (clean, code-first), Energy (bold captions, quick cuts),
 * Story (cinematic type, slow fades and push-ins), Signature (branded boxed captions and lower third). */
export const StylePreset = z.enum(["focus", "energy", "story", "signature"]);

export const RenderSettings = z.object({
  quality: z.enum(["draft", "looks", "delivery"]).default("looks"),
});

export const Composition = z
  .object({
    id: z.string().min(1),
    schemaVersion: z.literal(SCHEMA_VERSION),
    title: z.string().max(120).default(""),
    fps: z.union([z.literal(24), z.literal(30), z.literal(60)]).default(30),
    width: z.number().int().positive(),
    height: z.number().int().positive(),
    duration: z.number().positive(),
    source: z.object({ recordingId: z.string(), highlightId: z.string(), editId: z.string() }).partial().default({}),
    assets: z.record(z.string(), Asset),
    tracks: z.array(Track),
    brand: Brand,
    captionStyle: CaptionStyle,
    stylePreset: StylePreset.default("focus"),
    renderSettings: RenderSettings,
  })
  .superRefine((c, ctx) => {
    if (c.brand.logoAssetId && !c.assets[c.brand.logoAssetId])
      ctx.addIssue({ code: "custom", path: ["brand", "logoAssetId"], message: `unknown asset ${c.brand.logoAssetId}` });
    c.tracks.forEach((track, ti) =>
      track.items.forEach((item, ii) => {
        const path = ["tracks", ti, "items", ii];
        if (item.start + item.duration > c.duration + 1e-3)
          ctx.addIssue({ code: "custom", path, message: "item ends after the composition" });
        if (item.type === "video" || item.type === "audio") {
          if (!c.assets[item.assetId]) ctx.addIssue({ code: "custom", path, message: `unknown asset ${item.assetId}` });
          else if (c.assets[item.assetId].kind !== item.type)
            ctx.addIssue({ code: "custom", path, message: "media asset kind must match item type" });
          if (item.fadeIn + item.fadeOut > item.duration + 1e-3)
            ctx.addIssue({ code: "custom", path, message: "fades are longer than the item" });
          if (Math.abs(item.sourceEnd - item.sourceStart - item.duration) > 1e-3)
            ctx.addIssue({ code: "custom", path, message: "duration must equal sourceEnd - sourceStart (no speed change yet)" });
          if (c.assets[item.assetId]?.duration !== undefined && item.sourceEnd > c.assets[item.assetId].duration! + 1e-3)
            ctx.addIssue({ code: "custom", path, message: "sourceEnd exceeds asset duration" });
        }
        if (item.type === "motion" && item.media.some(id => !c.assets[id] || !["image", "video"].includes(c.assets[id].kind)))
          ctx.addIssue({ code: "custom", path, message: "motion media must be image or video assets" });
        if (item.type === "caption" && item.words.some(w => w.end < w.start || w.end > item.duration + 1e-3))
          ctx.addIssue({ code: "custom", path, message: "caption word timing is outside the item" });
        if (item.type === "code" && (item.typingDuration > item.duration || item.changes.some((change, i) =>
          change.at + change.typingDuration > item.duration || (i > 0 && change.at <= item.changes[i - 1].at))))
          ctx.addIssue({ code: "custom", path, message: "code changes must be ordered and finish within the item" });
      }),
    );
  });

export type Composition = z.infer<typeof Composition>;
export type CropKeyframe = z.infer<typeof CropKeyframe>;
export type CaptionWord = z.infer<typeof CaptionWord>;

/** Parse untrusted JSON into a validated composition (throws ZodError with paths). */
export const parseComposition = (doc: unknown): Composition => Composition.parse(doc);

/** JSON Schema for non-TS consumers. Cross-field rules (superRefine) are enforced again in Python. */
export const jsonSchema = () => z.toJSONSchema(Composition, { target: "draft-2020-12", io: "input" });
