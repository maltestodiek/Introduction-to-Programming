-- Battle Deck catalogue for the Decks page. Apply after battle-deck-availability.sql.
-- Lists public Battle Decks of the signed-in student's university and courses,
-- with metadata only: the 15 Battle questions stay hidden until a Battle starts.
-- Read-only and additive: no table, policy or existing function is changed.
begin;

create or replace function public.battle_deck_catalog()
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare me uuid:=auth.uid(); campus text; profile_courses text[];
begin
 if me is null then raise exception 'Sign in first'; end if;
 select p.university into campus from public.profiles p where p.id=me;
 select pp.courses into profile_courses from public.profile_private pp where pp.user_id=me;
 if campus is null or profile_courses is null then return jsonb_build_object('decks','[]'::jsonb); end if;
 return jsonb_build_object('decks',coalesce((
  select jsonb_agg(jsonb_build_object(
    'id',b.id,'name',b.name,'course',b.course,'language',b.language,
    'author',coalesce(p.username,'Student'),'count',jsonb_array_length(b.cards),
    'owned',b.creator_id=me,'created_at',b.created_at
  ) order by b.created_at desc)
  from public.battle_decks b left join public.profiles p on p.id=b.creator_id
  where b.university=campus
   and exists(select 1 from unnest(profile_courses) c where lower(trim(c))=lower(trim(b.course)))
 ),'[]'::jsonb));
end $$;

revoke all on function public.battle_deck_catalog() from public,anon;
grant execute on function public.battle_deck_catalog() to authenticated;

commit;
