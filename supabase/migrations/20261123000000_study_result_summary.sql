-- Completed Study Together sessions need a deck-by-deck result summary.
-- This only exposes the signed-in student's own snapshot, answers and their
-- matched partner's public username and aggregate scores.
create or replace function public.study_session_progress(p_session uuid)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
    session_row public.study_sessions;
    partner_row public.study_sessions;
    partner_username text;
    payload jsonb;
begin
    if auth.uid() is null then raise exception 'Sign in first'; end if;
    select * into session_row from public.study_sessions
    where id = p_session and user_id = auth.uid();
    if not found then raise exception 'Study session unavailable'; end if;

    select * into partner_row from public.study_sessions where id = session_row.partner_id;
    if partner_row.id is not null then
        select username into partner_username from public.profiles where id = partner_row.user_id;
    end if;

    select jsonb_build_object(
        'cursor', session_row.cursor,
        'total', session_row.total,
        'match_deadline', session_row.deadline,
        'mode', session_row.mode,
        'course', session_row.course,
        'deck_name', session_row.snapshot->>'name',
        'partner_username', partner_username,
        'answers', coalesce(jsonb_agg(jsonb_build_object('index', idx, 'correct', correct) order by idx), '[]'::jsonb)
    ) into payload
    from public.study_answers where session_id = p_session;

    if session_row.finished_at is not null or session_row.state in ('completed','expired','cancelled')
       or session_row.deadline <= now() then
        select payload || jsonb_build_object(
            'own_deck_score', coalesce((
                select count(*) from public.study_answers a
                where a.session_id = session_row.id and a.correct
                  and (session_row.cards->a.idx)->>'source_deck' = session_row.deck_id::text
            ), 0),
            'partner_deck_score', coalesce((
                select count(*) from public.study_answers a
                where a.session_id = session_row.id and a.correct
                  and (session_row.cards->a.idx)->>'source_deck' = partner_row.deck_id::text
            ), 0),
            'partner_own_deck_score', case when partner_row.id is null then null else coalesce((
                select count(*) from public.study_answers a
                where a.session_id = partner_row.id and a.correct
                  and (partner_row.cards->a.idx)->>'source_deck' = session_row.deck_id::text
            ), 0) end,
            'partner_partner_deck_score', case when partner_row.id is null then null else coalesce((
                select count(*) from public.study_answers a
                where a.session_id = partner_row.id and a.correct
                  and (partner_row.cards->a.idx)->>'source_deck' = partner_row.deck_id::text
            ), 0) end,
            'review', coalesce((
                select jsonb_agg(jsonb_build_object(
                    'index', a.idx,
                    'correct', a.correct,
                    'question', c.card->>'question',
                    'selected', (select opt->>'text' from jsonb_array_elements(c.card->'answers') opt where opt->>'id' = a.answer_id::text),
                    'solution', (select opt->>'text' from jsonb_array_elements(c.card->'answers') opt where opt->>'id' = c.card->>'correct_answer_id'),
                    'selected_id', a.answer_id,
                    'correct_answer_id', c.card->>'correct_answer_id',
                    'options', coalesce(c.card->'answers', '[]'::jsonb)
                ) order by a.idx)
                from public.study_answers a
                cross join lateral (select session_row.cards->a.idx as card) c
                where a.session_id = session_row.id
            ), '[]'::jsonb)
        ) into payload;
    end if;
    return payload;
end $$;

revoke all on function public.study_session_progress(uuid) from public, anon;
grant execute on function public.study_session_progress(uuid) to authenticated;
