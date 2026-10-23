"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { createFromIdea } from "@/app/(app)/campaigns/actions";
import { createClient } from "@/lib/supabase/client";

type Reel = { key: string; title: string; hook: string; script: string; caption: string; hashtags: string[]; cta: string; mode: "edit" | "recording"; style: string; duration_s: number; shots: string[] };
type Plan = { concept: string; strategy: string; pillars: string[]; reels: Reel[]; series: { name: string; reel_keys: string[] }[]; schedule: { date: string; time: string; reel_key: string }[] };
type Campaign = { id: string; code: string; status: string; error: string | null; language: string; business: Record<string, string>; plan: Plan | null; provenance: { engine: string; grounding: string[]; errors: string[] } | null };
type Link = { slug: string; reel_key: string; kind: string; destination: string; clicks: number };
type Click = { slug: string; at: string; device: string };
type Inquiry = { id: string; channel: string; source: string; name: string | null; message: string | null; created_at: string; slug: string | null };

/** Suggestions from recorded numbers only (same thresholds documented in docs/REEL_STUDIO_2_HANDOFF.md). */
function suggest(plan: Plan | null, links: Link[], clicks: Click[], inq: Inquiry[]): string[] {
  if (!clicks.length && !inq.length) return ["No clicks or inquiries recorded yet. Post the first reel and put its tracked link in your bio, story or DM replies."];
  const reelOf = Object.fromEntries(links.map((l) => [l.slug, l.reel_key]));
  const by: Record<string, number> = {};
  clicks.forEach((c) => { by[reelOf[c.slug]] = (by[reelOf[c.slug]] ?? 0) + 1; });
  const out: string[] = [];
  const [best, n] = Object.entries(by).sort((a, b) => b[1] - a[1])[0] ?? ["", 0];
  const title = plan?.reels.find((r) => r.key === best)?.title ?? best;
  if (clicks.length >= 10 && n / clicks.length >= 0.4) out.push(`"${title}" brought ${n} of ${clicks.length} clicks: make the next reel in the same format.`);
  if (clicks.length >= 20 && !inq.length) out.push(`${clicks.length} clicks but no inquiries yet: make the call to action more specific (what to ask, when to visit).`);
  const mob = clicks.filter((c) => c.device === "mobile").length;
  if (clicks.length >= 10 && mob / clicks.length > 0.8) out.push(`${mob} of ${clicks.length} clicks came from phones: keep forms and pages short.`);
  if (!out.length) out.push(`So far: ${clicks.length} recorded clicks and ${inq.length} inquiries. More data is needed before a reliable pattern shows.`);
  return out;
}

export function CampaignView({ id, orgId, canEdit, siteUrl }: { id: string; orgId: string; canEdit: boolean; siteUrl: string }) {
  const qc = useQueryClient();
  const origin = siteUrl || (typeof window !== "undefined" ? window.location.origin : "");
  const data = useQuery({
    queryKey: ["campaign", id],
    queryFn: async () => {
      const sb = createClient();
      const [c, l, i] = await Promise.all([
        sb.from("campaigns").select("id, code, status, error, language, business, plan, provenance").eq("id", id).single(),
        sb.from("tracked_links").select("slug, reel_key, kind, destination, clicks").eq("campaign_id", id),
        sb.from("inquiries").select("id, channel, source, name, message, created_at, slug").eq("campaign_id", id).order("created_at", { ascending: false }),
      ]);
      if (c.error) throw c.error;
      const slugs = (l.data ?? []).map((x) => x.slug);
      const k = slugs.length ? await sb.from("link_clicks").select("slug, at, device").in("slug", slugs) : { data: [] };
      return { c: c.data as Campaign, links: (l.data ?? []) as Link[], inq: (i.data ?? []) as Inquiry[], clicks: (k.data ?? []) as Click[] };
    },
    refetchInterval: (q) => (q.state.data?.c.status === "ready" || q.state.data?.c.status === "failed" ? 30_000 : 3000),
  });
  useEffect(() => {
    const sb = createClient();
    const ch = sb.channel(`campaign:${id}:${crypto.randomUUID()}`).on("postgres_changes", { event: "*", schema: "public", table: "campaigns", filter: `id=eq.${id}` }, () => qc.invalidateQueries({ queryKey: ["campaign", id] })).subscribe();
    return () => { sb.removeChannel(ch); };
  }, [id, qc]);
  const [busy, setBusy] = useState<string | null>(null);
  const [inquiry, setInquiry] = useState({ channel: "whatsapp", name: "", message: "" });
  if (data.isLoading) return <p className="text-muted">Loading…</p>;
  if (!data.data) return <p className="text-danger">Campaign could not load.</p>;
  const { c, links, inq, clicks } = data.data;
  const p = c.plan;
  const linkFor = (key: string) => links.filter((l) => l.reel_key === key);

  async function record() {
    const { error } = await createClient().from("inquiries").insert({ organization_id: orgId, campaign_id: id, channel: inquiry.channel, name: inquiry.name || null,
      message: inquiry.message || null, source: "member", recorded_by: (await createClient().auth.getUser()).data.user?.id });
    if (!error) setInquiry({ ...inquiry, name: "", message: "" });
    qc.invalidateQueries({ queryKey: ["campaign", id] });
  }

  return (
    <div className="space-y-6">
      <header><p className="studio-eyebrow">Campaign · {c.code}</p><h1 className="studio-heading mt-2">{c.business.name}</h1>
        <p className="mt-1 text-[13px] text-muted">{c.business.industry}{c.business.city ? ` · ${c.business.city}` : ""} · goal: {c.business.goal} · language: {c.language}</p></header>
      {c.status !== "ready" && <p className="flex items-center gap-2 text-[14px]">{c.status === "failed" ? <span className="text-danger">Planning failed: {c.error}</span> : <><LoaderCircle size={15} className="animate-spin" aria-hidden />The local AI is writing the campaign…</>}</p>}
      {p && <>
        <section className="studio-panel space-y-2 p-5"><h2 className="text-[17px] font-semibold">{p.concept}</h2><p className="text-[13px] leading-6">{p.strategy}</p>
          <p className="text-[12px] text-muted">Pillars: {p.pillars.join(" · ")} · written by {c.provenance?.engine === "rules" ? "the rule-based planner (no AI model answered)" : c.provenance?.engine}</p>
          {!!c.provenance?.grounding.length && <p className="text-[11px] text-muted">Fact checks applied: {c.provenance.grounding.join("; ")}</p>}</section>
        <section className="grid gap-4 lg:grid-cols-2">{p.reels.map((r) => <article key={r.key} className="studio-panel space-y-2 p-5 text-[13px]">
          <div className="flex items-start justify-between gap-3"><h3 className="text-[15px] font-semibold">{r.title}</h3><span className="studio-pill">{r.mode === "edit" ? "Prompt → Edit" : "Recording → Reels"} · {r.duration_s}s</span></div>
          <p><b>Hook:</b> {r.hook}</p><p><b>Script:</b> {r.script}</p><p><b>Caption:</b> {r.caption} <span className="text-accent">{r.hashtags.join(" ")}</span></p><p><b>CTA:</b> {r.cta}</p>
          {r.shots.length > 0 && <p className="text-muted">Shots: {r.shots.join(" · ")}</p>}
          {linkFor(r.key).map((l) => <p key={l.slug} className="flex items-center gap-2 text-[12px]"><span className="text-muted">{l.kind === "whatsapp" ? "WhatsApp link" : "Website link"}:</span><code>{origin}/r/{l.slug}</code>
            <button type="button" aria-label="Copy link" onClick={() => navigator.clipboard.writeText(`${origin}/r/${l.slug}`)}><Copy size={12} /></button><span className="text-muted">{l.clicks} clicks</span></p>)}
          {canEdit && <button type="button" className="studio-button !py-2 !text-[12px]" disabled={busy === r.key}
            onClick={async () => { setBusy(r.key); await createFromIdea(id, r.key, r.mode, `${c.business.name}: ${r.title}`); }}>{busy === r.key ? "Creating…" : r.mode === "edit" ? "Make this reel from my clips" : "Make this reel from a recording"}</button>}
        </article>)}</section>
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="studio-panel p-5"><h2 className="text-[15px] font-semibold">Posting plan</h2><ul className="mt-3 space-y-1 text-[13px]">{p.schedule.map((s, i) => <li key={i}>{s.date} · {s.time} — {p.reels.find((r) => r.key === s.reel_key)?.title}</li>)}</ul>
            {p.series.map((s) => <p key={s.name} className="mt-2 text-[12px] text-muted">Series “{s.name}”: {s.reel_keys.map((k) => p.reels.find((r) => r.key === k)?.title).join(" → ")}</p>)}</div>
          <div className="studio-panel p-5"><h2 className="text-[15px] font-semibold">Results (recorded events only)</h2>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-[13px]"><dt className="text-muted">Link clicks</dt><dd className="font-semibold tabular-nums">{clicks.length}</dd>
              <dt className="text-muted">Inquiries</dt><dd className="font-semibold tabular-nums">{inq.length} ({inq.filter((i) => i.source === "visitor").length} via form, {inq.filter((i) => i.source === "member").length} recorded by you)</dd></dl>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-[12px]">{suggest(p, links, clicks, inq).map((s) => <li key={s}>{s}</li>)}</ul>
            {links[0] && <p className="mt-3 text-[12px] text-muted">Inquiry form for this campaign: <code>{origin}/i/{links[0].slug}</code></p>}
          </div>
        </section>
        {canEdit && <section className="studio-panel space-y-3 p-5"><h2 className="text-[15px] font-semibold">Record an inquiry</h2>
          <p className="text-[12px] text-muted">Got a WhatsApp message, call or walk-in because of this campaign? Record it here so the results stay real.</p>
          <div className="grid gap-3 sm:grid-cols-[150px_1fr_2fr_auto]">
            <select className="studio-input" value={inquiry.channel} onChange={(e) => setInquiry({ ...inquiry, channel: e.target.value })}>{["whatsapp", "call", "walk-in", "other"].map((x) => <option key={x}>{x}</option>)}</select>
            <input className="studio-input" placeholder="Name (optional)" maxLength={80} value={inquiry.name} onChange={(e) => setInquiry({ ...inquiry, name: e.target.value })} />
            <input className="studio-input" placeholder="What they asked" maxLength={1000} value={inquiry.message} onChange={(e) => setInquiry({ ...inquiry, message: e.target.value })} />
            <button type="button" className="studio-button" onClick={record}>Record</button></div>
          {inq.length > 0 && <ul className="divide-y divide-line text-[12px]">{inq.slice(0, 20).map((i) => <li key={i.id} className="py-2">{new Date(i.created_at).toLocaleString()} · {i.channel} · {i.source === "visitor" ? "form" : "recorded"}{i.name ? ` · ${i.name}` : ""}{i.message ? ` — ${i.message}` : ""}</li>)}</ul>}
        </section>}
      </>}
    </div>
  );
}
