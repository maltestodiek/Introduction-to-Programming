begin;

-- Active courses stay in the column already used by the catalog and matchmaking.
alter table public.profile_private
    add column course_history jsonb not null default '{}' check (jsonb_typeof(course_history) = 'object'),
    drop constraint profile_private_courses_check,
    add constraint profile_private_courses_check check (
        cardinality(courses) between 0 and 50 and array_position(courses, null) is null
    );

-- A transfer may leave the current campus empty. First-time setup still needs a course.
create function public.require_first_profile_course() returns trigger
language plpgsql set search_path='' as $$
begin
    raise exception 'Choose at least one course';
end;
$$;
create trigger first_profile_course after insert on public.profile_private
for each row when (cardinality(new.courses)=0) execute function public.require_first_profile_course();

create function public.save_profile_v4(
    p_username text, p_university text, p_languages text[], p_courses text[],
    p_avatar jsonb, p_image_mode text, p_image_path text, p_degree text, p_area text,
    p_graduation_year integer, p_expected_university text
) returns void language plpgsql security definer set search_path='' as $$
declare
    me uuid := auth.uid();
    campus text;
    active_courses text[];
    history jsonb;
begin
    if me is null then raise exception 'Sign in first'; end if;
    -- Serialize transfers with matching so a pending search cannot be paired halfway through.
    perform pg_advisory_xact_lock(791146221);
    select p.university, v.courses, v.course_history into strict campus, active_courses, history
      from public.profiles p join public.profile_private v on v.user_id=p.id where p.id=me for update;
    if p_expected_university is distinct from campus then
        raise exception 'Your university changed. Reload your profile before saving.';
    end if;
    if campus <> trim(p_university) then
        if cardinality(active_courses)>0 then
            history := history || jsonb_build_object(campus, active_courses);
        end if;
        history := history - trim(p_university);
        delete from public.battle_searches where user_id=me;
        update public.battle_invites set state='cancelled' where state='pending' and me in (sender,recipient);
        update public.study_sessions set state='cancelled'
         where mode <> 'solo' and partner_id is null and state in ('own','waiting') and me in (user_id,friend_id);
    end if;
    if cardinality(p_courses)=0 and history='{}' then raise exception 'Choose at least one course'; end if;
    perform public.save_profile_v3(p_username,p_university,p_languages,p_courses,p_avatar,p_image_mode,
                                   p_image_path,p_degree,p_area,p_graduation_year);
    update public.profile_private set course_history=history where user_id=me;
end;
$$;
revoke all on function public.save_profile_v4(text,text,text[],text[],jsonb,text,text,text,text,integer,text) from public,anon;
grant execute on function public.save_profile_v4(text,text,text[],text[],jsonb,text,text,text,text,integer,text) to authenticated;

-- Study Together friend starts must obey the same active-course rule as random starts.
create function public.check_study_session_course() returns trigger
language plpgsql set search_path='' as $$
begin
    if not exists (
        select 1 from public.profiles p join public.profile_private v on v.user_id=p.id,
             unnest(v.courses) c
         where p.id=new.user_id and p.university=new.university and lower(trim(c))=lower(trim(new.course))
    ) then raise exception 'Choose a course at your current university in Profile'; end if;
    return new;
end;
$$;
create trigger study_session_active_course before insert on public.study_sessions
for each row when (new.mode <> 'solo') execute function public.check_study_session_course();

commit;
