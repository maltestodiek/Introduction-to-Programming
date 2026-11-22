begin;

-- Preserve a settled single-player loss when its search is removed.
create or replace function public.close_unmatched_battle() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 delete from public.battle_sessions where id=old.session_id and p2 is null and settled_at is null;
 return old;
end $$;

create or replace function public.cancel_battle_search() returns jsonb
language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null then raise exception 'Sign in first';end if;
 perform pg_advisory_xact_lock(791146221);
 delete from public.battle_searches q where q.user_id=auth.uid()
  and not exists(select 1 from public.battle_rounds r where r.session_id=q.session_id and r.user_id=q.user_id
                 and r.started_at is not null and r.finished_at is null);
 return jsonb_build_object('cancelled',found);
end $$;

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
   'waiting_for_match',s.p2 is null and s.settled_at is null,'search_until',q.expires_at,'score',r.score,
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
commit;
