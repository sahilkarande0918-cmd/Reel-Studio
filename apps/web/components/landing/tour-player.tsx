"use client";

import { Play } from "lucide-react";
import { useRef, useState } from "react";

/** The 60-second product tour (composed and rendered with Hyperframes). Never autoplays with sound. */
export function TourPlayer() {
  const ref = useRef<HTMLVideoElement>(null);
  const [started, setStarted] = useState(false);
  return <div className="relative overflow-hidden rounded-[22px] bg-forest shadow-[0_50px_100px_-50px_rgba(29,38,24,.6)] ring-1 ring-black/5">
    <video ref={ref} className="aspect-video w-full bg-forest" controls={started} playsInline preload="none" poster="/landing/tour-poster.jpg"
      onPlay={() => setStarted(true)}>
      <source src="/landing/reel-studio-tour.mp4" type="video/mp4" />
      <track kind="captions" src="/landing/reel-studio-tour.vtt" srcLang="en" label="English" />
      Your browser cannot play this video. <a href="/landing/reel-studio-tour.mp4">Download the tour (MP4)</a>.
    </video>
    {!started && <button type="button" onClick={() => { setStarted(true); ref.current?.play(); }} aria-label="Play the 60-second tour"
      className="group absolute inset-0 grid place-items-center bg-gradient-to-t from-forest/40 via-transparent to-transparent">
      <span className="flex items-center gap-3 rounded-full bg-[#FCF9F4] py-3 pl-3 pr-6 text-[15px] font-semibold text-forest shadow-xl transition-transform group-hover:scale-[1.04]">
        <span className="grid h-11 w-11 place-items-center rounded-full bg-forest text-[#FCF9F4]"><Play size={18} fill="currentColor" aria-hidden /></span>
        Watch the tour · 1:01
      </span>
    </button>}
  </div>;
}
