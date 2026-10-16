"use client";

import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, ChartNoAxesCombined, ExternalLink, LoaderCircle, RefreshCw, Sparkles, Trophy } from "lucide-react";
import { useEffect, useState } from "react";
import { useBackend } from "@/lib/backend";
import { createClient } from "@/lib/supabase/client";
import { platformName, socialRequest, type AccountInsights, type FeedbackRow, type FeedbackSummary, type ReelMedia, type SocialAccount } from "@/lib/social";

const METRIC_NAMES: Record<string, string> = {
  views: "Views", reach: "Accounts reached", impressions: "Impressions", likes: "Likes", comments: "Comments", shares: "Shares", saved: "Saves", total_interactions: "Total interactions", accounts_engaged: "Accounts engaged", ig_reels_video_view_total_time: "Total watch time", ig_reels_avg_watch_time: "Average watch time",
};
type RefreshJob = { status: string; error: string | null; progress: number; current_stage: string | null };
const num = (v: number | null | undefined) => (typeof v === "number" && Number.isFinite(v) ? v.toLocaleString() : "—");

function engagement(m: ReelMedia) {
  const i = m.insights ?? {};
  const reach = i.reach;
  const inter = i.total_interactions ?? ((i.likes ?? m.like_count ?? 0) + (i.comments ?? m.comments_count ?? 0) + (i.shares ?? 0) + (i.saved ?? 0));
  return reach ? inter / reach : null;
}

export function AnalyticsStudio({ organizationId, canEdit }: { organizationId: string; canEdit: boolean }) {
  const backend = useBackend();
  const base = backend.data?.state === "online" ? backend.data.url : null;
  const qc = useQueryClient();
  const [accountId, setAccountId] = useState("");
  const [refreshJobs, setRefreshJobs] = useState<Record<string, string>>({});
  const [requesting, setRequesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const accounts = useQuery({ queryKey: ["social-accounts", organizationId, base], enabled: !!base, queryFn: () => socialRequest<SocialAccount[]>(base!, `/social/accounts?organization_id=${encodeURIComponent(organizationId)}`) });
  const selected = accounts.data?.find((a) => a.id === accountId) ?? accounts.data?.[0];
  const insights = useQuery({ queryKey: ["social-insights", selected?.id, base], enabled: !!base && !!selected, queryFn: () => socialRequest<AccountInsights>(base!, `/social/accounts/${selected!.id}/insights`) });
  const jobId = selected ? refreshJobs[selected.id] : undefined;
  const job = useQuery<RefreshJob>({
    queryKey: ["insights-job", jobId], enabled: !!jobId,
    queryFn: async () => {
      const { data, error } = await createClient().from("jobs").select("status,error,progress,current_stage").eq("id", jobId!).single();
      if (error) throw error;
      return data as RefreshJob;
    },
    refetchInterval: (q) => ["succeeded", "failed", "cancelled"].includes(q.state.data?.status ?? "") ? false : 3000,
  });
  useEffect(() => {
    if (job.data?.status === "succeeded" && selected) {
      qc.invalidateQueries({ queryKey: ["social-insights", selected.id] });
      qc.invalidateQueries({ queryKey: ["feedback", organizationId] });
    }
  }, [job.data?.status, selected, qc, organizationId]);
  const running = requesting || (!!jobId && (!job.data || ["queued", "running"].includes(job.data.status)));

  async function refresh() {
    if (!base || !selected || !canEdit || running) return;
    const id = selected.id;
    setError(null); setRequesting(true);
    try {
      const result = await socialRequest<{ job_id: string }>(base, `/social/accounts/${id}/insights`, {});
      setRefreshJobs((previous) => ({ ...previous, [id]: result.job_id }));
    } catch (e) { setError(e instanceof Error ? e.message : "Metrics refresh could not start."); }
    finally { setRequesting(false); }
  }
  const metrics = insights.data?.metrics ?? [];
  const reels = [...(insights.data?.media ?? [])].sort((a, b) => (b.insights?.views ?? 0) - (a.insights?.views ?? 0));

  return <div className="space-y-7">
    <header className="flex flex-wrap items-end justify-between gap-4"><div><p className="studio-eyebrow mb-2">Instagram</p><h1 className="studio-heading">Analytics</h1><p className="mt-2 text-[14px] text-muted">Real numbers from Instagram, and what they suggest for your next reel.</p></div><Link href="/publishing" className="studio-button studio-button-secondary">Publishing<ArrowUpRight size={14} aria-hidden /></Link></header>
    {!base && <div className="studio-panel p-4 text-[13px] text-muted">{backend.isLoading ? "Connecting to the processing machine…" : "The processing machine is offline. Connect it to load or refresh Instagram metrics."}</div>}
    {accounts.error && <p role="alert" className="text-[13px] text-danger">Accounts could not load: {accounts.error.message}</p>}
    {accounts.data?.length === 0 ? <section className="studio-panel p-8 sm:p-12"><ChartNoAxesCombined size={34} strokeWidth={1.3} className="mb-6 text-accent" aria-hidden /><h2 className="text-[22px] font-semibold tracking-[-.02em]">No Instagram account connected yet</h2><p className="mt-3 max-w-[55ch] text-[14px] leading-7 text-muted">Connect your Instagram Business account and publish a reel. Its real views, reach and engagement appear here after a refresh. Nothing is estimated.</p><Link href="/publishing" className="studio-button mt-6">Connect Instagram</Link></section> : <>
      <section className="studio-panel flex flex-wrap items-end justify-between gap-4 p-5"><label className="studio-label min-w-0 flex-1 sm:max-w-[360px]">Account<select className="studio-input" value={selected?.id ?? ""} onChange={(e) => { setAccountId(e.target.value); setError(null); }} disabled={!accounts.data?.length}><option value="" disabled>Select an account</option>{accounts.data?.map((a) => <option key={a.id} value={a.id}>{platformName(a.platform)} · @{a.username}</option>)}</select></label><div className="flex flex-wrap items-center gap-4"><span className="text-[11px] text-muted">{insights.data?.updated_at ? `Updated ${new Date(insights.data.updated_at).toLocaleString()}` : "Never refreshed"}</span>{canEdit && <button type="button" disabled={!base || !selected || running} onClick={refresh} className="studio-button">{running ? <LoaderCircle size={14} className="animate-spin" aria-hidden /> : <RefreshCw size={14} aria-hidden />}{running ? "Refreshing…" : "Refresh from Instagram"}</button>}</div></section>
      {running && <div className="studio-panel p-4 text-[13px] text-muted" role="status">{job.data?.current_stage?.replaceAll("_", " ") || "Refresh queued on the processing machine."}{job.data && <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-2"><div className="h-full bg-signal transition-[width]" style={{ width: `${Math.round(job.data.progress * 100)}%` }} /></div>}</div>}
      {(error || insights.error || job.error || job.data?.error) && <p role="alert" className="text-[13px] leading-6 text-danger">{error || insights.error?.message || job.error?.message || job.data?.error}</p>}

      {metrics.length > 0 && <section aria-label="Account metrics" className="grid grid-cols-2 gap-3 xl:grid-cols-4">{metrics.slice(0, 8).map((metric, i) => <article key={`${metric.name}-${i}`} className="studio-panel p-5"><h2 className="text-[12px] font-medium text-muted">{METRIC_NAMES[metric.name] || metric.name.replaceAll("_", " ")}</h2><p className="mt-3 text-[30px] font-semibold leading-none tracking-[-.03em] tabular-nums">{num(metric.value)}</p><p className="mt-2 text-[11px] text-muted">{metric.period ? `Per ${metric.period.replaceAll("_", " ")}` : "Reporting period"}{metric.as_of ? ` · ${new Date(metric.as_of).toLocaleDateString()}` : ""}</p></article>)}</section>}

      {reels.length > 0 ? <ReelsSection reels={reels} /> : selected && !running && <section className="studio-panel p-8"><ChartNoAxesCombined size={26} strokeWidth={1.4} className="mb-4 text-accent" aria-hidden /><h2 className="text-[17px] font-semibold">No reel metrics yet</h2><p className="mt-2 max-w-[60ch] text-[13px] leading-6 text-muted">{insights.isFetching ? "Loading saved metrics…" : "Refresh from Instagram to load your recent reels and their insights. Metrics Instagram does not provide are listed below, never shown as zero."}</p></section>}

      <FeedbackPanel base={base} organizationId={organizationId} canEdit={canEdit} />

      {!!insights.data?.unavailable.length && <details className="studio-panel p-5"><summary className="cursor-pointer text-[13px] font-medium">Metrics Instagram did not provide ({insights.data.unavailable.length})</summary><ul className="mt-3 list-inside list-disc space-y-1.5 text-[12.5px] leading-6 text-muted">{insights.data.unavailable.map((reason, i) => <li key={i}>{reason}</li>)}</ul></details>}
    </>}
  </div>;
}

function ReelsSection({ reels }: { reels: ReelMedia[] }) {
  const maxViews = Math.max(1, ...reels.map((r) => r.insights?.views ?? 0));
  const timeline = [...reels].filter((r) => r.timestamp).sort((a, b) => a.timestamp!.localeCompare(b.timestamp!));
  const maxT = Math.max(1, ...timeline.map((r) => r.insights?.views ?? 0));
  return <section className="space-y-4">
    <div className="studio-panel p-5">
      <h2 className="text-[15px] font-semibold">Views over time</h2><p className="mt-1 text-[12px] text-muted">Each bar is one reel, in posting order.</p>
      <div className="mt-5 flex h-40 items-end gap-1.5" role="img" aria-label="Views per reel over time">{timeline.map((r) => { const v = r.insights?.views ?? 0; return <div key={r.id} className="group relative flex h-full flex-1 flex-col justify-end"><div className="min-h-[2px] rounded-t bg-accent/80 transition-colors group-hover:bg-accent" style={{ height: `${(v / maxT) * 100}%` }} /><span className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1 hidden -translate-x-1/2 whitespace-nowrap rounded bg-surface-3 px-2 py-1 text-[11px] group-hover:block">{num(r.insights?.views)} views · {new Date(r.timestamp!).toLocaleDateString()}</span></div>; })}</div>
    </div>
    <div className="studio-panel overflow-x-auto">
      <table className="w-full min-w-[760px] text-left text-[12.5px]">
        <caption className="px-5 pt-5 text-left text-[15px] font-semibold">Reel comparison</caption>
        <thead className="text-[11px] uppercase tracking-[.06em] text-muted"><tr className="border-b border-line">{["Reel", "Views", "Reach", "Likes", "Comments", "Shares", "Saves", "Avg watch", "Engagement"].map((h) => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}</tr></thead>
        <tbody>{reels.map((r, i) => { const ins = r.insights ?? {}; const e = engagement(r); return <tr key={r.id} className="border-b border-line/60 last:border-0">
          <td className="max-w-[260px] px-4 py-3"><div className="flex items-center gap-2">{i === 0 && <Trophy size={14} className="shrink-0 text-accent" aria-label="Top reel" />}<span className="truncate">{r.caption?.split("\n")[0] || "Untitled reel"}</span>{r.permalink && <a href={r.permalink} target="_blank" rel="noopener noreferrer" aria-label="Open on Instagram" className="text-muted hover:text-ink"><ExternalLink size={12} aria-hidden /></a>}</div><div className="mt-1.5 h-1 rounded-full bg-surface-2"><div className="h-full rounded-full bg-accent/70" style={{ width: `${((ins.views ?? 0) / maxViews) * 100}%` }} /></div></td>
          <td className="px-4 py-3 tabular-nums">{num(ins.views)}</td><td className="px-4 py-3 tabular-nums">{num(ins.reach)}</td><td className="px-4 py-3 tabular-nums">{num(ins.likes ?? r.like_count)}</td><td className="px-4 py-3 tabular-nums">{num(ins.comments ?? r.comments_count)}</td><td className="px-4 py-3 tabular-nums">{num(ins.shares)}</td><td className="px-4 py-3 tabular-nums">{num(ins.saved)}</td>
          <td className="px-4 py-3 tabular-nums">{ins.ig_reels_avg_watch_time ? `${(ins.ig_reels_avg_watch_time / 1000).toFixed(1)} s` : "—"}</td>
          <td className="px-4 py-3 tabular-nums">{e === null ? "—" : `${(e * 100).toFixed(1)}%`}</td>
        </tr>; })}</tbody>
      </table>
      <p className="px-5 pb-4 text-[11px] text-muted">Engagement = interactions ÷ accounts reached. “—” means Instagram did not return that metric.</p>
    </div>
  </section>;
}

function FeedbackPanel({ base, organizationId, canEdit }: { base: string | null; organizationId: string; canEdit: boolean }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<FeedbackSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const data = useQuery({ queryKey: ["feedback", organizationId, base], enabled: !!base, queryFn: () => socialRequest<{ rows: FeedbackRow[]; stored: { summary: FeedbackSummary; updated_at: string } | null; min_posts: number }>(base!, `/feedback?organization_id=${organizationId}`) });
  const summary = result ?? data.data?.stored?.summary ?? null;
  async function analyse() {
    if (!base) return;
    setBusy(true); setError(null);
    try { setResult((await socialRequest<{ summary: FeedbackSummary }>(base, "/feedback", { organization_id: organizationId })).summary); await data.refetch(); }
    catch (e) { setError(e instanceof Error ? e.message : "Analysis failed."); }
    finally { setBusy(false); }
  }
  const rows = data.data?.rows ?? [];
  return <section className="studio-panel p-5 sm:p-6">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><h2 className="flex items-center gap-2 text-[16px] font-semibold"><Sparkles size={17} className="text-accent" aria-hidden />AI feedback</h2><p className="mt-1 max-w-[70ch] text-[13px] leading-6 text-muted">Compares reels you published from Reel Studio by length, style and type, then tunes future highlight suggestions toward what your audience engages with.</p></div>
      {canEdit && <button type="button" onClick={analyse} disabled={!base || busy} className="studio-button">{busy ? <LoaderCircle size={15} className="animate-spin" aria-hidden /> : <Sparkles size={15} aria-hidden />}{busy ? "Analysing…" : "Analyse my reels"}</button>}
    </div>
    <p className="mt-4 text-[12px] text-muted">{rows.length} of your published reels have Instagram metrics{data.data ? ` · ${data.data.min_posts} needed` : ""}.</p>
    {summary && !summary.enough && <p className="mt-3 rounded-lg bg-surface-2 p-4 text-[13px] leading-6">{summary.message}</p>}
    {summary?.enough && <div className="mt-4 grid gap-5 lg:grid-cols-2">
      <div className="space-y-2">{summary.findings?.map((f, i) => <p key={i} className="rounded-lg bg-surface-2 p-3 text-[13px] leading-6">{f}</p>)}</div>
      <div>{summary.recommendations?.length ? <><h3 className="text-[12px] font-semibold uppercase tracking-[.08em] text-muted">Suggestions from the local AI</h3><ol className="mt-2 list-decimal space-y-2 pl-5 text-[13px] leading-6">{summary.recommendations.map((r, i) => <li key={i}>{r}</li>)}</ol></> : <p className="text-[12.5px] text-muted">The local AI was offline, so only measured findings are shown.</p>}</div>
    </div>}
    {!summary && rows.length === 0 && <p className="mt-3 text-[13px] leading-6 text-muted">No published reels with metrics yet. Feedback appears after you publish at least {data.data?.min_posts ?? 3} reels and refresh analytics. No conclusions are drawn from too little data.</p>}
    {error && <p role="alert" className="mt-3 text-[12.5px] text-danger">{error}</p>}
  </section>;
}
