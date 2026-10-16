import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { ProjectPreview } from "./project-preview";

export type ProjectRow = { id: string; name: string; mode: string; status: string; updated_at: string };

export function statusTone(status: string) {
  if (/fail|error/.test(status)) return "!bg-danger/12 !text-danger";
  if (/ready|done|rendered|published/.test(status)) return "!bg-success/12 !text-success";
  return "";
}

export function ProjectGrid({ projects, cols = "sm:grid-cols-2 xl:grid-cols-3" }: { projects: ProjectRow[]; cols?: string }) {
  return <div className={`grid gap-4 ${cols}`}>
    {projects.map((p) => <Link key={p.id} href={`/projects/${p.id}`} className="studio-panel group overflow-hidden transition-[border-color,transform,box-shadow] duration-200 hover:-translate-y-0.5 hover:border-[#3a404e] hover:shadow-[0_12px_32px_-20px_rgba(0,0,0,.9)]">
      <ProjectPreview projectId={p.id} mode={p.mode} />
      <div className="p-4">
        <div className="flex items-start justify-between gap-3"><h3 className="min-w-0 truncate text-[15px] font-semibold tracking-[-.02em] group-hover:text-accent">{p.name}</h3><ArrowUpRight size={16} className="shrink-0 text-muted transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" aria-hidden /></div>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2"><span className={`studio-pill ${statusTone(p.status)}`}>{p.status.replaceAll("_", " ")}</span><time dateTime={p.updated_at} className="text-[11px] text-muted">{new Date(p.updated_at).toLocaleDateString("en", { month: "short", day: "numeric" })}</time></div>
      </div>
    </Link>)}
  </div>;
}
