-- Battle Mode. Apply after study-schema.sql and ai-question-generation-flow.sql.
-- Additive: legacy 30-question Play rows remain readable and are never changed.
begin;

alter table public.profiles add column if not exists game_xp integer not null default 0 check(game_xp>=0);
alter table public.profiles add column if not exists creator_xp integer not null default 0 check(creator_xp>=0);
update public.profiles set game_xp=xp where game_xp=0 and xp>0;

create table public.battle_decks(
 id uuid primary key default gen_random_uuid(), creator_id uuid not null references public.profiles(id),
 source_deck_id uuid not null references public.study_decks(id), source_revision integer not null,
 source_origin text not null check(source_origin in ('human','ai','chatbot')),
 university text not null, course text not null, language text not null, name text not null,
 cards jsonb not null check(jsonb_typeof(cards)='array' and jsonb_array_length(cards)=15),
 public_consent_at timestamptz not null, created_at timestamptz not null default now()
);
create table public.battle_searches(
 user_id uuid primary key references public.profiles(id) on delete cascade, source_kind text not null check(source_kind in ('random','top')),
 deck_id uuid references public.battle_decks(id), university text not null, course text not null, language text not null,
 expires_at timestamptz not null default(now()+interval '1 hour'), created_at timestamptz not null default now(),
 check((source_kind='random' and deck_id is null) or (source_kind='top' and deck_id is not null))
);
create table public.battle_invites(
 id uuid primary key default gen_random_uuid(), sender uuid not null references public.profiles(id), recipient uuid not null references public.profiles(id),
 source_kind text not null check(source_kind in ('random','top')), deck_id uuid references public.battle_decks(id),
 university text not null, course text not null, language text not null, state text not null default 'pending' check(state in ('pending','accepted','declined','cancelled','expired')),
 created_at timestamptz not null default now(), expires_at timestamptz not null default(now()+interval '24 hours'), session_id uuid,
 check(sender<>recipient), check((source_kind='random' and deck_id is null) or (source_kind='top' and deck_id is not null))
);
create table public.battle_sessions(
 id uuid primary key default gen_random_uuid(), p1 uuid not null references public.profiles(id), p2 uuid not null references public.profiles(id),
 battle_deck_id uuid not null references public.battle_decks(id), source_kind text not null check(source_kind in ('random','top')),
 cards jsonb not null check(jsonb_typeof(cards)='array' and jsonb_array_length(cards)=15), course text not null, language text not null,
 created_at timestamptz not null default now(), deadline timestamptz not null default(now()+interval '24 hours'),
 settled_at timestamptz, winner uuid references public.profiles(id), draw boolean not null default false, check(p1<>p2)
);
create table public.battle_rounds(
 session_id uuid not null references public.battle_sessions(id) on delete cascade, user_id uuid not null references public.profiles(id),
 cursor integer not null default 0 check(cursor between 0 and 15), answers jsonb not null default '[]', question_started timestamptz,
 started_at timestamptz, finished_at timestamptz, forfeited boolean not null default false, score integer not null default 0,
 result text, game_xp_delta integer, primary key(session_id,user_id)
);
create table public.battle_ratings(
 battle_deck_id uuid not null references public.battle_decks(id), reviewer_id uuid not null references public.profiles(id),
 rating text check(rating in ('good','neutral','bad')), automatic boolean not null default false, non_scoring boolean not null default false,
 rated_at timestamptz not null default now(), primary key(battle_deck_id,reviewer_id),
 check((rating is not null) or non_scoring)
);
create table public.battle_daily_ratings(
 berlin_day date not null, battle_deck_id uuid not null references public.battle_decks(id), score integer not null default 0,
 rating_count integer not null default 0, good_count integer not null default 0, neutral_count integer not null default 0, bad_count integer not null default 0,
 primary key(berlin_day,battle_deck_id)
);
create index battle_decks_eligible on public.battle_decks(university,course,language,created_at);
create index battle_sessions_member on public.battle_sessions(p1,p2,created_at);
create index battle_invites_recipient on public.battle_invites(recipient,state);
alter table public.battle_decks enable row level security;
alter table public.battle_searches enable row level security;
alter table public.battle_invites enable row level security;
alter table public.battle_sessions enable row level security;
alter table public.battle_rounds enable row level security;
alter table public.battle_ratings enable row level security;
alter table public.battle_daily_ratings enable row level security;
revoke all on public.battle_decks,public.battle_searches,public.battle_invites,public.battle_sessions,public.battle_rounds,public.battle_ratings,public.battle_daily_ratings from public,anon,authenticated;

create function public.battle_rate(p_deck uuid,p_reviewer uuid,p_rating text,p_automatic boolean default false,p_non_scoring boolean default false) returns void language plpgsql security definer set search_path='' as $$
declare d public.battle_decks; day date:=(now() at time zone 'Europe/Berlin')::date; reward integer:=0;
begin
 select * into d from public.battle_decks where id=p_deck;
 if d.id is null then raise exception 'Battle Deck unavailable'; end if;
 insert into public.battle_ratings(battle_deck_id,reviewer_id,rating,automatic,non_scoring) values(p_deck,p_reviewer,p_rating,p_automatic,p_non_scoring) on conflict do nothing;
 if not found then return; end if;
 if not p_non_scoring then
  insert into public.battle_daily_ratings(berlin_day,battle_deck_id,score,rating_count,good_count,neutral_count,bad_count)
  values(day,p_deck,case p_rating when 'good' then 1 when 'bad' then -1 else 0 end,1,case when p_rating='good' then 1 else 0 end,case when p_rating='neutral' then 1 else 0 end,case when p_rating='bad' then 1 else 0 end)
  on conflict(berlin_day,battle_deck_id) do update set score=battle_daily_ratings.score+excluded.score,rating_count=battle_daily_ratings.rating_count+1,good_count=battle_daily_ratings.good_count+excluded.good_count,neutral_count=battle_daily_ratings.neutral_count+excluded.neutral_count,bad_count=battle_daily_ratings.bad_count+excluded.bad_count;
  if p_rating='good' and d.source_origin='human' and d.creator_id<>p_reviewer then reward:=5; end if;
 end if;
 if reward>0 then update public.profiles set creator_xp=creator_xp+reward,xp=xp+reward where id=d.creator_id; end if;
end $$;

create function public.battle_finish(p_session uuid) returns void language plpgsql security definer set search_path='' as $$
declare s public.battle_sessions;a public.battle_rounds;b public.battle_rounds;r record; delta integer; old_game integer; streak integer; outcome text;
begin
 select * into s from public.battle_sessions where id=p_session for update; if s.settled_at is not null then return; end if;
 select * into a from public.battle_rounds where session_id=p_session and user_id=s.p1; select * into b from public.battle_rounds where session_id=p_session and user_id=s.p2;
 if a.forfeited then s.winner:=s.p2; elsif b.forfeited then s.winner:=s.p1; elsif a.finished_at is not null and b.finished_at is not null then
  if a.score>b.score then s.winner:=s.p1; elsif b.score>a.score then s.winner:=s.p2; else s.draw:=true; end if;
 elsif s.deadline<=now() then if a.finished_at is not null then s.winner:=s.p1; elsif b.finished_at is not null then s.winner:=s.p2; end if; else return; end if;
 update public.battle_sessions set settled_at=now(),winner=s.winner,draw=s.draw where id=p_session;
 for r in select user_id from public.battle_rounds where session_id=p_session order by user_id loop
  select game_xp,win_streak into old_game,streak from public.profiles where id=r.user_id for update;
  if r.user_id=s.winner then outcome:='win';delta:=case when streak>=3 then 80 else 40 end;streak:=streak+1;
  elsif s.draw then outcome:='draw';delta:=0;streak:=0; else outcome:='loss';delta:=-least(old_game,10);streak:=0; end if;
  update public.profiles set game_xp=game_xp+delta,xp=xp+delta,win_streak=streak where id=r.user_id;
  update public.battle_rounds set result=outcome,game_xp_delta=delta where session_id=p_session and user_id=r.user_id;
 end loop;
end $$;

create function public.battle_action(p_action text,p_data jsonb default '{}') returns jsonb language plpgsql security definer set search_path='' as $$
declare me uuid:=auth.uid(); campus text; langs text[]; courses text[]; d jsonb; source public.study_decks; deck public.battle_decks; s public.battle_sessions; r public.battle_rounds; peer record; invite record; chosen uuid; card jsonb; idx integer; correct boolean; origin text; ids text[]:='{}';
begin
 if me is null then raise exception 'Sign in first'; end if; perform pg_advisory_xact_lock(791146221);
 select university,languages into campus,langs from public.profiles where id=me; select courses into courses from public.profile_private where user_id=me;
 if campus is null or courses is null then raise exception 'Complete your profile first'; end if;
 delete from public.battle_searches where expires_at<=now();
 for s in select * from public.battle_sessions where settled_at is null and (p1=me or p2=me) loop
  if s.deadline<=now() then
   for peer in select user_id from public.battle_rounds where session_id=s.id and finished_at is null and not forfeited loop
    update public.battle_rounds set forfeited=true where session_id=s.id and user_id=peer.user_id;
    perform public.battle_rate(s.battle_deck_id,peer.user_id,'neutral',true,(select creator_id=peer.user_id from public.battle_decks where id=s.battle_deck_id));
   end loop;
   perform public.battle_finish(s.id);
  end if;
 end loop;
 if p_action='sources' then
  return jsonb_build_object('sources',coalesce((select jsonb_agg(jsonb_build_object('id',x.id,'name',x.snapshot->>'name','course',x.snapshot->>'course','language',x.snapshot->>'language','count',jsonb_array_length(x.snapshot->'cards'),'revision',x.revision,'battle_capable',jsonb_array_length(x.snapshot->'cards')>=15) order by x.updated_at desc) from public.study_decks x where x.creator_id=me),'[]'::jsonb));
 elsif p_action='source' then
  select * into source from public.study_decks where id=(p_data->>'id')::uuid and creator_id=me; if source.id is null then raise exception 'Choose one of your own reviewed Study decks'; end if;
  return source.snapshot||jsonb_build_object('revision',source.revision);
 elsif p_action='create_deck' then
  if not coalesce((p_data->>'consent')::boolean,false) then raise exception 'Accept that the deck can be played by everyone'; end if;
  select * into source from public.study_decks where id=(p_data->>'source_deck_id')::uuid and creator_id=me; if source.id is null then raise exception 'Choose one of your own reviewed Study decks'; end if;
  if jsonb_array_length(source.snapshot->'cards')<15 then raise exception 'This source deck is not Battle-capable yet'; end if;
  if jsonb_typeof(p_data->'card_ids') is distinct from 'array' or jsonb_array_length(p_data->'card_ids')<>15 then raise exception 'Choose exactly 15 questions'; end if;
  for d in select value from jsonb_array_elements(p_data->'card_ids') loop if d #>> '{}' is null or d #>> '{}' = any(ids) or not exists(select 1 from jsonb_array_elements(source.snapshot->'cards') c where c->>'id'=d #>> '{}') then raise exception 'Choose 15 distinct source questions'; end if; ids:=array_append(ids,d #>> '{}'); end loop;
  if not coalesce((source.snapshot->>'language')=any(langs),false) or not exists(select 1 from unnest(courses) c where lower(trim(c))=lower(trim(source.snapshot->>'course'))) then raise exception 'Select a source deck for one of your profile courses and languages'; end if;
  origin:=case when exists(select 1 from public.ai_question_drafts q where q.owner_id=me and q.status='published' and q.question in (select c->>'question' from jsonb_array_elements(source.snapshot->'cards') c where c->>'id'=any(ids))) then 'ai' else 'human' end;
  insert into public.battle_decks(creator_id,source_deck_id,source_revision,source_origin,university,course,language,name,cards,public_consent_at)
  values(me,source.id,source.revision,origin,campus,source.snapshot->>'course',source.snapshot->>'language',coalesce(nullif(trim(p_data->>'name'),''),source.snapshot->>'name'),(select jsonb_agg(c order by array_position(ids,c->>'id')) from jsonb_array_elements(source.snapshot->'cards') c where c->>'id'=any(ids)),now()) returning * into deck;
  return jsonb_build_object('id',deck.id);
 elsif p_action='top' then
  if not exists(select 1 from unnest(courses)c where lower(trim(c))=lower(trim(p_data->>'course'))) or not coalesce((p_data->>'language')=any(langs),false) then raise exception 'Choose one of your courses and languages'; end if;
  return jsonb_build_object('decks',coalesce((select jsonb_agg(jsonb_build_object('id',x.id,'name',x.name,'score',x.score,'rating_count',x.rating_count,'creator',x.username) order by x.score desc,x.rating_count desc,x.id) from (select b.id,b.name,dr.score,dr.rating_count,p.username from public.battle_daily_ratings dr join public.battle_decks b on b.id=dr.battle_deck_id join public.profiles p on p.id=b.creator_id where dr.berlin_day=(now() at time zone 'Europe/Berlin')::date and dr.rating_count>=3 and b.university=campus and lower(trim(b.course))=lower(trim(p_data->>'course')) and b.language=p_data->>'language' order by dr.score desc,dr.rating_count desc,b.id limit 10)x),'[]'::jsonb));
 elsif p_action='friend_options' then
  if not exists(select 1 from unnest(courses)c where lower(trim(c))=lower(trim(p_data->>'course'))) or not coalesce((p_data->>'language')=any(langs),false) then raise exception 'Choose one of your courses and languages'; end if;
  return jsonb_build_object('friends',coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'username',p.username)) from public.friend_edges f join public.profiles p on p.id=case when f.low_id=me then f.high_id else f.low_id end join public.profile_private v on v.user_id=p.id where f.state='accepted' and me in(f.low_id,f.high_id) and p.university=campus and p_data->>'language'=any(p.languages) and exists(select 1 from unnest(v.courses)c where lower(trim(c))=lower(trim(p_data->>'course')))),'[]'::jsonb));
 elsif p_action='invite' then
  if p_data->>'source_kind' not in ('random','top') then raise exception 'Choose Random Deck or Top Decks';end if;
  if not exists(select 1 from unnest(courses)c where lower(trim(c))=lower(trim(p_data->>'course'))) or not coalesce((p_data->>'language')=any(langs),false) then raise exception 'Choose one of your courses and languages';end if;
  if not exists(select 1 from public.friend_edges where state='accepted' and me in(low_id,high_id) and (p_data->>'friend_id')::uuid in(low_id,high_id)) then raise exception 'Choose an accepted friend';end if;
  if not exists(select 1 from public.profiles p join public.profile_private v on v.user_id=p.id where p.id=(p_data->>'friend_id')::uuid and p.university=campus and p_data->>'language'=any(p.languages) and exists(select 1 from unnest(v.courses)c where lower(trim(c))=lower(trim(p_data->>'course')))) then raise exception 'Your friend needs this course, language and university in their profile';end if;
  if p_data->>'source_kind'='top' then select * into deck from public.battle_decks where id=(p_data->>'deck_id')::uuid and university=campus and lower(trim(course))=lower(trim(p_data->>'course')) and language=p_data->>'language';if deck.id is null then raise exception 'Choose an eligible Top Deck';end if;end if;
  if exists(select 1 from public.battle_invites where state='pending' and ((sender=me and recipient=(p_data->>'friend_id')::uuid) or (recipient=me and sender=(p_data->>'friend_id')::uuid))) then raise exception 'There is already a pending Battle invitation between you';end if;
  insert into public.battle_invites(sender,recipient,source_kind,deck_id,university,course,language) values(me,(p_data->>'friend_id')::uuid,p_data->>'source_kind',case when p_data->>'source_kind'='top' then (p_data->>'deck_id')::uuid else null end,campus,p_data->>'course',p_data->>'language');return jsonb_build_object('message','Battle invitation sent.');
 elsif p_action in ('accept_invite','decline_invite','cancel_invite') then
  select * into invite from public.battle_invites where id=(p_data->>'invite_id')::uuid and (sender=me or recipient=me) for update;if invite.id is null or invite.state<>'pending' or invite.expires_at<=now() then raise exception 'Battle invitation unavailable';end if;
  if p_action='cancel_invite' then if invite.sender<>me then raise exception 'Only the sender can cancel';end if;update public.battle_invites set state='cancelled' where id=invite.id;return '{}';end if;
  if invite.recipient<>me then raise exception 'Only the invited friend can respond';end if;
  if p_action='decline_invite' then update public.battle_invites set state='declined' where id=invite.id;return '{}';end if;
  if invite.source_kind='top' then chosen:=invite.deck_id;else select id into chosen from public.battle_decks where university=invite.university and lower(trim(course))=lower(trim(invite.course)) and language=invite.language order by random() limit 1;end if;
  if chosen is null then raise exception 'No eligible Battle Deck is available for this course and language';end if;select * into deck from public.battle_decks where id=chosen;
  insert into public.battle_sessions(p1,p2,battle_deck_id,source_kind,cards,course,language) values(invite.sender,me,deck.id,invite.source_kind,deck.cards,deck.course,deck.language) returning * into s;
  insert into public.battle_rounds(session_id,user_id) values(s.id,s.p1),(s.id,s.p2);update public.battle_invites set state='accepted',session_id=s.id where id=invite.id;return jsonb_build_object('session_id',s.id);
 elsif p_action='join' then
  if not exists(select 1 from unnest(courses)c where lower(trim(c))=lower(trim(p_data->>'course'))) or not coalesce((p_data->>'language')=any(langs),false) then raise exception 'Choose one of your courses and languages'; end if;
  if p_data->>'source_kind' not in ('random','top') then raise exception 'Choose Random Deck or Top Decks'; end if;
  if p_data->>'source_kind'='top' then select * into deck from public.battle_decks where id=(p_data->>'deck_id')::uuid and university=campus and lower(trim(course))=lower(trim(p_data->>'course')) and language=p_data->>'language'; if deck.id is null then raise exception 'Choose an eligible Top Deck'; end if; end if;
  select * into peer from public.battle_searches q join public.profiles p on p.id=q.user_id join public.profile_private v on v.user_id=q.user_id where q.user_id<>me and q.expires_at>now() and q.university=campus and lower(trim(q.course))=lower(trim(p_data->>'course')) and q.language=p_data->>'language' and q.language=any(p.languages) and exists(select 1 from unnest(v.courses)c where lower(trim(c))=lower(trim(q.course))) order by q.created_at limit 1;
  if peer.user_id is null then insert into public.battle_searches(user_id,source_kind,deck_id,university,course,language) values(me,p_data->>'source_kind',case when p_data->>'source_kind'='top' then (p_data->>'deck_id')::uuid else null end,campus,p_data->>'course',p_data->>'language') on conflict(user_id) do update set source_kind=excluded.source_kind,deck_id=excluded.deck_id,university=excluded.university,course=excluded.course,language=excluded.language,expires_at=now()+interval '1 hour'; return jsonb_build_object('message','Searching for one hour.'); end if;
  if peer.deck_id is not null then chosen:=peer.deck_id; elsif p_data->>'source_kind'='top' then chosen:=(p_data->>'deck_id')::uuid; else select id into chosen from public.battle_decks where university=campus and lower(trim(course))=lower(trim(p_data->>'course')) and language=p_data->>'language' order by random() limit 1; end if;
  if chosen is null then raise exception 'No eligible Battle Deck is available for this course and language'; end if;
  select * into deck from public.battle_decks where id=chosen;
  insert into public.battle_sessions(p1,p2,battle_deck_id,source_kind,cards,course,language) values(peer.user_id,me,deck.id,case when peer.deck_id is null then 'random' else 'top' end,deck.cards,deck.course,deck.language) returning * into s;
  insert into public.battle_rounds(session_id,user_id) values(s.id,s.p1),(s.id,s.p2); delete from public.battle_searches where user_id in(me,peer.user_id); return jsonb_build_object('session_id',s.id,'message','Opponent found.');
 elsif p_action='list' then
  update public.battle_invites set state='expired' where state='pending' and expires_at<=now();
  return jsonb_build_object('search',(select jsonb_build_object('course',course,'language',language,'expires_at',expires_at) from public.battle_searches where user_id=me),'invites',coalesce((select jsonb_agg(jsonb_build_object('id',i.id,'incoming',i.recipient=me,'username',p.username,'source_kind',i.source_kind,'deck_name',b.name,'course',i.course,'language',i.language,'expires_at',i.expires_at) order by i.created_at desc) from public.battle_invites i join public.profiles p on p.id=case when i.sender=me then i.recipient else i.sender end left join public.battle_decks b on b.id=i.deck_id where i.state='pending' and me in(i.sender,i.recipient)),'[]'::jsonb),'sessions',coalesce((select jsonb_agg(jsonb_build_object('id',x.id,'deck_name',x.name,'course',x.course,'language',x.language,'status',x.status,'score',x.score,'opponent_score',x.opponent_score,'result',x.result,'game_xp_delta',x.game_xp_delta,'started',x.started) order by x.created_at desc) from (select s.id,b.name,s.course,s.language,s.created_at,r.score,r.result,r.game_xp_delta,r.started_at is not null started,case when s.settled_at is not null then 'completed' when r.finished_at is not null then 'pending' else 'ongoing' end status,case when s.settled_at is not null then o.score end opponent_score from public.battle_sessions s join public.battle_rounds r on r.session_id=s.id and r.user_id=me join public.battle_rounds o on o.session_id=s.id and o.user_id=case when s.p1=me then s.p2 else s.p1 end join public.battle_decks b on b.id=s.battle_deck_id where me in(s.p1,s.p2))x),'[]'::jsonb));
 elsif p_action in ('round','answer','finish','abandon','rate','review') then
  select * into s from public.battle_sessions where id=(p_data->>'id')::uuid and me in(p1,p2); if s.id is null then raise exception 'Battle unavailable'; end if; select * into r from public.battle_rounds where session_id=s.id and user_id=me for update;
  if p_action='review' then if s.settled_at is null then raise exception 'Review is available after the Battle';end if;return jsonb_build_object('cards',s.cards,'answers',r.answers,'score',r.score,'result',r.result,'game_xp_delta',r.game_xp_delta);end if;
  if s.deadline<=now() and s.settled_at is null then
   for peer in select user_id from public.battle_rounds where session_id=s.id and finished_at is null and not forfeited loop
    update public.battle_rounds set forfeited=true where session_id=s.id and user_id=peer.user_id;
    perform public.battle_rate(s.battle_deck_id,peer.user_id,'neutral',true,(select creator_id=peer.user_id from public.battle_decks where id=s.battle_deck_id));
   end loop;
   perform public.battle_finish(s.id);
  end if;
  if p_action='abandon' then if not coalesce((p_data->>'confirmed')::boolean,false) then raise exception 'Confirm abandonment first'; end if;update public.battle_rounds set forfeited=true where session_id=s.id and user_id=me;perform public.battle_rate(s.battle_deck_id,me,'neutral',true,(select creator_id=me from public.battle_decks where id=s.battle_deck_id));perform public.battle_finish(s.id);return jsonb_build_object('state','completed');end if;
  if p_action='rate' then if r.finished_at is null then raise exception 'Finish the Battle before rating';end if; perform public.battle_rate(s.battle_deck_id,me,p_data->>'rating',false,(select creator_id=me from public.battle_decks where id=s.battle_deck_id));return '{}';end if;
  if p_action='finish' then if r.cursor<>15 then raise exception 'Answer all 15 questions first';end if;update public.battle_rounds set finished_at=now() where session_id=s.id and user_id=me;perform public.battle_finish(s.id);return jsonb_build_object('state','pending');end if;
  if s.settled_at is not null then return jsonb_build_object('state','completed');end if;
  if r.question_started is not null and r.question_started+interval '30 seconds'<=now() and r.cursor<15 and not exists(select 1 from jsonb_array_elements(r.answers)x where (x->>'index')::int=r.cursor) then idx:=r.cursor;card:=s.cards->idx;update public.battle_rounds set answers=answers||jsonb_build_array(jsonb_build_object('index',idx,'answer_id',null,'correct',false,'timed_out',true)),cursor=cursor+1,question_started=null where session_id=s.id and user_id=me returning * into r;if p_action in ('round','answer') then return jsonb_build_object('state','feedback','card',card,'feedback',jsonb_build_object('index',idx,'answer_id',null,'correct',false,'timed_out',true));end if;end if;
  if p_action='round' then if r.finished_at is not null then return jsonb_build_object('state','rating','score',r.score,'can_rate',(select creator_id<>me from public.battle_decks where id=s.battle_deck_id));end if;if r.cursor>=15 then return jsonb_build_object('state','finish','score',r.score);end if; if r.question_started is null then update public.battle_rounds set question_started=now(),started_at=coalesce(started_at,now()) where session_id=s.id and user_id=me returning * into r;end if;card:=s.cards->r.cursor;return jsonb_build_object('state','question','index',r.cursor,'seconds',greatest(0,30-extract(epoch from(now()-r.question_started))::int),'question',card->>'question','options',card->'answers','allow_calculator',coalesce((card->>'allow_calculator')::boolean,false));end if;
  idx:=(p_data->>'index')::int;if r.cursor<>idx or r.question_started is null or idx>=15 then raise exception 'This question cannot be answered now';end if;card:=s.cards->idx;if not exists(select 1 from jsonb_array_elements(card->'answers')a where a->>'id'=p_data->>'answer_id') then raise exception 'Choose one of the four answers';end if;correct:=p_data->>'answer_id'=card->>'correct_answer_id';update public.battle_rounds set answers=answers||jsonb_build_array(jsonb_build_object('index',idx,'answer_id',p_data->>'answer_id','correct',correct,'timed_out',false)),cursor=cursor+1,score=score+case when correct then 1 else 0 end,question_started=null where session_id=s.id and user_id=me;return jsonb_build_object('state','feedback','card',card,'feedback',jsonb_build_object('index',idx,'answer_id',p_data->>'answer_id','correct',correct,'timed_out',false));
 end if;
 raise exception 'Unknown Battle action';
end $$;
revoke all on function public.battle_rate(uuid,uuid,text,boolean,boolean),public.battle_finish(uuid) from public,anon,authenticated;
grant execute on function public.battle_action(text,jsonb) to authenticated;
commit;
