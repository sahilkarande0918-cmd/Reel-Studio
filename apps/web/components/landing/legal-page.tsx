import { SiteNav } from "./site-nav";

export function LegalPage({ title, updated, children }: { title: string; updated: string; children: React.ReactNode }) {
  return <div className="flex-1 bg-[#FCF9F4] text-[#20271C]">
    <SiteNav />
    <main className="mx-auto max-w-[720px] px-5 py-16 md:py-24">
      <h1 className="font-serif text-[44px] font-normal tracking-[-.02em] text-forest">{title}</h1>
      <p className="mt-2 text-[14px] text-[#6b7064]">Last updated {updated}</p>
      <div className="mt-10 space-y-5 text-[16.5px] leading-[1.75] text-[#3b4235] [&_h2]:mt-10 [&_h2]:text-[20px] [&_h2]:font-semibold [&_h2]:text-forest">{children}</div>
    </main>
  </div>;
}
