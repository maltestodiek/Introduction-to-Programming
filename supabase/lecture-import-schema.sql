-- Private, text-only lecture sources. The uploaded PDF itself is never stored.
begin;

create table public.lecture_imports (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.profiles(id) on delete cascade,
  name text not null,
  course text not null,
  language text not null,
  page_count integer not null check (page_count between 1 and 100),
  created_at timestamptz not null default now()
);

create table public.lecture_source_sections (
  id uuid primary key default gen_random_uuid(),
  lecture_import_id uuid not null references public.lecture_imports(id) on delete cascade,
  position integer not null check (position between 1 and 100),
  title text not null,
  page_start integer not null check (page_start >= 1),
  page_end integer not null check (page_end >= page_start),
  content text not null check (length(trim(content)) > 0),
  unique (lecture_import_id, position)
);

alter table public.lecture_imports enable row level security;
alter table public.lecture_source_sections enable row level security;
revoke all on public.lecture_imports, public.lecture_source_sections from public, anon, authenticated;
grant select on public.lecture_imports, public.lecture_source_sections to authenticated;

create policy lecture_imports_owner_read on public.lecture_imports
  for select to authenticated using (owner_id = auth.uid());
create policy lecture_sections_owner_read on public.lecture_source_sections
  for select to authenticated using (
    exists (
      select 1 from public.lecture_imports lecture
      where lecture.id = lecture_import_id and lecture.owner_id = auth.uid()
    )
  );

create function public.import_lecture_text(
  p_name text, p_course text, p_language text, p_page_count integer, p_sections jsonb
) returns jsonb
language plpgsql security definer set search_path='' as $$
declare
  me uuid := auth.uid();
  lecture_id uuid;
  section jsonb;
  position integer := 0;
  courses text[];
  languages text[];
begin
  if me is null then raise exception 'Sign in first'; end if;

  select private.courses, profile.languages into courses, languages
  from public.profile_private private
  join public.profiles profile on profile.id = private.user_id
  where private.user_id = me;

  if coalesce(length(trim(p_name)), 0) = 0
     or p_page_count not between 1 and 100
     or not exists (select 1 from unnest(courses) course where lower(trim(course)) = lower(trim(p_course)))
     or not coalesce(p_language = any(languages), false) then
    raise exception 'Enter a lecture name and select your course and language';
  end if;

  if jsonb_typeof(p_sections) is distinct from 'array'
     or jsonb_array_length(p_sections) not between 1 and 100 then
    raise exception 'Import between 1 and 100 text sections';
  end if;

  for section in select value from jsonb_array_elements(p_sections) loop
    if jsonb_typeof(section->'position') is distinct from 'number'
       or jsonb_typeof(section->'title') is distinct from 'string'
       or jsonb_typeof(section->'page_start') is distinct from 'number'
       or jsonb_typeof(section->'page_end') is distinct from 'number'
       or jsonb_typeof(section->'content') is distinct from 'string'
       or coalesce(length(trim(section->>'content')), 0) = 0 then
      raise exception 'Every lecture section needs text';
    end if;
  end loop;

  insert into public.lecture_imports(owner_id, name, course, language, page_count)
  values (me, trim(p_name), trim(p_course), p_language, p_page_count)
  returning id into lecture_id;

  for section in select value from jsonb_array_elements(p_sections) loop
    position := position + 1;
    insert into public.lecture_source_sections(
      lecture_import_id, position, title, page_start, page_end, content
    ) values (
      lecture_id, position, trim(section->>'title'),
      (section->>'page_start')::integer, (section->>'page_end')::integer,
      trim(section->>'content')
    );
  end loop;

  return jsonb_build_object('id', lecture_id, 'count', position);
end $$;

revoke all on function public.import_lecture_text(text, text, text, integer, jsonb) from public, anon;
grant execute on function public.import_lecture_text(text, text, text, integer, jsonb) to authenticated;

commit;
