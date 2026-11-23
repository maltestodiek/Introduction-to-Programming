-- Random searches also release their slot once every answer has been saved.
do $$
declare
    definition text := pg_get_functiondef('public.study_action(text,jsonb)'::regprocedure);
    old_guard text := $guard$active_session.mode='random' and state in ('own','waiting','paired') and finished_at is null$guard$;
begin
    if position(old_guard in definition) = 0 then
        raise exception 'Expected random Study Together slot rule was not found';
    end if;
    execute replace(definition, old_guard, old_guard || ' and not public.study_session_has_all_answers(active_session.id)');
end $$;
