-- Read settled Battle results without changing profile totals or prior settlements.
create index if not exists battle_sessions_leaderboard_settled_at_idx
    on public.battle_sessions (settled_at) where settled_at is not null;

create function public.leaderboard_30_days() returns jsonb
language plpgsql stable security definer set search_path = '' as $$
declare
    viewer uuid := auth.uid();
    campus text;
    standings jsonb;
begin
    select university into campus from public.profiles where id = viewer;
    if not found then
        return jsonb_build_object('error', 'Sign in and complete your profile first.');
    end if;

    with recent_xp as (
        select r.user_id, sum(r.game_xp_delta) as xp
        from public.battle_sessions s
        join public.battle_rounds r on r.session_id = s.id
        where s.settled_at > now() - interval '720 hours' and s.settled_at <= now()
        group by r.user_id
    ), scores as (
        select p.id, p.username, p.university, p.image_path, coalesce(x.xp, 0) as xp
        from public.profiles p left join recent_xp x on x.user_id = p.id
    ), scoped as (
        select 'top' as scope, s.* from scores s
        union all
        select 'university', s.* from scores s where s.university = campus and btrim(campus) <> ''
        union all
        select 'friends', s.* from scores s where s.id = viewer or exists (
            select 1 from public.friend_edges e where e.state = 'accepted'
              and ((e.low_id = viewer and e.high_id = s.id) or (e.high_id = viewer and e.low_id = s.id))
        )
    ), ranked as (
        select scope, username, id = viewer as me,
               rank() over (partition by scope order by xp desc) as place,
               row_number() over (partition by scope order by xp desc, username, id) as position,
               jsonb_build_object('username', username, 'university', university,
                                  'image_path', image_path, 'xp', xp, 'me', id = viewer) as player
        from scoped
    ), rows as (
        select scope, position, me, player || jsonb_build_object('rank', place) as entry from ranked
    )
    select jsonb_build_object(
        'top', coalesce(jsonb_agg(entry order by position) filter (where scope = 'top' and position <= 10), '[]'),
        'me', (select entry from rows where scope = 'top' and me),
        'university', coalesce(jsonb_agg(entry order by position) filter (where scope = 'university' and position <= 10), '[]'),
        'friends', jsonb_agg(entry order by position) filter (where scope = 'friends')
    ) into standings from rows;
    return standings;
end;
$$;
revoke all on function public.leaderboard_30_days() from public, anon;
grant execute on function public.leaderboard_30_days() to authenticated;
