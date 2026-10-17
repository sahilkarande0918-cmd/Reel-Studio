import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const dmSans = localFont({ src: "./fonts/dm-sans-latin.woff2", variable: "--font-dm-sans", weight: "100 1000", display: "swap" });
const fraunces = localFont({ src: "./fonts/fraunces-latin.woff2", variable: "--font-fraunces", weight: "100 900", display: "swap" });
// Monospace is only for real code (editor fragments, code blocks).
const code = localFont({ src: "./fonts/jetbrains-mono-latin.woff2", variable: "--font-code", weight: "400", display: "swap" });

// Server code runs next to the Supabase database (ap-southeast-1, Singapore) instead of Vercel's US-East default:
// every page makes several database round trips, so this removes ~200 ms from each of them.
export const preferredRegion = "sin1";

export const metadata: Metadata = {
  title: "Reel Studio — class recordings to reels",
  description:
    "AI video studio for technical educators. Turn recorded programming classes and topic prompts into branded 9:16 reels.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${dmSans.variable} ${fraunces.variable} ${code.variable} h-full`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: "document.documentElement.classList.add('js')" }} />
      </head>
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}
