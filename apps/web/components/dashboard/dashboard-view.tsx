"use client";

import Link from "next/link";
import {
  CheckCircle2,
  ChevronRight,
  Clock,
  Download,
  Heart,
  MessageCircle,
  MoreHorizontal,
  Play,
  Sparkles,
  Video,
} from "lucide-react";

export interface ProjectCardItem {
  id: string;
  title: string;
  duration: string;
  timeAgo: string;
  bgImage: string;
}

export interface ProcessingJobItem {
  id: string;
  title: string;
  desc: string;
  progress: number;
  status: string;
  timeRemaining: string;
  action: string;
  img: string;
  projectId?: string;
}

const DEFAULT_SAMPLE_PROJECTS: ProjectCardItem[] = [
  {
    id: "sample-1",
    title: "Morning Routine",
    duration: "0:28",
    timeAgo: "Edited 2 hours ago",
    bgImage: "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&q=80",
  },
  {
    id: "sample-2",
    title: "Travel Essentials",
    duration: "0:16",
    timeAgo: "Edited 1 day ago",
    bgImage: "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=400&q=80",
  },
  {
    id: "sample-3",
    title: "Product Showcase",
    duration: "0:32",
    timeAgo: "Edited 2 days ago",
    bgImage: "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&q=80",
  },
  {
    id: "sample-4",
    title: "Brand Story",
    duration: "0:21",
    timeAgo: "Edited 3 days ago",
    bgImage: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&q=80",
  },
  {
    id: "sample-5",
    title: "Healthy Recipes",
    duration: "0:27",
    timeAgo: "Edited 4 days ago",
    bgImage: "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=400&q=80",
  },
];

const DEFAULT_SAMPLE_JOBS: ProcessingJobItem[] = [
  {
    id: "job-1",
    title: "Summer Campaign",
    desc: "Generating video... This may take a few minutes.",
    progress: 68,
    status: "running",
    timeRemaining: "2 min left",
    action: "Cancel",
    img: "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=100&q=80",
  },
  {
    id: "job-2",
    title: "Product Demo",
    desc: "Enhancing visuals with AI...",
    progress: 32,
    status: "running",
    timeRemaining: "4 min left",
    action: "Cancel",
    img: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&q=80",
  },
  {
    id: "job-3",
    title: "Recipe Series",
    desc: "Queued for processing.",
    progress: 0,
    status: "queued",
    timeRemaining: "In queue",
    action: "View",
    img: "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=100&q=80",
  },
  {
    id: "job-4",
    title: "Brand Story - Final Cut",
    desc: "Completed • Ready to download.",
    progress: 100,
    status: "completed",
    timeRemaining: "Completed 8 min ago",
    action: "Download",
    img: "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=100&q=80",
  },
];

export function DashboardView({
  projects = DEFAULT_SAMPLE_PROJECTS,
  jobs = DEFAULT_SAMPLE_JOBS,
}: {
  projects?: ProjectCardItem[];
  jobs?: ProcessingJobItem[];
}) {
  const displayProjects = projects.length > 0 ? projects : DEFAULT_SAMPLE_PROJECTS;
  const processingRows = jobs.length > 0 ? jobs : DEFAULT_SAMPLE_JOBS;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_340px] xl:grid-cols-[minmax(0,1fr)_360px]">
      {/* ─── MAIN COLUMN (LEFT) ─── */}
      <div className="min-w-0 space-y-6">
        {/* 1. HERO BANNER */}
        <section className="relative overflow-hidden rounded-[20px] border border-[#E7E5DE] bg-[#1D2618] text-white shadow-sm">
          {/* Nature mountain background layer */}
          <div
            className="absolute inset-0 bg-cover bg-center opacity-40 mix-blend-overlay"
            style={{
              backgroundImage:
                "url('https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1600&q=80')",
            }}
          />
          {/* Rich multi-stop forest/olive gradient */}
          <div className="absolute inset-0 bg-gradient-to-r from-[#172010] via-[#24301B]/95 to-[#3C462F]/40" />

          <div className="relative z-10 flex flex-col justify-between p-6 sm:p-8 lg:p-9 xl:min-h-[290px]">
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-center">
              {/* Left Text Content */}
              <div className="lg:col-span-7 xl:col-span-8 space-y-3.5">
                <div className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#98A886]" />
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#A3A694]">
                    Turn ideas into impact
                  </p>
                </div>

                <h1 className="font-serif text-[28px] sm:text-[34px] lg:text-[38px] font-medium leading-[1.14] tracking-tight text-[#FCF9F4]">
                  Create short-form videos that grow your brand.
                </h1>

                <p className="max-w-[48ch] text-[13.5px] sm:text-[14px] leading-relaxed text-[#EFECE5]/80">
                  Use the power of AI to create, edit, and publish stunning short
                  videos in minutes — no experience required.
                </p>

                {/* CTAs */}
                <div className="flex flex-wrap items-center gap-3 pt-2">
                  <Link
                    href="/topics"
                    className="inline-flex items-center gap-2 rounded-xl border border-[rgba(255,255,255,0.18)] bg-[#172010]/80 px-4 py-2.5 text-[13.5px] font-medium text-[#FCF9F4] backdrop-blur transition-all hover:bg-[#172010] hover:border-white/30"
                  >
                    <Sparkles size={16} className="text-[#98A886]" />
                    <span>Create a New Video</span>
                    <ChevronRight size={14} className="text-[#A3A694]" />
                  </Link>

                  <Link
                    href="/recordings"
                    className="inline-flex items-center gap-2 rounded-xl bg-[#FCF9F4] px-4 py-2.5 text-[13.5px] font-semibold text-[#1D2618] shadow-sm transition-all hover:bg-white active:scale-[0.98]"
                  >
                    <Video size={16} className="text-[#3C462F]" />
                    <span>Explore Templates</span>
                  </Link>
                </div>
              </div>

              {/* Right Side Visual: Calligraphic text & Layered 9:16 Video Mockup */}
              <div className="relative hidden lg:col-span-5 xl:col-span-4 lg:flex lg:items-center lg:justify-end">
                {/* Handwritten style cursive text */}
                <div className="absolute -left-12 top-6 z-20 pointer-events-none select-none text-right">
                  <p className="font-serif italic text-[16px] text-[#A3A694]/90 leading-tight">
                    Ideas<br />
                    Create<br />
                    Grow<br />
                    Repeat
                  </p>
                  <svg
                    className="ml-auto mt-1 h-6 w-12 text-[#A3A694]/70"
                    viewBox="0 0 50 25"
                    fill="none"
                    stroke="currentColor"
                  >
                    <path
                      d="M5 5 Q 30 5, 42 20 M 35 18 L 42 20 L 40 13"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                    />
                  </svg>
                </div>

                {/* Layered Cards Stack */}
                <div className="relative h-[220px] w-[140px] xl:w-[155px]">
                  {/* Third Card (Deepest) */}
                  <div className="absolute right-0 top-3 h-[190px] w-[115px] rotate-6 rounded-2xl border border-white/10 bg-[#283321] opacity-40 shadow-xl overflow-hidden" />

                  {/* Second Card (Middle) */}
                  <div className="absolute right-3 top-1.5 h-[200px] w-[122px] rotate-3 rounded-2xl border border-white/15 bg-[#283321] opacity-70 shadow-xl overflow-hidden" />

                  {/* Front Card */}
                  <div className="absolute right-6 top-0 h-[215px] w-[130px] rounded-2xl border border-white/25 bg-[#172010] shadow-2xl overflow-hidden">
                    <div
                      className="absolute inset-0 bg-cover bg-center"
                      style={{
                        backgroundImage:
                          "url('https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=400&q=80')",
                      }}
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/30" />
                    <div className="relative z-10 flex h-full flex-col justify-between p-2.5 text-white">
                      <div className="flex justify-between items-center">
                        <span className="rounded-full bg-black/40 px-1.5 py-0.5 text-[9px] backdrop-blur font-medium">
                          0:28
                        </span>
                      </div>
                      <div className="space-y-1">
                        <p className="text-[10.5px] font-medium leading-tight text-white/95 drop-shadow">
                          Good Stories Grow Further
                        </p>
                        <div className="flex items-center gap-1 text-[9px] text-white/70">
                          <Play size={8} fill="white" />
                          <span>Watch</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 2. RECENT PROJECTS SECTION */}
        <section className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-[17px] font-semibold tracking-tight text-[#1D2618]">
              Recent Projects
            </h2>
            <Link
              href="/projects"
              className="text-[12.5px] font-medium text-[#707267] transition-colors hover:text-[#1D2618]"
            >
              View all
            </Link>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {displayProjects.map((p) => (
              <div
                key={p.id}
                className="group relative flex flex-col rounded-2xl border border-[#E7E5DE] bg-white p-2.5 shadow-sm transition-all hover:border-[#3C462F]/40 hover:shadow-md"
              >
                {/* Thumbnail Card */}
                <Link
                  href={p.id.startsWith("sample-") ? "/projects" : `/projects/${p.id}`}
                  className="relative aspect-[4/3] w-full overflow-hidden rounded-xl bg-[#F6F3EC]"
                >
                  <div
                    className="absolute inset-0 bg-cover bg-center transition-transform duration-300 group-hover:scale-105"
                    style={{ backgroundImage: `url('${p.bgImage}')` }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/10" />

                  {/* Duration Pill at bottom left */}
                  <span className="absolute bottom-2 left-2 flex items-center gap-1 rounded-md bg-black/60 px-1.5 py-0.5 text-[10.5px] font-medium text-white backdrop-blur">
                    <Play size={9} fill="white" />
                    <span>{p.duration}</span>
                  </span>

                  {/* 3-dots button top right */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                    }}
                    className="absolute right-1.5 top-1.5 grid h-6 w-6 place-items-center rounded-full bg-black/40 text-white opacity-0 transition-opacity group-hover:opacity-100 hover:bg-black/70"
                  >
                    <MoreHorizontal size={13} />
                  </button>
                </Link>

                {/* Project Title & Timestamp */}
                <div className="mt-2.5 flex items-start justify-between gap-1 px-1">
                  <div className="min-w-0 flex-1">
                    <Link
                      href={p.id.startsWith("sample-") ? "/projects" : `/projects/${p.id}`}
                      className="block truncate text-[13px] font-semibold text-[#1D2618] hover:underline"
                    >
                      {p.title}
                    </Link>
                    <p className="mt-0.5 truncate text-[11px] text-[#707267]">
                      {p.timeAgo}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="mt-0.5 rounded p-1 text-[#707267] hover:bg-[#F6F3EC] hover:text-[#1D2618]"
                  >
                    <MoreHorizontal size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* 3. PROCESSING & JOBS SECTION */}
        <section className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-[17px] font-semibold tracking-tight text-[#1D2618]">
              Processing & Jobs
            </h2>
            <Link
              href="/projects"
              className="text-[12.5px] font-medium text-[#707267] transition-colors hover:text-[#1D2618]"
            >
              View all
            </Link>
          </div>

          <div className="divide-y divide-[#E7E5DE] rounded-2xl border border-[#E7E5DE] bg-white px-4 py-1 shadow-sm">
            {processingRows.map((row) => (
              <div
                key={row.id}
                className="flex flex-col gap-3 py-3.5 sm:flex-row sm:items-center sm:justify-between"
              >
                {/* Left: Thumbnail & Title/Status */}
                <div className="flex items-center gap-3 min-w-[220px]">
                  <div className="relative h-11 w-11 shrink-0 overflow-hidden rounded-xl bg-[#F6F3EC]">
                    <div
                      className="absolute inset-0 bg-cover bg-center"
                      style={{ backgroundImage: `url('${row.img}')` }}
                    />
                  </div>
                  <div className="min-w-0">
                    <h3 className="truncate text-[13.5px] font-semibold text-[#1D2618]">
                      {row.title}
                    </h3>
                    <div className="flex items-center gap-1.5 text-[11.5px] text-[#707267]">
                      {row.status === "completed" || row.status === "succeeded" ? (
                        <CheckCircle2 size={13} className="text-[#2F6B3A]" />
                      ) : row.status === "queued" ? (
                        <Clock size={13} className="text-[#A3A094]" />
                      ) : (
                        <span className="relative flex h-2 w-2">
                          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#3C462F] opacity-75" />
                          <span className="relative inline-flex h-2 w-2 rounded-full bg-[#3C462F]" />
                        </span>
                      )}
                      <span className="truncate">{row.desc}</span>
                    </div>
                  </div>
                </div>

                {/* Center: Progress Bar & Status Text */}
                <div className="flex flex-1 items-center gap-4 sm:max-w-xs md:max-w-sm">
                  {row.status === "queued" ? (
                    <div className="flex items-center gap-2 text-[12px] text-[#707267]">
                      <Clock size={14} />
                      <span>In queue</span>
                    </div>
                  ) : row.status === "completed" || row.status === "succeeded" ? (
                    <div className="text-[12px] text-[#707267] sm:text-right w-full pr-2">
                      {row.timeRemaining}
                    </div>
                  ) : (
                    <div className="w-full space-y-1">
                      <div className="flex justify-between text-[11px] text-[#707267]">
                        <span className="font-medium text-[#1D2618]">{row.progress}%</span>
                        <span>{row.timeRemaining}</span>
                      </div>
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#EFECE5]">
                        <div
                          className="h-full rounded-full bg-[#3C462F] transition-all duration-300"
                          style={{ width: `${row.progress}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Right: Action Buttons */}
                <div className="flex items-center justify-end gap-2 shrink-0">
                  {row.action === "Download" ? (
                    <button
                      type="button"
                      className="inline-flex items-center gap-1.5 rounded-lg border border-[#E7E5DE] bg-white px-3 py-1.5 text-[12px] font-semibold text-[#1D2618] shadow-xs hover:bg-[#F6F3EC]"
                    >
                      <Download size={13} />
                      <span>Download</span>
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="rounded-lg border border-[#E7E5DE] bg-white px-3 py-1.5 text-[12px] font-medium text-[#707267] shadow-xs hover:bg-[#F6F3EC] hover:text-[#1D2618]"
                    >
                      {row.action}
                    </button>
                  )}
                  <button
                    type="button"
                    className="rounded-lg p-1.5 text-[#A3A094] hover:bg-[#F6F3EC] hover:text-[#1D2618]"
                  >
                    <MoreHorizontal size={15} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* ─── SIDEBAR COLUMN (RIGHT) ─── */}
      <aside className="space-y-5">
        {/* 1. ANALYTICS CARD */}
        <section className="rounded-2xl border border-[#E7E5DE] bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-[16px] font-semibold text-[#1D2618]">Analytics</h2>
            <div className="flex items-center gap-1 rounded-lg border border-[#E7E5DE] bg-[#FCF9F4] px-2.5 py-1 text-[11px] font-medium text-[#707267]">
              <span>Last 30 days</span>
              <ChevronRight size={12} className="rotate-90" />
            </div>
          </div>

          {/* 3 Prominent Statistics */}
          <div className="mt-4 grid grid-cols-3 gap-2 border-b border-[#E7E5DE] pb-4">
            <div>
              <p className="text-[20px] font-semibold tracking-tight text-[#1D2618]">
                1.2M
              </p>
              <p className="text-[10.5px] text-[#707267]">Total Views</p>
              <p className="mt-1 flex items-center gap-0.5 text-[10.5px] font-medium text-[#2F6B3A]">
                <span>↑</span> 24%
              </p>
            </div>
            <div>
              <p className="text-[20px] font-semibold tracking-tight text-[#1D2618]">
                86.4K
              </p>
              <p className="text-[10.5px] text-[#707267]">Engagements</p>
              <p className="mt-1 flex items-center gap-0.5 text-[10.5px] font-medium text-[#2F6B3A]">
                <span>↑</span> 32%
              </p>
            </div>
            <div>
              <p className="text-[20px] font-semibold tracking-tight text-[#1D2618]">
                12.6K
              </p>
              <p className="text-[10.5px] text-[#707267]">Followers</p>
              <p className="mt-1 flex items-center gap-0.5 text-[10.5px] font-medium text-[#2F6B3A]">
                <span>↑</span> 18%
              </p>
            </div>
          </div>

          {/* Area Chart with SVG Curve */}
          <div className="mt-4">
            <div className="relative h-28 w-full">
              <svg
                viewBox="0 0 300 100"
                preserveAspectRatio="none"
                className="h-full w-full overflow-visible"
              >
                <defs>
                  <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3C462F" stopOpacity="0.25" />
                    <stop offset="100%" stopColor="#3C462F" stopOpacity="0.0" />
                  </linearGradient>
                </defs>
                {/* Horizontal reference lines */}
                <line x1="0" y1="20" x2="300" y2="20" stroke="#F6F3EC" strokeDasharray="3 3" />
                <line x1="0" y1="55" x2="300" y2="55" stroke="#F6F3EC" strokeDasharray="3 3" />
                <line x1="0" y1="90" x2="300" y2="90" stroke="#F6F3EC" />

                {/* Area fill */}
                <path
                  d="M 0 85 C 30 80, 50 85, 75 70 C 100 55, 120 75, 150 60 C 180 45, 200 65, 230 45 C 260 25, 280 40, 300 15 L 300 100 L 0 100 Z"
                  fill="url(#areaGradient)"
                />
                {/* Smooth trend curve */}
                <path
                  d="M 0 85 C 30 80, 50 85, 75 70 C 100 55, 120 75, 150 60 C 180 45, 200 65, 230 45 C 260 25, 280 40, 300 15"
                  fill="none"
                  stroke="#3C462F"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />
                {/* Peak point indicator */}
                <circle cx="300" cy="15" r="3.5" fill="#3C462F" stroke="#FFFFFF" strokeWidth="2" />
              </svg>
            </div>

            {/* X-axis date labels */}
            <div className="mt-2 flex justify-between text-[10px] text-[#A3A094]">
              <span>Apr 1</span>
              <span>Apr 8</span>
              <span>Apr 15</span>
              <span>Apr 22</span>
              <span>Apr 30</span>
            </div>
          </div>
        </section>

        {/* 2. TOP PERFORMING VIDEO */}
        <section className="rounded-2xl border border-[#E7E5DE] bg-white p-4 shadow-sm">
          <h2 className="text-[14.5px] font-semibold text-[#1D2618]">
            Top Performing Video
          </h2>

          <div className="mt-3 flex items-center justify-between gap-3 rounded-xl p-1 transition-colors hover:bg-[#F6F3EC]">
            {/* Thumbnail */}
            <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-xl bg-[#F6F3EC]">
              <div
                className="absolute inset-0 bg-cover bg-center"
                style={{
                  backgroundImage:
                    "url('https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=200&q=80')",
                }}
              />
              <span className="absolute bottom-1 left-1 rounded bg-black/60 px-1 py-0.2 text-[8px] font-medium text-white">
                0:28
              </span>
            </div>

            {/* Metrics */}
            <div className="min-w-0 flex-1">
              <h3 className="truncate text-[13px] font-semibold text-[#1D2618]">
                Find More You
              </h3>
              <div className="mt-1 flex items-center gap-3 text-[11px] text-[#707267]">
                <span className="flex items-center gap-1">
                  <Play size={10} fill="#707267" /> 412K
                </span>
                <span className="flex items-center gap-1">
                  <Heart size={10} /> 24.8K
                </span>
                <span className="flex items-center gap-1">
                  <MessageCircle size={10} /> 1.2K
                </span>
              </div>
            </div>

            {/* Chevron */}
            <ChevronRight size={16} className="text-[#A3A094]" />
          </div>
        </section>

        {/* 3. PROMOTIONAL FEATURE CARD */}
        <section className="relative overflow-hidden rounded-2xl bg-[#172010] p-5 text-white shadow-md">
          {/* Subtle tropical leaf silhouette background */}
          <div
            className="absolute -right-6 -bottom-6 h-40 w-40 opacity-20 bg-contain bg-no-repeat"
            style={{
              backgroundImage:
                "radial-gradient(circle, #647457 0%, transparent 70%)",
            }}
          />

          <div className="relative z-10 space-y-2">
            <span className="inline-block text-[10px] font-bold uppercase tracking-widest text-[#98A886]">
              • New
            </span>
            <h3 className="font-serif text-[18px] font-medium leading-snug text-[#FCF9F4]">
              Turn a blog post into a video with AI
            </h3>
            <p className="text-[12px] leading-relaxed text-[#A3A694]">
              Paste a link and let Reel Studio create a stunning video for you.
            </p>

            <div className="pt-2">
              <Link
                href="/topics"
                className="inline-flex items-center gap-1.5 rounded-xl bg-[#FCF9F4] px-4 py-2 text-[12px] font-semibold text-[#1D2618] transition-colors hover:bg-white active:scale-[0.98]"
              >
                <span>Try It Now</span>
                <ChevronRight size={13} />
              </Link>
            </div>
          </div>
        </section>
      </aside>
    </div>
  );
}
