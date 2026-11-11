// Isolated PostgreSQL tests: no production identities or network calls.
import fs from 'node:fs/promises';import os from 'node:os';import path from 'node:path';
import assert from 'node:assert/strict';import {randomUUID} from 'node:crypto';import {spawnSync} from 'node:child_process';
const {PGlite}=await import(process.env.PGLITE_MODULE || '@electric-sql/pglite');
if(process.argv[2]==='reload'){
 const db=new PGlite(process.argv[3]);const row=(await db.query('select * from public.play_rounds where duel_id=$1 and user_id=$2',[process.argv[4],process.argv[5]])).rows[0];
 assert.equal(row.cursor,1);assert.equal(row.answers.length,1);await db.close();console.log('PASS full process restart retains question progress');process.exit(0);
}
const dir=await fs.mkdtemp(path.join(os.tmpdir(),'studyduel-play-'));const db=new PGlite(path.join(dir,'db'));
const A=randomUUID(),B=randomUUID(),C=randomUUID(),D=randomUUID();let passed=0;
async function admin(sql,args=[]){await db.exec('reset role');return db.query(sql,args);}
async function who(id,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id]);await db.exec('set role '+role);}
async function action(id,act,data={}){await who(id);return (await db.query('select public.play_action($1,$2::jsonb) r',[act,JSON.stringify(data)])).rows[0].r;}
async function ok(id,act,data={}){const r=await action(id,act,data);assert.ok(!r.error,r.error);return r;}
async function fail(id,act,data={},match){const r=await action(id,act,data);assert.ok(r.error,JSON.stringify(r));if(match)assert.match(r.error,match);return r;}
async function test(name,fn){await fn();passed++;console.log('PASS '+name);}
async function deck(owner,name='Deck',language='English',course='Finance'){
 await who(owner);const d={id:randomUUID(),name,language,course,cards:Array.from({length:15},(_,i)=>{const answers=Array.from({length:4},(_,j)=>({id:randomUUID(),text:`${name} answer ${i}.${j}`}));return {id:randomUUID(),question:`${name} question ${i}`,answers,correct_answer_id:answers[0].id};})};
 const r=(await db.query('select public.review_deck($1::jsonb) r',[JSON.stringify(d)])).rows[0].r;
 const k=(await db.query('select public.publish_deck($1,$2::jsonb) r',[r.id,JSON.stringify(d)])).rows[0].r;return {...d,id:k.id};
}
async function expire(did){await admin("update public.play_duels set deadline=now()-interval '1 second' where id=$1",[did]);await ok(A,'list');}
try{
 await db.exec(`create role anon;create role authenticated;create schema auth;
 create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
 grant usage on schema auth to anon,authenticated;
 create table public.profiles(id uuid primary key,username text,university text,languages text[] not null,xp integer not null default 0,win_streak integer not null default 0);
 create table public.profile_private(user_id uuid primary key references public.profiles(id),courses text[]);
 create table public.friend_edges(low_id uuid,high_id uuid,state text);
 grant select on public.profiles to authenticated;
 grant select on public.profile_private to authenticated;
 alter table public.profile_private enable row level security;create policy own_read on public.profile_private for select to authenticated using(user_id=auth.uid());`);
 for(const [id,name,uni,langs]of [[A,'Alice','Uni A',['English','Portuguese']],[B,'Bob','Uni A',['English','Portuguese']],[C,'Chris','Uni B',['English']],[D,'Dana','Uni A',['German']]]){
  await db.query('insert into public.profiles(id,username,university,languages) values($1,$2,$3,$4)',[id,name,uni,langs]);await db.query("insert into public.profile_private values($1,array['Finance','Math'])",[id]);
 }
 await db.exec(await fs.readFile(new URL('../supabase/decks-schema.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/play-schema.sql',import.meta.url),'utf8'));
 for(const peer of [B,C,D])await db.query("insert into public.friend_edges values(least($1::uuid,$2::uuid),greatest($1::uuid,$2::uuid),'accepted')",[A,peer]);
 const da=await deck(A,'A'),dbb=await deck(B,'B'),dc=await deck(C,'C'),dd=await deck(D,'D','German'),pt=await deck(B,'Portuguese','Portuguese'),math=await deck(B,'Math','English','Math');
 await test('new deck rejects undeclared language',async()=>{await who(A);await assert.rejects(()=>db.query('select public.review_deck($1::jsonb)',[JSON.stringify({...da,id:randomUUID(),language:''})]));});
 await test('legacy language is creator-only and can only be set once',async()=>{await admin('update public.decks set language=null where id=$1',[da.id]);await fail(B,'set_language',{deck_id:da.id,language:'English'});await fail(A,'join',{deck_id:da.id});await ok(A,'set_language',{deck_id:da.id,language:'English'});await fail(A,'set_language',{deck_id:da.id,language:'Portuguese'});});
 await test('no match without two explicit searches; window is one hour and poll/retry cannot renew',async()=>{
  await ok(B,'list');await ok(A,'join',{deck_id:da.id});let state=await ok(A,'list');assert.equal(state.duels.length,0);const end=state.queue.expires_at;assert.ok(Date.parse(end)-Date.now()>3590000);await ok(A,'join',{deck_id:da.id});assert.equal((await ok(A,'list')).queue.expires_at,end);
 });
 await test('cancellation removes eligibility',async()=>{await ok(A,'cancel_search');await ok(B,'join',{deck_id:dbb.id});assert.equal((await ok(B,'list')).duels.length,0);await ok(B,'cancel_search');});
 await test('university, language and course filters keep incompatible opt-ins separate',async()=>{
  await ok(A,'join',{deck_id:da.id});for(const [u,k] of [[C,dc],[D,dd],[B,pt],[B,math]]){await ok(u,'join',{deck_id:k.id});assert.equal((await ok(u,'list')).duels.length,0);await ok(u,'cancel_search');}await ok(A,'cancel_search');
 });
 await test('expired and inactive searches do not match',async()=>{
  await ok(B,'join',{deck_id:dbb.id});await admin("update public.play_presence set last_seen=now()-interval '25 hours' where user_id=$1",[B]);await ok(A,'join',{deck_id:da.id});assert.equal((await ok(A,'list')).duels.length,0);await ok(A,'cancel_search');await ok(B,'cancel_search');
  await ok(B,'join',{deck_id:dbb.id});await admin("update public.play_queue set expires_at=now()-interval '1 second' where user_id=$1",[B]);await ok(A,'join',{deck_id:da.id});assert.equal((await ok(A,'list')).duels.length,0);await ok(A,'cancel_search');
 });
 let duel;
 await test('compatible random opt-ins create one shared 30-question snapshot and consume both queues',async()=>{
  await ok(A,'join',{deck_id:da.id});duel=(await ok(B,'join',{deck_id:dbb.id})).duel_id;assert.ok(duel);assert.equal((await ok(A,'list')).queue,null);assert.equal((await ok(B,'list')).queue,null);
  const g=(await admin('select cards from public.play_duels where id=$1',[duel])).rows[0];assert.deepEqual(g.cards,[...dbb.cards,...da.cards]);
 });
 await test('third parties and anonymous users cannot access private play state or helper functions',async()=>{
  await fail(C,'round',{duel_id:duel});await who(C);for(const table of ['play_queue','play_rounds','play_duels','play_presence','play_invites'])await assert.rejects(()=>db.query('select * from public.'+table));await assert.rejects(()=>db.query('select public.play_finish($1)',[duel]));await who('','anon');await assert.rejects(()=>db.query("select public.play_action('list')"));
 });
 await test('question timer survives reload; no future answers; duplicate answer scores once',async()=>{
  const q=await ok(A,'round',{duel_id:duel});assert.equal(q.state,'question');assert.equal(q.index,0);assert.ok(!JSON.stringify(q).includes('correct_answer_id'));
  const before=(await admin('select question_started from public.play_rounds where duel_id=$1 and user_id=$2',[duel,A])).rows[0].question_started;
  await ok(A,'round',{duel_id:duel});const after=(await admin('select question_started from public.play_rounds where duel_id=$1 and user_id=$2',[duel,A])).rows[0].question_started;assert.equal(+before,+after);
  const response=await ok(A,'answer',{duel_id:duel,index:0,answer_id:dbb.cards[0].correct_answer_id});assert.equal(response.feedback.correct,true);
  await ok(A,'answer',{duel_id:duel,index:0,answer_id:dbb.cards[0].answers[1].id});const r=(await admin('select score,cursor from public.play_rounds where duel_id=$1 and user_id=$2',[duel,A])).rows[0];assert.deepEqual(r,{score:1,cursor:1});
 });
 await test('late answer times out on server without awarding points',async()=>{
  await ok(A,'round',{duel_id:duel});await admin("update public.play_rounds set question_started=now()-interval '31 seconds' where duel_id=$1 and user_id=$2",[duel,A]);const r=await ok(A,'answer',{duel_id:duel,index:1,answer_id:dbb.cards[1].correct_answer_id});assert.equal(r.feedback.timed_out,true);assert.equal(r.feedback.correct,false);
 });
 await test('complete 30 answers, require both ratings, hide opponent score while pending, settle XP once',async()=>{
  for(const [u,start]of [[A,2],[B,0]]){
   for(let i=start;i<30;i++){const q=await ok(u,'round',{duel_id:duel});assert.equal(q.index,i);await ok(u,'answer',{duel_id:duel,index:i,answer_id:(i<15?dbb.cards[i]:da.cards[i-15]).correct_answer_id});}
   assert.equal((await ok(u,'round',{duel_id:duel})).state,'rating');await fail(u,'finish',{duel_id:duel,ratings:{[da.id]:'up'}});
   await ok(u,'finish',{duel_id:duel,ratings:{[da.id]:'up',[dbb.id]:'neutral'}});
   if(u===A){const s=await ok(A,'list');assert.equal(s.duels[0].status,'Pending');assert.equal(s.duels[0].opponent_score,null);}
  }
  const a=(await ok(A,'list')).duels[0],b=(await ok(B,'list')).duels[0];assert.equal(a.result,'loss');assert.equal(b.result,'win');assert.equal(b.xp_delta,40);assert.equal(a.opponent_score,30);await ok(B,'finish',{duel_id:duel,ratings:{}});assert.equal((await admin('select xp from public.profiles where id=$1',[B])).rows[0].xp,40);
 });
 await test('friend course mismatch requires explicit override; language mismatch always blocks',async()=>{
  await admin("update public.profile_private set courses=array['Math'] where user_id=$1",[B]);await fail(A,'invite',{deck_id:da.id,friend_id:B},/Confirm/);await fail(A,'invite',{deck_id:da.id,friend_id:D,confirm_missing_course:true},/language/);
  await ok(A,'invite',{deck_id:da.id,friend_id:B,confirm_missing_course:true});await fail(A,'invite',{deck_id:da.id,friend_id:B,confirm_missing_course:true},/pending/);
 });
 let friendDuel;
 await test('only recipient accepts; accepts selected same deck with exactly 30 entries; retry is idempotent',async()=>{
  const inv=(await ok(B,'list')).invites[0];assert.equal((await ok(B,'list')).duels.length,1);await fail(A,'accept',{invite_id:inv.id,deck_id:da.id});await fail(C,'accept',{invite_id:inv.id,deck_id:dc.id});
  friendDuel=(await ok(B,'accept',{invite_id:inv.id,deck_id:da.id})).duel_id;assert.equal((await ok(B,'accept',{invite_id:inv.id,deck_id:da.id})).duel_id,friendDuel);
  const cards=(await admin('select cards from public.play_duels where id=$1',[friendDuel])).rows[0].cards;assert.deepEqual(cards,[...da.cards,...da.cards]);await admin("update public.profile_private set courses=array['Finance','Math'] where user_id=$1",[B]);
 });
 await test('abandonment requires confirmation and awards a single loss/win',async()=>{await fail(A,'abandon',{duel_id:friendDuel});await ok(A,'abandon',{duel_id:friendDuel,confirmed:true});await ok(A,'abandon',{duel_id:friendDuel,confirmed:true});assert.equal((await admin('select xp from public.profiles where id=$1',[B])).rows[0].xp,80);});
 await test('paused invitations, decline cooldown and expired invitations cannot create duels',async()=>{
  await ok(B,'set_pause',{paused:true});await fail(A,'invite',{friend_id:B,deck_id:da.id},/paused/);await ok(B,'set_pause',{paused:false});await ok(A,'invite',{friend_id:B,deck_id:da.id});let inv=(await ok(B,'list')).invites[0];await ok(B,'decline',{invite_id:inv.id});await fail(A,'invite',{friend_id:B,deck_id:da.id},/24 hours/);
  await ok(A,'invite',{friend_id:C,deck_id:da.id});inv=(await ok(C,'list')).invites[0];await admin("update public.play_invites set expires_at=now()-interval '1 second' where id=$1",[inv.id]);await fail(C,'accept',{invite_id:inv.id,deck_id:dc.id},/pending/);
 });
 await test('timeout of both unfinished rounds settles losses once',async()=>{
  await ok(A,'join',{deck_id:da.id});const id=(await ok(B,'join',{deck_id:dbb.id})).duel_id;await expire(id);assert.equal((await ok(A,'list')).duels.find(d=>d.id===id).result,'loss');assert.equal((await ok(B,'list')).duels.find(d=>d.id===id).result,'loss');
 });
 await test('pending and hourly invitation limits are enforced on the server',async()=>{
  await admin('delete from public.play_invites');
  for(let i=0;i<5;i++)await admin("insert into public.play_invites(sender,recipient,deck_id,state,created_at) values($1,$2,$3,'pending',now()-interval '2 hours')",[A,C,da.id]);
  await fail(A,'invite',{friend_id:B,deck_id:da.id},/limit/);
  await admin("update public.play_invites set state='cancelled',created_at=now()");await fail(A,'invite',{friend_id:B,deck_id:da.id},/limit/);
  await admin('delete from public.play_invites');
  for(let i=0;i<10;i++)await admin("insert into public.play_invites(sender,recipient,deck_id) values($1,$2,$3)",[C,B,dc.id]);
  await fail(A,'invite',{friend_id:B,deck_id:da.id},/limit/);await admin('delete from public.play_invites');
 });
 async function newPair(){await ok(A,'join',{deck_id:da.id});return (await ok(B,'join',{deck_id:dbb.id})).duel_id;}
 await test('fourth consecutive win awards 80 XP once',async()=>{
  await admin('update public.profiles set xp=120,win_streak=3 where id=$1',[B]);const id=await newPair();await ok(A,'abandon',{duel_id:id,confirmed:true});await ok(B,'list');const row=(await admin('select xp,win_streak from public.profiles where id=$1',[B])).rows[0];assert.deepEqual(row,{xp:200,win_streak:4});
 });
 await test('equal completed scores draw and reset streaks without XP change',async()=>{
  const id=await newPair();await admin('update public.play_rounds set cursor=30,score=20 where duel_id=$1',[id]);const ratings={[da.id]:'up',[dbb.id]:'up'};await ok(A,'finish',{duel_id:id,ratings});await ok(B,'finish',{duel_id:id,ratings});const r=(await ok(B,'list')).duels.find(d=>d.id===id);assert.equal(r.result,'draw');assert.equal(r.xp_delta,0);assert.equal((await admin('select win_streak from public.profiles where id=$1',[B])).rows[0].win_streak,0);
 });
 await test('only completed player wins when the 24-hour deadline expires',async()=>{
  const id=await newPair();await admin('update public.play_rounds set cursor=30,score=12 where duel_id=$1 and user_id=$2',[id,A]);await ok(A,'finish',{duel_id:id,ratings:{[da.id]:'up',[dbb.id]:'up'}});await expire(id);const r=(await ok(A,'list')).duels.find(d=>d.id===id);assert.equal(r.result,'win');assert.equal(r.opponent_score,null);assert.equal(r.xp_delta,40);
 });
 // Leave one durable answer for a fresh-process check.
 await ok(A,'join',{deck_id:da.id});const saved=(await ok(B,'join',{deck_id:dbb.id})).duel_id;await ok(A,'round',{duel_id:saved});await ok(A,'answer',{duel_id:saved,index:0,answer_id:dbb.cards[0].correct_answer_id});
 await db.close();const child=spawnSync(process.execPath,[new URL(import.meta.url).pathname,'reload',path.join(dir,'db'),saved,A],{encoding:'utf8',env:process.env});assert.equal(child.status,0,child.stderr);console.log(child.stdout.trim());console.log(`${passed+1} isolated Play database checks passed`);
}catch(error){console.error(error.message,error.where||'',error.detail||'');process.exitCode=1;}finally{await db.close().catch(()=>{});await fs.rm(dir,{recursive:true,force:true});}
