begin;
create table public.chat_threads(
 id uuid primary key default gen_random_uuid(),low_id uuid not null references public.profiles(id),high_id uuid not null references public.profiles(id),
 created_at timestamptz not null default now(),check(low_id<high_id),unique(low_id,high_id));
create table public.chat_messages(
 id bigint generated always as identity primary key,thread_id uuid not null references public.chat_threads(id),sender uuid not null references public.profiles(id),
 request_id uuid not null,body text not null check(length(btrim(body)) between 1 and 2000),created_at timestamptz not null default now(),unique(sender,request_id));
create index chat_messages_thread on public.chat_messages(thread_id,id desc);
create index chat_messages_rate on public.chat_messages(sender,created_at desc);
create table public.chat_reads(thread_id uuid references public.chat_threads(id),user_id uuid references public.profiles(id),last_id bigint not null default 0,primary key(thread_id,user_id));
alter table public.chat_threads enable row level security;
alter table public.chat_messages enable row level security;
alter table public.chat_reads enable row level security;
revoke all on public.chat_threads,public.chat_messages,public.chat_reads from public,anon,authenticated;
revoke all on sequence public.chat_messages_id_seq from public,anon,authenticated;
create function public.chat_action(p_action text,p_data jsonb default '{}') returns jsonb language plpgsql security definer set search_path='' as $$
declare me uuid:=auth.uid();peer uuid;tid uuid;entry public.chat_threads;message_row public.chat_messages;result jsonb;items jsonb;body_text text;rid uuid;before_id bigint;through_id bigint;
begin
 if me is null or not exists(select 1 from public.profiles where id=me) then raise exception 'Sign in and complete your profile first';end if;
 if p_action='partner' then
  if p_data->>'kind'='battle' then
   select case when p1=me then p2 else p1 end into peer from public.play_duels where id=(p_data->>'id')::uuid and me in(p1,p2);
  elsif p_data->>'kind'='study' then
   select other.user_id into peer from public.study_sessions own join public.study_sessions other on other.id=own.partner_id and other.partner_id=own.id where own.id=(p_data->>'id')::uuid and own.user_id=me;
  else raise exception 'Session unavailable';end if;
  return jsonb_build_object('partner',(select jsonb_build_object('id',id,'username',username,'image_path',image_path) from public.profiles where id=peer));
 elsif p_action='open' then
  peer:=(p_data->>'user_id')::uuid;
  if peer=me or not exists(select 1 from public.profiles where id=peer) then raise exception 'Choose another participant';end if;
  if not exists(select 1 from public.chat_threads where low_id=least(me,peer) and high_id=greatest(me,peer)) and
     not exists(select 1 from public.friend_edges where low_id=least(me,peer) and high_id=greatest(me,peer) and state='accepted') and
     not exists(select 1 from public.play_duels where me in(p1,p2) and peer in(p1,p2)) and
     not exists(select 1 from public.study_sessions own join public.study_sessions other on other.id=own.partner_id and other.partner_id=own.id where own.user_id=me and other.user_id=peer)
  then raise exception 'You can message friends or matched session partners';end if;
  insert into public.chat_threads(low_id,high_id) values(least(me,peer),greatest(me,peer)) on conflict(low_id,high_id) do update set low_id=excluded.low_id returning id into tid;
  return jsonb_build_object('id',tid);
 elsif p_action='list' then
  select coalesce(jsonb_agg(row_data order by latest desc nulls last),'[]') into result from (
   select coalesce(last_message.created_at,t.created_at) latest,jsonb_build_object('id',t.id,'username',p.username,'image_path',p.image_path,'user_id',p.id,
    'preview',left(coalesce(last_message.body,'No messages yet'),140),'from_me',last_message.sender=me,'updated_at',coalesce(last_message.created_at,t.created_at),
    'unread',(select count(*) from public.chat_messages m where m.thread_id=t.id and m.sender<>me and m.id>coalesce(r.last_id,0))) row_data
   from public.chat_threads t join public.profiles p on p.id=case when t.low_id=me then t.high_id else t.low_id end
   left join public.chat_reads r on r.thread_id=t.id and r.user_id=me
   left join lateral(select body,sender,created_at from public.chat_messages where thread_id=t.id order by id desc limit 1) last_message on true
   where me in(t.low_id,t.high_id)) q;
  return jsonb_build_object('threads',result);
 end if;
 tid:=(p_data->>'id')::uuid;
 select * into entry from public.chat_threads where id=tid and me in(low_id,high_id);
 if not found then raise exception 'Conversation unavailable';end if;
 peer:=case when entry.low_id=me then entry.high_id else entry.low_id end;
 if p_action='read' then
  perform pg_advisory_xact_lock(hashtextextended(tid::text,8124));
  before_id:=(p_data->>'before')::bigint;
  select coalesce(jsonb_agg(to_jsonb(m) order by m.id),'[]') into items from
   (select id,body,created_at,sender=me as from_me from public.chat_messages where thread_id=tid and (before_id is null or id<before_id) order by id desc limit 100) m;
  return jsonb_build_object('partner',(select jsonb_build_object('id',id,'username',username,'image_path',image_path) from public.profiles where id=peer),'messages',items,
   'has_older',exists(select 1 from public.chat_messages where thread_id=tid and id<(items->0->>'id')::bigint));
 elsif p_action='seen' then
  through_id:=(p_data->>'through')::bigint;
  if not exists(select 1 from public.chat_messages where thread_id=tid and id=through_id) then raise exception 'Message unavailable';end if;
  insert into public.chat_reads values(tid,me,through_id) on conflict(thread_id,user_id) do update set last_id=greatest(chat_reads.last_id,excluded.last_id);
  return '{}';
 elsif p_action='send' then
  body_text:=btrim(p_data->>'body');rid:=(p_data->>'request_id')::uuid;
  if body_text is null or length(body_text) not between 1 and 2000 or rid is null then raise exception 'Enter a message of 1 to 2,000 characters';end if;
  perform pg_advisory_xact_lock(hashtextextended(me::text,8123));
  perform pg_advisory_xact_lock(hashtextextended(tid::text,8124));
  select * into message_row from public.chat_messages where sender=me and request_id=rid;
  if found then
   if message_row.thread_id<>tid or message_row.body<>body_text then raise exception 'Please submit the changed message again';end if;
   return jsonb_build_object('id',message_row.id);
  end if;
  if (select count(*) from public.chat_messages where sender=me and created_at>now()-interval '1 minute')>=20 then raise exception 'Please wait a moment before sending more messages';end if;
  insert into public.chat_messages(thread_id,sender,request_id,body,created_at) values(tid,me,rid,body_text,clock_timestamp()) returning * into message_row;
  return jsonb_build_object('id',message_row.id);
 end if;
 raise exception 'Unknown chat action';
exception when others then
 return jsonb_build_object('error',case when sqlstate='P0001' then sqlerrm else 'Could not complete this chat action. Please retry.' end);
end $$;
revoke all on function public.chat_action(text,jsonb) from public,anon;
grant execute on function public.chat_action(text,jsonb) to authenticated;
commit;
