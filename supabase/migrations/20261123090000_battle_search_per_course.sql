begin;
-- Existing rows are preserved. Course identity is case/whitespace insensitive and spans languages.
alter table public.battle_searches add column course_key text generated always as (lower(trim(course))) stored;
alter table public.battle_searches drop constraint battle_searches_pkey;
alter table public.battle_searches add primary key (user_id,course_key);

create or replace function public.start_random_battle(p_data jsonb) returns jsonb
language plpgsql security definer set search_path='' as $$
declare
 me uuid:=auth.uid(); campus text; course_name text:=trim(p_data->>'course'); lang text:=p_data->>'language';
 kind text:=p_data->>'source_kind'; requested uuid:=(p_data->>'deck_id')::uuid; token uuid:=(p_data->>'request_id')::uuid;
 deck public.battle_decks; peer public.battle_searches; own public.battle_searches; sid uuid;
begin
 -- The caller holds the matchmaking lock and has expired overdue rounds.
 select session_id into sid from public.battle_rounds where user_id=me and start_request=token;
 if found then return jsonb_build_object('session_id',sid,'resumed',true);end if;
 select p.university into campus from public.profiles p join public.profile_private v on v.user_id=p.id
 where p.id=me and lang=any(p.languages) and exists(select 1 from unnest(v.courses)c where lower(trim(c))=lower(course_name));
 if campus is null then raise exception 'Choose one of your courses and languages';end if;
 if kind is null or kind not in ('random','top') then raise exception 'Choose Random Deck or Top Decks';end if;
 if kind='top' and not exists(select 1 from public.battle_decks where id=requested and university=campus and lower(trim(course))=lower(course_name) and language=lang)
 then raise exception 'Choose an eligible Top Deck';end if;
 select * into own from public.battle_searches where user_id=me and lower(trim(course))=lower(course_name);
 if own.user_id is not null and (own.language<>lang or own.university<>campus) then
  raise exception 'You already have an active random search for this course';
 end if;
 if own.session_id is not null then
  if lower(trim(own.course))<>lower(course_name) or own.language<>lang or own.university<>campus
     or (kind='top' and requested is distinct from (select battle_deck_id from public.battle_sessions where id=own.session_id))
  then raise exception 'You already have an active random search for this course';end if;
  return jsonb_build_object('session_id',own.session_id,'resumed',true);
 end if;
 select q.* into peer from public.battle_searches q join public.profiles p on p.id=q.user_id
 join public.profile_private v on v.user_id=p.id
 left join public.battle_sessions s on s.id=q.session_id
 where q.user_id<>me and q.university=campus and p.university=campus and q.language=lang and lang=any(p.languages)
 and lower(trim(q.course))=lower(course_name) and exists(select 1 from unnest(v.courses)c where lower(trim(c))=lower(course_name))
 and (kind='random' or coalesce(s.battle_deck_id,q.deck_id,requested)=requested)
 order by q.created_at,q.user_id limit 1;
 if peer.session_id is not null then
  sid:=peer.session_id;
  update public.battle_sessions set p2=me where id=sid and p2 is null;
 else
  select b.* into deck from public.battle_decks b where b.university=campus and lower(trim(b.course))=lower(course_name) and b.language=lang
   and (coalesce(peer.deck_id,case when kind='top' then requested end) is null or b.id=coalesce(peer.deck_id,requested))
   order by random() limit 1;
  if deck.id is null then raise exception 'No eligible Battle Deck is available for this course and language';end if;
  insert into public.battle_sessions(p1,p2,battle_deck_id,source_kind,cards,course,language,deadline)
  values(coalesce(peer.user_id,me),case when peer.user_id is not null then me end,deck.id,coalesce(peer.source_kind,kind),deck.cards,deck.course,lang,'infinity')
  returning id into sid;
  if peer.user_id is not null then
   insert into public.battle_rounds(session_id,user_id,finish_by) values(sid,peer.user_id,now()+interval '1 hour');
  end if;
 end if;
 insert into public.battle_rounds(session_id,user_id,start_request,finish_by) values(sid,me,token,now()+interval '1 hour');
 delete from public.battle_searches where user_id in(me,peer.user_id) and lower(trim(course))=lower(course_name);
 if peer.user_id is null then
  insert into public.battle_searches(user_id,source_kind,deck_id,university,course,language,expires_at,session_id)
  values(me,kind,case when kind='top' then requested end,campus,course_name,lang,now()+interval '48 hours',sid);
 end if;
 return jsonb_build_object('session_id',sid);
end $$;

-- Keep no-argument clients safe: never cancel several courses implicitly.
drop function public.cancel_battle_search();
create function public.cancel_battle_search(p_course text default null) returns jsonb
language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null then raise exception 'Sign in first';end if;
 perform pg_advisory_xact_lock(791146221);
 if p_course is null and (select count(*) from public.battle_searches where user_id=auth.uid())>1 then
  raise exception 'Choose the course whose search you want to cancel';
 end if;
 delete from public.battle_searches q where q.user_id=auth.uid()
  and (p_course is null or lower(trim(q.course))=lower(trim(p_course)))
  and not exists(select 1 from public.battle_rounds r where r.session_id=q.session_id and r.user_id=q.user_id
                 and r.started_at is not null and r.finished_at is null);
 return jsonb_build_object('cancelled',found);
end $$;
revoke all on function public.cancel_battle_search(text) from public,anon;
grant execute on function public.cancel_battle_search(text) to authenticated;

create or replace function public.battle_action(p_action text,p_data jsonb default '{}') returns jsonb
language plpgsql security definer set search_path='' as $$
declare me uuid:=auth.uid(); sid uuid; r public.battle_rounds; s public.battle_sessions; reply jsonb;
begin
 if me is null then raise exception 'Sign in first';end if;
 perform public.expire_battle_searches();
 if p_action in ('start_random','join') then return public.start_random_battle(p_data);end if;
 if p_action='cancel_unmatched' then
  delete from public.battle_searches q where q.session_id=(p_data->>'id')::uuid and q.user_id=me
   and not exists(select 1 from public.battle_rounds r1 where r1.session_id=q.session_id and r1.user_id=me
                  and r1.started_at is not null and r1.finished_at is null);
  return jsonb_build_object('cancelled',found);
 end if;
 if p_action in ('round','answer','finish','abandon','leave','rate','review','clock') then
  sid:=(p_data->>'id')::uuid;
  select * into r from public.battle_rounds where session_id=sid and user_id=me;
  if not found then raise exception 'Battle unavailable';end if;
  select * into strict s from public.battle_sessions where id=sid;
  if p_action='clock' then return jsonb_build_object('finish_by',coalesce(r.finish_by,s.deadline),'matched',s.p2 is not null);end if;
  if p_action in ('leave','abandon') then
   if not coalesce((p_data->>'confirmed')::boolean,false) then raise exception 'Confirm leaving first';end if;
   if s.settled_at is not null then return jsonb_build_object('state','completed','result',r.result);end if;
   if r.finished_at is not null then return jsonb_build_object('state','pending');end if;
   -- Use the normal rating, XP floor and streak settlement for a forfeit.
   perform public.battle_action_before_async('abandon',p_data);
   delete from public.battle_searches where session_id=sid;
   return jsonb_build_object('state','completed','result','loss');
  end if;
  if s.settled_at is not null and p_action in ('answer','abandon','finish') then return jsonb_build_object('state','completed');end if;
  if p_action='round' and r.finish_by is not null and r.started_at is null and s.settled_at is null then
   update public.battle_rounds set finish_by=now()+interval '1 hour' where session_id=sid and user_id=me returning * into r;
  end if;
 end if;
 if p_action='list' then
  update public.battle_invites set state='expired' where state='pending' and expires_at<=now();
  return jsonb_build_object(
   'includes_unmatched',true,'sessions',public.battle_sessions_list(),
   'searches',coalesce((select jsonb_agg(jsonb_build_object('course',q.course,'language',q.language,
      'expires_at',q.expires_at,'session_id',q.session_id) order by q.created_at,q.course)
      from public.battle_searches q where q.user_id=me),'[]'::jsonb),
   -- Legacy clients still display a standalone search; async searches appear as sessions.
   'search',(select jsonb_build_object('course',q.course,'language',q.language,'expires_at',q.expires_at)
      from public.battle_searches q where q.user_id=me and q.session_id is null order by q.created_at limit 1),
   'invites',coalesce((select jsonb_agg(jsonb_build_object('id',i.id,'incoming',i.recipient=me,
      'username',p.username,'source_kind',i.source_kind,'deck_name',b.name,'course',i.course,
      'language',i.language,'expires_at',i.expires_at) order by i.created_at desc)
      from public.battle_invites i join public.profiles p on p.id=case when i.sender=me then i.recipient else i.sender end
      left join public.battle_decks b on b.id=i.deck_id
      where i.state='pending' and me in(i.sender,i.recipient)),'[]'::jsonb));
 end if;
 reply:=public.battle_action_before_async(p_action,p_data);
 if p_action='accept_invite' then
  sid:=(reply->>'session_id')::uuid;
  -- Both may start an accepted invitation within the existing 24-hour window.
  update public.battle_rounds set finish_by=(select deadline from public.battle_sessions where id=sid) where session_id=sid;
  update public.battle_sessions set deadline='infinity' where id=sid;
 elsif p_action in ('round','answer') and r.finish_by is not null then
  -- The fifteenth answer (including a timed-out question) finishes the attempt immediately.
  update public.battle_rounds set finished_at=now() where session_id=sid and user_id=me and cursor=15 and finished_at is null;
  if found and s.p2 is not null then perform public.battle_finish(sid);end if;
  if p_action='round' and r.finished_at is not null and reply->>'state'='completed' and not r.forfeited then
   reply:=jsonb_build_object('state','rating','score',r.score,'can_rate',(select creator_id<>me from public.battle_decks where id=s.battle_deck_id));
  end if;
  reply:=reply||jsonb_build_object('finish_by',r.finish_by);
 end if;
 return reply;
end $$;
revoke all on function public.battle_action(text,jsonb) from public,anon;
grant execute on function public.battle_action(text,jsonb) to authenticated;


commit;
