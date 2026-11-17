begin;
create table if not exists public.friend_codes (
 user_id uuid primary key references public.profiles(id) on delete cascade,
 code text not null unique check(code ~ '^[A-HJ-NP-Z2-9]{8}$')
);
create table if not exists public.friend_edges (
 id uuid primary key default gen_random_uuid(),
 low_id uuid not null references public.profiles(id) on delete cascade,
 high_id uuid not null references public.profiles(id) on delete cascade,
 sender uuid not null references public.profiles(id) on delete cascade,
 state text not null check(state in ('pending','accepted')),
 created_at timestamptz not null default now(),
 check(low_id < high_id), check(sender in (low_id,high_id)), unique(low_id,high_id)
);
create table if not exists public.friend_invites (
 owner_id uuid primary key references public.profiles(id) on delete cascade,
 token_hash text not null unique,
 expires_at timestamptz not null
);
create table if not exists public.friend_limits (
 user_id uuid not null references auth.users(id) on delete cascade,
 action text not null, bucket timestamptz not null, count integer not null,
 primary key(user_id,action)
);
alter table public.friend_codes enable row level security;
alter table public.friend_edges enable row level security;
alter table public.friend_invites enable row level security;
alter table public.friend_limits enable row level security;
revoke all on public.friend_codes,public.friend_edges,public.friend_invites,public.friend_limits from public,anon,authenticated;
grant select on public.friend_codes,public.friend_edges to authenticated;
create policy friend_codes_owner on public.friend_codes for select to authenticated using(user_id=(select auth.uid()));
create policy friend_edges_participants on public.friend_edges for select to authenticated using((select auth.uid()) in (low_id,high_id));
create function public.friend_person(p_id uuid) returns jsonb language sql stable security definer set search_path='' as $$
 select jsonb_build_object('id',id,'username',username,'image_path',image_path) from public.profiles where id=p_id
$$;
revoke all on function public.friend_person(uuid) from public,anon,authenticated;
create function public.friends_action(p_action text,p_value text default '') returns jsonb
language plpgsql security definer set search_path='' as $$
declare
 me uuid:=auth.uid(); other_id uuid; lo uuid; hi uuid; edge public.friend_edges;
 code_value text; token_value text; invite public.friend_invites; n integer; i integer;
 direct_request boolean:=p_action='request_user';
 alphabet text:='ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; raw bytea;
begin
 if me is null then raise exception 'Sign in required'; end if;
 if not exists(select 1 from public.profiles where id=me) then return jsonb_build_object('error','Complete your profile first.'); end if;
 if direct_request then p_action:='request'; end if;
 if p_action not in ('list','lookup','request','accept','decline','cancel','remove','create_invite','revoke_invite','preview_invite','accept_invite') then
 return jsonb_build_object('error','Unknown friend action.'); end if;
 -- Failed attempts consume a bounded rate counter, but never alter relationships.
 if p_action <> 'list' then
 insert into public.friend_limits as f(user_id,action,bucket,count) values(me,p_action,date_trunc('minute',now()),1)
 on conflict(user_id,action) do update set bucket=excluded.bucket,
 count=case when f.bucket=excluded.bucket then f.count+1 else 1 end returning count into n;
 if n>(case when p_action in ('request','create_invite') then 5 else 30 end) then
 return jsonb_build_object('error','Too many attempts. Please wait a minute and try again.'); end if;
 end if;
 if p_action='list' then
 select code into code_value from public.friend_codes where user_id=me;
 while code_value is null loop
 raw:=extensions.gen_random_bytes(8); token_value:='';
 for i in 0..7 loop token_value:=token_value||substr(alphabet,(get_byte(raw,i)%32)+1,1); end loop;
 begin
 insert into public.friend_codes(user_id,code) values(me,token_value) on conflict(user_id) do nothing;
 exception when unique_violation then null; end;
 select code into code_value from public.friend_codes where user_id=me;
 end loop;
 return jsonb_build_object('code',code_value,
 'friends',coalesce((select jsonb_agg(jsonb_build_object('id',e.id,'person',public.friend_person(case when e.low_id=me then e.high_id else e.low_id end)) order by e.created_at desc) from public.friend_edges e where me in(e.low_id,e.high_id) and e.state='accepted'),'[]'::jsonb),
 'incoming',coalesce((select jsonb_agg(jsonb_build_object('id',e.id,'person',public.friend_person(e.sender)) order by e.created_at desc) from public.friend_edges e where me in(e.low_id,e.high_id) and e.state='pending' and e.sender<>me),'[]'::jsonb),
 'sent',coalesce((select jsonb_agg(jsonb_build_object('id',e.id,'person',public.friend_person(case when e.low_id=me then e.high_id else e.low_id end)) order by e.created_at desc) from public.friend_edges e where e.sender=me and e.state='pending'),'[]'::jsonb),
 'invite_expires',(select expires_at from public.friend_invites where owner_id=me and expires_at>now()));
 end if;
 if direct_request then
 begin other_id:=p_value::uuid;
 exception when invalid_text_representation then return jsonb_build_object('error','Session partner unavailable.'); end;
 if other_id is null or other_id=me or (
 not exists(select 1 from public.chat_threads where low_id=least(me,other_id) and high_id=greatest(me,other_id)) and
 not exists(select 1 from public.play_duels where me in(p1,p2) and other_id in(p1,p2)) and
 not exists(select 1 from public.study_sessions own join public.study_sessions partner on partner.id=own.partner_id and partner.partner_id=own.id where own.user_id=me and partner.user_id=other_id)
 ) then return jsonb_build_object('error','Choose a conversation or matched session partner.'); end if;
 elsif p_action in ('lookup','request') then
 code_value:=upper(trim(leading '#' from btrim(p_value)));
 if code_value !~ '^[A-HJ-NP-Z2-9]{8}$' then return jsonb_build_object('error','Enter a valid eight-character friend code.'); end if;
 select user_id into other_id from public.friend_codes where code=code_value;
 if other_id is null then return jsonb_build_object('error','No student found with that code.'); end if;
 if other_id=me then return jsonb_build_object('error','That is your own friend code.'); end if;
 if p_action='lookup' then return jsonb_build_object('person',public.friend_person(other_id)); end if;
 elsif p_action='create_invite' then
 perform pg_advisory_xact_lock(hashtextextended(me::text,7));
 token_value:=encode(extensions.gen_random_bytes(24),'hex');
 insert into public.friend_invites(owner_id,token_hash,expires_at) values(me,encode(extensions.digest(token_value,'sha256'),'hex'),now()+interval '7 days')
 on conflict(owner_id) do update set token_hash=excluded.token_hash,expires_at=excluded.expires_at;
 return jsonb_build_object('token',token_value,'message','Invitation link created. It expires in seven days.');
 elsif p_action='revoke_invite' then
 perform pg_advisory_xact_lock(hashtextextended(me::text,7));
 delete from public.friend_invites where owner_id=me;
 return jsonb_build_object('message','Invitation link revoked.');
 elsif p_action in ('preview_invite','accept_invite') then
 if p_value !~ '^[a-f0-9]{48}$' then return jsonb_build_object('error','This invitation is invalid or expired.'); end if;
 -- Hold the invitation row while accepting, serializing with rotation/revocation.
 select * into invite from public.friend_invites where token_hash=encode(extensions.digest(p_value,'sha256'),'hex') and expires_at>now() for share;
 if not found then return jsonb_build_object('error','This invitation is invalid or expired.'); end if;
 other_id:=invite.owner_id;
 if other_id=me then return jsonb_build_object('error','This is your own invitation. Share it with a friend.'); end if;
 if p_action='preview_invite' then return jsonb_build_object('person',public.friend_person(other_id)); end if;
 else
 begin select * into edge from public.friend_edges where id=p_value::uuid and me in(low_id,high_id);
 exception when invalid_text_representation then return jsonb_build_object('error','Request no longer available.'); end;
 if not found or edge.id is null then return jsonb_build_object('error','Request no longer available.'); end if;
 other_id:=case when edge.low_id=me then edge.high_id else edge.low_id end;
 end if;
 lo:=least(me,other_id); hi:=greatest(me,other_id);
 perform pg_advisory_xact_lock(hashtextextended(lo::text||hi::text,0));
 select * into edge from public.friend_edges where low_id=lo and high_id=hi for update;
 if p_action='request' then
 if edge.id is not null then return jsonb_build_object('error',case when edge.state='accepted' then 'You are already friends.' when edge.sender=me then 'A request is already pending.' else 'This student already invited you. Accept their incoming request.' end); end if;
 insert into public.friend_edges(low_id,high_id,sender,state) values(lo,hi,me,'pending');
 return jsonb_build_object('message','Friend request sent.');
 elsif p_action='accept_invite' then
 insert into public.friend_edges(low_id,high_id,sender,state) values(lo,hi,other_id,'accepted')
 on conflict(low_id,high_id) do update set state='accepted';
 return jsonb_build_object('message','Invitation accepted. You are now friends.');
 end if;
 if edge.id is null or edge.id::text<>p_value then return jsonb_build_object('error','Request no longer available.'); end if;
 if p_action='accept' and edge.state='pending' and edge.sender<>me then
 update public.friend_edges set state='accepted' where id=edge.id;
 return jsonb_build_object('message','Friend request accepted.');
 elsif (p_action='decline' and edge.state='pending' and edge.sender<>me) or (p_action='cancel' and edge.state='pending' and edge.sender=me) or (p_action='remove' and edge.state='accepted') then
 delete from public.friend_edges where id=edge.id;
 return jsonb_build_object('message',case p_action when 'remove' then 'Friend removed.' when 'decline' then 'Request declined.' else 'Request cancelled.' end);
 end if;
 return jsonb_build_object('error','You cannot perform that action on this request.');
end; $$;
revoke all on function public.friends_action(text,text) from public,anon;
grant execute on function public.friends_action(text,text) to authenticated;
commit;
