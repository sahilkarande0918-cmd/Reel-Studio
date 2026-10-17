import Image from "next/image";
import Link from "next/link";
import { ArrowRight, Captions, Code2, Download, ExternalLink, Film, Layers, Mic, Palette, Play, Sparkles, Upload, Wand2 } from "lucide-react";
import { HeroVisual } from "@/components/landing/hero-visual";
import { HinglishCompare } from "@/components/landing/hinglish-compare";
import { Reveal } from "@/components/landing/reveal";
import { Logo, SiteNav } from "@/components/landing/site-nav";
import { TourPlayer } from "@/components/landing/tour-player";

const PUBLISHED_REEL = "https://www.instagram.com/reel/DekyGWcDEAl/";

function Eyebrow({ children }: { children: React.ReactNode }) {
  return <p className="mb-4 text-[12.5px] font-semibold uppercase tracking-[.16em] text-sage">{children}</p>;
}

function H2({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <h2 data-reveal className={`font-serif text-[clamp(32px,4.2vw,54px)] font-normal leading-[1.06] tracking-[-.025em] text-forest ${className}`}>{children}</h2>;
}

function Shot({ src, alt, className = "", position = "top left", zoom = 1 }: { src: string; alt: string; className?: string; position?: string; zoom?: number }) {
  return <div className={`relative overflow-hidden rounded-[18px] border border-line bg-white shadow-[0_30px_70px_-45px_rgba(29,38,24,.5)] ${className}`}>
    <div className="flex h-7 items-center gap-1.5 border-b border-line bg-[#FCF9F4] px-3"><i className="h-2.5 w-2.5 rounded-full bg-[#E7E5DE]" /><i className="h-2.5 w-2.5 rounded-full bg-[#E7E5DE]" /><i className="h-2.5 w-2.5 rounded-full bg-[#E7E5DE]" /></div>
    <div className="relative aspect-[16/10]"><Image src={src} alt={alt} fill sizes="(min-width: 1024px) 640px, 100vw" className="object-cover" style={{ objectPosition: position, transform: `scale(${zoom})`, transformOrigin: position }} /></div>
  </div>;
}

function Phone({ video, poster, label, className = "" }: { video?: string; poster: string; label: string; className?: string }) {
  return <div className={`overflow-hidden rounded-[26px] bg-black shadow-[0_40px_80px_-35px_rgba(29,38,24,.7)] ring-[7px] ring-forest ${className}`}>
    {video ? <video src={video} poster={poster} autoPlay muted loop playsInline preload="none" aria-label={label} className="aspect-[9/16] w-full object-cover" />
      : <Image src={poster} alt={label} width={540} height={960} className="aspect-[9/16] w-full object-cover" />}
  </div>;
}

export default function Landing() {
  return (
    <div className="flex-1 bg-[#FCF9F4] text-[#20271C]">
      <Reveal />
      <SiteNav />
      <main>
        {/* 1 — Hero */}
        <section className="mx-auto grid max-w-[1240px] items-center gap-14 px-5 pb-20 pt-12 md:px-8 lg:grid-cols-[1fr_1.12fr] lg:gap-10 lg:pb-28 lg:pt-20">
          <div>
            <p className="mb-6 inline-flex items-center gap-2 rounded-full border border-line bg-white px-3.5 py-1.5 text-[13px] text-[#4d5446]"><Sparkles size={14} className="text-sage" aria-hidden />AI video studio for educators</p>
            <h1 className="lines font-serif text-[clamp(40px,5.6vw,72px)] font-normal leading-[1.02] tracking-[-.03em] text-forest">
              <span className="line"><span data-line style={{ "--i": 0 } as React.CSSProperties}>From long recordings</span></span>
              <span className="line"><span data-line style={{ "--i": 1 } as React.CSSProperties}>to stories <em className="text-olive">worth watching.</em></span></span>
            </h1>
            <div data-after-lines>
              <p className="mt-7 max-w-[52ch] text-[18px] leading-[1.65] text-[#4d5446]">Turn classes and ideas into polished short-form videos. Find the best moments, keep technical details readable, edit your story, and publish to Instagram — all in one studio.</p>
              <div className="mt-9 flex flex-wrap items-center gap-3">
                <Link href="/signup" className="inline-flex items-center gap-2 rounded-full bg-forest px-6 py-3.5 text-[15.5px] font-semibold text-[#FCF9F4] transition-[background-color,transform] hover:bg-olive active:scale-[.98]">Start Creating Free <ArrowRight size={17} aria-hidden /></Link>
                <a href="#tour" className="inline-flex items-center gap-2.5 rounded-full border border-line bg-white px-5 py-3.5 text-[15.5px] font-semibold text-forest transition-colors hover:border-sage">
                  <span className="grid h-7 w-7 place-items-center rounded-full bg-[#E3E9DA]"><Play size={13} fill="currentColor" aria-hidden /></span>Watch 60-Second Tour</a>
              </div>
              <p className="mt-6 text-[13.5px] text-[#6b7064]">Hinglish-aware · Runs on your own GPU machine · Free</p>
            </div>
          </div>
          <HeroVisual />
        </section>

        {/* 2 — Tour */}
        <section id="tour" className="scroll-mt-20 bg-[#F6F3EC] py-20 md:py-28">
          <div className="mx-auto max-w-[1120px] px-5 md:px-8">
            <div className="mx-auto mb-12 max-w-[720px] text-center">
              <Eyebrow>Product tour</Eyebrow>
              <H2>Your first Reel, in 60 seconds.</H2>
              <p data-reveal className="mt-5 text-[18px] leading-relaxed text-[#4d5446]">See how Reel Studio turns a recording or an idea into a ready-to-publish video.</p>
            </div>
            <div data-reveal><TourPlayer /></div>
            <p className="mt-4 text-center text-[13px] text-[#6b7064]">Real screens from the app, composed and rendered with Hyperframes. Captions available.</p>
          </div>
        </section>

        {/* 3 — How it works */}
        <section id="how-it-works" className="mx-auto max-w-[1240px] scroll-mt-20 px-5 py-24 md:px-8 md:py-32">
          <div className="mb-14 max-w-[640px]"><Eyebrow>How it works</Eyebrow><H2>Three steps from raw footage to a finished Reel.</H2></div>
          <ol className="grid gap-8 lg:grid-cols-3">
            {[
              { n: "01", icon: Upload, title: "Bring your content", body: "Upload a class recording, or type the topic you want explained.", src: "/landing/app-uploader.jpg", pos: "57% 38%", zoom: 2.1 },
              { n: "02", icon: Wand2, title: "Let intelligence do the groundwork", body: "Hinglish transcription, ranked highlights, code understanding and smart 9:16 reframing.", src: "/landing/app-recording-highlights.jpg", pos: "40% 22%", zoom: 1.75 },
              { n: "03", icon: Film, title: "Make it yours", body: "Edit on a multitrack timeline, apply your brand, export the MP4 and publish.", src: "/landing/app-editor-recording.jpg", pos: "62% 40%", zoom: 1.45 },
            ].map(({ n, icon: Icon, title, body, src, pos, zoom }, i) => <li key={n} data-reveal style={{ "--d": i } as React.CSSProperties} className="group">
              <Shot src={src} alt={`${title}: Reel Studio screen`} position={pos} zoom={zoom} />
              <div className="mt-6 flex items-start gap-4">
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-forest text-[#FCF9F4]"><Icon size={19} aria-hidden /></span>
                <div><p className="font-mono text-[12px] text-sage">{n}</p><h3 className="mt-0.5 text-[20px] font-semibold tracking-[-.015em] text-forest">{title}</h3><p className="mt-2 text-[15.5px] leading-relaxed text-[#5b6153]">{body}</p></div>
              </div>
            </li>)}
          </ol>
        </section>

        {/* 4 — Hinglish + code */}
        <section id="features" className="scroll-mt-20 bg-[#F6F3EC] py-24 md:py-32">
          <div className="mx-auto max-w-[1240px] px-5 md:px-8">
            <div className="mb-12 grid gap-6 lg:grid-cols-[1fr_1fr] lg:items-end">
              <div><Eyebrow>Hinglish and code understanding</Eyebrow><H2>It hears the class.<br />It reads the code.</H2></div>
              <p data-reveal className="max-w-[52ch] text-[17px] leading-relaxed text-[#4d5446]">Speech recognition hears “about controller”. Reel Studio checks the code on screen and your glossary, and writes <code className="rounded bg-white px-1.5 py-0.5 font-mono text-[15px] text-forest">AbortController</code>. These examples come from a real transcript of a recorded React class.</p>
            </div>
            <div data-reveal><HinglishCompare /></div>
          </div>
        </section>

        {/* 5 — Reframing */}
        <section className="mx-auto max-w-[1240px] px-5 py-24 md:px-8 md:py-32">
          <div className="grid items-center gap-14 lg:grid-cols-[1.15fr_1fr]">
            <div data-reveal className="relative">
              <div className="relative overflow-hidden rounded-[20px] bg-[#1e1f1c] shadow-[0_40px_90px_-50px_rgba(29,38,24,.6)]">
                <div className="relative aspect-video">
                  <Image src="/landing/source-abort.jpg" alt="Widescreen class recording" fill sizes="(min-width: 1024px) 700px, 100vw" className="object-cover" />
                  <div className="reframe-crop absolute inset-y-0 left-[23.44%] w-[31.67%] rounded-[4px] border-[3px] border-[#F2E7C9] shadow-[0_0_0_2000px_rgba(15,18,12,.5)]" />
                  <span className="absolute left-[47%] top-[30%] h-3 w-3 rounded-full bg-[#F2E7C9] shadow-[0_0_0_6px_rgba(242,231,201,.3)]" aria-hidden />
                </div>
              </div>
              <div className="mt-5 grid grid-cols-3 gap-3 text-[13px]">
                {[["Source", "1920×1080"], ["Crop window", "608×1080"], ["Output", "1080×1920"]].map(([k, v]) => <div key={k} className="rounded-xl border border-line bg-white px-4 py-3"><p className="text-[#6b7064]">{k}</p><p className="mt-0.5 font-mono text-forest">{v}</p></div>)}
              </div>
            </div>
            <div className="grid grid-cols-1 items-center gap-8 sm:grid-cols-[1fr_0.62fr]">
              <div><Eyebrow>Smart 9:16 reframing</Eyebrow><H2>The crop follows the code, not the centre.</H2>
                <p data-reveal className="mt-6 text-[17px] leading-relaxed text-[#4d5446]">Reel Studio tracks where the instructor is typing and moves the vertical window with them. The animation on the left replays the real crop keyframes of the reel beside it.</p></div>
              <Phone video="/landing/reel-hooks.mp4" poster="/landing/reel-hooks.jpg" label="The reframed reel" className="mx-auto w-full max-w-[230px]" />
            </div>
          </div>
        </section>

        {/* 6 — Two ways */}
        <section id="examples" className="scroll-mt-20 bg-forest py-24 text-[#F6F3EC] md:py-32">
          <div className="mx-auto max-w-[1240px] px-5 md:px-8">
            <div className="mb-16 max-w-[640px]"><p className="mb-4 text-[12.5px] font-semibold uppercase tracking-[.16em] text-[#A9B59A]">Two ways to create</p>
              <h2 data-reveal className="font-serif text-[clamp(32px,4.2vw,54px)] font-normal leading-[1.06] tracking-[-.025em]">Start from a recording.<br /><em className="text-[#C9D2BD]">Or from a single idea.</em></h2></div>
            <div className="grid gap-10 lg:grid-cols-2">
              {[
                { icon: Mic, title: "Recording → Reels", body: "Upload a class. Get ranked 30–60 s highlights that start and end on complete thoughts, framed for phones, with synced captions.", shot: "/landing/app-recording-highlights.jpg", video: "/landing/reel-hooks.mp4", poster: "/landing/reel-hooks.jpg", cta: "Upload a recording" },
                { icon: Code2, title: "Topic → Video", body: "Type “JSON vs XML”. Get an editable script, animated code cards, a natural local voiceover and a 9:16 MP4.", shot: "/landing/app-topic-script.jpg", video: "/landing/reel-topic.mp4", poster: "/landing/reel-topic.jpg", cta: "Create from a topic" },
              ].map(({ icon: Icon, title, body, shot, video, poster, cta }, i) => <article key={title} data-reveal style={{ "--d": i } as React.CSSProperties} className="rounded-[26px] bg-[#26301F] p-6 ring-1 ring-white/5 md:p-8">
                <div className="relative mb-8 pr-[28%]">
                  <div className="overflow-hidden rounded-[14px] ring-1 ring-white/10"><div className="relative aspect-[16/10]"><Image src={shot} alt={`${title} in the app`} fill sizes="(min-width: 1024px) 420px, 80vw" className="object-cover object-left-top" /></div></div>
                  <Phone video={video} poster={poster} label={`${title} output`} className="absolute -bottom-6 right-0 w-[34%] ring-[5px] ring-[#1D2618]" />
                </div>
                <span className="grid h-10 w-10 place-items-center rounded-full bg-[#F6F3EC] text-forest"><Icon size={18} aria-hidden /></span>
                <h3 className="mt-5 font-serif text-[30px] tracking-[-.02em]">{title}</h3>
                <p className="mt-3 max-w-[46ch] text-[16px] leading-relaxed text-[#C9D2BD]">{body}</p>
                <Link href="/signup" className="mt-6 inline-flex items-center gap-2 text-[15px] font-semibold text-[#F6F3EC] underline-offset-4 hover:underline">{cta} <ArrowRight size={16} aria-hidden /></Link>
              </article>)}
            </div>
          </div>
        </section>

        {/* 7 — Editing and branding */}
        <section className="mx-auto max-w-[1240px] px-5 py-24 md:px-8 md:py-32">
          <div className="mb-14 grid gap-6 lg:grid-cols-2 lg:items-end"><div><Eyebrow>Professional editing and branding</Eyebrow><H2>Fine-tune every frame. Keep it on brand.</H2></div>
            <p data-reveal className="max-w-[52ch] text-[17px] leading-relaxed text-[#4d5446]">A real multitrack editor on the same timeline the renderer uses: what you preview is what exports.</p></div>
          <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
            <div data-reveal><Shot src="/landing/app-editor-recording.jpg" alt="The Reel Studio timeline editor" position="55% 55%" zoom={1.18} /></div>
            <div data-reveal style={{ "--d": 1 } as React.CSSProperties}><Shot src="/landing/app-brand.jpg" alt="Brand kit editor with live previews" position="62% 30%" zoom={1.6} /></div>
          </div>
          <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {[
              [Layers, "Timeline editor", "Split, trim, move and duplicate across video, audio, caption and overlay tracks."],
              [Captions, "Caption presets", "Highlight word, karaoke or boxed, with word-level text and timing edits."],
              [Palette, "Brand kits", "Colours, fonts, logo, watermark, intro and outro, applied to any video."],
              [Code2, "Code animations", "Typed code cards with readable fonts and syntax colour."],
              [Download, "MP4 export", "Verified 1080×1920 MP4 plus SRT and VTT subtitles."],
            ].map(([Icon, title, body], i) => { const I = Icon as typeof Layers; return <li key={title as string} data-reveal style={{ "--d": i } as React.CSSProperties} className="rounded-2xl border border-line bg-white p-5"><I size={20} className="text-sage" aria-hidden /><h3 className="mt-4 text-[16px] font-semibold text-forest">{title as string}</h3><p className="mt-1.5 text-[14px] leading-relaxed text-[#5b6153]">{body as string}</p></li>; })}
          </ul>
        </section>

        {/* 8 — Instagram */}
        <section className="bg-[#F6F3EC] py-24 md:py-32">
          <div className="mx-auto grid max-w-[1240px] items-center gap-14 px-5 md:px-8 lg:grid-cols-[1fr_1.1fr]">
            <div className="order-2 lg:order-1"><Eyebrow>Instagram publishing</Eyebrow><H2>Publish where your students already scroll.</H2>
              <p data-reveal className="mt-6 max-w-[50ch] text-[17px] leading-relaxed text-[#4d5446]">Connect an Instagram Business account through the official Instagram API. Write the caption and hashtags, then publish now or schedule it. Every post is checked and never published twice.</p>
              <ul data-reveal className="mt-7 space-y-3 text-[15.5px] text-[#2b3326]">
                {["Official Instagram Login, tokens encrypted at rest", "Publish now or schedule, with a queue and calendar", "Real post links and analytics after publishing"].map((t) => <li key={t} className="flex gap-3"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-sage" />{t}</li>)}
              </ul>
              <a href={PUBLISHED_REEL} target="_blank" rel="noopener noreferrer" className="mt-8 inline-flex items-center gap-2 rounded-full border border-line bg-white px-5 py-3 text-[15px] font-semibold text-forest hover:border-sage">See a Reel published from Reel Studio <ExternalLink size={15} aria-hidden /></a>
            </div>
            <div data-reveal className="order-1 grid grid-cols-[1.4fr_1fr] items-end gap-5 lg:order-2">
              <Shot src="/landing/app-publishing.jpg" alt="The Publish screen" position="22% 30%" zoom={1.7} />
              <figure><Phone poster="/landing/reel-physics.jpg" label="A physics reel published to Instagram from Reel Studio" /><figcaption className="mt-4 text-center text-[13px] text-[#6b7064]">Published via the API · @career.with.purpose</figcaption></figure>
            </div>
          </div>
        </section>

        {/* 9 — CTA */}
        <section className="bg-forest px-5 py-24 text-center text-[#F6F3EC] md:py-32">
          <h2 data-reveal className="mx-auto max-w-[16ch] font-serif text-[clamp(36px,5vw,64px)] font-normal leading-[1.04] tracking-[-.03em]">Your best content deserves to be seen.</h2>
          <p data-reveal className="mx-auto mt-6 max-w-[44ch] text-[18px] text-[#C9D2BD]">Create your next Reel from a recording or an idea.</p>
          <Link data-reveal href="/signup" className="mt-10 inline-flex items-center gap-2 rounded-full bg-[#F6F3EC] px-7 py-4 text-[16px] font-semibold text-forest transition-transform hover:scale-[1.03]">Start Creating Free <ArrowRight size={17} aria-hidden /></Link>
        </section>
      </main>

      <footer className="bg-[#172010] px-5 py-12 text-[14px] text-[#A9B59A] md:px-8">
        <div className="mx-auto flex max-w-[1240px] flex-col gap-8 md:flex-row md:items-start md:justify-between">
          <div><Logo light /><p className="mt-4 max-w-[34ch]">The AI video studio for technical educators.</p></div>
          <nav aria-label="Footer" className="grid grid-cols-2 gap-x-14 gap-y-3 sm:grid-cols-3">
            <a href="#features" className="hover:text-[#F6F3EC]">Features</a><a href="#how-it-works" className="hover:text-[#F6F3EC]">How it works</a><a href="#examples" className="hover:text-[#F6F3EC]">Examples</a>
            <Link href="/login" className="hover:text-[#F6F3EC]">Sign in</Link><Link href="/privacy" className="hover:text-[#F6F3EC]">Privacy</Link><Link href="/terms" className="hover:text-[#F6F3EC]">Terms</Link>
            <a href="https://github.com/sahilkarande0918-cmd/Reel-Studio" className="hover:text-[#F6F3EC]">GitHub</a>
          </nav>
        </div>
        <p className="mx-auto mt-10 max-w-[1240px] border-t border-white/10 pt-6 text-[12.5px]">© 2026 Reel Studio · Open source under the MIT licence</p>
      </footer>
    </div>
  );
}
