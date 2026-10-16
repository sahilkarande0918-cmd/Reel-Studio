import type { Metadata } from "next";
import { Archivo, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const archivo = Archivo({ variable: "--font-archivo", subsets: ["latin"], weight: ["400", "600"] });
// Monospace is only for real code (editor fragments, code blocks).
const code = JetBrains_Mono({ variable: "--font-code", subsets: ["latin"], weight: ["400"] });

export const metadata: Metadata = {
  title: "Reel Studio — class recordings to reels",
  description:
    "AI video studio for technical educators. Turn recorded programming classes and topic prompts into branded 9:16 reels.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" suppressHydrationWarning className={`${archivo.variable} ${inter.variable} ${code.variable} h-full`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: "document.documentElement.classList.add('js')" }} />
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
