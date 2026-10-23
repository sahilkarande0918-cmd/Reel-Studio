-- Reel Studio 2.0: consented, reusable voice profiles. The voice sample and generated previews live on the processing
-- machine (DATA_DIR/orgs/<org>/voices/<id>/), never in Postgres or git. A profile is usable only by the person who
-- recorded and authorised it (enforced by the API); workspace members can see that it exists.
create table public.voice_profiles (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  created_by uuid not null references auth.users (id) on delete cascade,
  name text not null check (char_length(name) between 1 and 60),
  status text not null default 'ready' check (status in ('ready', 'failed')),
  consent_statement text not null,
  consent_at timestamptz not null,
  sample_seconds real,
  quality jsonb not null default '{}',
  pronunciations jsonb not null default '{}',   -- {"SQL": "sequel"}: whole-word replacements before synthesis
  engine text not null default 'chatterbox-multilingual',
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on public.voice_profiles (organization_id, created_at desc);
create trigger voice_profiles_touch before update on public.voice_profiles
  for each row execute function private.touch_updated_at();
alter table public.voice_profiles enable row level security;
create policy "voices: members read" on public.voice_profiles for select to authenticated
  using (private.is_member(organization_id));
revoke all on public.voice_profiles from anon, authenticated;
grant select on public.voice_profiles to authenticated;
grant select, insert, update, delete on public.voice_profiles to service_role;
