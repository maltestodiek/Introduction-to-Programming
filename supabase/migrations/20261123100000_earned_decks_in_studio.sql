-- List already-earned Study Together snapshots alongside personal decks.
begin;

alter table public.study_shared add column hidden_from_studio boolean not null default false;

create or replace function public.remove_study_deck_from_studio(p_deck_id uuid)
returns void language plpgsql security definer set search_path='' as $$
begin
    update public.study_decks set hidden_from_studio=true
    where id=p_deck_id and creator_id=auth.uid();
    if found then return; end if;
    update public.study_shared set hidden_from_studio=true
    where id=p_deck_id and user_id=auth.uid();
    if not found then raise exception 'Study deck unavailable'; end if;
end $$;

create or replace function public.deck_studio()
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare me uuid:=auth.uid();
begin
    if me is null then raise exception 'Sign in first'; end if;
    return jsonb_build_object('decks',coalesce((
        select jsonb_agg(x.deck order by x.sort_at desc, x.deck->>'id')
        from (
            select jsonb_build_object(
                'kind','study','id',d.id,'name',d.snapshot->>'name','course',d.snapshot->>'course',
                'language',d.snapshot->>'language','count',jsonb_array_length(d.snapshot->'cards'),
                'revision',d.revision,'created_at',d.created_at,'updated_at',d.updated_at,
                'published_at',d.published_at,'author',p.username
            ) as deck, coalesce(d.created_at,d.updated_at) as sort_at
            from public.study_decks d
            left join public.study_decks source on source.id=d.course_source_id
            left join public.profiles p on p.id=coalesce(source.creator_id,d.creator_id)
            where d.creator_id=me and not d.hidden_from_studio
            union all
            select jsonb_build_object(
                'kind','battle','id',b.id,'name',b.name,'course',b.course,'language',b.language,
                'count',jsonb_array_length(b.cards),'created_at',b.created_at,
                'source_deck_id',b.source_deck_id,'author',p.username
            ), b.created_at
            from public.battle_decks b left join public.profiles p on p.id=b.creator_id
            where b.creator_id=me
            union all
            select jsonb_build_object(
                'kind','shared','id',s.id,'name',s.snapshot->>'name','course',s.snapshot->>'course',
                'language',s.snapshot->>'language','count',jsonb_array_length(s.snapshot->'cards'),
                'received_at',s.created_at,'author',s.snapshot->>'author'
            ), s.created_at
            from public.study_shared s
            where s.user_id=me and not s.hidden_from_studio
        ) x
    ),'[]'::jsonb));
end $$;

commit;
