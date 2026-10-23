-- Reel Studio 2.0 tables: isolation, write paths and public tracking functions. Run: pnpm exec supabase test db
begin;
create extension if not exists pgtap with schema extensions;
select plan(20);

insert into auth.users (id, email, raw_user_meta_data) values
  ('31111111-1111-1111-1111-111111111111', 'v2a@test.local', '{"full_name":"A"}'),
  ('32222222-2222-2222-2222-222222222222', 'v2b@test.local', '{"full_name":"B"}');

create function pg_temp.login(uid uuid) returns void language sql as $$
  select set_config('request.jwt.claims', json_build_object('sub', uid, 'role', 'authenticated')::text, true);
  set local role authenticated;
$$;

select pg_temp.login('31111111-1111-1111-1111-111111111111');
select public.create_organization('V2 Alpha', 'v2-alpha');
select lives_ok($$ insert into public.projects (organization_id, name, mode, created_by)
  select id, 'Edit project', 'edit', auth.uid() from public.organizations where slug = 'v2-alpha' $$, 'members create Prompt → Edit projects');
reset role;
select pg_temp.login('32222222-2222-2222-2222-222222222222');
select public.create_organization('V2 Beta', 'v2-beta');
reset role;

select set_config('test.v2alpha', (select id::text from public.organizations where slug = 'v2-alpha'), true);

-- rows written by the backend (service role)
insert into public.media_assets (organization_id, project_id, created_by, kind, filename, size_bytes)
  select p.organization_id, p.id, p.created_by, 'clip', 'a.mp4', 10 from public.projects p where p.name = 'Edit project';
insert into public.campaigns (organization_id, created_by, code, business)
  select id, '31111111-1111-1111-1111-111111111111', 'v2-test-0001', '{"name":"Shop","offer":"10% off"}' from public.organizations where slug = 'v2-alpha';
insert into public.tracked_links (slug, organization_id, campaign_id, kind, destination)
  select 'abc12345', c.organization_id, c.id, 'whatsapp', 'https://wa.me/911234567890' from public.campaigns c where code = 'v2-test-0001';
insert into public.voice_profiles (organization_id, created_by, name, consent_statement, consent_at)
  select id, '31111111-1111-1111-1111-111111111111', 'My voice', 'consent', now() from public.organizations where slug = 'v2-alpha';

-- members read their org; outsiders see nothing
select pg_temp.login('31111111-1111-1111-1111-111111111111');
select is((select count(*)::int from public.media_assets), 1, 'member sees media assets');
select is((select count(*)::int from public.campaigns), 1, 'member sees campaigns');
select is((select count(*)::int from public.voice_profiles), 1, 'member sees voice profiles');
select throws_ok($$ insert into public.media_assets (organization_id, project_id, created_by, kind, filename, size_bytes)
  select organization_id, project_id, created_by, 'clip', 'x.mp4', 1 from public.media_assets $$, '42501', null,
  'members cannot write media assets directly (backend only)');
select throws_ok($$ update public.campaigns set code = 'hijack' $$, '42501', null, 'members cannot rewrite campaigns');
select throws_ok($$ insert into public.link_clicks (slug, organization_id) select slug, organization_id from public.tracked_links $$,
  '42501', null, 'members cannot fabricate clicks');
select lives_ok($$ insert into public.inquiries (organization_id, campaign_id, channel, message, source, recorded_by)
  select organization_id, id, 'walk-in', 'asked about sizes', 'member', auth.uid() from public.campaigns $$, 'editors record a real inquiry');
select throws_ok($$ insert into public.inquiries (organization_id, channel, message, source, recorded_by)
  select organization_id, 'form', 'fake', 'visitor', auth.uid() from public.campaigns $$, '42501', null,
  'members cannot pose as public visitors');
reset role;

select pg_temp.login('32222222-2222-2222-2222-222222222222');
select is((select count(*)::int from public.media_assets), 0, 'outsider sees no media assets');
select is((select count(*)::int from public.campaigns), 0, 'outsider sees no campaigns');
select is((select count(*)::int from public.tracked_links), 0, 'outsider sees no links');
select is((select count(*)::int from public.inquiries), 0, 'outsider sees no inquiries');
select is((select count(*)::int from public.voice_profiles), 0, 'outsider sees no voice profiles');
select throws_ok($$ insert into public.inquiries (organization_id, channel, message, source, recorded_by)
  values (current_setting('test.v2alpha')::uuid, 'call', 'x', 'member', auth.uid()) $$, '42501', null,
  'outsiders cannot record inquiries into another org');
reset role;

-- public visitors: clicks and form inquiries only through the slug functions
set local role anon;
select is(public.track_click('abc12345', 'instagram.com', 'mobile'), 'https://wa.me/911234567890', 'a click redirects to the destination');
select is(public.track_click('nope0000'), null, 'unknown slugs record nothing');
select ok(public.submit_inquiry('abc12345', 'Riya', '98xxxx', 'Do you have size 9?'), 'a visitor can send an inquiry');
select throws_ok($$ select count(*) from public.link_clicks $$, '42501', null, 'anon cannot read clicks');
reset role;
select is((select clicks from public.tracked_links where slug = 'abc12345'), 1, 'click counter incremented once');

select * from finish();
rollback;
