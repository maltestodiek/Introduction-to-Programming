-- Studio visibility is personal to the deck's sole creator.
begin;

alter table public.study_decks add column hidden_from_studio boolean not null default false;

create function public.remove_study_deck_from_studio(p_deck_id uuid)
returns void language plpgsql security definer set search_path='' as $$
begin
    update public.study_decks set hidden_from_studio=true
    where id=p_deck_id and creator_id=auth.uid();
    if not found then raise exception 'Study deck unavailable'; end if;
end $$;
revoke all on function public.remove_study_deck_from_studio(uuid) from public, anon;
grant execute on function public.remove_study_deck_from_studio(uuid) to authenticated;

create or replace function public.deck_studio()
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare me uuid:=auth.uid();
begin
 if me is null then raise exception 'Sign in first'; end if;
 return jsonb_build_object('decks',coalesce((select jsonb_agg(x.deck order by x.sort_at desc) from (
  select jsonb_build_object(
    'kind','study','id',d.id,'name',d.snapshot->>'name','course',d.snapshot->>'course','language',d.snapshot->>'language',
    'count',jsonb_array_length(d.snapshot->'cards'),'revision',d.revision,
    'created_at',d.created_at,'updated_at',d.updated_at,'published_at',d.published_at
  ) deck, coalesce(d.created_at,d.updated_at) sort_at
  from public.study_decks d where d.creator_id=me and not d.hidden_from_studio
  union all
  select jsonb_build_object(
    'kind','battle','id',b.id,'name',b.name,'course',b.course,'language',b.language,
    'count',jsonb_array_length(b.cards),'created_at',b.created_at,'source_deck_id',b.source_deck_id
  ), b.created_at
  from public.battle_decks b where b.creator_id=me
 ) x),'[]'::jsonb));
end $$;

revoke all on function public.deck_studio() from public,anon;
grant execute on function public.deck_studio() to authenticated;

commit;
