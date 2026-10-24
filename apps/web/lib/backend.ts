"use client";

import { useQuery } from "@tanstack/react-query";
import { useSyncExternalStore } from "react";
import { createClient } from "@/lib/supabase/client";

export type BackendStatus =
  | { state: "online"; url: string; capabilities: Record<string, boolean> }
  | { state: "offline"; reason: string };

const STALE_MS = 90_000;
/** Dev Tunnels shows an HTML interstitial to browser requests unless this header is sent. */
const TUNNEL_HEADERS = { "X-Tunnel-Skip-AntiPhishing-Page": "true" };
/** On the machine running the backend, networks that intercept TLS (e.g. Fortinet) break the tunnel. */
const SAME_MACHINE = "http://127.0.0.1:8000";

async function health(url: string) {
  const r = await fetch(`${url.replace(/\/$/, "")}/health`, { headers: TUNNEL_HEADERS, signal: AbortSignal.timeout(5000) });
  if (!r.ok) throw new Error(`Health check returned ${r.status}.`);
  return (await r.json()).capabilities ?? {};
}

const REMEMBER = "rs-backend-url";

/** Finds the local processing API: explicit env override, else the URL it last heartbeated to Supabase.
 * Candidates (tunnel and same-machine) are probed in parallel and the first healthy one wins, so a route that
 * hangs (e.g. a TLS-intercepted tunnel) never delays the other. The winner is remembered for the session. */
async function discover(): Promise<BackendStatus> {
  let url = process.env.NEXT_PUBLIC_API_URL || "";
  if (!url) {
    const { data, error } = await createClient()
      .from("backend_endpoints")
      .select("url, last_seen_at")
      .eq("id", "primary")
      .maybeSingle();
    if (error) return { state: "offline", reason: error.message };
    if (!data) return { state: "offline", reason: "The processing backend has never connected." };
    if (Date.now() - new Date(data.last_seen_at).getTime() > STALE_MS)
      return { state: "offline", reason: `Last seen ${new Date(data.last_seen_at).toLocaleString()}.` };
    url = data.url;
  }
  const candidates = [...new Set([url, SAME_MACHINE])];
  try {
    return await Promise.any(candidates.map(async (candidate) => {
      const capabilities = await health(candidate);
      try { sessionStorage.setItem(REMEMBER, candidate); } catch { /* storage unavailable */ }
      return { state: "online" as const, url: candidate, capabilities };
    }));
  } catch {
    return { state: "offline", reason: "Health check did not respond." };
  }
}

function remembered(): BackendStatus | undefined {
  try {
    const url = sessionStorage.getItem(REMEMBER);
    return url ? { state: "online", url, capabilities: {} } : undefined;
  } catch {
    return undefined;
  }
}

const noop = () => () => {};

export function useBackend() {
  // Start from the last working URL so engine-dependent UI renders immediately; the probe confirms it in the background.
  // Only after hydration: sessionStorage does not exist on the server, so using it in the first render mismatched the HTML.
  // The probe can also finish before a later-streamed page segment hydrates, so its answer is withheld until then too.
  const hydrated = useSyncExternalStore(noop, () => true, () => false);
  const q = useQuery({ queryKey: ["backend"], queryFn: discover, refetchInterval: 20_000, staleTime: 15_000, placeholderData: hydrated ? remembered : undefined });
  return hydrated ? q : { ...q, data: undefined, isLoading: true };
}

/** Authenticated call to the local API. */
export async function apiFetch(base: string, path: string, init: RequestInit = {}) {
  const { data } = await createClient().auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error("Not signed in");
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  headers.set("X-Tunnel-Skip-AntiPhishing-Page", "true");
  return fetch(`${base.replace(/\/$/, "")}${path}`, { ...init, headers });
}

export { apiErrorMessage } from "./api-error";
