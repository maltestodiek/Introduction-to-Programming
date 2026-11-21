-- Apply after study-deck-publication-course-variable.sql.
-- Exposes only the public publication time needed for client-side list sorting.
begin;

create or replace function public.study_public_action(p_action text,p_data jsonb default '{}') returns jsonb language plpgsql security definer set search_path='' as $$
declare
 me uuid:=auth.uid(); campus text; langs text[]; profile_courses text[]; did uuid; source public.study_decks; copy_id uuid;
begin
 if me is null then raise exception 'Sign in first';end if;
 select university,languages into campus,langs from public.profiles where id=me;
 select pp.courses into profile_courses from public.profile_private pp where pp.user_id=me;
 if campus is null or profile_courses is null then raise exception 'Complete your profile first';end if;
 if p_action='list' then
  return jsonb_build_object(
   'published_ids',coalesce((select jsonb_agg(id) from public.study_decks where creator_id=me and published_at is not null),'[]'),
   'decks',coalesce((select jsonb_agg(jsonb_build_object('id',d.id,'name',d.snapshot->>'name','course',d.snapshot->>'course','language',d.snapshot->>'language','author',p.username,'count',jsonb_array_length(d.snapshot->'cards'),'owned',d.creator_id=me,'published_at',d.published_at) order by d.published_at desc) from public.study_decks d join public.profiles p on p.id=d.creator_id where d.published_at is not null and (d.creator_id=me or (p.university=campus and (d.snapshot->>'language')=any(langs) and exists(select 1 from unnest(profile_courses) course_option where lower(trim(course_option))=lower(trim(d.snapshot->>'course')))))),'[]')
  );
 end if;
 did:=(p_data->>'id')::uuid;
 if did is null then raise exception 'Choose a Study deck';end if;
 if p_action in ('publish','unpublish') then
  if not exists(select 1 from public.study_decks where id=did and creator_id=me) then raise exception 'Study deck unavailable';end if;
  update public.study_decks set published_at=case when p_action='publish' then now() else null end,updated_at=now() where id=did;
  return jsonb_build_object('id',did,'published',p_action='publish');
 end if;
 select d.* into source from public.study_decks d join public.profiles p on p.id=d.creator_id where d.id=did and d.published_at is not null and d.creator_id<>me and p.university=campus and (d.snapshot->>'language')=any(langs) and exists(select 1 from unnest(profile_courses) course_option where lower(trim(course_option))=lower(trim(d.snapshot->>'course')));
 if source.id is null then raise exception 'Published Study deck unavailable';end if;
 if p_action='deck' then return public.study_decorate(public.study_snapshot(source.snapshot,source.id,source.creator_id)||jsonb_build_object('revision',source.revision,'legacy',false),me);end if;
 if p_action='copy' then copy_id:=gen_random_uuid();insert into public.study_decks(id,creator_id,snapshot) values(copy_id,me,source.snapshot);return jsonb_build_object('id',copy_id);end if;
 raise exception 'Unknown Study publication action';
end $$;

revoke all on function public.study_public_action(text,jsonb) from public,anon;
grant execute on function public.study_public_action(text,jsonb) to authenticated;
commit;
