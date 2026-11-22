-- Show every live Friend invitation to its recipient. Compatibility is checked
-- again when the recipient accepts, rather than hiding the invitation.
do $$
declare
    definition text;
    old_filter text := $filter$where session_row.friend_id=me and session_row.mode='friend' and session_row.state='waiting' and session_row.expires_at>now() and public.has_study_invite_deck(me,session_row.course,session_row.language,session_row.total)),'[]'),$filter$;
    new_filter text := $filter$where session_row.friend_id=me and session_row.mode='friend' and session_row.state='waiting' and session_row.expires_at>now()),'[]'),$filter$;
begin
    select pg_get_functiondef('public.study_action(text,jsonb)'::regprocedure) into definition;
    if position(old_filter in definition) = 0 then
        raise exception 'Expected Study invitation visibility rule was not found';
    end if;
    execute replace(definition, old_filter, new_filter);
end $$;
