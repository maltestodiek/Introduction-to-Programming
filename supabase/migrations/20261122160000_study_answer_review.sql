-- Return the signed-in student's submitted answers from the original session snapshot.
create or replace function public.study_session_progress(p_session uuid)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
    session_row public.study_sessions;
    payload jsonb;
begin
    if auth.uid() is null then raise exception 'Sign in first'; end if;
    select * into session_row from public.study_sessions where id = p_session and user_id = auth.uid();
    if not found then raise exception 'Study session unavailable'; end if;

    select jsonb_build_object('cursor', session_row.cursor, 'total', session_row.total, 'match_deadline', session_row.deadline,
        'answers', coalesce(jsonb_agg(jsonb_build_object('index', idx, 'correct', correct) order by idx), '[]'))
    into payload from public.study_answers where session_id = p_session;

    if session_row.finished_at is not null or session_row.state in ('completed','expired','cancelled')
       or session_row.deadline <= now() then
        select payload || jsonb_build_object('review', coalesce(jsonb_agg(jsonb_build_object(
            'index', a.idx, 'correct', a.correct, 'question', c.card->>'question',
            'selected', (select opt->>'text' from jsonb_array_elements(c.card->'answers') opt where opt->>'id' = a.answer_id::text),
            'solution', (select opt->>'text' from jsonb_array_elements(c.card->'answers') opt where opt->>'id' = c.card->>'correct_answer_id')
        ) order by a.idx), '[]')) into payload
        from public.study_answers a
        cross join lateral (select session_row.cards->a.idx as card) c
        where a.session_id = p_session;
    end if;
    return payload;
end $$;

revoke all on function public.study_session_progress(uuid) from public, anon;
grant execute on function public.study_session_progress(uuid) to authenticated;
