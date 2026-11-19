-- Battle XP only. Apply after battle-mode-schema.sql and leaderboard-game-xp.sql.
-- This follow-up migration intentionally preserves applied migration files.
begin;

-- Battle XP is the only XP balance. The retired reward balance is deliberately
-- not carried into the profile total or the leaderboard.
update public.profiles set xp=game_xp where xp is distinct from game_xp;

-- Ratings still affect each deck's daily Top Deck score, but never award XP.
create or replace function public.battle_rate(
 p_deck uuid,p_reviewer uuid,p_rating text,p_automatic boolean default false,p_non_scoring boolean default false
) returns void language plpgsql security definer set search_path='' as $$
declare day date:=(now() at time zone 'Europe/Berlin')::date;
begin
 if not exists(select 1 from public.battle_decks where id=p_deck) then
  raise exception 'Battle Deck unavailable';
 end if;
 insert into public.battle_ratings(battle_deck_id,reviewer_id,rating,automatic,non_scoring)
 values(p_deck,p_reviewer,p_rating,p_automatic,p_non_scoring) on conflict do nothing;
 if not found or p_non_scoring then return; end if;
 insert into public.battle_daily_ratings(berlin_day,battle_deck_id,score,rating_count,good_count,neutral_count,bad_count)
 values(day,p_deck,case p_rating when 'good' then 1 when 'bad' then -1 else 0 end,1,
        case when p_rating='good' then 1 else 0 end,
        case when p_rating='neutral' then 1 else 0 end,
        case when p_rating='bad' then 1 else 0 end)
 on conflict(berlin_day,battle_deck_id) do update set
  score=battle_daily_ratings.score+excluded.score,
  rating_count=battle_daily_ratings.rating_count+1,
  good_count=battle_daily_ratings.good_count+excluded.good_count,
  neutral_count=battle_daily_ratings.neutral_count+excluded.neutral_count,
  bad_count=battle_daily_ratings.bad_count+excluded.bad_count;
end $$;

alter table public.profiles drop column if exists creator_xp;

-- Session rows expose only the opponent's public username, never an id or
-- private-profile fields. This makes completed Battles reviewable from Play.
create or replace function public.battle_sessions_list() returns jsonb language plpgsql stable security definer set search_path='' as $$
declare me uuid:=auth.uid();
begin
 if me is null then raise exception 'Sign in first'; end if;
 return coalesce((select jsonb_agg(jsonb_build_object(
  'id',x.id,'deck_name',x.name,'course',x.course,'language',x.language,
  'status',x.status,'score',x.score,'opponent_score',x.opponent_score,
  'result',x.result,'game_xp_delta',x.game_xp_delta,'started',x.started,
  'opponent_username',x.opponent_username) order by x.created_at desc)
 from (
  select s.id,b.name,s.course,s.language,s.created_at,r.score,r.result,r.game_xp_delta,
   r.started_at is not null started,
   case when s.settled_at is not null then 'completed' when r.finished_at is not null then 'pending' else 'ongoing' end status,
   case when s.settled_at is not null then o.score end opponent_score,
   p.username opponent_username
  from public.battle_sessions s
  join public.battle_rounds r on r.session_id=s.id and r.user_id=me
  join public.battle_rounds o on o.session_id=s.id and o.user_id=case when s.p1=me then s.p2 else s.p1 end
  join public.battle_decks b on b.id=s.battle_deck_id
  join public.profiles p on p.id=case when s.p1=me then s.p2 else s.p1 end
  where me in(s.p1,s.p2)
 ) x),'[]'::jsonb);
end $$;

-- The leaderboard is read-only and ranks only the stored Battle XP balance.
create or replace function public.leaderboard() returns jsonb language plpgsql stable security definer set search_path='' as $$
declare me uuid:=auth.uid();
begin
 if me is null or not exists(select 1 from public.profiles where id=me) then
  return jsonb_build_object('error','Sign in and complete your profile first.');
 end if;
 return jsonb_build_object(
  'top',coalesce((select jsonb_agg(jsonb_build_object('rank',r.place,'username',r.username,'image_path',r.image_path,'xp',r.game_xp,'me',r.id=me) order by r.place,r.username)
   from (select p.id,p.username,p.image_path,p.game_xp,rank() over(order by p.game_xp desc) as place from public.profiles p order by p.game_xp desc,p.username limit 10) r),'[]'::jsonb),
  'me',(select jsonb_build_object('rank',1+(select count(*) from public.profiles o where o.game_xp>p.game_xp),'username',p.username,'image_path',p.image_path,'xp',p.game_xp,'me',true) from public.profiles p where p.id=me),
  'friends',coalesce((select jsonb_agg(jsonb_build_object('rank',f.place,'username',f.username,'image_path',f.image_path,'xp',f.game_xp,'me',f.id=me) order by f.place,f.username)
   from (select p.id,p.username,p.image_path,p.game_xp,rank() over(order by p.game_xp desc) as place from public.profiles p
         where p.id=me or exists(select 1 from public.friend_edges e where e.state='accepted' and ((e.low_id=me and e.high_id=p.id) or (e.high_id=me and e.low_id=p.id)))) f),'[]'::jsonb));
end $$;

revoke all on function public.battle_rate(uuid,uuid,text,boolean,boolean),public.battle_sessions_list(),public.leaderboard() from public,anon;
grant execute on function public.battle_action(text,jsonb),public.battle_sessions_list(),public.leaderboard() to authenticated;
commit;
