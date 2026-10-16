"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, Check, ChevronLeft, ChevronRight, Clock3, ExternalLink, Film, LoaderCircle, RefreshCw, Send, X } from "lucide-react";
import { useState } from "react";
import { useBackend } from "@/lib/backend";
import { accountReady, platformName, socialRequest, type PublishExport, type PublishJob, type SocialAccount, type SocialConfig } from "@/lib/social";
import { AccountConnections } from "./account-connections";

const ACTIVE = ["queued", "scheduled", "processing", "publishing"];
const LABELS: Record<string, string> = { queued: "Queued", scheduled: "Scheduled", processing: "Preparing media", publishing: "Publishing", published: "Published", failed: "Failed", cancelled: "Cancelled", needs_review: "Needs review" };

function dayKey(value: string) {
  const date = new Date(value);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
function exportName(render: PublishExport) {
  const title = render.title && render.title !== render.project_name ? ` · ${render.title}` : "";
  return `${render.project_name || "Project"}${title}`;
}
function postLink(value?: string | null) {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" && ["instagram.com", "www.instagram.com", "youtube.com", "www.youtube.com", "youtu.be"].includes(url.hostname) ? url.href : null;
  } catch { return null; }
}

export function PublishingStudio({ organizationId, canEdit }: { organizationId: string; canEdit: boolean }) {
  const backend = useBackend();
  const base = backend.data?.state === "online" ? backend.data.url : null;
  const qc = useQueryClient();
  const [renderId, setRenderId] = useState("");
  const [accountId, setAccountId] = useState("");
  const [caption, setCaption] = useState("");
  const [tags, setTags] = useState("");
  const tagLine = tags.split(/[\s,]+/).filter(Boolean).map((t) => "#" + t.replace(/^#+/, "").replace(/[^\p{L}\p{N}_]/gu, "")).filter((t) => t.length > 1).join(" ");
  const fullCaption = [caption.trim(), tagLine].filter(Boolean).join("\n\n");
  const [timing, setTiming] = useState("now");
  const [scheduledAt, setScheduledAt] = useState("");
  const [day, setDay] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const accounts = useQuery({ queryKey: ["social-accounts", organizationId, base], enabled: !!base, queryFn: () => socialRequest<SocialAccount[]>(base!, `/social/accounts?organization_id=${encodeURIComponent(organizationId)}`) });
  const config = useQuery({ queryKey: ["social-config", base], enabled: !!base, queryFn: () => socialRequest<SocialConfig>(base!, "/social/config"), staleTime: 30_000 });
  const exports = useQuery({ queryKey: ["publish-exports", organizationId, base], enabled: !!base, queryFn: () => socialRequest<PublishExport[]>(base!, `/publishing/exports?organization_id=${encodeURIComponent(organizationId)}`) });
  const queue = useQuery({ queryKey: ["publishing", organizationId, base], enabled: !!base, queryFn: () => socialRequest<PublishJob[]>(base!, `/publishing?organization_id=${encodeURIComponent(organizationId)}`), refetchInterval: 5000 });
  const readyAccounts = accounts.data?.filter((a) => accountReady(a) && config.data?.[a.platform]?.configured) ?? [];
  const account = readyAccounts.find((a) => a.id === accountId);
  const selected = exports.data?.find((r) => r.id === renderId);
  const existing = queue.data?.find((j) => j.render_id === renderId && j.account_id === accountId && j.status !== "cancelled");
  const preview = useQuery<{ video: string; thumb: string }>({
    queryKey: ["publishing-preview", renderId, base], enabled: !!base && !!selected,
    queryFn: async () => {
      const urls = await socialRequest<{ video: string; thumb: string }>(base!, `/renders/${renderId}/urls`);
      return { video: `${base!.replace(/\/$/, "")}${urls.video}`, thumb: `${base!.replace(/\/$/, "")}${urls.thumb}` };
    }, staleTime: 60 * 60_000,
  });
  const visible = (queue.data ?? []).filter((job) => (!day || dayKey(job.scheduled_at || job.created_at) === day) && (statusFilter === "all" || (statusFilter === "upcoming" ? ACTIVE.includes(job.status) : job.status === statusFilter)));
  const upcoming = queue.data?.filter((j) => ACTIVE.includes(j.status)).length ?? 0;

  async function publish(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!base || !selected || !account || !canEdit || busy || existing) return;
    setError(null); setNotice(null);
    let scheduled: string | null = null;
    if (timing === "later") {
      const timestamp = new Date(scheduledAt).getTime();
      if (!Number.isFinite(timestamp) || timestamp <= Date.now()) return setError("Choose a future date and time for this post.");
      scheduled = new Date(timestamp).toISOString();
    }
    setBusy("publish");
    try {
      const result = await socialRequest<PublishJob>(base, "/publishing", { render_id: renderId, account_id: accountId, caption: fullCaption, scheduled_at: scheduled });
      setNotice(result.status === "published" ? "This export has already been published to this account. Its status is shown below." : scheduled ? "Post scheduled. Keep the processing machine running when it is due." : "Post saved in the queue. Follow its actual status below.");
      setDay(""); setStatusFilter("all");
      await qc.invalidateQueries({ queryKey: ["publishing", organizationId] });
    } catch (e) { setError(e instanceof Error ? e.message : "The post could not be queued."); }
    finally { setBusy(null); }
  }
  async function changeJob(id: string, action: "retry" | "cancel") {
    if (!base || !canEdit || busy) return;
    setBusy(id); setError(null); setNotice(null);
    try {
      await socialRequest(base, `/publishing/${id}/${action}`, {});
      await qc.invalidateQueries({ queryKey: ["publishing", organizationId] });
    } catch (e) { setError(e instanceof Error ? e.message : `Could not ${action} this post.`); }
    finally { setBusy(null); }
  }

  return <div className="space-y-7">
    <header className="flex flex-wrap items-end justify-between gap-4"><div><p className="studio-eyebrow mb-2">Instagram</p><h1 className="studio-heading">Publish</h1><p className="mt-2 text-[14px] text-muted">Pick a finished reel, write the caption, then publish now or schedule it.</p></div><span className="studio-pill"><CalendarDays size={13} aria-hidden />{queue.data ? `${upcoming} upcoming` : "Queue not loaded"}</span></header>
    {!base && <div className="studio-panel p-4 text-[13px] text-muted">{backend.isLoading ? "Connecting to the processing machine…" : "The processing machine is offline. Account connections, publishing and schedules need it online."}</div>}
    <AccountConnections organizationId={organizationId} base={base} accounts={accounts.data ?? []} canEdit={canEdit} />
    {accounts.error && <p role="alert" className="text-[13px] text-danger">Accounts could not load: {accounts.error.message}</p>}
    <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
      <form onSubmit={publish} className="studio-panel p-5 sm:p-6">
        <p className="studio-eyebrow mb-2">Review before it goes live</p><h2 className="mb-5 text-[20px] font-semibold tracking-[-.03em]">Prepare a post</h2>
        <fieldset disabled={!canEdit || busy === "publish"} className="space-y-4 disabled:opacity-60">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="studio-label">Finished export<select required value={renderId} onChange={(e) => setRenderId(e.target.value)} className="studio-input"><option value="">Choose a rendered video</option>{exports.data?.map((r) => <option key={r.id} value={r.id}>{exportName(r)}{r.duration_s ? ` · ${Math.round(r.duration_s)}s` : ""} · {new Date(r.created_at).toLocaleString()}</option>)}</select></label>
            <label className="studio-label">Publish to<select required value={accountId} onChange={(e) => setAccountId(e.target.value)} className="studio-input"><option value="">Choose a connected account</option>{readyAccounts.map((a) => <option key={a.id} value={a.id}>{platformName(a.platform)} · {a.username}</option>)}</select></label>
          </div>
          {exports.data?.length === 0 && <p className="text-[12px] text-muted">No finished exports yet. Render a video in a project first.</p>}
          {!readyAccounts.length && accounts.data && <p className="text-[12px] text-muted">Connect an account above before publishing.</p>}
          <label className="studio-label">Caption<textarea value={caption} onChange={(e) => setCaption(e.target.value)} maxLength={2200} rows={5} placeholder="Introduce the lesson, add context, and tell your audience what to try next." className="studio-input resize-y !leading-7" /></label>
          <label className="studio-label">Hashtags<input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="python coding learntocode" className="studio-input" /><span className={`text-right text-[10px] font-normal tabular-nums ${fullCaption.length > 2200 ? "text-danger" : ""}`}>{tagLine && <span className="float-left text-accent">{tagLine}</span>}{fullCaption.length} / 2,200 · Instagram allows up to 30 hashtags</span></label>
          <fieldset><legend className="mb-2 text-[12px] font-semibold text-muted">When should it publish?</legend><div className="flex flex-wrap gap-4 text-[13px]"><label className="flex items-center gap-2"><input type="radio" name="timing" value="now" checked={timing === "now"} onChange={() => setTiming("now")} className="accent-[var(--accent)]" />Publish now</label><label className="flex items-center gap-2"><input type="radio" name="timing" value="later" checked={timing === "later"} onChange={() => setTiming("later")} className="accent-[var(--accent)]" />Schedule for later</label></div></fieldset>
          {timing === "later" && <label className="studio-label">Local date & time<input type="datetime-local" required value={scheduledAt} onChange={(e) => setScheduledAt(e.target.value)} className="studio-input max-w-[300px]" /><span className="text-[11px] font-normal">Uses your browser’s local time. Stored in UTC.</span></label>}
        </fieldset>
        <div className="mt-6 border-t border-line pt-5"><p className="mb-4 text-[12px] leading-6 text-muted">{canEdit ? timing === "later" ? "Scheduling authorizes this post to go live at the selected time. The processing machine must be running." : "Publishing sends this video and caption to the selected account as a live post." : "You have view access. A workspace editor can publish and manage schedules."}</p>{canEdit && <button type="submit" disabled={!base || !selected || !account || !!busy || !!existing || queue.isPending} className="studio-button">{busy === "publish" ? <LoaderCircle size={15} className="animate-spin" aria-hidden /> : timing === "later" ? <Clock3 size={15} aria-hidden /> : <Send size={15} aria-hidden />}{busy === "publish" ? "Submitting…" : timing === "later" ? "Schedule post" : account ? `Publish to ${platformName(account.platform)}` : "Publish now"}</button>}</div>
        {existing && <p className="mt-3 text-[12px] leading-6 text-muted">This export already has a {LABELS[existing.status]?.toLowerCase() || existing.status} post for this account. Manage it in the queue below.</p>}
        {exports.error && <p role="alert" className="mt-3 text-[13px] text-danger">Exports could not load: {exports.error.message}</p>}
      </form>
      <section className="studio-panel overflow-hidden"><h2 className="border-b border-line px-5 py-4 text-[14px] font-semibold">Export preview</h2><div className="p-5">{preview.data ? <video key={renderId} src={preview.data.video} poster={preview.data.thumb} controls playsInline preload="metadata" className="aspect-[9/16] w-full rounded-xl bg-[var(--canvas)]" /> : <div className="flex aspect-[9/16] flex-col items-center justify-center gap-4 rounded-xl bg-surface-2 p-5 text-center"><Film size={30} strokeWidth={1.3} className="text-accent" aria-hidden /><p className="text-[12px] leading-6 text-muted">{preview.error ? "The preview could not load." : selected ? "Loading the actual export…" : "Choose an export to review the video here."}</p></div>}{selected && <p className="mt-4 text-[12px] text-muted">{exportName(selected)}{selected.duration_s ? ` · ${selected.duration_s.toFixed(1)} seconds` : ""}</p>}{preview.error && <p role="alert" className="mt-3 text-[12px] text-danger">{preview.error.message}</p>}</div></section>
    </div>
    {error && <p role="alert" className="rounded-lg border border-danger/30 bg-surface p-4 text-[13px] text-danger">{error}</p>}
    {notice && <p role="status" className="flex items-start gap-2 rounded-lg border border-line bg-surface p-4 text-[13px] text-accent"><Check size={16} className="mt-0.5 shrink-0" aria-hidden />{notice}</p>}
    <section className="studio-panel p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-4"><div><p className="studio-eyebrow mb-2">The publishing desk</p><h2 className="text-[20px] font-semibold tracking-[-.03em]">Schedule & queue</h2></div><button type="button" onClick={() => queue.refetch()} disabled={!base || queue.isFetching} className="studio-button studio-button-secondary"><RefreshCw size={14} className={queue.isFetching ? "animate-spin" : ""} aria-hidden />Refresh</button></div>
      <MonthCalendar jobs={queue.data ?? []} day={day} onDay={setDay} />
      <div className="mt-5 flex flex-wrap items-end gap-3 border-b border-line pb-5"><label className="studio-label">Calendar day<input type="date" value={day} onChange={(e) => setDay(e.target.value)} className="studio-input !w-auto" /></label><label className="studio-label">Status<select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="studio-input !w-auto"><option value="all">All posts</option><option value="upcoming">Upcoming</option><option value="published">Published</option><option value="failed">Failed</option><option value="needs_review">Needs review</option><option value="cancelled">Cancelled</option></select></label>{(day || statusFilter !== "all") && <button type="button" className="studio-button studio-button-secondary" onClick={() => { setDay(""); setStatusFilter("all"); }}>Clear filters</button>}</div>
      {queue.error ? <p role="alert" className="py-6 text-[13px] text-danger">Queue could not load: {queue.error.message}</p> : !base ? <p className="py-8 text-[13px] text-muted">Connect the processing machine to load the queue.</p> : queue.isPending ? <p className="py-8 text-[13px] text-muted">Loading scheduled posts…</p> : !visible.length ? <p className="py-8 text-[13px] text-muted">{day || statusFilter !== "all" ? "No posts match these filters." : "Nothing queued yet. Your scheduled and published posts will appear here."}</p> : <ul className="divide-y divide-line">{visible.map((job) => {
        const owner = accounts.data?.find((a) => a.id === job.account_id);
        const asset = exports.data?.find((r) => r.id === job.render_id);
        const url = postLink(job.platform_url);
        return <li key={job.id} className="grid gap-3 py-5 lg:grid-cols-[minmax(0,1fr)_180px_auto]"><div><h3 className="text-[14px] font-semibold">{asset ? exportName(asset) : `Export ${job.render_id.slice(0, 8)}`}</h3><p className="mt-1 text-[11px] text-muted">{platformName(owner?.platform || job.platform || "Account")} · {owner?.username || "Connected account"}</p>{job.caption && <p className="mt-3 line-clamp-3 max-w-[65ch] whitespace-pre-wrap text-[13px] leading-6 text-muted">{job.caption}</p>}{job.error && <p className="mt-2 text-[12px] leading-6 text-danger">{job.error}</p>}{job.status === "needs_review" && <p className="mt-2 text-[12px] leading-6 text-danger">The platform outcome is uncertain. Check the account before taking further action; automatic retry is paused.</p>}</div><div className="text-[12px]"><span className={`studio-pill ${job.status === "failed" || job.status === "needs_review" ? "!text-danger" : job.status === "published" ? "!text-success" : ""}`}>{LABELS[job.status] || job.status}</span><time dateTime={job.scheduled_at || job.created_at} className="mt-2 block text-[11px] leading-5 text-muted">{job.scheduled_at ? "Scheduled " : "Created "}{new Date(job.scheduled_at || job.created_at).toLocaleString()}</time></div><div className="flex items-start gap-2">{url && <a href={url} target="_blank" rel="noopener noreferrer" className="studio-button studio-button-secondary"><ExternalLink size={13} aria-hidden />View post</a>}{canEdit && job.status === "failed" && <button type="button" disabled={!base || !!busy} onClick={() => changeJob(job.id, "retry")} className="studio-button studio-button-secondary"><RefreshCw size={13} aria-hidden />Retry</button>}{canEdit && ["scheduled", "queued"].includes(job.status) && <button type="button" disabled={!base || !!busy} onClick={() => changeJob(job.id, "cancel")} className="studio-button studio-button-secondary"><X size={13} aria-hidden />Cancel</button>}</div></li>;
      })}</ul>}
    </section>
  </div>;
}

function MonthCalendar({ jobs, day, onDay }: { jobs: PublishJob[]; day: string; onDay: (d: string) => void }) {
  const [month, setMonth] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1); });
  const counts = new Map<string, PublishJob[]>();
  for (const j of jobs) { const k = dayKey(j.scheduled_at || j.created_at); counts.set(k, [...(counts.get(k) ?? []), j]); }
  const lead = (month.getDay() + 6) % 7;
  const days = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
  const today = dayKey(new Date().toISOString());
  const cells = [...Array(lead).fill(null), ...Array.from({ length: days }, (_, i) => new Date(month.getFullYear(), month.getMonth(), i + 1))];
  return <div className="mt-5">
    <div className="mb-3 flex items-center justify-between">
      <h3 className="text-[14px] font-semibold">{month.toLocaleDateString("en", { month: "long", year: "numeric" })}</h3>
      <div className="flex gap-1">
        <button type="button" aria-label="Previous month" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))} className="rounded-md p-1.5 text-muted hover:bg-surface-2 hover:text-ink"><ChevronLeft size={16} aria-hidden /></button>
        <button type="button" aria-label="Next month" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))} className="rounded-md p-1.5 text-muted hover:bg-surface-2 hover:text-ink"><ChevronRight size={16} aria-hidden /></button>
      </div>
    </div>
    <div className="grid grid-cols-7 gap-1 text-center text-[10.5px] text-muted">{["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => <span key={d} className="pb-1">{d}</span>)}</div>
    <div className="grid grid-cols-7 gap-1">{cells.map((d, i) => {
      if (!d) return <span key={i} />;
      const key = dayKey(new Date(d.getFullYear(), d.getMonth(), d.getDate(), 12).toISOString());
      const list = counts.get(key) ?? [];
      return <button key={i} type="button" onClick={() => onDay(day === key ? "" : key)} aria-pressed={day === key} aria-label={`${d.toDateString()}: ${list.length} posts`}
        className={`flex h-14 flex-col items-start rounded-lg border p-1.5 text-left text-[11px] transition-colors ${day === key ? "border-accent bg-accent/10" : "border-line hover:border-[#3a404e]"} ${key === today ? "text-accent" : ""}`}>
        <span className="tabular-nums">{d.getDate()}</span>
        {list.length > 0 && <span className="mt-auto flex flex-wrap gap-0.5">{list.slice(0, 4).map((j) => <span key={j.id} className={`h-1.5 w-1.5 rounded-full ${j.status === "published" ? "bg-success" : ["failed", "needs_review"].includes(j.status) ? "bg-danger" : "bg-signal"}`} />)}</span>}
      </button>;
    })}</div>
  </div>;
}
