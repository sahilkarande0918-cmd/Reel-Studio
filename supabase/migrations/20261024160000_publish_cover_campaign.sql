-- Instagram 2.0: chosen cover frame (Graph API thumb_offset, ms into the video) and the campaign a post belongs to
alter table public.publish_jobs add column cover_ms int check (cover_ms between 0 and 900000);
alter table public.publish_jobs add column campaign_id uuid references public.campaigns (id) on delete set null;
