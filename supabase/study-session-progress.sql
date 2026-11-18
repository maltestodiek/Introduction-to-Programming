-- Read the current user's saved Study answer states for the round overview.
begin;

create or replace function public.study_session_progress(p_session uuid) returns jsonb language plpgsql security definer set search_path='' as $$
declare
 me uuid:=auth.uid(); session_row public.study_sessions; answer_states jsonb;
begin
 if me is null then raise exception 'Sign in first'; end if;
 select * into session_row from public.study_sessions where id=p_session and user_id=me;
 if session_row.id is null then raise exception 'Study session unavailable'; end if;
 select coalesce(jsonb_agg(jsonb_build_object('index',idx,'correct',correct) order by idx),'[]'::jsonb)
 into answer_states from public.study_answers where session_id=session_row.id;
 return jsonb_build_object('answers',answer_states,'cursor',session_row.cursor,'total',session_row.total);
end $$;

revoke all on function public.study_session_progress(uuid) from public,anon;
grant execute on function public.study_session_progress(uuid) to authenticated;
commit;
