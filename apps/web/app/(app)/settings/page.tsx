import Link from "next/link";
import { ArrowRight, BookA, CalendarDays, Palette, Server, Users } from "lucide-react";
import { BackendBadge } from "@/components/app/backend-badge";
import { PageHeader } from "@/components/app/page-header";
import { VoiceProfiles } from "@/components/settings/voice-profiles";
import { requireOrg } from "@/lib/supabase/server";

export default async function SettingsPage() {
  const { supabase, org, email, userId } = await requireOrg();
  const { data: members, error } = await supabase.from("organization_members").select("user_id, role, created_at").eq("organization_id", org.id).order("created_at");
  const links = [
    { href: "/brand", icon: Palette, title: "Brand Kits", body: "Colours, fonts, logo, captions, intro and outro." },
    { href: "/glossary", icon: BookA, title: "Technical glossary", body: "Terms the transcriber should always spell correctly." },
    { href: "/publishing", icon: CalendarDays, title: "Instagram connection", body: "Connect, reconnect or disconnect the publishing account." },
  ];
  return (
    <div className="max-w-[1100px] space-y-7">
      <PageHeader eyebrow={org.name} title="Settings">Workspace, people, processing engine and connected services.</PageHeader>
      <div className="grid gap-5 lg:grid-cols-2">
        <section className="studio-panel p-6">
          <h2 className="text-[15px] font-semibold">Workspace</h2>
          <dl className="mt-4 grid grid-cols-[120px_1fr] gap-y-3 text-[13.5px]">
            <dt className="text-muted">Name</dt><dd className="font-semibold">{org.name}</dd>
            <dt className="text-muted">Address</dt><dd className="font-mono text-[12.5px]">{org.slug}</dd>
            <dt className="text-muted">Your role</dt><dd className="capitalize">{org.role}</dd>
            <dt className="text-muted">Signed in as</dt><dd className="truncate">{email}</dd>
          </dl>
        </section>
        <section className="studio-panel p-6">
          <h2 className="flex items-center gap-2 text-[15px] font-semibold"><Server size={17} className="text-accent" aria-hidden /> Processing engine</h2>
          <p className="mt-2 text-[13.5px] leading-6 text-muted">Transcription, AI generation and rendering run on the studio&apos;s own GPU machine, so there is no cloud cost. The app stays usable when it is offline; jobs wait in the queue.</p>
          <div className="mt-4"><BackendBadge /></div>
        </section>
      </div>
      <section className="studio-panel p-6">
        <h2 className="flex items-center gap-2 text-[15px] font-semibold"><Users size={17} className="text-accent" aria-hidden /> Members</h2>
        {error ? <p className="mt-3 text-[13px] text-danger">Members could not load.</p> : <ul className="mt-3 divide-y divide-line">{members?.map((m) => <li key={m.user_id} className="flex items-center justify-between py-3 text-[13.5px]"><span>{m.user_id === userId ? `${email} (you)` : `Member ${m.user_id.slice(0, 8)}`}</span><span className="studio-pill capitalize">{m.role}</span></li>)}</ul>}
      </section>
      {org.role !== "viewer" && <VoiceProfiles orgId={org.id} />}
      <div className="grid gap-4 md:grid-cols-3">{links.map(({ href, icon: Icon, title, body }) => <Link key={href} href={href} className="studio-panel group p-5 transition-colors hover:border-accent"><Icon size={20} className="text-accent" aria-hidden /><h3 className="mt-4 flex items-center justify-between text-[14px] font-semibold">{title}<ArrowRight size={15} className="text-muted transition-transform group-hover:translate-x-1" aria-hidden /></h3><p className="mt-1 text-[12.5px] leading-5 text-muted">{body}</p></Link>)}</div>
    </div>
  );
}
