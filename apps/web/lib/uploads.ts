"use client";

/**
 * App-wide upload manager. Uploads live here, outside any page component, so they keep running while you switch
 * sections or leave the tab in the background, and their progress shows in the top bar (UploadTray).
 *
 * A refresh or closed tab ends the browser's access to the file, so: the browser asks before leaving while an upload
 * runs, every unfinished upload is remembered (localStorage: server id and bytes received) and offered again after the
 * reload. Files dropped in Chrome/Edge also keep a file handle (IndexedDB), so "Resume" re-opens them with one click;
 * otherwise you pick the same file again and the upload continues where the server stopped (chunked, resumable).
 * Everything after the upload (transcription, analysis, edits, renders) runs on the processing computer anyway.
 */

import { useSyncExternalStore } from "react";
import { apiFetch } from "@/lib/backend";

export type UploadKind = "recording" | "clip" | "image" | "audio" | "reference";
export type UploadItem = {
  key: string; kind: UploadKind; projectId: string; name: string; size: number; lastModified: number;
  sent: number; status: "queued" | "uploading" | "validating" | "done" | "error" | "paused";
  error?: string; id?: string; duplicate?: boolean; hasHandle?: boolean;
};
type Live = UploadItem & { file?: File };

const PARALLEL = 2;
const STORE = "rs-uploads-v1";
const items = new Map<string, Live>();
const listeners = new Set<() => void>();
const doneListeners = new Set<(it: UploadItem) => void>();
let base = "";
let active = 0;
let snapshot: UploadItem[] = [];

const strip = (i: Live): UploadItem => { const out = { ...i }; delete out.file; return out; };
const emit = () => {
  snapshot = [...items.values()].map(strip);
  listeners.forEach((l) => l());
};

export const uploadKey = (kind: UploadKind, projectId: string, f: { name: string; size: number; lastModified: number }) =>
  `${kind}:${projectId}:${f.name}:${f.size}:${f.lastModified}`;

// ---------------------------------------------------------------- persistence (survives a refresh)

function persist() {
  const keep = [...items.values()].filter((i) => i.status !== "done").map(strip);
  try { localStorage.setItem(STORE, JSON.stringify(keep)); } catch { /* storage unavailable */ }
}

function db(): Promise<IDBDatabase | null> {
  return new Promise((res) => {
    try {
      const r = indexedDB.open("rs-uploads", 1);
      r.onupgradeneeded = () => r.result.createObjectStore("handles");
      r.onsuccess = () => res(r.result);
      r.onerror = () => res(null);
    } catch { res(null); }
  });
}
async function idb<T>(mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest): Promise<T | null> {
  const d = await db();
  if (!d) return null;
  return new Promise((res) => {
    const req = fn(d.transaction("handles", mode).objectStore("handles"));
    req.onsuccess = () => res(req.result as T);
    req.onerror = () => res(null);
  });
}

type Handle = { getFile(): Promise<File>; queryPermission?(o: object): Promise<string>; requestPermission?(o: object): Promise<string> };

if (typeof window !== "undefined") {
  try {
    for (const it of JSON.parse(localStorage.getItem(STORE) || "[]") as UploadItem[])
      items.set(it.key, { ...it, status: "paused", error: undefined });
  } catch { /* nothing remembered */ }
  window.addEventListener("beforeunload", (e) => {
    if ([...items.values()].some((i) => i.status === "uploading" || i.status === "queued" || i.status === "validating")) {
      e.preventDefault(); // the browser asks "Leave site?": leaving pauses the upload (it can be resumed after)
    }
  });
  emit();
}

// ---------------------------------------------------------------- public API

/** Current backend URL (set by the UploadTray, which is mounted on every app page). Starts waiting uploads. */
export function setUploadBase(url: string) {
  if (url === base) return;
  base = url;
  pump();
}

export function useUploads(): UploadItem[] {
  return useSyncExternalStore((l) => { listeners.add(l); return () => listeners.delete(l); }, () => snapshot, () => []);
}

/** Called once per finished upload (pages refresh their lists, show "duplicate" notices). */
export function onUploadDone(cb: (it: UploadItem) => void) {
  doneListeners.add(cb);
  return () => { doneListeners.delete(cb); };
}

export function enqueue(kind: UploadKind, projectId: string, file: File, handle?: Handle | null): string {
  const key = uploadKey(kind, projectId, file);
  const prev = items.get(key);
  if (prev && (prev.status === "uploading" || prev.status === "queued" || prev.status === "validating")) return key;
  items.set(key, { key, kind, projectId, name: file.name, size: file.size, lastModified: file.lastModified, sent: prev?.sent ?? 0,
    id: prev?.id, status: "queued", file, hasHandle: !!handle || prev?.hasHandle });
  if (handle) void idb("readwrite", (s) => s.put(handle, key));
  persist();
  emit();
  pump();
  return key;
}

/** Resume a remembered upload: re-open its saved file handle (one permission click) or use a file the user picked. */
export async function resume(key: string, picked?: File): Promise<string | null> {
  const it = items.get(key);
  if (!it) return null;
  if (!picked && it.file) {  // still in memory (a connection error, not a refresh): just try again
    update(it, { status: "queued", error: undefined });
    pump();
    return null;
  }
  let file = picked ?? null;
  if (!file && it.hasHandle) {
    const h = await idb<Handle>("readonly", (s) => s.get(key));
    if (h) {
      const ok = (await h.queryPermission?.({ mode: "read" })) === "granted" || (await h.requestPermission?.({ mode: "read" })) === "granted";
      if (ok) file = await h.getFile().catch(() => null);
    }
  }
  if (!file) return "Choose the same file again to continue.";
  if (file.name !== it.name || file.size !== it.size) return `That is a different file. Choose “${it.name}”.`;
  enqueue(it.kind, it.projectId, file);
  return null;
}

export function dismiss(key: string) {
  items.delete(key);
  void idb("readwrite", (s) => s.delete(key));
  persist();
  emit();
}

/** Chromium: a dropped file's handle can be re-opened after a refresh (call synchronously inside the drop event). */
export function dropHandles(e: { dataTransfer: DataTransfer | null }): Promise<(Handle | null)[]> {
  const list = [...(e.dataTransfer?.items ?? [])].filter((i) => i.kind === "file");
  return Promise.all(list.map((i) => {
    const get = (i as unknown as { getAsFileSystemHandle?: () => Promise<Handle | null> }).getAsFileSystemHandle;
    return get ? get.call(i).catch(() => null) : Promise.resolve(null);
  }));
}

// ---------------------------------------------------------------- the upload loop

function update(it: Live, fields: Partial<Live>) {
  Object.assign(it, fields);
  emit();
}

function pump() {
  if (!base) return;
  for (const it of items.values()) {
    if (active >= PARALLEL) break;
    if (it.status !== "queued" || !it.file) continue;
    active++;
    run(it).finally(() => { active--; pump(); });
  }
}

const isRecording = (k: UploadKind) => k === "recording";

async function run(it: Live) {
  const file = it.file!;
  const path = isRecording(it.kind) ? "/recordings" : "/assets";
  try {
    update(it, { status: "uploading", error: undefined });
    let chunk = 8 * 1024 * 1024; // matches the API's CHUNK_MAX
    if (it.id) {
      const r = await apiFetch(base, `${path}/${it.id}`);
      const body = r.ok ? await r.json() : null;
      if (body?.status === "uploading") it.sent = body.received_bytes;
      else it.id = undefined;
    }
    if (!it.id) {
      const r = await apiFetch(base, path, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(isRecording(it.kind)
          ? { project_id: it.projectId, filename: file.name, size_bytes: file.size }
          : { project_id: it.projectId, kind: it.kind, filename: file.name, size_bytes: file.size }),
      });
      if (!r.ok) throw new Error((await r.json()).detail ?? `Upload refused (${r.status})`);
      const body = await r.json();
      it.id = body.id as string;
      it.sent = 0;
      chunk = body.chunk_size ?? chunk;
      persist();
    }
    let failures = 0;
    while (it.sent < file.size) {
      const r = await apiFetch(base, `${path}/${it.id}/chunk?offset=${it.sent}`, {
        method: "PUT", headers: { "Content-Type": "application/octet-stream" }, body: file.slice(it.sent, it.sent + chunk),
      }).catch(() => null);
      if (r?.ok) { update(it, { sent: (await r.json()).received_bytes }); failures = 0; }
      else if (r?.status === 409) update(it, { sent: (await r.json()).detail.received_bytes }); // server says where to resume
      else {
        if (++failures > 6) throw new Error("The processing computer keeps dropping the connection. Press Resume to continue.");
        await new Promise((res) => setTimeout(res, 1000 * 2 ** failures));
      }
      if (failures === 0 && it.sent % (64 * 1024 * 1024) < chunk) persist(); // remember progress every ~64 MB
    }
    update(it, { status: "validating" });
    const done = await apiFetch(base, `${path}/${it.id}/complete`, { method: "POST" });
    const body = await done.json().catch(() => ({}));
    if (!done.ok) {
      const d = body.detail;
      throw new Error(typeof d === "string" ? d : (d?.message ?? "Validation failed"));
    }
    update(it, { status: "done", duplicate: !!body.duplicate, file: undefined });
    void idb("readwrite", (s) => s.delete(it.key));
    persist();
    doneListeners.forEach((cb) => cb({ ...it }));
    setTimeout(() => { if (items.get(it.key)?.status === "done") { items.delete(it.key); emit(); } }, 8000);
  } catch (e) {
    update(it, { status: "error", error: e instanceof Error ? e.message : String(e) });
    persist();
  }
}
