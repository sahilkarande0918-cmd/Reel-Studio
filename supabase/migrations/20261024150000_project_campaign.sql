-- a project made from a campaign idea remembers it (prompt prefill, campaign-aware publishing and results)
alter table public.projects add column campaign_id uuid references public.campaigns (id) on delete set null;
alter table public.projects add column campaign_reel text check (campaign_reel ~ '^[a-z0-9-]{1,20}$');
