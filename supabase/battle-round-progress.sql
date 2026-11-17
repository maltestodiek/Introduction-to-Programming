-- Read the current user's saved Battle answer states for the round overview.
begin;

create or replace function public.battle_round_progress(p_session uuid) returns jsonb language plpgsql security definer set search_path='' as $$
declare
 me uuid:=auth.uid(); round_row public.battle_rounds;
begin
 if me is null then raise exception 'Sign in first'; end if;
 select r.* into round_row
 from public.battle_rounds r
 join public.battle_sessions s on s.id=r.session_id
 where r.session_id=p_session and r.user_id=me and me in(s.p1,s.p2);
 if round_row.session_id is null then raise exception 'Battle unavailable'; end if;
 return jsonb_build_object('answers',round_row.answers,'cursor',round_row.cursor,'score',round_row.score);
end $$;

revoke all on function public.battle_round_progress(uuid) from public,anon;
grant execute on function public.battle_round_progress(uuid) to authenticated;
commit;
