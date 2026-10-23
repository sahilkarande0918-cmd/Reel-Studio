"use client";

import Image from "next/image";
import { useQuery } from "@tanstack/react-query";
import { AudioLines, Code2, Wand2 } from "lucide-react";
import { apiFetch, useBackend } from "@/lib/backend";
import { createClient } from "@/lib/supabase/client";

/** Only finished, authorized renders are used as project artwork. */
export function ProjectPreview({ projectId, mode }: { projectId: string; mode: string }) {
  const backend = useBackend();
  const base = backend.data?.state === "online" ? backend.data.url : null;
  const thumbnail = useQuery<string | null>({
    queryKey: ["project-thumbnail", projectId, base],
    enabled: !!base,
    staleTime: 5 * 60_000,
    retry: 1,
    queryFn: async () => {
      const { data, error } = await createClient().from("render_jobs").select("id").eq("project_id", projectId).eq("status", "ready").order("created_at", { ascending: false }).limit(1).maybeSingle();
      if (error) throw error;
      if (!data) return null;
      const response = await apiFetch(base!, `/renders/${data.id}/urls`);
      if (!response.ok) throw new Error("Preview is unavailable");
      const urls = await response.json();
      return `${base!.replace(/\/$/, "")}${urls.thumb}`;
    },
  });
  const Icon = mode === "edit" ? Wand2 : mode === "topic" ? Code2 : AudioLines;
  const label = mode === "edit" ? "Prompt → Edit" : mode === "topic" ? "Topic → Video" : "Recording → Reels";
  return <div className="relative flex h-40 items-center justify-center overflow-hidden border-b border-line bg-[var(--canvas)]">
    {thumbnail.data ? <>
      <Image src={thumbnail.data} alt="" fill sizes="400px" unoptimized aria-hidden className="scale-110 object-cover opacity-30 blur-xl" />
      <div className="relative h-[136px] w-[77px] overflow-hidden rounded-lg shadow-[0_8px_24px_rgba(0,0,0,.6)] ring-1 ring-white/10"><Image src={thumbnail.data} alt="Latest rendered reel" fill sizes="80px" unoptimized className="object-cover" /></div>
    </> : <div className="flex flex-col items-center gap-2 text-muted"><Icon size={30} strokeWidth={1.3} className="text-accent/80" aria-hidden /><span className="text-[11px]">{mode === "recording" ? "No reel exported yet" : "No video rendered yet"}</span></div>}
    <span className="absolute left-3 top-3 rounded-md bg-black/55 px-2 py-1 text-[10.5px] font-medium text-white/85 backdrop-blur">{label}</span>
  </div>;
}
