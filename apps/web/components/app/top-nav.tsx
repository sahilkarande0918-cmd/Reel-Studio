"use client";

import { Bell, ChevronDown, LogOut, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { signOut } from "@/app/(auth)/actions";
import { BackendBadge } from "@/components/app/backend-badge";
import type { Org } from "@/lib/supabase/server";

export function TopNav({
  org,
  email,
}: {
  org: Org;
  email: string;
}) {
  const [profileOpen, setProfileOpen] = useState(false);
  const displayName = email.split("@")[0].replace(/[._-]/g, " ") || "Creator";
  const capitalizedName = displayName
    .split(" ")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-4 border-b border-[#E7E5DE] bg-[#FCF9F4]/90 px-4 backdrop-blur-md sm:px-6 lg:px-8">
      {/* Search Input matching reference */}
      <div className="flex flex-1 items-center max-w-lg">
        <div className="relative w-full">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-[#707267]">
            <Search size={15} />
          </div>
          <input
            type="text"
            placeholder="Search your projects, videos, or templates..."
            className="w-full rounded-xl border border-[#E7E5DE] bg-[#FCF9F4] py-2 pl-9 pr-12 text-[13px] text-[#1D2618] placeholder:text-[#A3A094] transition-all focus:border-[#3C462F] focus:bg-white focus:outline-none focus:ring-1 focus:ring-[#3C462F]"
          />
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
            <kbd className="inline-flex items-center rounded border border-[#E7E5DE] bg-white px-1.5 py-0.5 text-[10px] font-medium text-[#707267]">
              ⌘ K
            </kbd>
          </div>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3.5">
        <BackendBadge />

        {/* Notifications */}
        <button
          type="button"
          aria-label="Notifications"
          className="relative grid h-9 w-9 place-items-center rounded-xl text-[#707267] transition-colors hover:bg-[#F6F3EC] hover:text-[#1D2618]"
        >
          <Bell size={18} />
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-[#3C462F] ring-2 ring-[#FCF9F4]" />
        </button>

        {/* User Profile */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setProfileOpen(!profileOpen)}
            className="flex items-center gap-2.5 rounded-xl p-1 transition-colors hover:bg-[#F6F3EC]"
          >
            <div className="grid h-8 w-8 place-items-center rounded-full bg-[#3C462F] text-[12px] font-semibold text-[#FCF9F4] overflow-hidden">
              <span className="uppercase">{email.slice(0, 1)}</span>
            </div>
            <div className="hidden text-left sm:block">
              <span className="block truncate text-[13px] font-semibold text-[#1D2618] leading-tight max-w-[120px]">
                {capitalizedName}
              </span>
              <span className="block text-[11px] text-[#707267] capitalize leading-tight">
                {org.role === "owner" ? "Creator" : org.role}
              </span>
            </div>
            <ChevronDown size={14} className="text-[#707267]" />
          </button>

          {profileOpen && (
            <div className="absolute right-0 mt-2 w-52 rounded-xl border border-[#E7E5DE] bg-[#FCF9F4] p-1.5 shadow-lg">
              <div className="border-b border-[#E7E5DE] px-3 py-2">
                <p className="text-[12px] font-semibold text-[#1D2618]">
                  {org.name}
                </p>
                <p className="truncate text-[11px] text-[#707267]">{email}</p>
              </div>
              <div className="py-1">
                <Link
                  href="/settings"
                  onClick={() => setProfileOpen(false)}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-[12.5px] text-[#1D2618] hover:bg-[#F6F3EC]"
                >
                  Settings
                </Link>
                <Link
                  href="/projects"
                  onClick={() => setProfileOpen(false)}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-[12.5px] text-[#1D2618] hover:bg-[#F6F3EC]"
                >
                  Projects
                </Link>
              </div>
              <div className="border-t border-[#E7E5DE] pt-1">
                <form action={signOut}>
                  <button
                    type="submit"
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-[12.5px] text-danger hover:bg-danger/10"
                  >
                    <LogOut size={13} /> Sign out
                  </button>
                </form>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
