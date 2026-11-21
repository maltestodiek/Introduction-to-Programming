begin;

-- Existing paired battles retain their original deadline. New rounds have an independent clock.
alter table public.battle_sessions alter column p2 drop not null;
alter table public.battle_rounds add column finish_by timestamptz, add column start_request uuid;
create unique index battle_start_request on public.battle_rounds(user_id,start_request) where start_request is not null;
create index battle_due_rounds on public.battle_rounds(finish_by) where finished_at is null and finish_by is not null;
alter table public.battle_searches add column session_id uuid unique references public.battle_sessions(id) on delete cascade;

-- Cancelling, changing campus, or expiring an unpaired search also closes its practice round.
create function public.close_unmatched_battle() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 delete from public.battle_sessions where id=old.session_id and p2 is null;
 return old;
end $$;
create trigger close_unmatched_battle after delete on public.battle_searches
for each row when (old.session_id is not null) execute function public.close_unmatched_battle();

create or replace function public.expire_battle_searches() returns jsonb
language plpgsql security definer set search_path='' as $$
declare expired integer; due record; opponent uuid;
begin
 perform pg_advisory_xact_lock(791146221);
 delete from public.battle_searches q where q.expires_at<=now() or exists (
  select 1 from public.battle_rounds r where r.session_id=q.session_id and r.user_id=q.user_id
    and r.finished_at is null and r.finish_by<=now());
 get diagnostics expired=row_count;
 -- Resolve the earliest missed deadline even when both players have since gone offline.
 for due in select distinct on (s.id) s.id,s.battle_deck_id,r.user_id,r.finish_by
  from public.battle_rounds r join public.battle_sessions s on s.id=r.session_id
  where s.p2 is not null and s.settled_at is null and r.finished_at is null and r.finish_by<=now()
  order by s.id,r.finish_by,r.user_id
 loop
  select user_id into opponent from public.battle_rounds where session_id=due.id and user_id<>due.user_id
   and finished_at is null and finish_by=due.finish_by;
  if found then
   -- Identical deadlines (e.g. an untouched friend invitation): both missed it.
   -- The existing deadline settlement records two losses when neither finished.
   update public.battle_sessions set deadline=now() where id=due.id;
   perform public.battle_finish(due.id);
   update public.battle_rounds set forfeited=true where session_id=due.id;
   perform public.battle_rate(due.battle_deck_id,opponent,'neutral',true,
     (select creator_id=opponent from public.battle_decks where id=due.battle_deck_id));
  else
   update public.battle_rounds set forfeited=true where session_id=due.id and user_id=due.user_id;
  end if;
  perform public.battle_rate(due.battle_deck_id,due.user_id,'neutral',true,
    (select creator_id=due.user_id from public.battle_decks where id=due.battle_deck_id));
  perform public.battle_finish(due.id);
 end loop;
 return jsonb_build_object('expired',expired);
end $$;

-- Serialise cancellation with attachment so it cannot remove a matched Battle.
create or replace function public.cancel_battle_search() returns jsonb
language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null then raise exception 'Sign in first';end if;
 perform pg_advisory_xact_lock(791146221);
 delete from public.battle_searches where user_id=auth.uid();
 return jsonb_build_object('cancelled',found);
end $$;

create function public.start_random_battle(p_data jsonb) returns jsonb
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
 select * into own from public.battle_searches where user_id=me;
 if own.session_id is not null then
  if lower(trim(own.course))<>lower(course_name) or own.language<>lang or own.university<>campus
     or (kind='top' and requested is distinct from (select battle_deck_id from public.battle_sessions where id=own.session_id))
  then raise exception 'You already have an active random search';end if;
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
 delete from public.battle_searches where user_id in(me,peer.user_id);
 if peer.user_id is null then
  insert into public.battle_searches(user_id,source_kind,deck_id,university,course,language,expires_at,session_id)
  values(me,kind,case when kind='top' then requested end,campus,course_name,lang,now()+interval '48 hours',sid);
 end if;
 return jsonb_build_object('session_id',sid);
end $$;

-- Keep the existing question validation, 30-second timer, ratings, and XP settlement.
alter function public.battle_action(text,jsonb) rename to battle_action_before_async;
revoke all on function public.battle_action_before_async(text,jsonb),public.start_random_battle(jsonb),
 public.close_unmatched_battle() from public,anon,authenticated;
create function public.battle_action(p_action text,p_data jsonb default '{}') returns jsonb
language plpgsql security definer set search_path='' as $$
declare me uuid:=auth.uid(); sid uuid; r public.battle_rounds; s public.battle_sessions; reply jsonb;
begin
 if me is null then raise exception 'Sign in first';end if;
 perform public.expire_battle_searches();
 if p_action in ('start_random','join') then return public.start_random_battle(p_data);end if;
 if p_action='cancel_unmatched' then
  delete from public.battle_searches where session_id=(p_data->>'id')::uuid and user_id=me;
  return jsonb_build_object('cancelled',found);
 end if;
 if p_action in ('round','answer','finish','abandon','rate','review','clock') then
  sid:=(p_data->>'id')::uuid;
  select * into r from public.battle_rounds where session_id=sid and user_id=me;
  if not found then raise exception 'Battle unavailable';end if;
  select * into strict s from public.battle_sessions where id=sid;
  if p_action='clock' then return jsonb_build_object('finish_by',coalesce(r.finish_by,s.deadline),'matched',s.p2 is not null);end if;
  if p_action='abandon' and s.p2 is null then
   if not coalesce((p_data->>'confirmed')::boolean,false) then raise exception 'Confirm abandonment first';end if;
   delete from public.battle_searches where session_id=sid;
   return jsonb_build_object('state','expired');
  end if;
  if s.settled_at is not null and p_action in ('answer','abandon','finish') then return jsonb_build_object('state','completed');end if;
  if p_action='round' and r.finish_by is not null and r.started_at is null and s.settled_at is null then
   update public.battle_rounds set finish_by=now()+interval '1 hour' where session_id=sid and user_id=me returning * into r;
  end if;
 end if;
 reply:=public.battle_action_before_async(p_action,p_data);
 if p_action='accept_invite' then
  sid:=(reply->>'session_id')::uuid;
  -- Both may start an accepted invitation within the existing 24-hour window.
  update public.battle_rounds set finish_by=(select deadline from public.battle_sessions where id=sid) where session_id=sid;
  update public.battle_sessions set deadline='infinity' where id=sid;
 elsif p_action='list' then
  reply:=reply||jsonb_build_object('sessions',public.battle_sessions_list(),'includes_unmatched',true);
  if exists(select 1 from public.battle_searches where user_id=me and session_id is not null) then
   reply:=reply||jsonb_build_object('search',null); -- Already represented by its playable session.
  end if;
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

create or replace function public.battle_sessions_list() returns jsonb
language sql stable security definer set search_path='' as $$
 select coalesce(jsonb_agg(jsonb_build_object(
   'id',s.id,'deck_name',d.name,'course',s.course,'language',s.language,
   'status',case when s.settled_at is not null then 'completed' when r.finished_at is not null then 'pending' else 'ongoing' end,
   'started',r.started_at is not null,'finish_by',coalesce(r.finish_by,s.deadline),
   'waiting_for_match',s.p2 is null,'search_until',q.expires_at,'score',r.score,
   'opponent_score',case when s.settled_at is not null then o.score end,
   'result',r.result,'game_xp_delta',r.game_xp_delta,'opponent_username',p.username
 ) order by coalesce(s.settled_at,s.created_at) desc),'[]'::jsonb)
 from public.battle_rounds r join public.battle_sessions s on s.id=r.session_id
 join public.battle_decks d on d.id=s.battle_deck_id
 left join public.battle_rounds o on o.session_id=s.id and o.user_id<>r.user_id
 left join public.profiles p on p.id=o.user_id
 left join public.battle_searches q on q.session_id=s.id
 where r.user_id=auth.uid();
$$;
-- Also install the minute job on projects that enabled Cron after Battle was introduced.
do $$
begin
 if exists(select 1 from pg_extension where extname='pg_cron') then
  execute 'select cron.schedule($1,$2,$3)' using 'expire-battle-searches','* * * * *','select public.expire_battle_searches()';
 end if;
end $$;
commit;
