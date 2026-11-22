-- Replace the global Study Together slot with one slot per friend pair.
-- Random matching remains limited to one outstanding search because it has no known partner.
do $$
declare
    definition text;
    old_guard text := $guard$if exists(select 1 from public.study_sessions active_session where user_id=me and active_session.mode<>'solo' and state in ('own','waiting','paired') and finished_at is null and (deadline is null or deadline>now()) and (expires_at is null or expires_at>now())) then raise exception 'You already have an unfinished Study Together session. Answer both halves or stop it before starting or accepting another.';end if;$guard$;
    new_guard text := $guard$
   if mode='random' and exists(select 1 from public.study_sessions active_session where user_id=me and active_session.mode='random' and state in ('own','waiting','paired') and finished_at is null and (deadline is null or deadline>now()) and (expires_at is null or expires_at>now())) then
    raise exception 'You already have an outstanding random Study Together search. Finish it or stop it before starting another random search';
   end if;
   if mode='friend' and exists(
    select 1 from public.study_sessions active_session
    left join public.study_sessions active_partner on active_partner.id=active_session.partner_id
    where active_session.user_id=me and active_session.mode='friend'
      and active_session.state in ('own','waiting','paired') and active_session.finished_at is null
      and (active_session.deadline is null or active_session.deadline>now())
      and (active_session.expires_at is null or active_session.expires_at>now())
      and (active_session.friend_id=coalesce((p_data->>'friend_id')::uuid,(select user_id from public.study_sessions where id=(p_data->>'join_id')::uuid))
           or active_partner.user_id=coalesce((p_data->>'friend_id')::uuid,(select user_id from public.study_sessions where id=(p_data->>'join_id')::uuid)))
   ) then
    raise exception 'You already have an ongoing Study Together session with this player. Finish it or stop it before starting another.';
   end if;$guard$;
begin
    select pg_get_functiondef('public.study_action(text,jsonb)'::regprocedure) into definition;
    if position(old_guard in definition) = 0 then
        raise exception 'Expected Study Together slot rule was not found';
    end if;
    execute replace(definition, old_guard, new_guard);
end $$;
