/** Shown instantly while a workspace page renders on the server (also what Next prefetches for each link). */
export default function Loading() {
  return <div className="animate-pulse space-y-6" aria-busy="true" aria-label="Loading">
    <div className="space-y-3"><div className="h-3 w-24 rounded bg-surface-3" /><div className="h-8 w-72 max-w-full rounded-lg bg-surface-3" /><div className="h-4 w-96 max-w-full rounded bg-surface-2" /></div>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[0, 1, 2, 3].map((i) => <div key={i} className="h-28 rounded-2xl bg-surface-2" />)}</div>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{[0, 1, 2].map((i) => <div key={i} className="h-56 rounded-2xl bg-surface-2" />)}</div>
  </div>;
}
