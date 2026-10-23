-- Reel Studio 2.0: business campaign agent + measurable results (campaign IDs, UTM links, WhatsApp CTAs, real clicks
-- and recorded inquiries). Click and inquiry rows are created only by real visitors through the public RPCs below or
-- by a member recording an inquiry by hand; nothing is estimated or synthesised.
create table public.campaigns (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  created_by uuid not null references auth.users (id),
  code text not null unique check (code ~ '^[a-z0-9-]{3,40}$'),
  business jsonb not null,
  language text not null default 'en' check (language in ('en', 'hi', 'hinglish')),
  plan jsonb,
  provenance jsonb,
  job_id uuid references public.jobs (id) on delete set null,
  status text not null default 'queued' check (status in ('queued', 'planning', 'ready', 'failed')),
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on public.campaigns (organization_id, created_at desc);
create trigger campaigns_touch before update on public.campaigns for each row execute function private.touch_updated_at();

create table public.tracked_links (
  slug text primary key check (slug ~ '^[a-z0-9]{6,16}$'),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  campaign_id uuid references public.campaigns (id) on delete cascade,
  reel_key text not null default '',
  kind text not null check (kind in ('website', 'whatsapp')),
  destination text not null check (destination ~ '^https://'),
  clicks int not null default 0,
  created_at timestamptz not null default now()
);
create index on public.tracked_links (campaign_id);

create table public.link_clicks (
  id bigint generated always as identity primary key,
  slug text not null references public.tracked_links (slug) on delete cascade,
  organization_id uuid not null references public.organizations (id) on delete cascade,
  at timestamptz not null default now(),
  referrer_host text,
  device text check (device in ('mobile', 'desktop', 'other'))
);
create index on public.link_clicks (slug, at);

create table public.inquiries (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations (id) on delete cascade,
  campaign_id uuid references public.campaigns (id) on delete set null,
  slug text references public.tracked_links (slug) on delete set null,
  channel text not null check (channel in ('form', 'whatsapp', 'call', 'walk-in', 'other')),
  name text check (char_length(name) <= 80),
  contact text check (char_length(contact) <= 80),
  message text check (char_length(message) <= 1000),
  source text not null check (source in ('visitor', 'member')),
  recorded_by uuid references auth.users (id),
  created_at timestamptz not null default now()
);
create index on public.inquiries (organization_id, created_at desc);
create index on public.inquiries (campaign_id);

alter table public.campaigns enable row level security;
alter table public.tracked_links enable row level security;
alter table public.link_clicks enable row level security;
alter table public.inquiries enable row level security;
create policy "campaigns: members read" on public.campaigns for select to authenticated using (private.is_member(organization_id));
create policy "links: members read" on public.tracked_links for select to authenticated using (private.is_member(organization_id));
create policy "clicks: members read" on public.link_clicks for select to authenticated using (private.is_member(organization_id));
create policy "inquiries: members read" on public.inquiries for select to authenticated using (private.is_member(organization_id));
create policy "inquiries: editors record" on public.inquiries for insert to authenticated
  with check (private.has_role(organization_id, '{owner,admin,editor}') and source = 'member' and recorded_by = auth.uid());
create policy "inquiries: editors delete" on public.inquiries for delete to authenticated
  using (private.has_role(organization_id, '{owner,admin,editor}'));
revoke all on public.campaigns, public.tracked_links, public.link_clicks, public.inquiries from anon, authenticated;
grant select on public.campaigns, public.tracked_links, public.link_clicks, public.inquiries to authenticated;
grant insert, delete on public.inquiries to authenticated;
grant select, insert, update, delete on public.campaigns, public.tracked_links, public.link_clicks, public.inquiries to service_role;
alter publication supabase_realtime add table public.campaigns;

-- Public, anonymous entry points (the only way visitors touch these tables). They take a slug, never an org id.
create function public.track_click(p_slug text, p_referrer text default null, p_device text default null)
returns text language plpgsql security definer set search_path = '' as $$
declare l public.tracked_links;
begin
  select * into l from public.tracked_links where slug = p_slug;
  if not found then return null; end if;
  insert into public.link_clicks(slug, organization_id, referrer_host, device)
    values (l.slug, l.organization_id, left(p_referrer, 120),
            case when p_device in ('mobile', 'desktop') then p_device else 'other' end);
  update public.tracked_links set clicks = clicks + 1 where slug = l.slug;
  return l.destination;
end;
$$;

create function public.submit_inquiry(p_slug text, p_name text, p_contact text, p_message text)
returns boolean language plpgsql security definer set search_path = '' as $$
declare l public.tracked_links;
begin
  select * into l from public.tracked_links where slug = p_slug;
  if not found or coalesce(length(trim(p_message)), 0) = 0 then return false; end if;
  -- ponytail: a coarse per-link rate limit (60 inquiries per 10 minutes) instead of a captcha
  if (select count(*) from public.inquiries where slug = p_slug and created_at > now() - interval '10 minutes') >= 60 then
    return false;
  end if;
  insert into public.inquiries(organization_id, campaign_id, slug, channel, name, contact, message, source)
    values (l.organization_id, l.campaign_id, l.slug, 'form', left(p_name, 80), left(p_contact, 80), left(p_message, 1000), 'visitor');
  return true;
end;
$$;

create function public.link_info(p_slug text) returns jsonb language sql security definer set search_path = '' stable as $$
  select jsonb_build_object('business', c.business->>'name', 'offer', c.business->>'offer', 'kind', l.kind)
  from public.tracked_links l left join public.campaigns c on c.id = l.campaign_id where l.slug = p_slug;
$$;

revoke all on function public.track_click(text, text, text), public.submit_inquiry(text, text, text, text), public.link_info(text) from public;
grant execute on function public.track_click(text, text, text), public.submit_inquiry(text, text, text, text), public.link_info(text) to anon, authenticated;
