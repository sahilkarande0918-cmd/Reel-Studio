"use client";

import Image from "next/image";
import { useState } from "react";

/** Real corrections from the synthetic React-hooks lecture's transcript (raw ASR vs corrected words + their source). */
const EXAMPLES = [
  {
    id: "abortcontroller", time: "1:23", term: "AbortController",
    before: ["Iska solution hai", "about controller", ". Ham ek naya", "about controller", "banenge…"],
    after: ["Iska solution hai", "AbortController", ". Ham ek naya", "AbortController", "banenge…"],
    why: "Heard as “about controller”. Matched to AbortController visible on screen at 1:30 (on-screen text match 93%).",
    frame: "/landing/source-abort.jpg", box: { left: "37%", top: "25.6%", width: "11.8%", height: "3.4%" }, line: "line 8",
  },
  {
    id: "aborterror", time: "1:50", term: "AbortError",
    before: ["…fetch ek", "Abbot error", "throw karta hai."],
    after: ["…fetch ek", "AbortError", "throw karta hai."],
    why: "Heard as “Abbot error”. Matched to \"AbortError\" on screen at 1:54 (on-screen text match 90%).",
    frame: "/landing/source-aborterror.jpg", box: { left: "39.6%", top: "36.9%", width: "8.2%", height: "3.2%" }, line: "line 12",
  },
  {
    id: "useeffect", time: "0:08", term: "useEffect",
    before: ["Aaj ki class mein ham React ka ek bahut important concept samjhenge,", "use effect", "."],
    after: ["Aaj ki class mein ham React ka ek bahut important concept samjhenge,", "useEffect", "."],
    why: "Heard as “use effect”. Corrected from the workspace's technical glossary, then underlined for review.",
    frame: "/landing/source-abort.jpg", box: { left: "21.6%", top: "23.1%", width: "5.9%", height: "3.2%" }, line: "line 7",
  },
];

function Sentence({ parts, fixed }: { parts: string[]; fixed: boolean }) {
  return <p className="text-[19px] leading-[1.75] text-[#2b3326] md:text-[21px]">{parts.map((p, i) => i % 2 === 1
    ? <mark key={i} className={fixed ? "rounded-md bg-[#E3E9DA] px-1.5 py-0.5 font-mono text-[0.86em] text-forest ring-1 ring-[#B9C6AA]" : "bg-transparent text-[#A44A3F] underline decoration-[#A44A3F]/50 decoration-wavy underline-offset-4"}>{p}</mark>
    : <span key={i}>{p.startsWith(".") ? p : ` ${p} `}</span>)}</p>;
}

export function HinglishCompare() {
  const [active, setActive] = useState(0);
  const [fixed, setFixed] = useState(true);
  const ex = EXAMPLES[active];
  return <div className="grid overflow-hidden rounded-[28px] border border-line bg-white shadow-[0_40px_90px_-60px_rgba(29,38,24,.45)] lg:grid-cols-[1.05fr_1fr]">
    <div className="relative bg-[#1e1f1c]">
      <div className="relative aspect-video">
        <Image src={ex.frame} alt={`The recorded class at ${ex.time}, showing ${ex.term} in the code`} fill sizes="(min-width: 1024px) 620px, 100vw" className="object-cover" />
        <span key={ex.id} className="hinglish-box absolute rounded-[6px] border-2 border-[#F2E7C9] shadow-[0_0_0_4px_rgba(242,231,201,.25)]" style={ex.box} />
      </div>
      <div className="flex items-center justify-between gap-3 px-5 py-4 text-[13px] text-[#B9BCB1]">
        <span>Code on screen · {ex.line}</span><span className="font-mono text-[#F2E7C9]">{ex.term}</span>
      </div>
    </div>
    <div className="flex flex-col p-6 md:p-9">
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Correction examples">
        {EXAMPLES.map((e, i) => <button key={e.id} type="button" role="tab" aria-selected={i === active} onClick={() => setActive(i)}
          className={`rounded-full px-3.5 py-1.5 font-mono text-[13px] transition-colors ${i === active ? "bg-forest text-[#FCF9F4]" : "bg-[#F6F3EC] text-[#4d5446] hover:bg-[#EFECE5]"}`}>{e.term}</button>)}
      </div>
      <div className="mt-7 inline-flex self-start rounded-full bg-[#F6F3EC] p-1 text-[13.5px]" role="group" aria-label="Transcript view">
        {[["Heard", false], ["Corrected", true]].map(([label, v]) => <button key={String(label)} type="button" aria-pressed={fixed === v} onClick={() => setFixed(v as boolean)}
          className={`rounded-full px-4 py-1.5 font-medium transition-colors ${fixed === v ? "bg-white text-forest shadow-sm" : "text-[#6b7064]"}`}>{label as string}</button>)}
      </div>
      <div className="mt-5 min-h-[120px]"><p className="mb-2 text-[12px] font-semibold uppercase tracking-[.12em] text-sage">{fixed ? "Reel Studio transcript" : "Raw speech recognition"} · {ex.time}</p>
        <Sentence parts={fixed ? ex.after : ex.before} fixed={fixed} /></div>
      <p className="mt-auto border-t border-line pt-5 text-[14.5px] leading-6 text-[#5b6153]"><span className="font-semibold text-forest">Why it changed. </span>{ex.why}</p>
    </div>
  </div>;
}
