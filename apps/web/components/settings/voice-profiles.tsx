"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Mic, Square, Trash2 } from "lucide-react";
import { useRef, useState } from "react";
import { apiErrorMessage, apiFetch, useBackend } from "@/lib/backend";
import { createClient } from "@/lib/supabase/client";

type Voice = { id: string; label: string; kind: "profile" | "builtin"; status?: string; profile_id?: string; quality?: { seconds: number; snr_db: number } };
const SCRIPT = "Read this aloud in your normal voice: Hi, I make short videos about what I love. Today I will show you something useful, step by step. Aaj hum kuch naya seekhenge, aur ise simple rakhenge.";

/** Consent-based voice profiles: one sample, explicit permission, quality check, preview, pronunciations, delete. */
export function VoiceProfiles({ orgId }: { orgId: string }) {
  const backend = useBackend();
  const base = backend.data?.state === "online" ? backend.data.url : null;
  const qc = useQueryClient();
  const consent = useQuery({ queryKey: ["voice-consent", base], enabled: !!base, queryFn: async () => (await (await apiFetch(base!, "/voices/consent")).json()) as { statement: string; engine_installed: boolean } });
  const voices = useQuery({ queryKey: ["voices", base], enabled: !!base, queryFn: async () => (await (await apiFetch(base!, "/voices")).json()) as Voice[] });
  const [name, setName] = useState("My voice");
  const [file, setFile] = useState<File | null>(null);
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const rec = useRef<MediaRecorder | null>(null);

  async function record() {
    if (recording) return rec.current?.stop();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: Blob[] = [];
      const r = new MediaRecorder(stream);
      r.ondataavailable = (e) => chunks.push(e.data);
      r.onstop = () => { stream.getTracks().forEach((t) => t.stop()); setRecording(false); setFile(new File(chunks, "recording.webm", { type: r.mimeType })); };
      rec.current = r; r.start(); setRecording(true);
    } catch { setMsg("Microphone access was not allowed. Upload a recording instead."); }
  }

  async function create() {
    if (!base || !file || !consent.data) return;
    setBusy(true); setMsg(null);
    const form = new FormData();
    form.set("org_id", orgId); form.set("name", name); form.set("consent", String(agreed)); form.set("consent_statement", consent.data.statement); form.set("sample", file);
    const r = await apiFetch(base, "/voices", { method: "POST", body: form });
    const body = await r.json().catch(() => null);
    if (!r.ok) setMsg(typeof body?.detail === "object" && body.detail.quality ? `${body.detail.message}: ${body.detail.quality.problems.join(" ")}` : apiErrorMessage(body, r.status));
    else { setMsg(`Voice saved (${body.quality.seconds} s, signal-to-noise ${body.quality.snr_db} dB).`); setFile(null); setAgreed(false); }
    setBusy(false);
    qc.invalidateQueries({ queryKey: ["voices"] });
  }

  const profiles = (voices.data ?? []).filter((v) => v.kind === "profile");
  return (
    <section className="studio-panel space-y-4 p-6">
      <h2 className="flex items-center gap-2 text-[15px] font-semibold"><Mic size={17} className="text-accent" aria-hidden /> Voice profiles</h2>
      <p className="text-[13px] leading-6 text-muted">Record your voice once and narrate future edits with it (English, Hindi and Hinglish). Generated speech carries an inaudible watermark that identifies it as synthetic. A clone sounds similar, not identical. Only you can use your voice.</p>
      {!base && <p className="text-[13px] text-danger">Voice profiles need the processing machine online.</p>}
      {consent.data && !consent.data.engine_installed && <p className="text-[13px] text-danger">The voice engine is not installed on the processing machine yet.</p>}
      {profiles.length > 0 && <ul className="divide-y divide-line">{profiles.map((v) => <ProfileRow key={v.id} v={v} base={base!} />)}</ul>}
      <div className="space-y-3 rounded-xl border border-line bg-surface p-4">
        <p className="text-[13px] font-semibold">New voice profile</p>
        <p className="text-[12px] text-muted">{SCRIPT}</p>
        <div className="flex flex-wrap items-center gap-3">
          <input className="studio-input max-w-[220px]" value={name} maxLength={60} onChange={(e) => setName(e.target.value)} aria-label="Profile name" />
          <button type="button" onClick={record} className="studio-button-secondary inline-flex items-center gap-2 rounded-xl px-3 py-2 text-[12px] font-semibold">{recording ? <><Square size={13} aria-hidden />Stop</> : <><Mic size={13} aria-hidden />Record</>}</button>
          <label className="cursor-pointer text-[12px] font-semibold text-accent">or upload audio<input type="file" accept="audio/*,video/*" className="sr-only" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></label>
          {file && <span className="text-[12px] text-muted">{file.name} · {(file.size / 1024).toFixed(0)} KB</span>}
        </div>
        {consent.data && <label className="flex items-start gap-2 text-[12px]"><input type="checkbox" className="mt-0.5" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />{consent.data.statement}</label>}
        <button type="button" className="studio-button" disabled={!file || !agreed || busy || !consent.data?.engine_installed} onClick={create}>{busy ? "Checking the sample…" : "Create voice profile"}</button>
        {msg && <p role="status" className="text-[12px] text-muted">{msg}</p>}
      </div>
    </section>
  );
}

function ProfileRow({ v, base }: { v: Voice; base: string }) {
  const qc = useQueryClient();
  const [text, setText] = useState("Hi! This is my Reel Studio voice. Aaj hum ek naya reel banayenge.");
  const [language, setLanguage] = useState("hinglish");
  const [job, setJob] = useState<string | null>(null);
  const [rules, setRules] = useState("");
  const status = useQuery({
    queryKey: ["voice-job", job], enabled: !!job,
    refetchInterval: (q) => (q.state.data?.status === "succeeded" || q.state.data?.status === "failed" ? false : 3000),
    queryFn: async () => {
      const { data } = await createClient().from("jobs").select("status, error, current_stage").eq("id", job!).single();
      if (data?.status !== "succeeded") return { status: data?.status ?? "queued", error: data?.error as string | null, url: null };
      const r = await apiFetch(base, `/voices/preview/${job}/url`);
      return { status: "succeeded", error: null, url: r.ok ? base.replace(/\/$/, "") + (await r.json()).path : null };
    },
  });
  async function preview() {
    const r = await apiFetch(base, `/voices/${v.profile_id}/preview`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, language }) });
    if (r.ok) setJob((await r.json()).job_id);
  }
  async function savePron() {
    const map = Object.fromEntries(rules.split("\n").map((l) => l.split("=").map((x) => x.trim())).filter((x) => x.length === 2 && x[0] && x[1]));
    await apiFetch(base, `/voices/${v.profile_id}/pronunciations`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ rules: map }) });
  }
  async function remove() {
    if (!confirm("Delete this voice profile and its recording? This cannot be undone.")) return;
    await apiFetch(base, `/voices/${v.profile_id}`, { method: "DELETE" });
    qc.invalidateQueries({ queryKey: ["voices"] });
  }
  return <li className="space-y-2 py-3 text-[13px]">
    <div className="flex items-center justify-between gap-3"><span className="font-semibold">{v.label}</span>
      <span className="text-[11px] text-muted">{v.quality ? `${v.quality.seconds} s sample · SNR ${v.quality.snr_db} dB` : v.status}</span>
      <button type="button" onClick={remove} className="inline-flex items-center gap-1 text-[12px] text-muted hover:text-danger"><Trash2 size={12} aria-hidden />Delete</button></div>
    <div className="flex flex-wrap items-center gap-2">
      <input className="studio-input min-w-[240px] flex-1" value={text} maxLength={300} onChange={(e) => setText(e.target.value)} aria-label="Preview text" />
      <select className="studio-input w-auto" value={language} onChange={(e) => setLanguage(e.target.value)} aria-label="Language"><option value="en">English</option><option value="hi">Hindi</option><option value="hinglish">Hinglish</option></select>
      <button type="button" className="studio-button-secondary rounded-xl px-3 py-2 text-[12px] font-semibold" onClick={preview}>Preview</button>
    </div>
    {job && status.data?.status !== "succeeded" && <p className="text-[12px] text-muted">{status.data?.status === "failed" ? `Preview failed: ${status.data.error}` : "Generating the preview on the processing machine…"}</p>}
    {status.data?.url && <audio controls src={status.data.url} className="w-full" />}
    <details className="text-[12px]"><summary className="cursor-pointer text-muted">Pronunciation rules</summary>
      <textarea className="studio-input mt-2 w-full" rows={3} placeholder={"SQL = sequel\nReel Studio = reel studio"} value={rules} onChange={(e) => setRules(e.target.value)} />
      <button type="button" className="mt-1 text-accent" onClick={savePron}>Save rules</button></details>
  </li>;
}
