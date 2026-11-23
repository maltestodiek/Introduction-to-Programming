-- Opponent and invite avatars in the Battle payloads.
-- Sessions gain opponent_image_path; invite entries gain the other party's
-- image_path. Patches the deployed battle_action surgically so the
-- per-course-search version stays untouched otherwise.
begin;

do $migration$
declare
  definition text;
  old_invites text := $$'username',p.username,'source_kind',i.source_kind$$;
  new_invites text := $$'username',p.username,'image_path',p.image_path,'source_kind',i.source_kind$$;
begin
  select pg_get_functiondef('public.battle_action(text,jsonb)'::regprocedure) into definition;
  if (length(definition)-length(replace(definition,old_invites,'')))/length(old_invites)<>1 then
    raise exception 'Cannot install Battle invite avatars: unexpected battle_action version';
  end if;
  execute replace(definition,old_invites,new_invites);
end $migration$;
grant execute on function public.battle_action(text,jsonb) to authenticated;

create or replace function public.battle_sessions_list() returns jsonb
language sql stable security definer set search_path='' as $$
 select coalesce(jsonb_agg(jsonb_build_object(
   'id',s.id,'deck_name',d.name,'course',s.course,'language',s.language,
   'status',case when s.settled_at is not null then 'completed' when r.finished_at is not null then 'pending' else 'ongoing' end,
   'started',r.started_at is not null,'finish_by',coalesce(r.finish_by,s.deadline),
   'waiting_for_match',s.p2 is null and s.settled_at is null,'search_until',q.expires_at,'score',r.score,
   'opponent_score',case when s.settled_at is not null then o.score end,
   'result',r.result,'game_xp_delta',r.game_xp_delta,'opponent_username',p.username,'opponent_image_path',p.image_path
 ) order by coalesce(s.settled_at,s.created_at) desc),'[]'::jsonb)
 from public.battle_rounds r join public.battle_sessions s on s.id=r.session_id
 join public.battle_decks d on d.id=s.battle_deck_id
 left join public.battle_rounds o on o.session_id=s.id and o.user_id<>r.user_id
 left join public.profiles p on p.id=o.user_id
 left join public.battle_searches q on q.session_id=s.id
 where r.user_id=auth.uid();
$$;

commit;
