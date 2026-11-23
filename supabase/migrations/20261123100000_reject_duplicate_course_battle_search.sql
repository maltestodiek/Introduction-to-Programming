begin;

-- A completed request is safely retryable through battle_rounds.start_request.
-- A separate click while an unmatched search still exists must stay in setup,
-- rather than reopen the saved round and its post-Battle rating screen.
create or replace function public.start_random_battle(p_data jsonb) returns jsonb
language plpgsql security definer set search_path='' as $$
declare
 me uuid:=auth.uid(); campus text; course_name text:=trim(p_data->>'course'); lang text:=p_data->>'language';
 kind text:=p_data->>'source_kind'; requested uuid:=(p_data->>'deck_id')::uuid; token uuid:=(p_data->>'request_id')::uuid;
 deck public.battle_decks; peer public.battle_searches; own public.battle_searches; sid uuid;
begin
 -- The caller holds the matchmaking lock and has expired overdue rounds.
 select session_id into sid from public.battle_rounds where user_id=me and start_request=token;
 if found then return jsonb_build_object('session_id',sid,'resumed',true);end if;
 select p.university into campus from public.profiles p join public.profile_private v on v.user_id=p.id
 where p.id=me and lang=any(p.languages) and exists(select 1 from unnest(v.courses)c where lower(trim(c))=lower(course_name));
 if campus is null then raise exception 'Choose one of your courses and languages';end if;
 if kind is null or kind not in ('random','top') then raise exception 'Choose Random Deck or Top Decks';end if;
 if kind='top' and not exists(select 1 from public.battle_decks where id=requested and university=campus and lower(trim(course))=lower(course_name) and language=lang)
 then raise exception 'Choose an eligible Top Deck';end if;

 -- The per-course primary key is the durable source of truth. Do not let a
 -- second setup submission reopen the existing pending session.
 select * into own from public.battle_searches where user_id=me and lower(trim(course))=lower(course_name);
 if own.user_id is not null then
  raise exception 'You are already searching for a random player for this course';
 end if;

 select q.* into peer from public.battle_searches q join public.profiles p on p.id=q.user_id
 join public.profile_private v on v.user_id=p.id
 left join public.battle_sessions s on s.id=q.session_id
 where q.user_id<>me and q.university=campus and p.university=campus and q.language=lang and lang=any(p.languages)
 and lower(trim(q.course))=lower(course_name) and exists(select 1 from unnest(v.courses)c where lower(trim(c))=lower(course_name))
 and (kind='random' or coalesce(s.battle_deck_id,q.deck_id,requested)=requested)
 order by q.created_at,q.user_id limit 1;
 if peer.session_id is not null then
  sid:=peer.session_id;
  update public.battle_sessions set p2=me where id=sid and p2 is null;
 else
  select b.* into deck from public.battle_decks b where b.university=campus and lower(trim(b.course))=lower(course_name) and b.language=lang
   and (coalesce(peer.deck_id,case when kind='top' then requested end) is null or b.id=coalesce(peer.deck_id,requested))
   order by random() limit 1;
  if deck.id is null then raise exception 'No eligible Battle Deck is available for this course and language';end if;
  insert into public.battle_sessions(p1,p2,battle_deck_id,source_kind,cards,course,language,deadline)
  values(coalesce(peer.user_id,me),case when peer.user_id is not null then me end,deck.id,coalesce(peer.source_kind,kind),deck.cards,deck.course,lang,'infinity')
  returning id into sid;
  if peer.user_id is not null then
   insert into public.battle_rounds(session_id,user_id,finish_by) values(sid,peer.user_id,now()+interval '1 hour');
  end if;
 end if;
 insert into public.battle_rounds(session_id,user_id,start_request,finish_by) values(sid,me,token,now()+interval '1 hour');
 delete from public.battle_searches where user_id in(me,peer.user_id) and lower(trim(course))=lower(course_name);
 if peer.user_id is null then
  insert into public.battle_searches(user_id,source_kind,deck_id,university,course,language,expires_at,session_id)
  values(me,kind,case when kind='top' then requested end,campus,course_name,lang,now()+interval '48 hours',sid);
 end if;
 return jsonb_build_object('session_id',sid);
end $$;

revoke all on function public.start_random_battle(jsonb) from public,anon;
grant execute on function public.start_random_battle(jsonb) to authenticated;

commit;
