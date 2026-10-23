-- Reel Studio 2.0 Mode A: AI clip collections (educational series) built from the lecture outline and the
-- context-aware highlights. Episodes reference highlight_candidates; titles and topics come from the transcript.
create table public.clip_collections (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  project_id uuid not null references public.projects (id) on delete cascade,
  recording_id uuid not null references public.source_recordings (id) on delete cascade,
  created_by uuid not null references auth.users (id),
  title text not null check (char_length(title) between 1 and 120),
  description text not null default '',
  topic text not null default '',
  episodes jsonb not null default '[]',   -- [{highlight_id, title, start_s, end_s, steps[], quote, render_id?}]
  edited boolean not null default false,  -- regenerating never overwrites a collection a person has edited
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on public.clip_collections (recording_id, created_at);
create index on public.clip_collections (organization_id);
create trigger clip_collections_touch before update on public.clip_collections
  for each row execute function private.touch_updated_at();
alter table public.clip_collections enable row level security;
create policy "collections: members read" on public.clip_collections for select to authenticated
  using (private.is_member(organization_id));
revoke all on public.clip_collections from anon, authenticated;
grant select on public.clip_collections to authenticated;
grant select, insert, update, delete on public.clip_collections to service_role;
alter publication supabase_realtime add table public.clip_collections;
