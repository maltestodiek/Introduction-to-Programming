-- Battle Deck availability before matchmaking. Apply after battle-xp-only.sql.
-- A search or random friend invitation may only be created when a matching
-- public 15-question Battle Deck is already available.
begin;

create or replace function public.battle_deck_available(
 p_university text,p_course text,p_language text
) returns boolean language sql stable security definer set search_path='' as $$
 select exists(
  select 1 from public.battle_decks deck
  where deck.university=p_university
   and lower(trim(deck.course))=lower(trim(p_course))
   and deck.language=p_language
 );
$$;

create or replace function public.battle_deck_availability(
 p_course text,p_language text
) returns jsonb language plpgsql stable security definer set search_path='' as $$
declare me uuid:=auth.uid(); campus text; langs text[]; profile_courses text[];
begin
 if me is null then raise exception 'Sign in first'; end if;
 select university,languages into campus,langs from public.profiles where id=me;
 select courses into profile_courses from public.profile_private where user_id=me;
 if campus is null or profile_courses is null then raise exception 'Complete your profile first'; end if;
 if not exists(select 1 from unnest(profile_courses) c where lower(trim(c))=lower(trim(p_course)))
    or not coalesce(p_language=any(langs),false) then
  raise exception 'Choose one of your courses and languages';
 end if;
 return jsonb_build_object('available',public.battle_deck_available(campus,p_course,p_language));
end $$;

create or replace function public.enforce_battle_deck_availability()
returns trigger language plpgsql security definer set search_path='' as $$
begin
 if new.source_kind='random'
    and not public.battle_deck_available(new.university,new.course,new.language) then
  raise exception 'No eligible Battle Deck is available for this course and language';
 end if;
 return new;
end $$;

drop trigger if exists battle_search_requires_deck on public.battle_searches;
create trigger battle_search_requires_deck
 before insert or update of source_kind,university,course,language on public.battle_searches
 for each row execute function public.enforce_battle_deck_availability();

drop trigger if exists battle_invite_requires_deck on public.battle_invites;
create trigger battle_invite_requires_deck
 before insert or update of source_kind,university,course,language on public.battle_invites
 for each row execute function public.enforce_battle_deck_availability();

revoke all on function public.battle_deck_available(text,text,text),public.battle_deck_availability(text,text),public.enforce_battle_deck_availability() from public,anon,authenticated;
grant execute on function public.battle_deck_availability(text,text) to authenticated;
commit;
