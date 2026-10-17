import type { Metadata } from "next";
import { DM_Sans, Fraunces, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const dmSans = DM_Sans({ variable: "--font-dm-sans", subsets: ["latin"] });
const fraunces = Fraunces({ variable: "--font-fraunces", subsets: ["latin"] });
// Monospace is only for real code (editor fragments, code blocks).
const code = JetBrains_Mono({ variable: "--font-code", subsets: ["latin"], weight: ["400"] });

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
