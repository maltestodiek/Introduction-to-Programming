begin;
create table public.play_update_reads (
 user_id uuid not null references public.profiles(id) on delete cascade,
 event_key text not null,
 primary key(user_id,event_key)
);
alter table public.play_update_reads enable row level security;
revoke all on public.play_update_reads from public,anon,authenticated;

-- Existing settled games are history. Current invitations and live matches are actionable.
insert into public.play_update_reads
 select r.user_id,'battle:result:'||r.session_id from public.battle_rounds r
 join public.battle_sessions s on s.id=r.session_id where s.settled_at is not null
 union all
 select s.user_id,'study:result:'||s.id from public.study_sessions s
 join public.study_sessions p on p.id=s.partner_id
 where s.timeout_result is not null or (s.finished_at is not null and (p.finished_at is not null or p.left_at is not null));

create function public.play_unread_updates(p_seen text[] default '{}') returns jsonb
language plpgsql security definer set search_path='' as $$
declare me uuid:=auth.uid(); active text[];
begin
 if me is null then raise exception 'Sign in first'; end if;
 select array(select event_key from (
   select 'battle:invite:'||id as event_key from public.battle_invites
    where recipient=me and state='pending' and expires_at>now()
   union all
   select 'battle:'||(case when s.settled_at is null then 'match' else 'result' end)||':'||s.id
    from public.battle_rounds r join public.battle_sessions s on s.id=r.session_id
    where r.user_id=me and (s.p2 is not null or s.settled_at is not null)
   union all
   select 'study:invite:'||s.id from public.study_sessions s
    where s.friend_id=me and s.mode='friend' and s.state='waiting' and s.expires_at>now()
     and public.has_study_invite_deck(me,s.course,s.language,s.total)
   union all
   select 'study:'||(case when s.timeout_result is not null or
     (s.finished_at is not null and (p.finished_at is not null or p.left_at is not null))
     then 'result' else 'match' end)||':'||s.id
    from public.study_sessions s join public.study_sessions p on p.id=s.partner_id where s.user_id=me
 ) events where not exists(select 1 from public.play_update_reads r where r.user_id=me and r.event_key=events.event_key))
 into active;
 insert into public.play_update_reads(user_id,event_key)
  select me,k from unnest(active) k where k=any(p_seen) on conflict do nothing;
 return to_jsonb(array(select k from unnest(active) k where not(k=any(coalesce(p_seen,'{}'))) order by k));
end $$;
revoke all on function public.play_unread_updates(text[]) from public,anon;
grant execute on function public.play_unread_updates(text[]) to authenticated;
commit;
