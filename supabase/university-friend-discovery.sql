-- Discover and request friendship with profiles at the caller's own university.
-- Only the same public identity fields as friend-code lookup are returned.
begin;

create or replace function public.university_friend_profiles() returns jsonb
language plpgsql security definer set search_path='' as $$
declare me uuid:=auth.uid(); campus text;
begin
 if me is null then raise exception 'Sign in required'; end if;
 select university into campus from public.profiles where id=me;
 if campus is null then return jsonb_build_object('error','Complete your profile first.'); end if;
 return jsonb_build_object('university',campus,'profiles',coalesce((
  select jsonb_agg(jsonb_build_object('id',p.id,'username',p.username,'image_path',p.image_path) order by lower(p.username),p.id)
  from public.profiles p
  where p.university=campus and p.id<>me
   and not exists(select 1 from public.friend_edges e where e.low_id=least(me,p.id) and e.high_id=greatest(me,p.id))
 ),'[]'::jsonb));
end $$;

create or replace function public.request_university_friend(p_user_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare me uuid:=auth.uid(); campus text; other_id uuid; lo uuid; hi uuid; edge public.friend_edges; n integer;
begin
 if me is null then raise exception 'Sign in required'; end if;
 select university into campus from public.profiles where id=me;
 if campus is null then return jsonb_build_object('error','Complete your profile first.'); end if;
 insert into public.friend_limits as f(user_id,action,bucket,count) values(me,'university_request',date_trunc('minute',now()),1)
 on conflict(user_id,action) do update set bucket=excluded.bucket,count=case when f.bucket=excluded.bucket then f.count+1 else 1 end returning count into n;
 if n>5 then return jsonb_build_object('error','Too many requests. Please wait a minute and try again.'); end if;
 select id into other_id from public.profiles where id=p_user_id and id<>me and university=campus;
 if other_id is null then return jsonb_build_object('error','Choose a student from your university.'); end if;
 lo:=least(me,other_id);hi:=greatest(me,other_id);
 perform pg_advisory_xact_lock(hashtextextended(lo::text||hi::text,0));
 select * into edge from public.friend_edges where low_id=lo and high_id=hi for update;
 if edge.id is not null then return jsonb_build_object('error',case when edge.state='accepted' then 'You are already friends.' when edge.sender=me then 'A request is already pending.' else 'This student already invited you. Accept their incoming request.' end); end if;
 insert into public.friend_edges(low_id,high_id,sender,state) values(lo,hi,me,'pending');
 return jsonb_build_object('message','Friend request sent.');
end $$;

revoke all on function public.university_friend_profiles(),public.request_university_friend(uuid) from public,anon,authenticated;
grant execute on function public.university_friend_profiles(),public.request_university_friend(uuid) to authenticated;
commit;
