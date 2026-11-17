-- Leaderboard. Apply after the profile and friends migrations. Read-only: creates no table and changes no data.
-- Ranks by profiles.xp, the Game XP settled from Battle results. Returns no user ids or friend codes.
begin;
create function public.leaderboard() returns jsonb language plpgsql stable security definer set search_path='' as $$
declare me uuid:=auth.uid();
begin
 if me is null or not exists(select 1 from public.profiles where id=me) then return jsonb_build_object('error','Sign in and complete your profile first.'); end if;
 return jsonb_build_object(
  'top',coalesce((select jsonb_agg(jsonb_build_object('rank',r.place,'username',r.username,'image_path',r.image_path,'xp',r.xp,'me',r.id=me) order by r.place,r.username)
   from (select p.id,p.username,p.image_path,p.xp,rank() over(order by p.xp desc) as place from public.profiles p order by p.xp desc,p.username limit 10) r),'[]'::jsonb),
  'me',(select jsonb_build_object('rank',1+(select count(*) from public.profiles o where o.xp>p.xp),'username',p.username,'image_path',p.image_path,'xp',p.xp,'me',true) from public.profiles p where p.id=me),
  'friends',coalesce((select jsonb_agg(jsonb_build_object('rank',f.place,'username',f.username,'image_path',f.image_path,'xp',f.xp,'me',f.id=me) order by f.place,f.username)
   from (select p.id,p.username,p.image_path,p.xp,rank() over(order by p.xp desc) as place from public.profiles p
         where p.id=me or exists(select 1 from public.friend_edges e where e.state='accepted' and ((e.low_id=me and e.high_id=p.id) or (e.high_id=me and e.low_id=p.id)))) f),'[]'::jsonb));
end $$;
revoke all on function public.leaderboard() from public, anon;
grant execute on function public.leaderboard() to authenticated;
commit;
