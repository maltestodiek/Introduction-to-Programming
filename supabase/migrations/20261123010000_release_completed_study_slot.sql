-- A completed answer set must never keep a Study Together slot reserved if an
-- older client left the session state behind before recording finished_at.
create or replace function public.study_session_has_all_answers(p_session uuid)
returns boolean language sql stable security definer set search_path = '' as $$
    select exists(
        select 1
        from public.study_sessions s
        where s.id = p_session
          and (s.finished_at is not null or (
              select count(*) from public.study_answers a where a.session_id = s.id
          ) = s.total)
    )
$$;

revoke all on function public.study_session_has_all_answers(uuid) from public, anon, authenticated;

do $$
declare
    definition text;
    old_guard text := 'active_session.finished_at is null';
    new_guard text := 'active_session.finished_at is null and not public.study_session_has_all_answers(active_session.id)';
begin
    select pg_get_functiondef('public.study_action(text,jsonb)'::regprocedure) into definition;
    if position(old_guard in definition) = 0 then
        raise exception 'Expected Study Together completion guard was not found';
    end if;
    execute replace(definition, old_guard, new_guard);
end $$;
