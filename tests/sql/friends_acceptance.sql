-- Synthetic identities only. Every row is rolled back at the end.
begin;
insert into auth.users(id) values('f1000000-0000-0000-0000-000000000001'),('f1000000-0000-0000-0000-000000000002'),('f1000000-0000-0000-0000-000000000003');
insert into public.profiles(id,username,university,languages,image_path) select id,'friend_test_'||right(id::text,1),'Example University',array['English'],id::text||'/test.png' from auth.users where id in ('f1000000-0000-0000-0000-000000000001','f1000000-0000-0000-0000-000000000002','f1000000-0000-0000-0000-000000000003');
set local role authenticated;
select set_config('request.jwt.claim.sub','f1000000-0000-0000-0000-000000000001',true);
do $$declare r jsonb; begin
 r:=public.friends_action('list');
 assert r->>'code' ~ '^[A-HJ-NP-Z2-9]{8}$','code format';
 perform set_config('test.code_a',r->>'code',true);
 assert public.friends_action('list')->>'code'=r->>'code','code stability';
 assert public.friends_action('request',r->>'code') ? 'error','self request';
 assert public.friends_action('lookup','ZZZZZZZZ') ? 'error','unknown code';
 assert (select count(*) from public.friend_edges)=0,'rejection changed relationships';
end $$;
select set_config('request.jwt.claim.sub','f1000000-0000-0000-0000-000000000002',true);
do $$declare r jsonb; begin
 r:=public.friends_action('list'); perform set_config('test.code_b',r->>'code',true);
 assert r->>'code'<>current_setting('test.code_a'),'unique codes';
 assert (select count(*) from public.friend_codes)=1,'code enumeration';
 assert (public.friends_action('lookup',current_setting('test.code_a'))->'person')->>'username'='friend_test_1','lookup';
 assert not ((public.friends_action('lookup',current_setting('test.code_a'))->'person') ? 'email'),'email exposed';
 assert not(public.friends_action('request',current_setting('test.code_a')) ? 'error'),'request';
 assert public.friends_action('request',current_setting('test.code_a')) ? 'error','duplicate request';
 r:=public.friends_action('list'); perform set_config('test.edge',r->'sent'->0->>'id',true);
 assert public.friends_action('accept',current_setting('test.edge')) ? 'error','sender accepted own request';
end $$;
select set_config('request.jwt.claim.sub','f1000000-0000-0000-0000-000000000003',true);
do $$begin
 assert (select count(*) from public.friend_edges)=0,'third party read';
 assert public.friends_action('accept',current_setting('test.edge')) ? 'error','third party accepted';
 begin delete from public.friend_edges; raise exception 'Direct delete permitted'; exception when insufficient_privilege then null; end;
end $$;
select set_config('request.jwt.claim.sub','f1000000-0000-0000-0000-000000000001',true);
do $$declare r jsonb;begin
 assert public.friends_action('request',current_setting('test.code_b')) ? 'error','crossed request';
 assert not(public.friends_action('accept',current_setting('test.edge')) ? 'error'),'recipient acceptance';
 r:=public.friends_action('list'); assert jsonb_array_length(r->'friends')=1,'friend count';
 assert not(public.friends_action('remove',current_setting('test.edge')) ? 'error'),'remove';
 r:=public.friends_action('create_invite'); perform set_config('test.token',r->>'token',true);
 assert length(r->>'token')=48,'token strength';
 assert public.friends_action('accept_invite',r->>'token') ? 'error','self invite';
end $$;
select set_config('request.jwt.claim.sub','f1000000-0000-0000-0000-000000000002',true);
do $$declare r jsonb;begin
 assert jsonb_array_length(public.friends_action('list')->'friends')=0,'remove mutual';
 r:=public.friends_action('preview_invite',current_setting('test.token'));
 assert r->'person'->>'username'='friend_test_1','preview';
 assert jsonb_array_length(public.friends_action('list')->'friends')=0,'preview creates friendship';
 assert not(public.friends_action('accept_invite',current_setting('test.token')) ? 'error'),'accept invite';
 assert not(public.friends_action('accept_invite',current_setting('test.token')) ? 'error'),'repeat acceptance';
 assert jsonb_array_length(public.friends_action('list')->'friends')=1,'duplicate friendship';
end $$;
select set_config('request.jwt.claim.sub','f1000000-0000-0000-0000-000000000001',true);
select public.friends_action('revoke_invite');
select set_config('request.jwt.claim.sub','f1000000-0000-0000-0000-000000000003',true);
do $$begin assert public.friends_action('accept_invite',current_setting('test.token')) ? 'error','revoked invite'; end $$;
select set_config('request.jwt.claim.sub','f1000000-0000-0000-0000-000000000001',true);
do $$declare r jsonb;begin
 r:=public.friends_action('create_invite'); perform set_config('test.token',r->>'token',true);
end $$;
reset role;
update public.friend_invites set expires_at=now()-interval '1 day' where owner_id='f1000000-0000-0000-0000-000000000001';
set local role authenticated;
select set_config('request.jwt.claim.sub','f1000000-0000-0000-0000-000000000003',true);
do $$begin assert public.friends_action('accept_invite',current_setting('test.token')) ? 'error','expired invite'; end $$;
set local role anon;
do $$begin
 begin perform public.friends_action('list'); raise exception 'Anonymous function access'; exception when insufficient_privilege then null; end;
 begin perform * from public.friend_codes; raise exception 'Anonymous code access'; exception when insufficient_privilege then null; end;
end $$;
reset role;
rollback;
select 'PASS: codes, requests, acceptance, invitation lifecycle, and access rules; synthetic data rolled back' as result;
