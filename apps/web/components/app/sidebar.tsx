"use client";

import { Aperture, BookA, CalendarDays, ChartNoAxesCombined, Clapperboard, Code2, FolderKanban, LayoutDashboard, LogOut, Menu, Mic, Palette, Plus, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "@/app/(auth)/actions";
import { switchWorkspace } from "@/app/onboarding/actions";
import type { Org } from "@/lib/supabase/server";

const GROUPS = [
  { label: "Create", items: [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/projects", label: "Projects", icon: FolderKanban },
    { href: "/recordings", label: "Recordings", icon: Mic },
    { href: "/topics", label: "Topic Studio", icon: Code2 },
    { href: "/editor", label: "Editor", icon: Clapperboard },
  ] },
  { label: "Brand", items: [
    { href: "/brand", label: "Brand Kits", icon: Palette },
    { href: "/glossary", label: "Glossary", icon: BookA },
  ] },
  { label: "Share", items: [
    { href: "/publishing", label: "Publish", icon: CalendarDays },
    { href: "/analytics", label: "Analytics", icon: ChartNoAxesCombined },
  ] },
  { label: "", items: [{ href: "/settings", label: "Settings", icon: Settings }] },
];

function Nav({ path }: { path: string }) {
  return <nav aria-label="Workspace navigation" className="space-y-5">
    {GROUPS.map((g, i) => <div key={i}>
      {g.label && <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-[.16em] text-[var(--rail-muted)]">{g.label}</p>}
      <ul className="space-y-0.5">{g.items.map(({ href, label, icon: Icon }) => {
        const active = path === href || path.startsWith(href + "/");
        return <li key={href}><Link href={href} aria-current={active ? "page" : undefined}
          className={`relative flex items-center gap-3 rounded-lg px-3 py-2 text-[13.5px] transition-colors ${active ? "bg-[var(--rail-active)] font-medium text-[var(--rail-ink)] before:absolute before:left-0 before:top-2 before:bottom-2 before:w-[3px] before:rounded-full before:bg-accent" : "text-[var(--rail-muted)] hover:bg-[var(--rail-active)]/70 hover:text-[var(--rail-ink)]"}`}>
          <Icon size={17} strokeWidth={1.8} className={active ? "text-accent" : ""} aria-hidden />{label}
        </Link></li>;
      })}</ul>
    </div>)}
  </nav>;
}

function Workspace({ orgs, org }: { orgs: Org[]; org: Org }) {
  return <form action={switchWorkspace}>
    <label className="sr-only" htmlFor="org-switch">Workspace</label>
    <select id="org-switch" name="org" defaultValue={org.id} onChange={(e) => e.currentTarget.form?.requestSubmit()}
      className="w-full rounded-lg border border-line px-3 py-2.5 text-[13px] font-medium">
      {orgs.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
    </select>
    <Link href="/onboarding" className="mt-2 flex items-center gap-1 px-1 text-[11px] text-[var(--rail-muted)] hover:text-[var(--rail-ink)]"><Plus size={12} aria-hidden /> New workspace</Link>
  </form>;
}

function Account({ email, org }: { email: string; org: Org }) {
  return <div className="flex items-center gap-2.5 border-t border-[var(--rail-active)] pt-4">
    <span aria-hidden className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-surface-3 text-[12px] font-semibold text-accent">{email.slice(0, 1).toUpperCase()}</span>
    <div className="min-w-0 flex-1"><span className="block truncate text-[12px]">{email}</span><span className="text-[10px] capitalize text-[var(--rail-muted)]">{org.role}</span></div>
    <form action={signOut}><button type="submit" aria-label="Sign out" title="Sign out" className="rounded-md p-2 text-[var(--rail-muted)] hover:bg-[var(--rail-active)] hover:text-[var(--rail-ink)]"><LogOut size={15} aria-hidden /></button></form>
  </div>;
}

const Logo = () => <Link href="/dashboard" className="flex items-center gap-2.5 text-[18px] font-semibold tracking-[-.04em]">
  <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent text-accent-ink"><Aperture size={19} strokeWidth={1.8} aria-hidden /></span>Reel Studio
</Link>;

/** Icon-only rail so the editor workspace gets the full width. */
function Rail({ path }: { path: string }) {
  return <aside className="studio-rail sticky top-0 hidden h-svh w-[60px] shrink-0 flex-col items-center gap-1 py-3 md:flex">
    <Link href="/dashboard" aria-label="Reel Studio dashboard" className="mb-3 grid h-9 w-9 place-items-center rounded-lg bg-accent text-accent-ink"><Aperture size={19} strokeWidth={1.8} aria-hidden /></Link>
    {GROUPS.flatMap((g) => g.items).map(({ href, label, icon: Icon }) => {
      const active = path === href || path.startsWith(href + "/");
      return <Link key={href} href={href} title={label} aria-label={label} aria-current={active ? "page" : undefined}
        className={`grid h-10 w-10 place-items-center rounded-lg transition-colors ${active ? "bg-[var(--rail-active)] text-accent" : "text-[var(--rail-muted)] hover:bg-[var(--rail-active)] hover:text-[var(--rail-ink)]"}`}><Icon size={18} strokeWidth={1.8} aria-hidden /></Link>;
    })}
  </aside>;
}

export function Sidebar({ orgs, org, email }: { orgs: Org[]; org: Org; email: string }) {
  const path = usePathname();
  if (path.startsWith("/editor/")) return <Rail path={path} />;
  return <>
    <aside className="studio-rail hidden w-[236px] shrink-0 flex-col gap-6 px-4 py-5 md:sticky md:top-0 md:flex md:h-svh md:overflow-y-auto">
      <div className="px-1"><Logo /></div>
      <Workspace orgs={orgs} org={org} />
      <Nav path={path} />
      <div className="mt-auto"><Account email={email} org={org} /></div>
    </aside>
    {/* Phones and small tablets: the same navigation in a native disclosure. */}
    <details className="studio-rail group md:hidden" key={path}>
      <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3"><Logo /><span className="rounded-md p-2 hover:bg-[var(--rail-active)]"><Menu size={20} aria-label="Open navigation" /></span></summary>
      <div className="space-y-5 border-t border-[var(--rail-active)] px-4 py-4"><Workspace orgs={orgs} org={org} /><Nav path={path} /><Account email={email} org={org} /></div>
    </details>
  </>;
}
