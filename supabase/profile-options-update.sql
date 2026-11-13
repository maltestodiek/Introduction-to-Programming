-- Applied 2026-11-11 after profile-schema.sql. Preserves existing profiles.
begin;
alter table public.profiles drop constraint profiles_university_check;
alter table public.profiles add constraint profiles_university_check check (length(trim(university)) between 2 and 160);
alter table public.profile_private drop constraint profile_private_courses_check;
alter table public.profile_private add constraint profile_private_courses_check check (cardinality(courses) between 1 and 50 and array_position(courses,null) is null);
alter table public.profile_private add column degree text not null default 'Not specified' check(degree in ('Not specified','Bachelor''s','Master''s','Doctorate','Associate','Diploma / certificate','Other'));
alter table public.profile_private add column area text not null default '' check(length(area)<=120);
create function public.save_profile_v2(p_username text,p_university text,p_languages text[],p_courses text[],p_avatar jsonb,p_image_mode text,p_image_path text,p_degree text,p_area text) returns void language plpgsql security invoker set search_path='' as $$
begin
 if auth.uid() is null then raise exception 'Authentication required'; end if;
 if not coalesce(jsonb_typeof(p_avatar)='object' and p_avatar ?& array['skin','hair','hair_color','clothing','accessory'] and
 p_avatar->>'skin'=any(array['Light','Medium','Deep','Blue','Green','Purple','Pink','Gold']) and
 p_avatar->>'hair'=any(array['Short','Long','Curly','Bald','Bob','Ponytail','Bun','Mohawk','Spiky','Side swept']) and
 p_avatar->>'hair_color'=any(array['Brown','Black','Blonde','Red','Silver']) and
 p_avatar->>'clothing'=any(array['Indigo','Green','Coral','Gold']) and
 p_avatar->>'accessory'=any(array['None','Glasses','Hat','Sunglasses','Headphones','Earrings','Headband','Bow','Crown','Scarf','Monocle']),false) then raise exception 'Invalid avatar';end if;
 if (select count(*) from jsonb_object_keys(p_avatar))<>5 then raise exception 'Invalid avatar';end if;
 if exists(select 1 from unnest(p_courses) c where length(trim(c)) not between 1 and 120) then raise exception 'Invalid course';end if;
 insert into public.profiles(id,username,university,languages,image_path)
 values(auth.uid(),trim(p_username),trim(p_university),p_languages,p_image_path)
 on conflict(id) do update set username=excluded.username,university=excluded.university,languages=excluded.languages,image_path=excluded.image_path;
 insert into public.profile_private(user_id,courses,avatar,image_mode,degree,area)
 values(auth.uid(),p_courses,p_avatar,p_image_mode,p_degree,trim(p_area))
 on conflict(user_id) do update set courses=excluded.courses,avatar=excluded.avatar,image_mode=excluded.image_mode,degree=excluded.degree,area=excluded.area;
end; $$;
revoke all on function public.save_profile_v2(text,text,text[],text[],jsonb,text,text,text,text) from public,anon;
grant execute on function public.save_profile_v2(text,text,text[],text[],jsonb,text,text,text,text) to authenticated;
commit;
