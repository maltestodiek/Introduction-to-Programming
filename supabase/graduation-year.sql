begin;
alter table public.profile_private add column graduation_year integer check (graduation_year between 2000 and 2100);
create function public.save_profile_v3(p_username text,p_university text,p_languages text[],p_courses text[],p_avatar jsonb,p_image_mode text,p_image_path text,p_degree text,p_area text,p_graduation_year integer) returns void language plpgsql security invoker set search_path='' as $$
begin
 if p_graduation_year is not null and p_graduation_year not between 2000 and 2100 then raise exception 'Invalid graduation year'; end if;
 perform public.save_profile_v2(p_username,p_university,p_languages,p_courses,p_avatar,p_image_mode,p_image_path,p_degree,p_area);
 update public.profile_private set graduation_year=p_graduation_year where user_id=auth.uid();
end; $$;
revoke all on function public.save_profile_v3(text,text,text[],text[],jsonb,text,text,text,text,integer) from public,anon;
grant execute on function public.save_profile_v3(text,text,text[],text[],jsonb,text,text,text,text,integer) to authenticated;
commit;
