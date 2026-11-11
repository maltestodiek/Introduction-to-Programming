-- Fourth feature. Apply once after decks-schema.sql. No existing content is deleted.
begin;
alter table public.decks add column language text;
alter function public.check_deck(jsonb) rename to check_deck_content;
create function public.check_deck(p_draft jsonb) returns void language plpgsql security definer set search_path='' as $$
begin
 perform public.check_deck_content(p_draft);
 if not exists(select 1 from public.profiles where id=auth.uid() and (p_draft->>'language')=any(languages)) then raise exception 'Select a language from your profile';end if;
end $$;
revoke all on function public.check_deck(jsonb) from public,anon,authenticated;
create or replace function public.publish_deck(p_review_id uuid,p_draft jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.deck_reviews; d public.decks; campus text; enrolled_course text;
begin
 if auth.uid() is null then raise exception 'Sign in first';end if;
 perform public.check_deck(p_draft);
 select * into r from public.deck_reviews where id=p_review_id and creator_id=auth.uid();
 if not found or r.snapshot<>p_draft then raise exception 'Review this exact deck first';end if;
 select p.university into campus from public.profiles p where p.id=auth.uid();
 select c into enrolled_course from public.profile_private p,unnest(p.courses) c where p.user_id=auth.uid() and lower(trim(c))=lower(trim(p_draft->>'course')) limit 1;
 if campus is null or enrolled_course is null then raise exception 'Complete your profile and select this course';end if;
 perform pg_advisory_xact_lock(hashtextextended(auth.uid()::text||r.draft_id::text,0));
 select * into d from public.decks where creator_id=auth.uid() and draft_id=r.draft_id;
 if found then
  if d.snapshot<>p_draft then raise exception 'This draft was already published with different content';end if;
  return jsonb_build_object('id',d.id);
 end if;
 insert into public.decks(creator_id,draft_id,university,course,name,cards,snapshot,language)
 values(auth.uid(),r.draft_id,campus,trim(enrolled_course),trim(p_draft->>'name'),p_draft->'cards',p_draft,p_draft->>'language') returning * into d;
 return jsonb_build_object('id',d.id);
end $$;
create table public.play_presence(user_id uuid primary key references public.profiles(id) on delete cascade,last_seen timestamptz not null default now(),pause_invites boolean not null default false);
create table public.play_queue(user_id uuid primary key references public.profiles(id) on delete cascade,deck_id uuid not null references public.decks(id),expires_at timestamptz not null default (now()+interval '1 hour'));
create table public.play_duels(id uuid primary key default gen_random_uuid(),p1 uuid not null references public.profiles(id),p2 uuid not null references public.profiles(id),deck1 uuid not null references public.decks(id),deck2 uuid not null references public.decks(id),course text not null,language text not null,cards jsonb not null check(jsonb_array_length(cards)=30),created_at timestamptz not null default now(),deadline timestamptz not null default(now()+interval '24 hours'),settled_at timestamptz,winner uuid,draw boolean not null default false,check(p1<>p2));
create table public.play_rounds(duel_id uuid references public.play_duels(id),user_id uuid references public.profiles(id),cursor integer not null default 0 check(cursor between 0 and 30),answers jsonb not null default '[]',question_started timestamptz,started_at timestamptz,finished_at timestamptz,forfeited boolean not null default false,ratings jsonb,score integer not null default 0,xp_delta integer,result text,primary key(duel_id,user_id));
create table public.play_invites(id uuid primary key default gen_random_uuid(),sender uuid not null references public.profiles(id),recipient uuid not null references public.profiles(id),deck_id uuid not null references public.decks(id),state text not null default 'pending' check(state in ('pending','accepted','declined','cancelled','expired')),created_at timestamptz not null default now(),responded_at timestamptz,expires_at timestamptz not null default(now()+interval '24 hours'),duel_id uuid references public.play_duels(id),check(sender<>recipient));
create index play_invites_recipient on public.play_invites(recipient,state);
create index play_invites_sender on public.play_invites(sender,state);
create index play_duels_p1 on public.play_duels(p1,created_at);
create index play_duels_p2 on public.play_duels(p2,created_at);
alter table public.play_presence enable row level security;
alter table public.play_queue enable row level security;
alter table public.play_duels enable row level security;
alter table public.play_rounds enable row level security;
alter table public.play_invites enable row level security;
revoke all on public.play_presence,public.play_queue,public.play_duels,public.play_rounds,public.play_invites from public,anon,authenticated;

create function public.play_finish(did uuid) returns void language plpgsql security definer set search_path='' as $$
declare d public.play_duels; a public.play_rounds; b public.play_rounds; r record; delta integer; oldxp integer; streak integer; outcome text;
begin
 select * into d from public.play_duels where id=did for update;
 if d.settled_at is not null then return;end if;
 select * into a from public.play_rounds where duel_id=did and user_id=d.p1;
 select * into b from public.play_rounds where duel_id=did and user_id=d.p2;
 if a.forfeited then d.winner:=d.p2;
 elsif b.forfeited then d.winner:=d.p1;
 elsif a.finished_at is not null and b.finished_at is not null then
  if a.score>b.score then d.winner:=d.p1;elsif b.score>a.score then d.winner:=d.p2;else d.draw:=true;end if;
 elsif d.deadline<=now() then
  if a.finished_at is not null then d.winner:=d.p1;elsif b.finished_at is not null then d.winner:=d.p2;end if;
 else return;end if;
 update public.play_duels set settled_at=now(),winner=d.winner,draw=d.draw where id=did;
 for r in select user_id from public.play_rounds where duel_id=did order by user_id loop
  select xp,win_streak into oldxp,streak from public.profiles where id=r.user_id for update;
  if r.user_id=d.winner then outcome:='win';delta:=case when streak>=3 then 80 else 40 end;streak:=streak+1;
  elsif d.draw then outcome:='draw';delta:=0;streak:=0;
  else outcome:='loss';delta:=-least(oldxp,10);streak:=0;end if;
  update public.profiles set xp=oldxp+delta,win_streak=streak where id=r.user_id;
  update public.play_rounds set result=outcome,xp_delta=delta where duel_id=did and user_id=r.user_id;
 end loop;
end $$;

create function public.play_create(a uuid,b uuid,ad uuid,bd uuid) returns uuid language plpgsql security definer set search_path='' as $$
declare x public.decks; y public.decks; did uuid;
begin
 select * into x from public.decks where id=ad;select * into y from public.decks where id=bd;
 if a=b or x.id is null or y.id is null or x.language is null or x.language is distinct from y.language or lower(trim(x.course))<>lower(trim(y.course)) then raise exception 'Choose decks for the same course and language';end if;
 if not exists(select 1 from public.profiles where id=a and x.language=any(languages)) or not exists(select 1 from public.profiles where id=b and x.language=any(languages)) then raise exception 'Both profiles must include the deck language';end if;
 if exists(select 1 from public.play_duels where settled_at is null and ((p1=a and p2=b) or (p1=b and p2=a))) then raise exception 'You already have an active duel with this player';end if;
 insert into public.play_duels(p1,p2,deck1,deck2,course,language,cards) values(a,b,ad,bd,x.course,x.language,x.cards||y.cards) returning id into did;
 insert into public.play_rounds(duel_id,user_id) values(did,a),(did,b);
 delete from public.play_queue where user_id in(a,b);
 update public.play_invites set state='cancelled',responded_at=now() where state='pending' and ((sender=a and recipient=b) or (sender=b and recipient=a));
 return did;
end $$;

create function public.play_action(p_action text,p_data jsonb default '{}') returns jsonb language plpgsql security definer set search_path='' as $$
declare me uuid:=auth.uid(); campus text; langs text[]; courses text[]; target uuid; did uuid; candidate record; d public.decks; otherdeck public.decks; inv public.play_invites; duel public.play_duels; round public.play_rounds; payload jsonb; card jsonb; options jsonb; answer text; correct boolean; timedout boolean; result jsonb; active boolean; idx integer; rating_id uuid; n integer;
begin
 if me is null then raise exception 'Sign in first';end if;
 -- Serialize short Play transactions, including matching and XP awards. Appropriate
 -- for this class release; prevents two concurrent searches claiming one player.
 perform pg_advisory_xact_lock(791146221);
 select university,languages into campus,langs from public.profiles where id=me;
 select p.courses into courses from public.profile_private p where p.user_id=me;
 if campus is null or courses is null then raise exception 'Complete your profile first';end if;
 insert into public.play_presence(user_id) values(me) on conflict(user_id) do update set last_seen=now();
 delete from public.play_queue where expires_at<=now();
 update public.play_invites set state='expired',responded_at=now() where state='pending' and expires_at<=now();
 for candidate in select id from public.play_duels where settled_at is null and (p1=me or p2=me) loop perform public.play_finish(candidate.id);end loop;
 if p_action='list' then
  select jsonb_build_object('queue',(select jsonb_build_object('expires_at',q.expires_at,'deck_name',k.name,'course',k.course,'language',k.language) from public.play_queue q join public.decks k on k.id=q.deck_id where q.user_id=me),'paused',(select pause_invites from public.play_presence where user_id=me),
   'invites',coalesce((select jsonb_agg(jsonb_build_object('id',i.id,'incoming',i.recipient=me,'username',p.username,'deck_name',k.name,'course',k.course,'language',k.language,'expires_at',i.expires_at,'deck_id',k.id) order by i.created_at desc) from public.play_invites i join public.profiles p on p.id=case when i.sender=me then i.recipient else i.sender end join public.decks k on k.id=i.deck_id where i.state='pending' and (i.sender=me or i.recipient=me)),'[]'),
   'duels',coalesce((select jsonb_agg(jsonb_build_object('id',g.id,'username',p.username,'course',g.course,'language',g.language,'deadline',g.deadline,'created_at',g.created_at,'status',case when g.settled_at is not null then 'Completed' when r.finished_at is not null then 'Pending' else 'Ongoing' end,'started',r.started_at is not null,'score',r.score,'opponent_score',case when g.settled_at is not null and o.finished_at is not null then o.score else null end,'result',r.result,'xp_delta',r.xp_delta) order by g.created_at desc) from public.play_duels g join public.play_rounds r on r.duel_id=g.id and r.user_id=me join public.profiles p on p.id=case when g.p1=me then g.p2 else g.p1 end join public.play_rounds o on o.duel_id=g.id and o.user_id=p.id where g.p1=me or g.p2=me),'[]')) into result;
  return result;
 elsif p_action='set_pause' then
  update public.play_presence set pause_invites=coalesce((p_data->>'paused')::boolean,false) where user_id=me;return '{}'::jsonb;
 elsif p_action='cancel_search' then
  delete from public.play_queue where user_id=me;return jsonb_build_object('message','Search cancelled.');
 elsif p_action='set_language' then
  if not coalesce((p_data->>'language')=any(langs),false) then raise exception 'Select a language from your profile';end if;
  update public.decks set language=p_data->>'language' where id=(p_data->>'deck_id')::uuid and creator_id=me and language is null;
  if not found then raise exception 'Only the creator can set a missing deck language';end if;return '{}'::jsonb;
 elsif p_action in ('join','friend_options','invite') then
  select * into d from public.decks where id=(p_data->>'deck_id')::uuid;
  if d.id is null or d.university<>campus or not exists(select 1 from unnest(courses) c where lower(trim(c))=lower(trim(d.course))) then raise exception 'Choose a deck in a course from your profile at your university';end if;
  if d.language is null or not coalesce(d.language=any(langs),false) then raise exception 'Choose a deck with a language listed in your profile';end if;
  if p_action='friend_options' then
   return jsonb_build_object('friends',coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'username',p.username,'has_course',exists(select 1 from public.profile_private v,unnest(v.courses)c where v.user_id=p.id and lower(trim(c))=lower(trim(d.course))),'speaks_language',d.language=any(p.languages))) from public.friend_edges f join public.profiles p on p.id=case when f.low_id=me then f.high_id else f.low_id end where f.state='accepted' and me in(f.low_id,f.high_id)),'[]'));
  elsif p_action='join' then
   -- Rejoining the same live search is idempotent, not an implicit renewal.
   if exists(select 1 from public.play_queue where user_id=me and deck_id=d.id) then return jsonb_build_object('message','Your search is already active.');end if;
   delete from public.play_queue where user_id=me;
   for candidate in
    select q.user_id,q.deck_id from public.play_queue q join public.decks k on k.id=q.deck_id join public.profiles p on p.id=q.user_id join public.play_presence s on s.user_id=q.user_id
    where q.user_id<>me and q.expires_at>now() and s.last_seen>now()-interval '24 hours' and p.university=campus and k.university=campus and lower(trim(k.course))=lower(trim(d.course)) and k.language=d.language and d.language=any(p.languages)
    and exists(select 1 from public.profile_private v,unnest(v.courses)c where v.user_id=p.id and lower(trim(c))=lower(trim(d.course)))
    and not exists(select 1 from public.play_duels g where g.settled_at is null and ((g.p1=me and g.p2=p.id) or (g.p2=me and g.p1=p.id)))
    and not exists(select 1 from public.play_invites i where i.state='pending' and ((i.sender=me and i.recipient=p.id) or (i.recipient=me and i.sender=p.id)))
    order by q.expires_at limit 1
   loop did:=public.play_create(me,candidate.user_id,d.id,candidate.deck_id);return jsonb_build_object('duel_id',did,'message','Opponent found!');end loop;
   insert into public.play_queue(user_id,deck_id) values(me,d.id);return jsonb_build_object('message','Searching for one hour. You may leave Play and return later.');
  else
   target:=(p_data->>'friend_id')::uuid;
   if not exists(select 1 from public.friend_edges where state='accepted' and ((low_id=me and high_id=target) or (high_id=me and low_id=target))) then raise exception 'Choose an accepted friend';end if;
   if not exists(select 1 from public.profiles where id=target and d.language=any(languages)) then raise exception 'Your friend does not list this deck language';end if;
   if not exists(select 1 from public.profile_private v,unnest(v.courses)c where v.user_id=target and lower(trim(c))=lower(trim(d.course))) and not coalesce((p_data->>'confirm_missing_course')::boolean,false) then raise exception 'Confirm that your friend has not added this course';end if;
   if exists(select 1 from public.play_presence where user_id=target and pause_invites) then raise exception 'This friend has paused invitations';end if;
   if exists(select 1 from public.play_invites where state='pending' and ((sender=me and recipient=target) or (sender=target and recipient=me))) then raise exception 'There is already a pending invitation between you';end if;
   if exists(select 1 from public.play_duels where settled_at is null and ((p1=me and p2=target) or (p2=me and p1=target))) then raise exception 'Finish your existing duel with this friend first';end if;
   if exists(select 1 from public.play_invites where sender=me and recipient=target and state='declined' and responded_at>now()-interval '24 hours') then raise exception 'Wait 24 hours after a declined invitation';end if;
   if (select count(*) from public.play_invites where sender=me and state='pending')>=5 or (select count(*) from public.play_invites where recipient=target and state='pending')>=10 or (select count(*) from public.play_invites where sender=me and created_at>now()-interval '1 hour')>=5 then raise exception 'Invitation limit reached. Try later';end if;
   insert into public.play_invites(sender,recipient,deck_id) values(me,target,d.id);return jsonb_build_object('message','Invitation sent. Your friend must accept before the duel starts.');
  end if;
 elsif p_action in ('invite_decks','accept','decline','cancel') then
  select * into inv from public.play_invites where id=(p_data->>'invite_id')::uuid and (sender=me or recipient=me) for update;
  if inv.id is null then raise exception 'Invitation unavailable';end if;
  if p_action='accept' and inv.recipient=me and inv.state='accepted' then return jsonb_build_object('duel_id',inv.duel_id);end if;
  if inv.state<>'pending' then raise exception 'This invitation is no longer pending';end if;
  if p_action='cancel' and inv.sender=me then update public.play_invites set state='cancelled',responded_at=now() where id=inv.id;return '{}'::jsonb;end if;
  if inv.recipient<>me then raise exception 'Only the recipient can respond';end if;
  if p_action='decline' then update public.play_invites set state='declined',responded_at=now() where id=inv.id;return '{}'::jsonb;end if;
  select * into d from public.decks where id=inv.deck_id;
  if p_action='invite_decks' then
   return jsonb_build_object('decks',coalesce((select jsonb_agg(jsonb_build_object('id',k.id,'name',k.name)) from public.decks k where (k.university=campus or k.id=d.id) and k.language=d.language and lower(trim(k.course))=lower(trim(d.course))),'[]'));
  end if;
  if p_action<>'accept' then raise exception 'Invalid invitation action';end if;
  if not exists(select 1 from public.friend_edges where state='accepted' and me in(low_id,high_id) and inv.sender in(low_id,high_id)) then raise exception 'This friendship is no longer active';end if;
  select * into otherdeck from public.decks where id=(p_data->>'deck_id')::uuid and (university=campus or id=d.id);
  if otherdeck.id is null then raise exception 'Choose an available deck';end if;
  did:=public.play_create(inv.sender,me,d.id,otherdeck.id);
  update public.play_invites set state='accepted',duel_id=did,responded_at=now() where id=inv.id;
  return jsonb_build_object('duel_id',did);
 elsif p_action in ('round','answer','finish','abandon','review') then
  did:=(p_data->>'duel_id')::uuid;
  select * into duel from public.play_duels where id=did and me in(p1,p2);
  if duel.id is null then raise exception 'Duel unavailable';end if;
  select * into round from public.play_rounds where duel_id=did and user_id=me for update;
  if p_action='review' then
   if duel.settled_at is null then raise exception 'Review is available after the duel completes';end if;
   return jsonb_build_object('cards',duel.cards,'answers',round.answers,'score',round.score,'result',round.result,'xp_delta',round.xp_delta);
  end if;
  if duel.settled_at is not null then return jsonb_build_object('state','completed');end if;
  if round.finished_at is not null then return jsonb_build_object('state','pending');end if;
  if p_action='abandon' then
   if not coalesce((p_data->>'confirmed')::boolean,false) then raise exception 'Confirm abandonment first';end if;
   update public.play_rounds set forfeited=true where duel_id=did and user_id=me;perform public.play_finish(did);return jsonb_build_object('state','completed');
  elsif p_action='finish' then
   if round.cursor<>30 then raise exception 'Answer all 30 questions first';end if;
   for rating_id in select distinct id from unnest(array[duel.deck1,duel.deck2]) id loop
    if not coalesce((p_data->'ratings'->>rating_id::text) in ('up','neutral','down'),false) then raise exception 'Rate both decks before finishing';end if;
   end loop;
   update public.play_rounds set ratings=p_data->'ratings',finished_at=now() where duel_id=did and user_id=me;perform public.play_finish(did);return jsonb_build_object('state','finished');
  end if;
  if round.cursor=30 then
   return jsonb_build_object('state','rating','score',round.score,'decks',(select jsonb_agg(jsonb_build_object('id',k.id,'name',k.name)) from public.decks k where k.id in(duel.deck1,duel.deck2)));
  end if;
  if p_action='answer' and (p_data->>'index')::integer is distinct from round.cursor then
   idx:=(p_data->>'index')::integer;
   if idx>=0 and idx<round.cursor then return jsonb_build_object('state','feedback','feedback',round.answers->idx,'card',duel.cards->idx);end if;
   raise exception 'Question changed. Reload the round';
  end if;
  card:=duel.cards->round.cursor;
  if p_action='round' then
   if round.question_started is null then
    update public.play_rounds set question_started=now(),started_at=coalesce(started_at,now()) where duel_id=did and user_id=me returning * into round;
   end if;
   -- Polling can expire a question, but never starts the next question silently.
   if round.question_started+interval '30 seconds'<=now() then p_action:='answer';p_data:=p_data||jsonb_build_object('index',round.cursor,'answer_id',null);end if;
  end if;
  if p_action='answer' then
   if round.question_started is null then raise exception 'Open the question before answering';end if;
   answer:=p_data->>'answer_id';timedout:=round.question_started+interval '30 seconds'<=now();
   if not timedout and not exists(select 1 from jsonb_array_elements(card->'answers')a where a->>'id'=answer) then raise exception 'Choose one of the four answers';end if;
   correct:=not timedout and answer=card->>'correct_answer_id';
   payload:=jsonb_build_object('index',round.cursor,'answer_id',case when timedout then null else answer end,'correct',coalesce(correct,false),'timed_out',timedout);
   update public.play_rounds set answers=answers||jsonb_build_array(payload),score=score+case when correct then 1 else 0 end,cursor=cursor+1,question_started=null where duel_id=did and user_id=me;
   return jsonb_build_object('state','feedback','feedback',payload,'card',card);
  end if;
  select jsonb_agg(a order by md5(did::text||me::text||round.cursor::text||(a->>'id'))) into options from jsonb_array_elements(card->'answers')a;
  return jsonb_build_object('state','question','index',round.cursor,'question',card->>'question','options',options,'seconds',greatest(0,ceil(extract(epoch from(round.question_started+interval '30 seconds'-now())))));
 end if;
 raise exception 'Unknown Play action';
exception when raise_exception then return jsonb_build_object('error',sqlerrm);
end $$;
revoke all on function public.play_finish(uuid),public.play_create(uuid,uuid,uuid,uuid),public.play_action(text,jsonb) from public,anon,authenticated;
grant execute on function public.play_action(text,jsonb) to authenticated;
commit;
