-- Deck studio: the signed-in student's own Study and Battle decks with their times.
-- Apply after battle-deck-catalog.sql. Additive: adds study_decks.created_at and a
-- read-only function; no existing column, policy or function is changed.
begin;

-- Study decks had no creation time. Every deck is reviewed before its first save,
-- so the earliest review is used for existing decks; decks without a review
-- (copies) keep an unknown creation time instead of a made-up one.
alter table public.study_decks add column if not exists created_at timestamptz;
update public.study_decks d
   set created_at=(select min(r.created_at) from public.study_reviews r where r.deck_id=d.id and r.created_at<=d.updated_at)
 where d.created_at is null;
alter table public.study_decks alter column created_at set default now();

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
  from public.study_decks d where d.creator_id=me
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
