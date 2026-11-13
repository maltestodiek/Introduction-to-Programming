-- Basic Anki text-card import. Apply after the existing profile migrations.
begin;
create table public.anki_imports (
 id uuid primary key default gen_random_uuid(),
 owner_id uuid not null references public.profiles(id) on delete cascade,
 name text not null,
 course text not null,
 language text not null,
 created_at timestamptz not null default now()
);
create table public.anki_source_cards (
 id uuid primary key default gen_random_uuid(),
 import_id uuid not null references public.anki_imports(id) on delete cascade,
 position integer not null check(position between 1 and 100),
 front text not null check(length(trim(front))>0),
 back text not null check(length(trim(back))>0),
 unique(import_id, position)
);
alter table public.anki_imports enable row level security;
alter table public.anki_source_cards enable row level security;
revoke all on public.anki_imports, public.anki_source_cards from public, anon, authenticated;
grant select on public.anki_imports, public.anki_source_cards to authenticated;
create policy anki_imports_owner_read on public.anki_imports for select to authenticated using (owner_id=auth.uid());
create policy anki_source_cards_owner_read on public.anki_source_cards for select to authenticated using (
 exists(select 1 from public.anki_imports i where i.id=import_id and i.owner_id=auth.uid())
);

create function public.import_basic_anki(p_name text, p_course text, p_language text, p_cards jsonb)
returns jsonb language plpgsql security definer set search_path='' as $$
declare me uuid:=auth.uid(); import_id uuid; card jsonb; position integer:=0; courses text[]; languages text[];
begin
 if me is null then raise exception 'Sign in first'; end if;
 select p.courses, q.languages into courses, languages from public.profile_private p join public.profiles q on q.id=p.user_id where p.user_id=me;
 if coalesce(length(trim(p_name)),0)=0 or not exists(select 1 from unnest(courses) c where lower(trim(c))=lower(trim(p_course))) or not coalesce(p_language=any(languages),false) then
   raise exception 'Enter an import name and select your course and language';
 end if;
 if jsonb_typeof(p_cards) is distinct from 'array' or jsonb_array_length(p_cards) not between 1 and 100 then raise exception 'Import between 1 and 100 Basic text cards'; end if;
 for card in select value from jsonb_array_elements(p_cards) loop
   if jsonb_typeof(card->'front') is distinct from 'string' or jsonb_typeof(card->'back') is distinct from 'string' or coalesce(length(trim(card->>'front')),0)=0 or coalesce(length(trim(card->>'back')),0)=0 then
     raise exception 'Every imported card needs text on both sides';
   end if;
 end loop;
 insert into public.anki_imports(owner_id,name,course,language) values(me,trim(p_name),trim(p_course),p_language) returning id into import_id;
 for card in select value from jsonb_array_elements(p_cards) loop
   position:=position+1;
   insert into public.anki_source_cards(import_id,position,front,back) values(import_id,position,trim(card->>'front'),trim(card->>'back'));
 end loop;
 return jsonb_build_object('id',import_id,'count',position);
end $$;
revoke all on function public.import_basic_anki(text,text,text,jsonb) from public, anon;
grant execute on function public.import_basic_anki(text,text,text,jsonb) to authenticated;
commit;
