-- Shared course names per university. Applied to the Supabase project on 2026-11-18, after the profile migrations. Read-only: creates no table and changes no data.
-- Returns course names only: no user ids, usernames or counts. See specs/tasks/study-fields-and-shared-courses.md.
begin;
create function public.university_courses(p_university text) returns text[] language sql stable security definer set search_path='' as $$
 with names as (
  select regexp_replace(btrim(c),'\s+',' ','g') as name
  from public.profiles p
  join public.profile_private pp on pp.user_id=p.id
  cross join lateral unnest(pp.courses) c
  where (select auth.uid()) is not null
    and length(btrim(coalesce(p_university,'')))>=2
    and lower(btrim(p.university))=lower(btrim(p_university))
 ),
 spellings as (select name,lower(name) as k,count(*) as n from names where name<>'' group by name),
 canonical as (select distinct on (k) name from spellings order by k,n desc,name)
 select coalesce(array_agg(name order by lower(name)),'{}'::text[]) from canonical;
$$;
revoke all on function public.university_courses(text) from public, anon;
grant execute on function public.university_courses(text) to authenticated;
commit;
