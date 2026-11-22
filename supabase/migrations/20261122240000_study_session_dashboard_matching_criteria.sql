-- Return matching criteria only for the signed-in student's own Study sessions.
-- The dashboard already scopes sessions to auth.uid(); course and language are
-- needed to explain why a Study Together session was paired or invited.
create or replace function public.study_session_dashboard() returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    listing jsonb;
    sessions jsonb;
begin
    listing := public.study_action('list', '{}'::jsonb);
    if listing ? 'error' then return listing; end if;
    select coalesce(jsonb_agg(item || jsonb_build_object(
        'state', case when s.finished_at is not null and p.id is not null
                            and p.finished_at is null and p.left_at is null and s.timeout_result is null
                      then 'waiting_for_finish' else item->>'state' end,
        'course', s.course, 'language', s.language,
        'friend_username', invited_friend.username,
        'answered', own.answered, 'score', own.score,
        'opponent_score', other.score,
        'result', case when s.timeout_result is not null then s.timeout_result
                       when s.finished_at is not null and p.left_at is not null then 'Win'
                       when other.score is not null then case when own.score > other.score then 'Win'
                            when own.score < other.score then 'Loss' else 'Draw' end
                       when s.finished_at is not null and s.mode='solo' then 'Completed' end
    ) order by seq), '[]'::jsonb) into sessions
    from jsonb_array_elements(listing->'sessions') with ordinality as entries(item, seq)
    join public.study_sessions s on s.id=(item->>'id')::uuid and s.user_id=auth.uid()
    left join public.study_sessions p on p.id=s.partner_id and p.partner_id=s.id
    left join public.profiles invited_friend on invited_friend.id=s.friend_id
    cross join lateral (
        select count(*) as answered, count(*) filter(where a.correct) as score
        from public.study_answers a where a.session_id=s.id
    ) own
    left join lateral (
        select count(*) filter(where a.correct) as score from public.study_answers a where a.session_id=p.id
    ) other on p.id is not null and (s.timeout_result is not null or s.finished_at is not null)
              and (p.finished_at is not null or p.left_at is not null or s.deadline<=now());
    return jsonb_set(listing, '{sessions}', sessions);
end $$;
revoke all on function public.study_session_dashboard() from public, anon;
grant execute on function public.study_session_dashboard() to authenticated;
