"use client";

import Image from "next/image";
import { useQuery } from "@tanstack/react-query";
import { Film } from "lucide-react";
import { apiFetch, useBackend } from "@/lib/backend";

export function RenderThumb({ renderId }: { renderId: string }) {
  const backend = useBackend();
  const base = backend.data?.state === "online" ? backend.data.url : null;
  const thumb = useQuery({
    queryKey: ["render-thumb", renderId, base], enabled: !!base, staleTime: 5 * 60_000, retry: 1,
    queryFn: async () => { const r = await apiFetch(base!, `/renders/${renderId}/urls`); if (!r.ok) throw new Error(); return base!.replace(/\/$/, "") + (await r.json()).thumb as string; },
  });
  return <div className="relative aspect-[9/16] bg-[var(--canvas)]">
    {thumb.data ? <Image src={thumb.data} alt="" fill sizes="200px" unoptimized className="object-cover" /> : <Film size={24} strokeWidth={1.3} className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-muted" aria-hidden />}
  </div>;
}
