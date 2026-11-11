begin;
insert into auth.users(id) values('f2000000-0000-0000-0000-000000000001'),('f2000000-0000-0000-0000-000000000002');
insert into public.profiles(id,username,university,languages,image_path) select id,'edge_test_'||right(id::text,1),'Example University',array['English'],id::text||'/test.png' from auth.users where id in ('f2000000-0000-0000-0000-000000000001','f2000000-0000-0000-0000-000000000002');
set local role authenticated;
select set_config('request.jwt.claim.sub','f2000000-0000-0000-0000-000000000002',true);
do $$begin perform set_config('test.code',public.friends_action('list')->>'code',true); end $$;
select set_config('request.jwt.claim.sub','f2000000-0000-0000-0000-000000000001',true);
do $$begin
 assert not(public.friends_action('request',current_setting('test.code')) ? 'error');
 perform set_config('test.edge',public.friends_action('list')->'sent'->0->>'id',true);
 assert not(public.friends_action('cancel',current_setting('test.edge')) ? 'error');
 assert jsonb_array_length(public.friends_action('list')->'sent')=0;
 assert not(public.friends_action('request',current_setting('test.code')) ? 'error');
 perform set_config('test.edge',public.friends_action('list')->'sent'->0->>'id',true);
 perform set_config('test.old_token',public.friends_action('create_invite')->>'token',true);
 perform public.friends_action('create_invite');
end $$;
select set_config('request.jwt.claim.sub','f2000000-0000-0000-0000-000000000002',true);
do $$declare i integer; r jsonb;begin
 assert public.friends_action('cancel',current_setting('test.edge')) ? 'error','recipient cancelled';
 assert not(public.friends_action('decline',current_setting('test.edge')) ? 'error'),'decline failed';
 assert public.friends_action('accept',current_setting('test.edge')) ? 'error','accepted declined request';
 assert public.friends_action('accept_invite',current_setting('test.old_token')) ? 'error','rotated link still valid';
 for i in 1..31 loop r:=public.friends_action('lookup','ZZZZZZZZ'); end loop;
 assert r->>'error'='Too many attempts. Please wait a minute and try again.','rate limit';
 assert jsonb_array_length(public.friends_action('list')->'friends')=0;
end $$;
reset role;
do $$begin
 begin insert into public.friend_codes(user_id,code) values('f2000000-0000-0000-0000-000000000001',current_setting('test.code'));
 raise exception 'duplicate code permitted'; exception when unique_violation then null; end;
end $$;
rollback;
select 'PASS: cancellation, decline, rotation, uniqueness and rate limits; rolled back' as result;
