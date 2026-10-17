import Link from "next/link";
import { Aperture, Menu } from "lucide-react";

const LINKS = [["Features", "#features"], ["How it works", "#how-it-works"], ["Examples", "#examples"]] as const;

export function Logo({ light = false }: { light?: boolean }) {
  return <Link href="/" className={`flex items-center gap-2.5 text-[17px] font-semibold tracking-[-.02em] ${light ? "text-[#F6F3EC]" : "text-forest"}`}>
    <span className={`grid h-8 w-8 place-items-center rounded-[9px] ${light ? "bg-[#F6F3EC] text-forest" : "bg-forest text-[#F6F3EC]"}`}><Aperture size={18} strokeWidth={1.9} aria-hidden /></span>
    Reel Studio
  </Link>;
}

export function SiteNav() {
  return <header className="sticky top-0 z-50 border-b border-line/70 bg-[#FCF9F4]/85 backdrop-blur-md">
    <nav aria-label="Main" className="mx-auto flex h-16 max-w-[1240px] items-center justify-between gap-6 px-5 md:px-8">
      <Logo />
      <ul className="hidden items-center gap-8 text-[14.5px] text-[#4d5446] md:flex">
        {LINKS.map(([label, href]) => <li key={href}><a href={href} className="transition-colors hover:text-forest">{label}</a></li>)}
      </ul>
      <div className="hidden items-center gap-2 md:flex">
        <Link href="/login" className="rounded-full px-4 py-2 text-[14.5px] text-forest transition-colors hover:bg-[#EFECE5]">Sign in</Link>
        <Link href="/signup" className="rounded-full bg-forest px-5 py-2.5 text-[14.5px] font-semibold text-[#FCF9F4] transition-[background-color,transform] hover:bg-olive active:scale-[.98]">Get started</Link>
      </div>
      <details className="group relative md:hidden">
        <summary className="grid h-10 w-10 cursor-pointer list-none place-items-center rounded-full text-forest hover:bg-[#EFECE5]"><Menu size={20} aria-label="Open menu" /></summary>
        <div className="absolute right-0 top-12 w-60 rounded-2xl border border-line bg-[#FCF9F4] p-2 shadow-[0_20px_40px_-20px_rgba(29,38,24,.35)]">
          {LINKS.map(([label, href]) => <a key={href} href={href} className="block rounded-xl px-4 py-3 text-[15px] text-forest hover:bg-[#F6F3EC]">{label}</a>)}
          <Link href="/login" className="block rounded-xl px-4 py-3 text-[15px] text-forest hover:bg-[#F6F3EC]">Sign in</Link>
          <Link href="/signup" className="mt-1 block rounded-xl bg-forest px-4 py-3 text-center text-[15px] font-semibold text-[#FCF9F4]">Get started</Link>
        </div>
      </details>
    </nav>
  </header>;
}
