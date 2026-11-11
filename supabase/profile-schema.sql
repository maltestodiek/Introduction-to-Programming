-- Applied to StudyDuel on 2026-11-11. For a fresh project only.
begin;
create table public.profiles (
 id uuid primary key references auth.users(id) on delete cascade,
 username text not null check (username ~ '^[A-Za-z0-9_]{3,24}$'),
 university text not null check (university = 'Nova SBE — prototype catalog'),
 languages text[] not null check (cardinality(languages)>0 and languages <@ array['English','Portuguese','German','Spanish','French','Italian','Dutch','Mandarin','Arabic','Hindi']),
 image_path text not null check (image_path like id::text || '/%'),
 xp integer not null default 0 check (xp>=0),
 win_streak integer not null default 0 check (win_streak>=0)
);
create unique index profiles_username_unique on public.profiles(lower(username));
create table public.profile_private (
 user_id uuid primary key references public.profiles(id) on delete cascade,
 courses text[] not null check (cardinality(courses)>0 and courses <@ array['Financial Modeling','Corporate Finance','Investments']),
 avatar jsonb not null,
 image_mode text not null check (image_mode in ('Avatar','Photo'))
);
alter table public.profiles enable row level security;
alter table public.profile_private enable row level security;
revoke all on public.profiles,public.profile_private from anon,authenticated;
grant select on public.profiles to authenticated;
grant insert(id,username,university,languages,image_path), update(username,university,languages,image_path) on public.profiles to authenticated;
grant select,insert,update on public.profile_private to authenticated;
create policy profiles_read on public.profiles for select to authenticated using ((select auth.uid()) is not null);
create policy profiles_insert on public.profiles for insert to authenticated with check (id=(select auth.uid()));
create policy profiles_update on public.profiles for update to authenticated using(id=(select auth.uid())) with check(id=(select auth.uid()));
create policy private_read on public.profile_private for select to authenticated using(user_id=(select auth.uid()));
create policy private_insert on public.profile_private for insert to authenticated with check(user_id=(select auth.uid()));
create policy private_update on public.profile_private for update to authenticated using(user_id=(select auth.uid())) with check(user_id=(select auth.uid()));
create function public.save_profile(p_username text,p_university text,p_languages text[],p_courses text[],p_avatar jsonb,p_image_mode text,p_image_path text) returns void language plpgsql security invoker set search_path='' as $$
begin
 if auth.uid() is null then raise exception 'Authentication required'; end if;
 if jsonb_typeof(p_avatar) <> 'object' or (select count(*) from jsonb_object_keys(p_avatar))<>5 or
 not (p_avatar->>'skin'=any(array['Light','Medium','Deep'])) or
 not (p_avatar->>'hair'=any(array['Short','Long','Curly','Bald'])) or
 not (p_avatar->>'hair_color'=any(array['Brown','Black','Blonde','Red','Silver'])) or
 not (p_avatar->>'clothing'=any(array['Indigo','Green','Coral','Gold'])) or
 not (p_avatar->>'accessory'=any(array['None','Glasses','Hat'])) or
 not (p_avatar ?& array['skin','hair','hair_color','clothing','accessory']) then
 raise exception 'Invalid avatar'; end if;
 insert into public.profiles(id,username,university,languages,image_path)
 values(auth.uid(),trim(p_username),p_university,p_languages,p_image_path)
 on conflict(id) do update set username=excluded.username,university=excluded.university,languages=excluded.languages,image_path=excluded.image_path;
 insert into public.profile_private(user_id,courses,avatar,image_mode)
 values(auth.uid(),p_courses,p_avatar,p_image_mode)
 on conflict(user_id) do update set courses=excluded.courses,avatar=excluded.avatar,image_mode=excluded.image_mode;
end; $$;
revoke all on function public.save_profile(text,text,text[],text[],jsonb,text,text) from public,anon;
grant execute on function public.save_profile(text,text,text[],text[],jsonb,text,text) to authenticated;
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types) values('profile-images','profile-images',false,5242880,array['image/png']);
create policy image_insert on storage.objects for insert to authenticated with check(bucket_id='profile-images' and (storage.foldername(name))[1]=(select auth.uid())::text);
create policy image_read on storage.objects for select to authenticated using(bucket_id='profile-images' and ((storage.foldername(name))[1]=(select auth.uid())::text or exists(select 1 from public.profiles p where p.image_path=name)));
create policy image_delete on storage.objects for delete to authenticated using(bucket_id='profile-images' and (storage.foldername(name))[1]=(select auth.uid())::text);
commit;
