"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Film, Scissors } from "lucide-react";
import { useState } from "react";
import { apiFetch, useBackend } from "@/lib/backend";
import { createClient } from "@/lib/supabase/client";

/** Same names as apps/api/app/services/highlights/profiles.py and app/api/recordings.py AnalyzeOptions. */
const PROFILES = [
  ["auto", "Auto: detect from the recording"],
  ["podcast", "Podcast / interview"],
  ["business", "Business / entrepreneurship"],
  ["motivational", "Motivational / storytelling"],
  ["general", "General creator clips"],
  ["education", "Educational / technical (class reels)"],
] as const;
const COUNTS = ["auto", "5", "10", "15", "20", "30", "custom"] as const;
const DURATIONS = [
  ["auto", "Auto: shortest length that keeps the idea whole"],
  ["15-30", "15–30 s"],
  ["30-45", "30–45 s"],
  ["45-60", "45–60 s"],
  ["30-60", "30–60 s"],
  ["60-90", "60–90 s"],
  ["90-180", "Up to 3 min (YouTube Shorts; check campaign rules)"],
] as const;
const PACES = [
  ["natural", "Natural: keeps conversational rhythm"],
  ["engaging", "Engaging: removes dead air and um/uh"],
  ["fast", "Fast: tight Shorts pacing"],
  ["original", "Original: no speech cuts"],
] as const;

export type AnalysisReport = {
  profile?: string;
  requested?: number | null;
  selected?: number;
  eligible?: number;
  candidates?: number;
  duplicates_rejected?: number;
  llm_rejected?: number;
  shortfall?: string;
  topics_covered?: number;
  rejected?: Record<string, number>;
};

type BatchClip = {
  highlight_id: string; title: string; start_s: number; end_s: number; status: string; score: number | null;
  render: { id: string; status: string; error: string | null; render_s: number | null } | null;
  job: { status: string; current_stage: string | null; attempts: number; error: string | null } | null;
};

/** "1:05:30", "12:40" or "90" → seconds; "" → null. */
const secs = (v: string) => {
  if (!v.trim()) return null;
  const n = v.split(":").map(Number);
  return n.some(Number.isNaN) ? null : n.reduce((a, x) => a * 60 + x, 0);
};
const field = "rounded-[4px] bg-surface-2 px-2 py-1.5 text-ink outline-none focus-visible:ring-2 focus-visible:ring-accent";

export function BulkClipping({ recordingId, projectId, canEdit, selectedIds, report }: {
  recordingId: string; projectId: string; canEdit: boolean; selectedIds: string[]; report?: AnalysisReport | null;
}) {
  const qc = useQueryClient();
  const backend = useBackend();
  const base = backend.data?.state === "online" ? backend.data.url : null;
  const [profile, setProfile] = useState<string>("auto");
  const [range, setRange] = useState({ start: "", end: "" });
  const [layout, setLayout] = useState("auto");
  const [hookStyle, setHookStyle] = useState("classic");
  const [zoom, setZoom] = useState(true);
  const [color, setColor] = useState(false);
  const [sfx, setSfx] = useState(false);
  const [enhance, setEnhance] = useState(true);
  const [count, setCount] = useState<(typeof COUNTS)[number]>("10");
  const [custom, setCustom] = useState(12);
  const [duration, setDuration] = useState("auto");
  const [pace, setPace] = useState("engaging");
  const [preset, setPreset] = useState("auto");
  const [hookTitle, setHookTitle] = useState(true);
  const [emphasis, setEmphasis] = useState(true);
  const [kit, setKit] = useState("");
  const [brief, setBrief] = useState("");
  const [campaignOn, setCampaignOn] = useState(false);
  const [camp, setCamp] = useState({ name: "", min_s: 15, max_s: 60, hashtags: "", mentions: "", required_text: "", topic: "", rights: false });
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const presets = useQuery({
    queryKey: ["caption-presets", base],
    enabled: !!base,
    staleTime: 3600_000,
    queryFn: async () => (await (await apiFetch(base!, "/captions/presets")).json()) as { id: string; name: string; family: string }[],
  });
  const kits = useQuery({
    queryKey: ["brand-kit-names", projectId],
    staleTime: 60_000,
    queryFn: async () => {
      const sb = createClient();
      const { data: p, error: pe } = await sb.from("projects").select("organization_id").eq("id", projectId).single();
      if (pe) throw pe;
      const { data, error } = await sb.from("brand_kits").select("id, name, is_default").eq("organization_id", p.organization_id).order("created_at");
      if (error) throw error;
      return data as { id: string; name: string; is_default: boolean }[];
    },
  });
  const batch = useQuery({
    queryKey: ["batch", recordingId, base],
    enabled: !!base,
    queryFn: async () => (await (await apiFetch(base!, `/recordings/${recordingId}/batch`)).json()) as { clips: BatchClip[]; counts: Record<string, number> },
    refetchInterval: (q) => (q.state.data?.clips.some((c) => c.render && ["queued", "rendering"].includes(c.render.status)) ? 3000 : false),
  });

  async function generate() {
    setError(null); setMsg(null);
    if (!base) return setError("The processing backend is offline.");
    const n = count === "auto" ? null : count === "custom" ? custom : Number(count);
    const r = await apiFetch(base, `/recordings/${recordingId}/analyze`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile, count: n, duration: profile === "education" ? "30-60" : duration, brief,
        range_start_s: secs(range.start), range_end_s: secs(range.end) }),
    });
    if (!r.ok) return setError((await r.json()).detail ?? "Could not start the analysis");
    setMsg("Finding clips. The transcript and earlier analysis are reused, so a new count is quick.");
    qc.invalidateQueries({ queryKey: ["jobs", projectId] });
  }

  async function renderClips(ids: string[] | null) {
    setError(null); setMsg(null);
    if (!base) return setError("The processing backend is offline.");
    const list = (s: string) => s.split(/[\s,]+/).filter(Boolean);
    const campaign = campaignOn ? { name: camp.name || "Campaign", source_rights_confirmed: camp.rights, min_s: camp.min_s, max_s: camp.max_s,
      hashtags: list(camp.hashtags), mentions: list(camp.mentions), required_text: camp.required_text, topic: camp.topic } : null;
    const r = await apiFetch(base, `/recordings/${recordingId}/render-batch`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ highlight_ids: ids, engine: "auto", pace, caption_preset: preset, emphasis, hook_title: hookTitle,
        hook_style: hookStyle, auto_zoom: zoom, color_correct: color, sfx, enhance_audio: enhance, layout,
        brand_kit_id: kit || null, captions: true, quality: "looks", campaign }),
    });
    const body = await r.json();
    if (!r.ok) return setError(typeof body.detail === "string" ? body.detail : "Batch render refused");
    const reused = body.renders.filter((x: { cached: boolean }) => x.cached).length;
    setMsg(`${body.renders.length} clip${body.renders.length === 1 ? "" : "s"} queued${reused ? ` (${reused} unchanged, reused)` : ""}` +
      (body.skipped.length ? `; ${body.skipped.length} skipped by the campaign checks: ${body.skipped.map((s: { title: string; campaign: { issues: string[] } }) => `${s.title}: ${s.campaign.issues.join(", ")}`).join("; ")}` : "."));
    qc.invalidateQueries({ queryKey: ["batch", recordingId] });
  }

  async function zip() {
    if (!base) return setError("The processing backend is offline.");
    const u = await (await apiFetch(base, `/recordings/${recordingId}/batch-zip-url`)).json();
    const r = await fetch(`${base.replace(/\/$/, "")}${u.url}`, { headers: { "X-Tunnel-Skip-AntiPhishing-Page": "true" } }).catch(() => null);
    if (!r?.ok) return setError(r?.status === 404 ? "No finished exports yet." : "Download failed. Is the processing backend online?");
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(await r.blob()), download: `shorts-${recordingId.slice(0, 8)}.zip` });
    a.click();
    URL.revokeObjectURL(a.href);
  }

  const clips = batch.data?.clips ?? [];
  const ready = clips.filter((c) => c.render?.status === "ready").length;
  return (
    <section className="space-y-4 rounded-[6px] bg-surface p-4">
      <header className="flex items-baseline justify-between gap-3">
        <h3 className="flex items-center gap-2 text-[17px]"><Scissors size={16} aria-hidden /> Bulk AI clipping</h3>
        <span className="text-[12px] text-muted">Analysis runs once and is reused when you change these settings</span>
      </header>
      {canEdit && (
        <div className="grid gap-3 text-[13px] sm:grid-cols-2 xl:grid-cols-3">
          <label className="grid gap-1 text-muted">Content category
            <select className={field} value={profile} onChange={(e) => setProfile(e.target.value)}>
              {PROFILES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-muted">How many clips do you want?
            <span className="flex gap-2">
              <select className={`${field} flex-1`} value={count} onChange={(e) => setCount(e.target.value as typeof count)}>
                {COUNTS.map((c) => <option key={c} value={c}>{c === "auto" ? "Auto: every strong, distinct clip" : c === "custom" ? "Custom number" : `${c} clips`}</option>)}
              </select>
              {count === "custom" && <input type="number" min={1} max={60} value={custom} onChange={(e) => setCustom(Math.max(1, Math.min(60, Number(e.target.value))))} className={`${field} w-20 tabular-nums`} aria-label="Custom clip count" />}
            </span>
          </label>
          <label className="grid gap-1 text-muted">Duration
            <select className={field} value={duration} onChange={(e) => setDuration(e.target.value)} disabled={profile === "education"}>
              {DURATIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-muted">Editing intensity
            <select className={field} value={pace} onChange={(e) => setPace(e.target.value)}>
              {PACES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-muted">Caption style
            <select className={field} value={preset} onChange={(e) => setPreset(e.target.value)}>
              <option value="auto">Auto: chosen for the content and pace</option>
              {(presets.data ?? []).map((p) => <option key={p.id} value={p.id}>{p.family} · {p.name}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-muted">Brand kit
            <select className={field} value={kit} onChange={(e) => setKit(e.target.value)}>
              <option value="">Organisation default</option>
              <option value="none">No branding</option>
              {(kits.data ?? []).map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-muted">Adjust range (optional)
            <span className="flex items-center gap-2">
              <input className={`${field} w-full tabular-nums`} placeholder="start 0:00" value={range.start} onChange={(e) => setRange({ ...range, start: e.target.value })} aria-label="Range start" />
              <input className={`${field} w-full tabular-nums`} placeholder="end" value={range.end} onChange={(e) => setRange({ ...range, end: e.target.value })} aria-label="Range end" />
            </span>
          </label>
          <label className="grid gap-1 text-muted">Layout (9:16)
            <select className={field} value={layout} onChange={(e) => setLayout(e.target.value)}>
              <option value="auto">Auto: follow the active speaker (split screen in fast exchanges)</option>
              <option value="fill">Fill: centred crop</option>
              <option value="fit">Fit: whole frame over a blurred background</option>
            </select>
          </label>
          <label className="grid gap-1 text-muted">Hook headline style
            <select className={field} value={hookStyle} onChange={(e) => setHookStyle(e.target.value)} disabled={!hookTitle}>
              <option value="classic">Classic: white card</option>
              <option value="statement">Statement: large bold lines</option>
              <option value="editorial">Editorial: serif in the accent colour</option>
            </select>
          </label>
          <label className="grid gap-1 text-muted sm:col-span-2 xl:col-span-3">Moments to include / editing prompt (optional)
            <textarea rows={2} value={brief} onChange={(e) => setBrief(e.target.value)} maxLength={2000} className={field}
              placeholder="e.g. Find the strongest business insights. Each clip explains one complete idea and ends naturally." />
          </label>
          <div className="flex flex-wrap gap-4 sm:col-span-2 xl:col-span-3">
            <label className="flex items-center gap-2"><input type="checkbox" checked={hookTitle} onChange={(e) => setHookTitle(e.target.checked)} /> Hook title from the clip&apos;s own words</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={emphasis} onChange={(e) => setEmphasis(e.target.checked)} /> Emphasise key numbers and claims</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={zoom} onChange={(e) => setZoom(e.target.checked)} /> Auto zoom on key words</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={enhance} onChange={(e) => setEnhance(e.target.checked)} /> Enhance audio</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={color} onChange={(e) => setColor(e.target.checked)} /> Auto colour correction</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={sfx} onChange={(e) => setSfx(e.target.checked)} /> Auto SFX</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={campaignOn} onChange={(e) => setCampaignOn(e.target.checked)} /> Clipping campaign brief</label>
          </div>
          {campaignOn && (
            <div className="grid gap-2 rounded-[6px] bg-surface-2 p-3 sm:col-span-2 xl:col-span-3 sm:grid-cols-3">
              <input className={field} placeholder="Campaign name" value={camp.name} onChange={(e) => setCamp({ ...camp, name: e.target.value })} />
              <input className={field} placeholder="Required topic" value={camp.topic} onChange={(e) => setCamp({ ...camp, topic: e.target.value })} />
              <span className="flex gap-2">
                <input type="number" className={`${field} w-full`} value={camp.min_s} onChange={(e) => setCamp({ ...camp, min_s: Number(e.target.value) })} aria-label="Minimum seconds" />
                <input type="number" className={`${field} w-full`} value={camp.max_s} onChange={(e) => setCamp({ ...camp, max_s: Number(e.target.value) })} aria-label="Maximum seconds" />
              </span>
              <input className={field} placeholder="#hashtags (space separated)" value={camp.hashtags} onChange={(e) => setCamp({ ...camp, hashtags: e.target.value })} />
              <input className={field} placeholder="@mentions" value={camp.mentions} onChange={(e) => setCamp({ ...camp, mentions: e.target.value })} />
              <input className={field} placeholder="Required caption text" value={camp.required_text} onChange={(e) => setCamp({ ...camp, required_text: e.target.value })} />
              <label className="flex items-center gap-2 text-ink sm:col-span-3"><input type="checkbox" checked={camp.rights} onChange={(e) => setCamp({ ...camp, rights: e.target.checked })} /> I am authorised to clip this source for this campaign</label>
              <p className="text-[12px] text-muted sm:col-span-3">Checks follow the brief as written. They do not guarantee approval, payment or views, and nothing is published automatically.</p>
            </div>
          )}
          <div className="flex flex-wrap gap-2 sm:col-span-2 xl:col-span-3">
            <button type="button" onClick={generate} className="flex items-center gap-1.5 rounded-[4px] bg-accent px-3 py-1.5 font-semibold text-accent-ink hover:brightness-110">
              <Scissors size={14} aria-hidden /> Generate clips
            </button>
            <button type="button" onClick={() => renderClips(selectedIds.length ? selectedIds : null)} className="flex items-center gap-1.5 rounded-[4px] bg-surface-3 px-3 py-1.5 hover:bg-surface-2">
              <Film size={14} aria-hidden /> {selectedIds.length ? `Render ${selectedIds.length} selected` : "Render all eligible"}
            </button>
            <button type="button" onClick={zip} disabled={!ready} className="flex items-center gap-1.5 rounded-[4px] bg-surface-3 px-3 py-1.5 hover:bg-surface-2 disabled:opacity-50">
              <Download size={14} aria-hidden /> Download all as ZIP ({ready})
            </button>
          </div>
        </div>
      )}
      {error && <p className="text-[13px] text-danger">{error}</p>}
      {msg && <p className="text-[13px] text-muted">{msg}</p>}
      {report && report.profile && report.profile !== "education" && (
        <p className="rounded-[6px] bg-surface-2 p-3 text-[13px]">
          {report.selected} distinct clip{report.selected === 1 ? "" : "s"} selected{report.requested ? ` of ${report.requested} requested` : " (auto)"} from {report.candidates} candidates
          {" · "}{report.topics_covered} topics{report.duplicates_rejected ? ` · ${report.duplicates_rejected} near-duplicates rejected` : ""}
          {report.shortfall && <span className="mt-1 block text-accent">{report.shortfall}</span>}
        </p>
      )}
      {clips.some((c) => c.render) && (
        <table className="w-full text-[12.5px]">
          <thead className="text-left text-muted"><tr><th className="font-normal">Clip</th><th className="font-normal">Length</th><th className="font-normal">Export</th></tr></thead>
          <tbody>
            {clips.filter((c) => c.render).map((c) => (
              <tr key={c.highlight_id} className="border-t border-line">
                <td className="py-1 pr-3">{c.title}</td>
                <td className="tabular-nums text-muted">{(c.end_s - c.start_s).toFixed(1)} s</td>
                <td className={c.render?.status === "ready" ? "text-success" : c.render?.status === "failed" ? "text-danger" : "text-muted"}>
                  {c.render?.status}{c.job?.current_stage && c.render?.status !== "ready" ? ` · ${c.job.current_stage}` : ""}
                  {c.render?.status === "ready" && c.render.render_s ? ` · ${c.render.render_s} s` : ""}
                  {c.render?.status === "failed" && canEdit && (
                    <button type="button" className="ml-2 underline" onClick={() => renderClips([c.highlight_id])}>retry</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
