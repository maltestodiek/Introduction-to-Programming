-- Third feature. Apply once after the existing profile migrations.
begin;
create table public.deck_reviews (
 id uuid primary key default gen_random_uuid(),
 creator_id uuid not null references public.profiles(id) on delete cascade,
 draft_id uuid not null,
 snapshot jsonb not null,
 created_at timestamptz not null default now()
);
create table public.decks (
 id uuid primary key default gen_random_uuid(),
 creator_id uuid not null references public.profiles(id) on delete cascade,
 draft_id uuid not null,
 university text not null,
 course text not null,
 name text not null,
 cards jsonb not null check(jsonb_typeof(cards)='array' and jsonb_array_length(cards)=15),
 snapshot jsonb not null,
 created_at timestamptz not null default now(),
 unique(creator_id,draft_id)
);
create index decks_course_idx on public.decks(university,lower(course));
alter table public.decks enable row level security;
alter table public.deck_reviews enable row level security;
revoke all on public.decks,public.deck_reviews from public,anon,authenticated;
grant select on public.decks to authenticated;
create policy decks_read on public.decks for select to authenticated using (
 university=(select p.university from public.profiles p where p.id=auth.uid())
);
create function public.check_deck(p_draft jsonb) returns void language plpgsql security invoker set search_path='' as $$
declare c jsonb; a jsonb; ids text[]:='{}'; correct_count integer;
begin
 if jsonb_typeof(p_draft) is distinct from 'object' or
 jsonb_typeof(p_draft->'name') is distinct from 'string' or length(trim(p_draft->>'name'))=0 or
 jsonb_typeof(p_draft->'course') is distinct from 'string' or length(trim(p_draft->>'course'))=0 then raise exception 'Enter a deck name and course';end if;
 if jsonb_typeof(p_draft->'id') is distinct from 'string' then raise exception 'Invalid draft identity';end if;
 perform (p_draft->>'id')::uuid;
 if jsonb_typeof(p_draft->'cards') is distinct from 'array' then raise exception 'Exactly 15 cards required';end if;
 if jsonb_array_length(p_draft->'cards')<>15 then raise exception 'Exactly 15 cards required';end if;
 for c in select value from jsonb_array_elements(p_draft->'cards') loop
   if c?'allow_calculator' and jsonb_typeof(c->'allow_calculator') is distinct from 'boolean' then raise exception 'Calculator permission must be true or false';end if;
  if jsonb_typeof(c->'id') is distinct from 'string' or jsonb_typeof(c->'question') is distinct from 'string' or length(trim(c->>'question'))=0 then raise exception 'Complete the question';end if;
  perform (c->>'id')::uuid;
  if c->>'id'=any(ids) then raise exception 'Duplicate identity';end if; ids:=array_append(ids,c->>'id');
  if jsonb_typeof(c->'answers') is distinct from 'array' then raise exception 'Four answers required';end if;
  if jsonb_array_length(c->'answers')<>4 then raise exception 'Four answers required';end if;
  correct_count:=0;
  for a in select value from jsonb_array_elements(c->'answers') loop
   if jsonb_typeof(a->'id') is distinct from 'string' or jsonb_typeof(a->'text') is distinct from 'string' or length(trim(a->>'text'))=0 then raise exception 'Complete all answers';end if;
   perform (a->>'id')::uuid;
   if a->>'id'=any(ids) then raise exception 'Duplicate identity';end if;ids:=array_append(ids,a->>'id');
   if jsonb_typeof(c->'correct_answer_id')='string' and a->>'id'=c->>'correct_answer_id' then correct_count:=correct_count+1;end if;
  end loop;
  if correct_count<>1 then raise exception 'One correct answer required';end if;
 end loop;
end $$;
revoke all on function public.check_deck(jsonb) from public,anon,authenticated;
create function public.review_deck(p_draft jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare r uuid;
begin
 if auth.uid() is null then raise exception 'Sign in first';end if;
 perform public.check_deck(p_draft);
 if not exists(select 1 from public.profile_private p,unnest(p.courses) c where p.user_id=auth.uid() and lower(trim(c))=lower(trim(p_draft->>'course'))) then raise exception 'Select a course from your profile';end if;
 insert into public.deck_reviews(creator_id,draft_id,snapshot) values(auth.uid(),(p_draft->>'id')::uuid,p_draft) returning id into r;
 return jsonb_build_object('id',r);
end $$;
create function public.publish_deck(p_review_id uuid,p_draft jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.deck_reviews; d public.decks; campus text; enrolled_course text;
begin
 if auth.uid() is null then raise exception 'Sign in first';end if;
 perform public.check_deck(p_draft);
 select * into r from public.deck_reviews where id=p_review_id and creator_id=auth.uid();
 if not found or r.snapshot<>p_draft then raise exception 'Review this exact deck first';end if;
 select p.university into campus from public.profiles p where p.id=auth.uid();
 select c into enrolled_course from public.profile_private p,unnest(p.courses) c where p.user_id=auth.uid() and lower(trim(c))=lower(trim(p_draft->>'course')) limit 1;
 if campus is null or enrolled_course is null then raise exception 'Complete your profile and select this course';end if;
 perform pg_advisory_xact_lock(hashtextextended(auth.uid()::text||r.draft_id::text,0));
 select * into d from public.decks where creator_id=auth.uid() and draft_id=r.draft_id;
 if found then
  if d.snapshot<>p_draft then raise exception 'This draft was already published with different content';end if;
  return jsonb_build_object('id',d.id);
 end if;
 insert into public.decks(creator_id,draft_id,university,course,name,cards,snapshot)
 values(auth.uid(),r.draft_id,campus,trim(enrolled_course),trim(p_draft->>'name'),p_draft->'cards',p_draft) returning * into d;
 return jsonb_build_object('id',d.id);
end $$;
revoke all on function public.review_deck(jsonb),public.publish_deck(uuid,jsonb) from public,anon;
grant execute on function public.review_deck(jsonb),public.publish_deck(uuid,jsonb) to authenticated;
commit;
