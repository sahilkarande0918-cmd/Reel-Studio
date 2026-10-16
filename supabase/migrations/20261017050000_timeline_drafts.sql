-- Phase 06: editor autosave. One working draft per (render being edited); editors write it directly through
-- RLS so autosave works even while the processing machine is offline. Rendering a draft creates a new
-- render_jobs row through the API (service role), so finished renders are never mutated.
create table public.timeline_drafts (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  project_id uuid not null references public.projects (id) on delete cascade,
  base_render_id uuid not null references public.render_jobs (id) on delete cascade,
  timeline jsonb not null,
  updated_by uuid references auth.users (id) default auth.uid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (base_render_id),
  check (octet_length(timeline::text) <= 2000000)
);
create index on public.timeline_drafts (organization_id, updated_at desc);
create trigger timeline_drafts_touch before update on public.timeline_drafts
  for each row execute function private.touch_updated_at();

alter table public.timeline_drafts enable row level security;
create policy "drafts: members read" on public.timeline_drafts for select to authenticated
  using (private.is_member(organization_id));
create policy "drafts: editors create" on public.timeline_drafts for insert to authenticated
  with check (private.has_role(organization_id, '{owner,admin,editor}')
    and exists (select 1 from public.render_jobs r where r.id = base_render_id
      and r.organization_id = timeline_drafts.organization_id and r.project_id = timeline_drafts.project_id));
create policy "drafts: editors update" on public.timeline_drafts for update to authenticated
  using (private.has_role(organization_id, '{owner,admin,editor}'))
  with check (private.has_role(organization_id, '{owner,admin,editor}'));
create policy "drafts: editors delete" on public.timeline_drafts for delete to authenticated
  using (private.has_role(organization_id, '{owner,admin,editor}'));

-- explicit grants (D-025): no TRUNCATE/REFERENCES/TRIGGER for API roles
revoke all on public.timeline_drafts from anon, authenticated;
grant select, insert, update, delete on public.timeline_drafts to authenticated;
grant select, insert, update, delete on public.timeline_drafts to service_role;

-- an edited render remembers what it was edited from
alter table public.render_jobs add column parent_render_id uuid references public.render_jobs (id) on delete set null;

-- Phase 08: per-reel Instagram metrics fetched by the insights worker (real API responses only).
alter table public.platform_metrics add column media jsonb not null default '[]';

-- Phase 08: what this workspace's published reels taught us. Written by the API (service role) from real
-- Instagram metrics; read by the analyze worker to tune highlight scoring (ideal length, weights).
create table public.performance_feedback (
  organization_id uuid primary key references public.organizations (id) on delete cascade,
  ideal_duration_s real check (ideal_duration_s between 20 and 90),
  weights jsonb,
  summary jsonb not null default '{}',
  updated_at timestamptz not null default now()
);
alter table public.performance_feedback enable row level security;
create policy "feedback: members read" on public.performance_feedback for select to authenticated
  using (private.is_member(organization_id));
revoke all on public.performance_feedback from anon, authenticated;
grant select on public.performance_feedback to authenticated;
grant select, insert, update, delete on public.performance_feedback to service_role;
