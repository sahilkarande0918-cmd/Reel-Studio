import Image from "next/image";

/**
 * The real conversion: a frame of the (synthetic) React-hooks class at 1920×1080, the 608×1080 crop window moving
 * through the actual keyframes of its render (x = 450 → 304 → 209 → 148), and that render playing as a 9:16 reel.
 */
export function HeroVisual() {
  return <div className="relative mx-auto w-full max-w-[680px] pb-10 lg:max-w-none lg:pb-0">
    <figure className="relative w-[86%] overflow-hidden rounded-[18px] bg-[#1e1f1c] shadow-[0_40px_90px_-40px_rgba(29,38,24,.55)] ring-1 ring-black/5">
      <div className="flex h-7 items-center gap-1.5 bg-[#2a2b28] px-3"><i className="h-2.5 w-2.5 rounded-full bg-[#4a4b46]" /><i className="h-2.5 w-2.5 rounded-full bg-[#4a4b46]" /><i className="h-2.5 w-2.5 rounded-full bg-[#4a4b46]" /><span className="ml-3 text-[11px] text-[#8b8d84]">class-recording.mp4 · 1920×1080</span></div>
      <div className="relative aspect-video">
        <Image src="/landing/source-abort.jpg" alt="A frame of a recorded React class: useFetch with AbortController in VS Code" fill priority sizes="(min-width: 1024px) 560px, 86vw" className="object-cover" />
        <div className="hero-crop absolute inset-y-0 w-[31.67%] rounded-[4px] border-[2.5px] border-[#F2E7C9] shadow-[0_0_0_2000px_rgba(15,18,12,.48)]">
          <span className="absolute left-1.5 top-1.5 rounded bg-[#F2E7C9] px-1.5 py-0.5 text-[10.5px] font-semibold text-forest">9:16</span>
        </div>
      </div>
      <figcaption className="sr-only">The crop window follows the code the instructor is working on.</figcaption>
    </figure>
    <svg aria-hidden className="pointer-events-none absolute left-[40%] top-[34%] hidden h-[30%] w-[40%] sm:block" viewBox="0 0 200 100" preserveAspectRatio="none">
      <path d="M0 10 C 90 10, 110 80, 200 80" className="hero-flow" fill="none" stroke="#647457" strokeWidth="2" strokeDasharray="6 6" vectorEffect="non-scaling-stroke" />
    </svg>
    <div className="absolute bottom-0 right-0 w-[34%] min-w-[150px] overflow-hidden rounded-[26px] bg-black shadow-[0_40px_80px_-30px_rgba(29,38,24,.7)] ring-[7px] ring-forest">
      <video src="/landing/reel-hooks.mp4" poster="/landing/reel-hooks.jpg" autoPlay muted loop playsInline preload="metadata" className="aspect-[9/16] w-full object-cover" aria-label="The rendered 9:16 reel from that class, with Hinglish captions" />
    </div>
    <span className="absolute -bottom-1 right-[36%] hidden rounded-full border border-line bg-[#FCF9F4] px-3 py-1.5 text-[12px] text-[#4d5446] shadow-sm sm:block">Rendered reel · 1080×1920</span>
  </div>;
}
