"use client";

import {
  BarChart2,
  ChevronDown,
  Crown,
  Film,
  Folder,
  Home,
  LayoutTemplate,
  Leaf,
  LogOut,
  Menu,
  Palette,
  Plus,
  Settings,
  Share2,
  Sparkles,
  Users,
  Video,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { signOut } from "@/app/(auth)/actions";
import { switchWorkspace } from "@/app/onboarding/actions";
import type { Org } from "@/lib/supabase/server";

const MAIN_NAV = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/topics", label: "Create", icon: Film },
  { href: "/projects", label: "Projects", icon: Folder },
  { href: "/topics#templates", label: "Templates", icon: LayoutTemplate },
  { href: "/recordings", label: "Media Library", icon: Video },
  { href: "/brand", label: "Brand Kit", icon: Palette },
  { href: "/glossary", label: "AI Tools", icon: Sparkles },
];

const SECONDARY_NAV = [
  { href: "/analytics", label: "Analytics", icon: BarChart2 },
  { href: "/publishing#audience", label: "Audience", icon: Users },
  { href: "/publishing#integrations", label: "Integrations", icon: Share2 },
  { href: "/settings", label: "Settings", icon: Settings },
];

function NavLink({
  href,
  label,
  icon: Icon,
  active,
}: {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string; size?: number }>;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`group flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-[14px] font-medium transition-all ${
        active
          ? "bg-[#3C462F] text-[#FCF9F4] shadow-sm"
          : "text-[#A3A694] hover:bg-[#283321] hover:text-[#FCF9F4]"
      }`}
    >
      <Icon
        size={18}
        className={`transition-colors ${
          active ? "text-[#FCF9F4]" : "text-[#A3A694] group-hover:text-[#FCF9F4]"
        }`}
      />
      <span>{label}</span>
    </Link>
  );
}

function ProPlanCard() {
  return (
    <div className="rounded-2xl border border-[rgba(255,255,255,0.08)] bg-[#172010] p-4 text-white">
      <div className="flex items-center gap-2">
        <Crown className="h-4 w-4 text-[#F2B544]" fill="#F2B544" aria-hidden />
        <span className="text-[13px] font-semibold text-[#FCF9F4]">Pro Plan</span>
      </div>
      <p className="mt-1 text-[11px] text-[#A3A694]">Unlimited creations</p>
      <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-[#2A3522]">
        <div className="h-full w-3/4 rounded-full bg-[#647457]" />
      </div>
      <button
        type="button"
        className="mt-3.5 w-full rounded-xl bg-[#FCF9F4] py-2 text-center text-[13px] font-semibold text-[#1D2618] transition-colors hover:bg-white active:scale-[0.98]"
      >
        Upgrade Plan
      </button>
    </div>
  );
}

function WorkspaceSwitcher({
  orgs,
  org,
}: {
  orgs: Org[];
  org: Org;
  email: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative pt-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between rounded-xl px-2.5 py-2 text-left transition-colors hover:bg-[#283321]"
      >
        <div className="flex items-center gap-2.5 overflow-hidden">
          <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-[#3C462F] text-[12px] font-semibold text-[#FCF9F4]">
            {org.name.slice(0, 1).toUpperCase()}
          </span>
          <div className="min-w-0">
            <span className="block truncate text-[12.5px] font-medium text-[#FCF9F4]">
              {org.name}
            </span>
            <span className="block truncate text-[10.5px] text-[#A3A694]">
              {org.role}
            </span>
          </div>
        </div>
        <ChevronDown size={14} className="text-[#A3A694]" />
      </button>

      {open && (
        <div className="absolute bottom-full left-0 mb-2 w-full rounded-xl border border-[rgba(255,255,255,0.1)] bg-[#172010] p-2 shadow-xl backdrop-blur-md">
          <p className="px-2 py-1 text-[10.5px] font-semibold uppercase tracking-wider text-[#A3A694]">
            Workspaces
          </p>
          <div className="space-y-1">
            {orgs.map((o) => (
              <form key={o.id} action={switchWorkspace}>
                <input type="hidden" name="org" value={o.id} />
                <button
                  type="submit"
                  className={`w-full rounded-lg px-2 py-1.5 text-left text-[12px] transition-colors ${
                    o.id === org.id
                      ? "bg-[#3C462F] font-medium text-[#FCF9F4]"
                      : "text-[#A3A694] hover:bg-[#283321] hover:text-[#FCF9F4]"
                  }`}
                >
                  {o.name}
                </button>
              </form>
            ))}
          </div>
          <div className="mt-2 border-t border-[rgba(255,255,255,0.08)] pt-2">
            <Link
              href="/onboarding"
              className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-[11.5px] text-[#A3A694] hover:text-[#FCF9F4]"
            >
              <Plus size={13} /> New workspace
            </Link>
            <form action={signOut} className="mt-1">
              <button
                type="submit"
                className="flex w-full items-center gap-1.5 rounded-lg px-2 py-1 text-[11.5px] text-danger/80 hover:text-danger"
              >
                <LogOut size={13} /> Sign out
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

/** Icon-only rail for dense editor workspace */
function Rail({ path }: { path: string }) {
  const allNav = [...MAIN_NAV, ...SECONDARY_NAV];
  return (
    <aside className="sticky top-0 hidden h-svh w-[64px] shrink-0 flex-col items-center gap-2 border-r border-[rgba(255,255,255,0.06)] bg-[#1D2618] py-4 md:flex">
      <Link
        href="/dashboard"
        aria-label="Reel Studio dashboard"
        className="mb-4 grid h-10 w-10 place-items-center rounded-xl bg-[#3C462F] text-[#FCF9F4]"
      >
        <Leaf size={20} className="text-[#98A886]" fill="#98A886" />
      </Link>
      <div className="flex flex-1 flex-col gap-1">
        {allNav.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/dashboard"
              ? path === "/dashboard"
              : path === href || path.startsWith(href.split("#")[0] + "/");
          return (
            <Link
              key={label}
              href={href}
              title={label}
              aria-label={label}
              className={`grid h-10 w-10 place-items-center rounded-xl transition-colors ${
                active
                  ? "bg-[#3C462F] text-[#FCF9F4]"
                  : "text-[#A3A694] hover:bg-[#283321] hover:text-[#FCF9F4]"
              }`}
            >
              <Icon size={18} />
            </Link>
          );
        })}
      </div>
    </aside>
  );
}

export function Sidebar({
  orgs,
  org,
  email,
}: {
  orgs: Org[];
  org: Org;
  email: string;
}) {
  const path = usePathname();
  if (path.startsWith("/editor/")) return <Rail path={path} />;

  return (
    <>
      <aside className="hidden w-[240px] shrink-0 flex-col justify-between border-r border-[rgba(255,255,255,0.06)] bg-[#1D2618] px-4 py-6 md:sticky md:top-0 md:flex md:h-svh md:overflow-y-auto">
        <div className="space-y-6">
          {/* Logo */}
          <Link
            href="/dashboard"
            className="flex items-center gap-2.5 px-2 text-white"
          >
            <span className="flex h-7 w-7 items-center justify-center">
              <Leaf
                size={22}
                className="text-[#98A886]"
                fill="#98A886"
                aria-hidden
              />
            </span>
            <span className="font-serif text-[21px] font-medium tracking-tight text-[#FCF9F4]">
              Reel Studio
            </span>
          </Link>

          {/* Primary Nav */}
          <nav className="space-y-1">
            {MAIN_NAV.map(({ href, label, icon }) => {
              const active =
                href === "/dashboard"
                  ? path === "/dashboard"
                  : path === href || path.startsWith(href.split("#")[0] + "/");
              return (
                <NavLink
                  key={label}
                  href={href}
                  label={label}
                  icon={icon}
                  active={active}
                />
              );
            })}

            <div className="my-3 mx-2 border-t border-[rgba(255,255,255,0.08)]" />

            {SECONDARY_NAV.map(({ href, label, icon }) => {
              const active =
                path === href || path.startsWith(href.split("#")[0] + "/");
              return (
                <NavLink
                  key={label}
                  href={href}
                  label={label}
                  icon={icon}
                  active={active}
                />
              );
            })}
          </nav>
        </div>

        {/* Bottom Section */}
        <div className="space-y-3 pt-4">
          <ProPlanCard />
          <WorkspaceSwitcher orgs={orgs} org={org} email={email} />
        </div>
      </aside>

      {/* Mobile drawer */}
      <details className="group border-b border-[#E7E5DE] bg-[#1D2618] text-[#FCF9F4] md:hidden" key={path}>
        <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3.5">
          <Link href="/dashboard" className="flex items-center gap-2.5 text-white">
            <Leaf size={20} className="text-[#98A886]" fill="#98A886" />
            <span className="font-serif text-[19px] font-medium text-[#FCF9F4]">
              Reel Studio
            </span>
          </Link>
          <span className="rounded-lg p-1.5 text-[#A3A694] hover:bg-[#283321]">
            <Menu size={22} aria-label="Open navigation" />
          </span>
        </summary>
        <div className="space-y-4 border-t border-[rgba(255,255,255,0.08)] px-4 py-4">
          <nav className="space-y-1">
            {MAIN_NAV.concat(SECONDARY_NAV).map(({ href, label, icon }) => {
              const active =
                href === "/dashboard"
                  ? path === "/dashboard"
                  : path === href || path.startsWith(href.split("#")[0] + "/");
              return (
                <NavLink
                  key={label}
                  href={href}
                  label={label}
                  icon={icon}
                  active={active}
                />
              );
            })}
          </nav>
          <ProPlanCard />
          <WorkspaceSwitcher orgs={orgs} org={org} email={email} />
        </div>
      </details>
    </>
  );
}
