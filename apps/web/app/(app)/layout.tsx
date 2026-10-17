import { Providers } from "@/components/app/providers";
import { Sidebar } from "@/components/app/sidebar";
import { TopNav } from "@/components/app/top-nav";
import { requireOrg } from "@/lib/supabase/server";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const { orgs, org, email } = await requireOrg();
  return (
    <Providers>
      <div className="studio-app flex min-h-svh flex-col md:flex-row bg-[#FCF9F4]">
        <Sidebar orgs={orgs} org={org} email={email} />
        <div className="min-w-0 flex-1 flex flex-col">
          <TopNav org={org} email={email} />
          <main className="mx-auto w-full max-w-[1520px] p-4 sm:p-6 lg:p-7 flex-1">{children}</main>
        </div>
      </div>
    </Providers>
  );
}
