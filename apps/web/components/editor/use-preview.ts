"use client";

import { useEffect, useState } from "react";
import type { Composition } from "@reel-studio/timeline-schema";
import { apiErrorMessage, apiFetch } from "@/lib/backend";

/**
 * Compiles the draft with the export compiler on the processing machine and returns the page as srcdoc.
 * A <base> pointing at the signed render folder lets its media, fonts and GSAP load as they would in a render.
 */
export function usePreview(base: string | null, renderId: string, doc: Composition | null, timeRef: React.RefObject<number>) {
  const [html, setHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const json = doc ? JSON.stringify(doc) : null;
  useEffect(() => {
    if (!base || !json) return;
    let cancelled = false;
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const r = await apiFetch(base, `/renders/${renderId}/preview`, { method: "POST", headers: { "Content-Type": "application/json" }, body: `{"timeline":${json}}` });
        const body = await r.json().catch(() => null);
        if (!r.ok) throw new Error(apiErrorMessage(body, r.status));
        const folder = `${base.replace(/\/$/, "")}${body.base}`;
        const page = await fetch(folder + body.page, { headers: { "X-Tunnel-Skip-AntiPhishing-Page": "true" } });
        if (!page.ok) throw new Error("The preview could not be loaded.");
        const text = await page.text();
        if (!cancelled) {
          setHtml(text.replace("<head>", `<head><base href="${folder}"><script>window.RS_START=${timeRef.current}</script>`));
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Preview failed.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 450);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [base, renderId, json, timeRef]);
  return { html, error, loading };
}
