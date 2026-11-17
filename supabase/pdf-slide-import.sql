-- Text-based PDF slides become the same private source-card format as Anki.
begin;
alter table public.anki_imports add column if not exists source_type text not null default 'anki' check(source_type in ('anki','pdf'));
create or replace function public.import_pdf_slides(p_name text,p_course text,p_language text,p_cards jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare me uuid:=auth.uid(); import_id uuid; card jsonb; position integer:=0; courses text[]; languages text[];
begin
 if me is null then raise exception 'Sign in first';end if;
 select p.courses,q.languages into courses,languages from public.profile_private p join public.profiles q on q.id=p.user_id where p.user_id=me;
 if coalesce(length(trim(p_name)),0)=0 or not exists(select 1 from unnest(courses) c where lower(trim(c))=lower(trim(p_course))) or not coalesce(p_language=any(languages),false) then raise exception 'Enter an import name and select your course and language';end if;
 if jsonb_typeof(p_cards) is distinct from 'array' or jsonb_array_length(p_cards) not between 1 and 100 then raise exception 'Import between 1 and 100 PDF text sources';end if;
 for card in select value from jsonb_array_elements(p_cards) loop
  if jsonb_typeof(card->'front') is distinct from 'string' or jsonb_typeof(card->'back') is distinct from 'string' or coalesce(length(trim(card->>'front')),0)=0 or coalesce(length(trim(card->>'back')),0)=0 then raise exception 'Every PDF source needs text';end if;
 end loop;
 insert into public.anki_imports(owner_id,name,course,language,source_type) values(me,trim(p_name),trim(p_course),p_language,'pdf') returning id into import_id;
 for card in select value from jsonb_array_elements(p_cards) loop position:=position+1;insert into public.anki_source_cards(import_id,position,front,back) values(import_id,position,trim(card->>'front'),trim(card->>'back'));end loop;
 return jsonb_build_object('id',import_id,'count',position);
end $$;
revoke all on function public.import_pdf_slides(text,text,text,jsonb) from public,anon;
grant execute on function public.import_pdf_slides(text,text,text,jsonb) to authenticated;
commit;
