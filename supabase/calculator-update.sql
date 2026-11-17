-- Per-question calculator permission; existing cards default to disabled.
begin;

create or replace function public.check_deck(p_draft jsonb) returns void language plpgsql security invoker set search_path='' as $$
declare c jsonb; a jsonb; ids text[]:='{}'; correct_count integer;
begin
 if jsonb_typeof(p_draft) is distinct from 'object' or
 jsonb_typeof(p_draft->'name') is distinct from 'string' or length(trim(p_draft->>'name'))=0 or
 jsonb_typeof(p_draft->'course') is distinct from 'string' or length(trim(p_draft->>'course'))=0 then raise exception 'Enter a deck name and course';end if;
 if jsonb_typeof(p_draft->'id') is distinct from 'string' then raise exception 'Invalid draft identity';end if;
 perform (p_draft->>'id')::uuid;
 if jsonb_typeof(p_draft->'cards') is distinct from 'array' then raise exception 'Exactly 15 cards required';end if;
 if jsonb_array_length(p_draft->'cards')<>15 then raise exception 'Exactly 15 cards required';end if;
 for c in select value from jsonb_array_elements(p_draft->'cards') loop
   if c?'allow_calculator' and jsonb_typeof(c->'allow_calculator') is distinct from 'boolean' then raise exception 'Calculator permission must be true or false';end if;
  if jsonb_typeof(c->'id') is distinct from 'string' or jsonb_typeof(c->'question') is distinct from 'string' or length(trim(c->>'question'))=0 then raise exception 'Complete the question';end if;
  perform (c->>'id')::uuid;
  if c->>'id'=any(ids) then raise exception 'Duplicate identity';end if; ids:=array_append(ids,c->>'id');
  if jsonb_typeof(c->'answers') is distinct from 'array' then raise exception 'Four answers required';end if;
  if jsonb_array_length(c->'answers')<>4 then raise exception 'Four answers required';end if;
  correct_count:=0;
  for a in select value from jsonb_array_elements(c->'answers') loop
   if jsonb_typeof(a->'id') is distinct from 'string' or jsonb_typeof(a->'text') is distinct from 'string' or length(trim(a->>'text'))=0 then raise exception 'Complete all answers';end if;
   perform (a->>'id')::uuid;
   if a->>'id'=any(ids) then raise exception 'Duplicate identity';end if;ids:=array_append(ids,a->>'id');
   if jsonb_typeof(c->'correct_answer_id')='string' and a->>'id'=c->>'correct_answer_id' then correct_count:=correct_count+1;end if;
  end loop;
  if correct_count<>1 then raise exception 'One correct answer required';end if;
 end loop;
end $$;

create or replace function public.study_action(p_action text,p_data jsonb default '{}') returns jsonb language plpgsql security definer set search_path='' as $$
declare me uuid:=auth.uid();s public.study_sessions;o public.study_sessions;k public.study_decks;legacy public.decks;
 d jsonb;c jsonb;payload jsonb;selected jsonb;answer public.study_answers;target uuid;rev integer;cnt integer;v_idx integer;score integer;other_score integer;
 campus text;langs text[];courses text[];mode text;result text;did uuid;review_id uuid;candidate record;ids text[];v jsonb;a jsonb;n integer;
begin
 if me is null then raise exception 'Sign in first';end if;
 -- Shared with Play lock: answer progress, matching and claims are atomic.
 perform pg_advisory_xact_lock(791146221);
 select university,languages into campus,langs from public.profiles where id=me;
 select p.courses into courses from public.profile_private p where p.user_id=me;
 if campus is null or courses is null then raise exception 'Complete your profile first';end if;
 update public.study_sessions set state='expired' where state='waiting' and expires_at<=now();
 if p_action in ('review_deck','save_deck') then
  d:=p_data->'draft';did:=(d->>'id')::uuid;rev:=coalesce((p_data->>'revision')::integer,0);
  if coalesce(length(trim(d->>'name')),0)=0 or not coalesce((d->>'language')=any(langs),false) or not exists(select 1 from unnest(courses) x where lower(trim(x))=lower(trim(d->>'course'))) then raise exception 'Enter a name and select your course and language';end if;
  if jsonb_typeof(d->'cards') is distinct from 'array' then raise exception 'Add questions';end if;
  if jsonb_array_length(d->'cards')<1 then raise exception 'Add at least one question';end if;
  ids:='{}';
  for c in select value from jsonb_array_elements(d->'cards') loop
   if c?'allow_calculator' and jsonb_typeof(c->'allow_calculator') is distinct from 'boolean' then raise exception 'Calculator permission must be true or false';end if;
   perform (c->>'id')::uuid;
   if c->>'id' is null or c->>'id'=any(ids) or coalesce(length(trim(c->>'question')),0)=0 then raise exception 'Complete each unique question';end if;ids:=array_append(ids,c->>'id');
   if jsonb_typeof(c->'answers') is distinct from 'array' then raise exception 'Four answers required';end if;
   if jsonb_array_length(c->'answers')<>4 then raise exception 'Four answers required';end if;n:=0;
   for a in select value from jsonb_array_elements(c->'answers') loop
    perform (a->>'id')::uuid;
    if a->>'id' is null or a->>'id'=any(ids) or coalesce(length(trim(a->>'text')),0)=0 then raise exception 'Complete four unique answers';end if;ids:=array_append(ids,a->>'id');
    if a->>'id'=c->>'correct_answer_id' then n:=n+1;end if;
   end loop;
   if n<>1 then raise exception 'Choose one correct answer';end if;
  end loop;
  select * into k from public.study_decks where id=did;
  if found then
   if k.creator_id<>me or k.revision<>rev then
    if p_action='save_deck' and k.creator_id=me and k.revision=rev+1 and k.snapshot=d then return jsonb_build_object('id',did);end if;
    raise exception 'This deck changed. Reload before editing';
   end if;
  elsif rev<>0 then raise exception 'Deck unavailable';end if;
  if exists(select 1 from public.decks where id=did) then raise exception 'Create a Study copy to edit a legacy deck';end if;
  if p_action='review_deck' then
   insert into public.study_reviews(user_id,deck_id,snapshot,revision) values(me,did,d,rev) returning id into review_id;return jsonb_build_object('id',review_id);
  end if;
  if not exists(select 1 from public.study_reviews where id=(p_data->>'review_id')::uuid and user_id=me and deck_id=did and revision=rev and snapshot=d) then raise exception 'Review this exact deck first';end if;
  insert into public.study_decks(id,creator_id,snapshot) values(did,me,d) on conflict(id) do update set snapshot=excluded.snapshot,revision=study_decks.revision+1,updated_at=now();return jsonb_build_object('id',did);
 elsif p_action='friend_options' then
  select snapshot into d from public.study_decks where id=(p_data->>'deck_id')::uuid and creator_id=me;
  if d is null then select jsonb_build_object('course',course,'language',language) into d from public.decks where id=(p_data->>'deck_id')::uuid and creator_id=me;end if;
  if d is null then raise exception 'Deck unavailable';end if;
  return jsonb_build_object('friends',coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'username',p.username)) from public.friend_edges f join public.profiles p on p.id=case when f.low_id=me then f.high_id else f.low_id end where f.state='accepted' and me in(f.low_id,f.high_id) and (d->>'language')=any(p.languages) and exists(select 1 from public.profile_private v,unnest(v.courses) course_option where v.user_id=p.id and lower(trim(course_option))=lower(trim(d->>'course')))),'[]'));
 elsif p_action='list' then
  return jsonb_build_object(
   'decks',coalesce((select jsonb_agg(x) from (
    select owned_deck.id,owned_deck.snapshot->>'name' name,owned_deck.snapshot->>'course' course,owned_deck.snapshot->>'language' language,jsonb_array_length(owned_deck.snapshot->'cards') count,owned_deck.revision,false legacy from public.study_decks owned_deck where creator_id=me
    union all select owned_deck.id,owned_deck.name,owned_deck.course,owned_deck.language,jsonb_array_length(owned_deck.cards),0,true from public.decks owned_deck where creator_id=me) x),'[]'),
   'shared',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',snapshot->>'name','course',snapshot->>'course','language',snapshot->>'language','author',snapshot->>'author','count',jsonb_array_length(snapshot->'cards'))) from public.study_shared where user_id=me),'[]'),
   'sessions',coalesce((select jsonb_agg(jsonb_build_object('id',session_row.id,'mode',session_row.mode,'name',session_row.snapshot->>'name','count',session_row.total,'state',case when session_row.finished_at is not null then 'completed' when session_row.deadline<=now() then 'expired' else session_row.state end,'cursor',session_row.cursor,'expires_at',session_row.expires_at,'deadline',session_row.deadline) order by session_row.created_at desc) from public.study_sessions session_row where session_row.user_id=me),'[]'),
   'open',coalesce((select jsonb_agg(jsonb_build_object('id',session_row.id,'course',session_row.course,'language',session_row.language,'count',session_row.total,'expires_at',session_row.expires_at)) from public.study_sessions session_row join public.profiles p on p.id=session_row.user_id where session_row.mode='random' and session_row.state='waiting' and session_row.expires_at>now() and session_row.user_id<>me and session_row.university=campus and session_row.language=any(langs) and session_row.language=any(p.languages) and exists(select 1 from unnest(courses) course_option where lower(trim(course_option))=lower(trim(session_row.course)))),'[]'),
   'invites',coalesce((select jsonb_agg(jsonb_build_object('id',session_row.id,'username',p.username,'course',session_row.course,'language',session_row.language,'count',session_row.total,'expires_at',session_row.expires_at)) from public.study_sessions session_row join public.profiles p on p.id=session_row.user_id where session_row.friend_id=me and session_row.mode='friend' and session_row.state='waiting' and session_row.expires_at>now()),'[]'),
   'friends',coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'username',p.username)) from public.friend_edges f join public.profiles p on p.id=case when f.low_id=me then f.high_id else f.low_id end where f.state='accepted' and me in(f.low_id,f.high_id)),'[]'),
   'feedback',coalesce((select jsonb_agg(jsonb_build_object('question',f.question,'body',f.body,'created_at',f.created_at,'username',p.username) order by f.created_at desc) from public.study_feedback f join public.profiles p on p.id=f.sender where f.author=me),'[]'));
 elsif p_action in ('deck','start') then
  did:=(p_data->>'deck_id')::uuid;if p_action='deck' then did:=(p_data->>'id')::uuid;end if;
  if coalesce((p_data->>'shared')::boolean,false) then
   select snapshot into d from public.study_shared where id=did and user_id=me;
   if p_action='start' and p_data->>'mode'<>'solo' then raise exception 'Only share a deck you authored';end if;
  else
   select * into k from public.study_decks where id=did and creator_id=me;
   if found then d:=public.study_snapshot(k.snapshot,k.id,me)||jsonb_build_object('revision',k.revision,'legacy',false);
   else
    select * into legacy from public.decks where id=did and creator_id=me;
    if found then d:=public.study_snapshot(jsonb_build_object('id',legacy.id,'name',legacy.name,'course',legacy.course,'language',legacy.language,'cards',legacy.cards),legacy.id,me)||jsonb_build_object('revision',0,'legacy',true);end if;
   end if;
  end if;
  if d is null then raise exception 'Deck unavailable';end if;
  if p_action='deck' then return public.study_decorate(d,me);end if;
  target:=(p_data->>'request_id')::uuid;
  if target is null then raise exception 'Session identity required';end if;
  select * into s from public.study_sessions where id=target;
  if found then if s.user_id<>me then raise exception 'Session unavailable';end if;return jsonb_build_object('id',s.id);end if;
  mode:=p_data->>'mode';cnt:=(p_data->>'count')::integer;
  if p_data?'levels' and (jsonb_typeof(p_data->'levels') is distinct from 'array' or jsonb_array_length(p_data->'levels')=0) then raise exception 'Choose at least one learning level';end if;
  if mode is null or mode not in ('solo','random','friend') then raise exception 'Choose a study mode';end if;
  if not coalesce((d->>'language')=any(langs),false) then raise exception 'Add this deck language to your profile';end if;
  if mode<>'solo' then
   if cnt is null or cnt not in (20,40,60,80,100) then raise exception 'Choose 20, 40, 60, 80 or 100 questions';end if;
   if not coalesce((p_data->>'consent')::boolean,false) then raise exception 'Agree to sharing your full deck snapshot';end if;
   if exists(select 1 from public.study_sessions active_session where user_id=me and active_session.mode<>'solo' and state in ('own','waiting','paired') and finished_at is null and (deadline is null or deadline>now()) and (expires_at is null or expires_at>now())) then raise exception 'Finish or cancel your existing together session first';end if;
   if jsonb_array_length(d->'cards')<cnt/2 then raise exception 'Your deck needs at least half the total question count';end if;
   if mode='random' and not exists(select 1 from unnest(courses) course_option where lower(trim(course_option))=lower(trim(d->>'course'))) then raise exception 'Select a course in your profile';end if;
  else
   if cnt is null or cnt<0 or cnt>100 then raise exception 'Choose 1 to 100 questions, or all';end if;
  end if;
  select coalesce(jsonb_agg(q.c),'[]') into selected from (
   select x.c from jsonb_array_elements(d->'cards') x(c)
   left join public.study_progress p on p.user_id=me and p.deck_id=(x.c->>'source_deck')::uuid and p.card_id=(x.c->>'id')::uuid and p.version=x.c->>'version'
   where mode<>'solo' or ((coalesce(jsonb_array_length(p_data->'chapters'),0)=0 or coalesce(x.c->>'chapter','') in(select jsonb_array_elements_text(p_data->'chapters'))) and (not(p_data?'levels') or coalesce(p.level::text,'new') in(select jsonb_array_elements_text(p_data->'levels'))))
   order by case when mode<>'solo' and p_data?'levels' and coalesce(p.level::text,'new') not in(select jsonb_array_elements_text(p_data->'levels')) then 1 else 0 end, random() limit case when mode<>'solo' then cnt/2 when cnt=0 then null else cnt end) q;
  if jsonb_array_length(selected)=0 or (cnt>0 and jsonb_array_length(selected)<case when mode='solo' then cnt else cnt/2 end) then raise exception 'Not enough eligible questions. Choose fewer questions or broader filters';end if;
  if mode='solo' then cnt:=jsonb_array_length(selected);end if;
  if mode='friend' and not(p_data?'join_id') then
   if exists(select 1 from public.play_presence where user_id=(p_data->>'friend_id')::uuid and pause_invites) then raise exception 'Your friend has paused invitations';end if;
   if (select count(*) from public.study_sessions session_row where session_row.user_id=me and session_row.mode='friend' and session_row.created_at>now()-interval '1 hour')>=5 then raise exception 'Study invitation limit reached. Try again later';end if;
   if not exists(select 1 from public.friend_edges where state='accepted' and me in(low_id,high_id) and (p_data->>'friend_id')::uuid in(low_id,high_id) and (p_data->>'friend_id')::uuid<>me) then raise exception 'Select an accepted friend';end if;
   if not exists(select 1 from public.profiles where id=(p_data->>'friend_id')::uuid and (d->>'language')=any(languages)) then raise exception 'Your friend must speak the deck language';end if;
   if not exists(select 1 from public.profile_private p,unnest(p.courses) course_option where p.user_id=(p_data->>'friend_id')::uuid and lower(trim(course_option))=lower(trim(d->>'course'))) then raise exception 'Your friend must have this course in their profile';end if;
  end if;
  insert into public.study_sessions(id,user_id,mode,deck_id,snapshot,cards,total,course,language,university,friend_id)
   values(target,me,mode,(d->>'id')::uuid,d,selected,cnt,d->>'course',d->>'language',campus,(p_data->>'friend_id')::uuid);
  if p_data?'join_id' then
   select * into o from public.study_sessions where id=(p_data->>'join_id')::uuid;
   if o.id is null or o.state<>'waiting' or o.expires_at<=now() or o.mode<>mode or o.user_id=me then raise exception 'This session is no longer available';end if;
   if mode='random' and o.university<>campus then raise exception 'Choose a session at your university';end if;
   if mode='friend' and o.friend_id is distinct from me then raise exception 'Only the invited friend can accept';end if;
   perform public.study_pair(o.id,target);
  end if;
  return jsonb_build_object('id',target);
 end if;
 select * into s from public.study_sessions where id=(p_data->>'id')::uuid;
 if p_action='decline' then
  if s.friend_id is distinct from me or s.state<>'waiting' then raise exception 'Invitation unavailable';end if;
  update public.study_sessions set state='cancelled' where id=s.id;return '{}';
 end if;
 if s.id is null or s.user_id<>me then raise exception 'Session unavailable';end if;
 if p_action='cancel' then
  if s.partner_id is not null then raise exception 'Your matched session stays resumable until its deadline';end if;
  update public.study_sessions set state='cancelled' where id=s.id and finished_at is null;return '{}';
 end if;
 if p_action='annotate' then
  v_idx:=(p_data->>'index')::integer;
  if not exists(select 1 from public.study_answers where session_id=s.id and study_answers.idx=v_idx) then raise exception 'Answer this question first';end if;
  c:=s.cards->v_idx;
  if length(coalesce(p_data->>'note',''))>4000 or length(coalesce(p_data->>'feedback',''))>2000 then raise exception 'Keep notes under 4000 and feedback under 2000 characters';end if;
  if p_data?'note' then insert into public.study_notes values(me,(c->>'source_deck')::uuid,(c->>'id')::uuid,c->>'version',coalesce(p_data->>'note','')) on conflict(user_id,deck_id,card_id,version) do update set note=excluded.note;end if;
  if length(trim(coalesce(p_data->>'feedback','')))>0 then insert into public.study_feedback(sender,author,deck_id,card_id,version,question,body) values(me,(c->>'author_id')::uuid,(c->>'source_deck')::uuid,(c->>'id')::uuid,c->>'version',c->>'question',trim(p_data->>'feedback')) on conflict do nothing;end if;
  return '{}';
 end if;
 if p_action='answer' then
  v_idx:=(p_data->>'index')::integer;
  if exists(select 1 from public.study_answers where session_id=s.id and study_answers.idx=v_idx) then return jsonb_build_object('saved',true);end if;
  if s.state in ('cancelled','expired','waiting') or s.deadline<=now() or s.finished_at is not null or v_idx is distinct from s.cursor or v_idx>=jsonb_array_length(s.cards) then raise exception 'This question cannot be answered now';end if;
  c:=s.cards->v_idx;
  if not exists(select 1 from jsonb_array_elements(c->'answers')ans where ans->>'id'=p_data->>'answer_id') then raise exception 'Choose one of the four answers';end if;
  insert into public.study_answers(session_id,idx,answer_id,correct) values(s.id,v_idx,(p_data->>'answer_id')::uuid,(p_data->>'answer_id')=(c->>'correct_answer_id'));
  perform public.study_progress_add(me,c,(p_data->>'answer_id')=(c->>'correct_answer_id'));
  if v_idx+1=s.total then
   update public.study_sessions set finished_at=now() where id=s.id;
   if s.partner_id is not null then insert into public.study_shared(user_id,session_id,snapshot) select me,s.id,snapshot from public.study_sessions where id=s.partner_id on conflict(session_id) do nothing;end if;
  end if;
  return jsonb_build_object('saved',true);
 elsif p_action='next' then
  v_idx:=(p_data->>'index')::integer;
  if v_idx is distinct from s.cursor then return '{}';end if;
  if not exists(select 1 from public.study_answers where session_id=s.id and study_answers.idx=v_idx) then raise exception 'Answer before continuing';end if;
  update public.study_sessions set cursor=cursor+1 where id=s.id returning * into s;
  if s.cursor=s.total then update public.study_sessions set state='completed' where id=s.id;
  elsif s.mode<>'solo' and s.cursor=s.total/2 and s.partner_id is null then
   update public.study_sessions set state='waiting',expires_at=now()+interval '24 hours' where id=s.id returning * into s;
   if s.mode='random' then
    select q.* into o from public.study_sessions q join public.profiles p on p.id=q.user_id
     where q.id<>s.id and q.user_id<>me and q.mode='random' and q.state='waiting' and q.expires_at>now() and q.total=s.total and q.university=s.university and lower(trim(q.course))=lower(trim(s.course)) and q.language=s.language and q.deck_id<>s.deck_id and q.language=any(p.languages)
     and exists(select 1 from public.profile_private v,unnest(v.courses) course_option where v.user_id=q.user_id and lower(trim(course_option))=lower(trim(s.course)))
     order by q.created_at limit 1;
    if o.id is not null then perform public.study_pair(o.id,s.id);end if;
   end if;
  end if;
  return '{}';
 elsif p_action='round' then
  select count(*) filter(where correct)::integer into score from public.study_answers where session_id=s.id;
  select * into o from public.study_sessions where id=s.partner_id;
  if s.cursor<s.total then
   select * into answer from public.study_answers where session_id=s.id and study_answers.idx=s.cursor;
   if found then
    c:=s.cards->s.cursor;
    payload:=public.study_decorate(jsonb_build_object('cards',jsonb_build_array(c)),me);
    return jsonb_build_object('state','feedback','index',s.cursor,'total',s.total,'card',payload->'cards'->0,'correct',answer.correct,'answer_id',answer.answer_id);
   end if;
  end if;
  if s.finished_at is not null then
   result:='Completed';
   if o.id is not null then
    if o.finished_at is not null then
     select count(*) filter(where correct)::integer into other_score from public.study_answers where session_id=o.id;
     result:=case when score>other_score then 'Win' when score<other_score then 'Loss' else 'Draw' end;
    elsif s.deadline<=now() then result:='Partner did not finish';else result:='Waiting for your study partner';end if;
   end if;
   return jsonb_build_object('state','completed','score',score,'total',s.total,'result',result,'opponent_score',other_score,'deadline',s.deadline,'shared',s.partner_id is not null);
  end if;
  if s.state in ('waiting','cancelled','expired') or s.deadline<=now() then return jsonb_build_object('state',case when s.deadline<=now() then 'expired' else s.state end,'expires_at',s.expires_at,'deadline',s.deadline,'score',score);end if;
  c:=s.cards->s.cursor;
  return jsonb_build_object('state','question','index',s.cursor,'total',s.total,'question',c->>'question','chapter',c->>'chapter','allow_calculator',coalesce(c->'allow_calculator','false'::jsonb),'options',c->'answers','part',case when s.mode='solo' then 'Solo study' when s.cursor<s.total/2 then 'Your questions' else 'Your partner’s questions' end,'deadline',s.deadline);
 end if;
 raise exception 'Unknown Study action';
exception when others then
 -- This block rolls back every write in a rejected action before returning a safe error.
 return jsonb_build_object('error',case when sqlstate='P0001' then sqlerrm else 'Study action could not be saved. Check your selections and refresh.' end);
end $$;

create or replace function public.play_action(p_action text,p_data jsonb default '{}') returns jsonb language plpgsql security definer set search_path='' as $$
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
  return jsonb_build_object('state','question','index',round.cursor,'question',card->>'question','allow_calculator',coalesce(card->'allow_calculator','false'::jsonb),'options',options,'seconds',greatest(0,ceil(extract(epoch from(round.question_started+interval '30 seconds'-now())))));
 end if;
 raise exception 'Unknown Play action';
exception when raise_exception then return jsonb_build_object('error',sqlerrm);
end $$;

commit;
