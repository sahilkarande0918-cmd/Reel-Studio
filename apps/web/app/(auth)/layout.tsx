import { Logo } from "@/components/landing/site-nav";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="grid min-h-svh md:grid-cols-2">
      <div className="hidden flex-col justify-between bg-surface p-10 md:flex">
        <Logo />
        <p className="max-w-[28ch] text-[32px] leading-[1.15] tracking-[-0.02em]">
          Every class you record has a minute worth posting.
        </p>
      </div>
      <div className="flex items-center justify-center px-5 py-16">
        <div className="w-full max-w-[380px]">{children}</div>
      </div>
    </main>
  );
}
