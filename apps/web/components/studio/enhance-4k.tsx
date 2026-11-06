"use client";

import { Download, LoaderCircle, Sparkles } from "lucide-react";
import { useState } from "react";
import { apiFetch } from "@/lib/backend";

/** A reel's 4K version as the API reports it (batch `hd`, or a render_jobs row with its job). */
export type Hd = {
  id: string; status: string; error: string | null; size_bytes?: number | null;
  stage?: string | null; progress?: number | null;
};

const STAGE: Record<string, string> = {
  queued: "waiting for the engine",
  base: "rebuilding the picture",
  upscale: "AI upscaling every frame",
  verify: "checking the 4K file",
  sync_check: "checking timing",
};

async function saveFile(url: string, name: string) {
  const r = await fetch(url, { headers: { "X-Tunnel-Skip-AntiPhishing-Page": "true" } });
  if (!r.ok) throw new Error("download failed");
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(await r.blob()), download: name });
  a.click();
  URL.revokeObjectURL(a.href);
}

/** "Enhance to 4K" for one finished reel: local Real-ESRGAN AI upscale to 2160×3840, captions redrawn at 4K,
 *  upload-grade bitrate. Shows the job's real stage and progress, then a 4K download. */
export function Enhance4K({ base, reelId, hd, name, onQueued, compact = false }: {
  base: string; reelId: string; hd: Hd | null; name: string; onQueued: () => void; compact?: boolean;
}) {
  const [vivid, setVivid] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const text = compact ? "text-[11px]" : "text-[13px]";

  async function enhance() {
    setError(null);
    setSending(true);
    try {
      const r = await apiFetch(base, `/renders/${reelId}/enhance`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ vivid }),
      });
      if (!r.ok) setError((await r.json().catch(() => ({}))).detail ?? `Refused (${r.status})`);
      onQueued();
    } catch { setError("The engine is offline."); } finally { setSending(false); }
  }

  async function download() {
    setError(null);
    try {
      const u = await (await apiFetch(base, `/renders/${hd!.id}/urls`)).json();
      await saveFile(`${base.replace(/\/$/, "")}${u.download}`, `${name}-4k.mp4`);
    } catch { setError("4K download failed. Is the engine online?"); }
  }

  if (hd && ["queued", "rendering"].includes(hd.status)) {
    return (
      <p className={`flex items-center gap-1.5 ${text} text-muted`}>
        <LoaderCircle size={13} className="animate-spin text-accent" />
        4K: {STAGE[hd.stage ?? "queued"] ?? hd.stage?.replaceAll("_", " ")} {Math.round((hd.progress ?? 0) * 100)}%
      </p>
    );
  }
  if (hd?.status === "ready") {
    return (
      <button type="button" onClick={download}
        className={`inline-flex items-center gap-1.5 rounded-lg bg-accent px-2.5 py-1.5 ${text} font-semibold text-white hover:bg-forest`}>
        <Download size={13} />Download 4K{hd.size_bytes ? ` · ${Math.round(hd.size_bytes / 1024 ** 2)} MB` : ""}
      </button>
    );
  }
  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={enhance} disabled={sending}
          title="AI-upscale this reel to 2160×3840 on the local GPU (Real-ESRGAN), captions redrawn sharp at 4K"
          className={`inline-flex items-center gap-1.5 rounded-lg border border-accent px-2.5 py-1.5 ${text} font-semibold text-accent hover:bg-surface-2 disabled:opacity-50`}>
          <Sparkles size={13} />Enhance to 4K
        </button>
        <label className={`flex items-center gap-1 ${text} text-muted`} title="A little more contrast and colour, like CapCut's HDR look (the file stays standard SDR)">
          <input type="checkbox" checked={vivid} onChange={(e) => setVivid(e.target.checked)} className="accent-[var(--accent)]" />HDR look
        </label>
      </div>
      {hd?.status === "failed" && <p className={`${text} text-danger`}>4K failed: {hd.error?.slice(0, 160)}</p>}
      {error && <p className={`${text} text-danger`}>{error}</p>}
    </div>
  );
}
