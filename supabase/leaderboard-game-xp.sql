-- Leaderboard Game XP repair. Apply after leaderboard-schema.sql.
-- Keeps existing profiles and reads only Battle Game XP, never Creator XP or Total XP.
create or replace function public.leaderboard() returns jsonb language plpgsql stable security definer set search_path='' as $$
declare me uuid:=auth.uid();
begin
 if me is null or not exists(select 1 from public.profiles where id=me) then return jsonb_build_object('error','Sign in and complete your profile first.'); end if;
 return jsonb_build_object(
  'top',coalesce((select jsonb_agg(jsonb_build_object('rank',r.place,'username',r.username,'image_path',r.image_path,'xp',r.game_xp,'me',r.id=me) order by r.place,r.username) from (select p.id,p.username,p.image_path,p.game_xp,rank() over(order by p.game_xp desc) as place from public.profiles p order by p.game_xp desc,p.username limit 10) r),'[]'::jsonb),
  'me',(select jsonb_build_object('rank',1+(select count(*) from public.profiles o where o.game_xp>p.game_xp),'username',p.username,'image_path',p.image_path,'xp',p.game_xp,'me',true) from public.profiles p where p.id=me),
  'friends',coalesce((select jsonb_agg(jsonb_build_object('rank',f.place,'username',f.username,'image_path',f.image_path,'xp',f.game_xp,'me',f.id=me) order by f.place,f.username) from (select p.id,p.username,p.image_path,p.game_xp,rank() over(order by p.game_xp desc) as place from public.profiles p where p.id=me or exists(select 1 from public.friend_edges e where e.state='accepted' and ((e.low_id=me and e.high_id=p.id) or (e.high_id=me and e.low_id=p.id)))) f),'[]'::jsonb));
end $$;
revoke all on function public.leaderboard() from public, anon;
grant execute on function public.leaderboard() to authenticated;
