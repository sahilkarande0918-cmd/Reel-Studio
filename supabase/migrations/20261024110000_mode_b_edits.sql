-- Reel Studio 2.0 Mode B: uploaded media (clips, images, music, reference reels) and AI edit generations.
-- Files live on the processing machine's disk (DATA_DIR/orgs/<org>/assets/<id>/); only metadata is stored here.

create table public.media_assets (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  project_id uuid not null references public.projects (id) on delete cascade,
  created_by uuid not null references auth.users (id),
  kind text not null check (kind in ('clip', 'image', 'audio', 'reference')),
  filename text not null check (char_length(filename) between 1 and 255),
  size_bytes bigint not null check (size_bytes > 0),
  status text not null default 'uploading'
    check (status in ('uploading', 'uploaded', 'analyzing', 'ready', 'failed')),
  sha256 text,                 -- duplicate detection inside a project
  duration_s real,
  width int,
  height int,
  fps real,
  probe jsonb,
  analysis jsonb,              -- clip moments / beat grid / reference style profile
  position int not null default 0,
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on public.media_assets (project_id, position, created_at);
create index on public.media_assets (organization_id);
create trigger media_assets_touch before update on public.media_assets
  for each row execute function private.touch_updated_at();

create table public.edit_generations (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  project_id uuid not null references public.projects (id) on delete cascade,
  created_by uuid not null references auth.users (id),
  prompt text not null check (char_length(prompt) between 1 and 2000),
  settings jsonb not null,
  brand_snapshot jsonb,
  director jsonb,              -- creative treatment + storyboard (LLM or rule-based, recorded which)
  plan jsonb,                  -- executable edit plan (segments, beats, effects, cues)
  qa jsonb,                    -- measured checks on the rendered file
  render_id uuid references public.render_jobs (id) on delete set null,
  job_id uuid not null references public.jobs (id),
  status text not null default 'queued'
    check (status in ('queued', 'planning', 'rendering', 'ready', 'failed', 'cancelled')),
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on public.edit_generations (project_id, created_at desc);
create index on public.edit_generations (organization_id);
create unique index edit_one_active on public.edit_generations (project_id)
  where status in ('queued', 'planning', 'rendering');
create trigger edit_generations_touch before update on public.edit_generations
  for each row execute function private.touch_updated_at();

alter table public.media_assets enable row level security;
alter table public.edit_generations enable row level security;
create policy "assets: members read" on public.media_assets for select to authenticated
  using (private.is_member(organization_id));
create policy "edits: members read" on public.edit_generations for select to authenticated
  using (private.is_member(organization_id));
-- explicit grants (D-025): written by the processing API / worker only
revoke all on public.media_assets, public.edit_generations from anon, authenticated;
grant select on public.media_assets, public.edit_generations to authenticated;
grant select, insert, update, delete on public.media_assets, public.edit_generations to service_role;

alter publication supabase_realtime add table public.media_assets;
alter publication supabase_realtime add table public.edit_generations;

-- Atomic queue insert with duplicate-click protection. Only the authenticated backend calls it.
create function public.enqueue_edit_generation(
  p_project uuid, p_user uuid, p_prompt text, p_settings jsonb, p_brand jsonb default null
) returns jsonb language plpgsql set search_path = '' as $$
declare p public.projects; g public.edit_generations; gid uuid := gen_random_uuid(); jid uuid;
begin
  select * into p from public.projects where id = p_project for update;
  if not found or p.mode::text <> 'edit' or not exists (
    select 1 from public.organization_members m where m.organization_id = p.organization_id
      and m.user_id = p_user and m.role in ('owner','admin','editor')
  ) then raise exception 'Project not found or access denied'; end if;
  select * into g from public.edit_generations where project_id = p_project
    and status in ('queued','planning','rendering') limit 1;
  if found then
    return jsonb_build_object('generation_id', g.id, 'job_id', g.job_id, 'existing', true);
  end if;
  insert into public.jobs(organization_id,project_id,created_by,job_type,payload,current_stage)
    values(p.organization_id,p.id,p_user,'edit',jsonb_build_object('generation_id',gid),'queued')
    returning id into jid;
  insert into public.edit_generations(id,organization_id,project_id,created_by,prompt,settings,brand_snapshot,job_id)
    values(gid,p.organization_id,p.id,p_user,p_prompt,p_settings,p_brand,jid);
  return jsonb_build_object('generation_id',gid,'job_id',jid);
end;
$$;
revoke all on function public.enqueue_edit_generation(uuid,uuid,text,jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.enqueue_edit_generation(uuid,uuid,text,jsonb,jsonb) to service_role;

-- A failed/cancelled/requeued job must not leave a generation stuck as active.
create function private.sync_edit_job() returns trigger language plpgsql security definer
set search_path = '' as $$
begin
  if new.job_type = 'edit' then
    update public.edit_generations set
      status = case new.status::text when 'failed' then 'failed' when 'cancelled' then 'cancelled'
        when 'queued' then 'queued' else status end,
      error = new.error
    where job_id = new.id and new.status::text in ('failed','cancelled','queued');
  end if;
  return new;
end;
$$;
revoke all on function private.sync_edit_job() from public,anon,authenticated;
create trigger sync_edit_job after update of status on public.jobs
  for each row execute function private.sync_edit_job();
