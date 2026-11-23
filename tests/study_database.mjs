// Real PostgreSQL semantics in an isolated local database; no production data.
import fs from 'node:fs/promises';import os from 'node:os';import path from 'node:path';
import assert from 'node:assert/strict';import {randomUUID} from 'node:crypto';import {spawnSync} from 'node:child_process';
const {PGlite}=await import(process.env.PGLITE_MODULE||'@electric-sql/pglite');
if(process.argv[2]==='reload') {const db=new PGlite(process.argv[3]);assert.equal((await db.query('select count(*)::int n from study_answers')).rows[0].n,Number(process.argv[4]));await db.close();console.log('PASS restart preserves study answers');process.exit(0);}
const dir=await fs.mkdtemp(path.join(os.tmpdir(),'uniarena-study-'));const db=new PGlite(path.join(dir,'db'));
const A=randomUUID(),B=randomUUID(),C=randomUUID();let passed=0;
async function admin(sql,args=[]){await db.exec('reset role');return db.query(sql,args);}
async function who(id,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id]);await db.exec('set role '+role);}
async function act(u,a,d={}){await who(u);return(await db.query('select study_action($1,$2::jsonb) r',[a,JSON.stringify(d)])).rows[0].r;}
async function ok(u,a,d={}){const r=await act(u,a,d);assert.ok(!r.error,r.error);return r;}
async function bad(u,a,d={}){assert.ok((await act(u,a,d)).error);}
async function publication(u,a,d={}){await who(u);return(await db.query('select study_public_action($1,$2::jsonb) r',[a,JSON.stringify(d)])).rows[0].r;}
async function publicationOk(u,a,d={}){const r=await publication(u,a,d);assert.ok(!r.error,r.error);return r;}
async function test(n,f){await f();passed++;console.log('PASS '+n);}
function draft(n=50){return {id:randomUUID(),name:'Study finance',course:'Finance',language:'English',cards:Array.from({length:n},(_,i)=>{const answers=Array.from({length:4},(_,j)=>({id:randomUUID(),text:`Answer ${j}`}));return{id:randomUUID(),question:`Question ${i}`,chapter:i<25?'Lecture 1':'Lecture 2',answers,correct_answer_id:answers[0].id};})};}
async function save(u,d,revision=0){const r=await ok(u,'review_deck',{draft:d,revision});return ok(u,'save_deck',{draft:d,revision,review_id:r.id});}
async function start(u,d,mode='solo',extra={}){return ok(u,'start',{request_id:randomUUID(),deck_id:d.id,mode,count:mode==='solo'?10:20,consent:true,...extra});}
async function half(u,id,n=10,wrong=false){for(let i=0;i<n;i++){const r=await ok(u,'round',{id});assert.equal(r.state,'question');const card=(await admin('select cards from study_sessions where id=$1',[id])).rows[0].cards[r.index];const answer=wrong?card.answers.find(a=>a.id!==card.correct_answer_id).id:card.correct_answer_id;await ok(u,'answer',{id,index:r.index,answer_id:answer});const feedback=await ok(u,'round',{id});assert.equal(feedback.state,'feedback');await ok(u,'next',{id,index:r.index});}}
try{
 await db.exec(`create role anon;create role authenticated;create schema auth;create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;grant usage on schema auth to anon,authenticated;
 create table profiles(id uuid primary key,username text,university text,languages text[],xp int default 0,win_streak int default 0);
 create table profile_private(user_id uuid primary key,courses text[]);create table friend_edges(low_id uuid,high_id uuid,state text);grant select on profiles,profile_private to authenticated;`);
 for(const [u,name,uni] of [[A,'Alice','Uni'],[B,'Bob','Uni'],[C,'Chris','Other']]){await db.query("insert into profiles values($1,$2,$3,array['English'],123,2)",[u,name,uni]);await db.query("insert into profile_private values($1,array['Finance'])",[u]);}
 await db.query("insert into friend_edges values(least($1::uuid,$2::uuid),greatest($1::uuid,$2::uuid),'accepted')",[A,B]);
 for(const f of ['decks-schema.sql','play-schema.sql','study-schema.sql'])await db.exec((await fs.readFile(new URL('../supabase/'+f,import.meta.url),'utf8')).replace("else 'Study action could not be saved. Check your selections and refresh.'","else sqlerrm"));
 await db.exec(await fs.readFile(new URL('../supabase/calculator-update.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/study-deck-publication.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/study-deck-publication-visibility.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/study-deck-publication-course-variable.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/study-deck-publication-sort-time.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/study-session-progress.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/migrations/20261121210000_study_timeouts.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/migrations/20261122160000_study_answer_review.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/migrations/20261122170000_study_session_dashboard.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/migrations/20261122190000_study_stop.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/migrations/20261122210000_study_friend_waiting_name.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/migrations/20261122220000_study_sessions_per_friend.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/migrations/20261122230000_list_all_study_friend_invites.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/migrations/20261122240000_study_session_dashboard_matching_criteria.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/migrations/20261123000000_study_result_summary.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/migrations/20261123010000_release_completed_study_slot.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/migrations/20261123020000_release_completed_random_study_slot.sql',import.meta.url),'utf8'));
 async function dashboard(user,id){
  await who(user);
  const data=(await db.query('select study_session_dashboard() as data')).rows[0].data;
  return data.sessions.find(row=>row.id===id);
 }
 await test('finished review uses original questions and answers, scoped to their player',async()=>{
  const d=draft(2);await save(A,d);const session=await start(A,d,'solo',{count:2});
  const read=async(user)=>{await who(user);return (await db.query('select study_session_progress($1) r',[session.id])).rows[0].r;};
  const firstRound=await ok(A,'round',{id:session.id});
  const firstCard=d.cards.find(card=>card.question===firstRound.question);
  assert.ok(firstCard,'The first question must belong to the original deck');
  await half(A,session.id,1,true);assert.equal((await read(A)).review,undefined);
  await half(A,session.id,1);const before=await read(A);
  assert.deepEqual(before.review.map(a=>a.correct),[false,true]);
  assert.equal(before.review[0].selected,'Answer 1');assert.equal(before.review[0].solution,'Answer 0');
  assert.equal(before.review[0].selected_id,firstCard.answers[1].id);
  assert.equal(before.review[0].correct_answer_id,firstCard.answers[0].id);
  assert.deepEqual(before.review[0].options,firstCard.answers);
  assert.equal(before.review[0].question,firstRound.question);
  firstCard.question='Rewritten';await save(A,d,1);
  assert.deepEqual((await read(A)).review,before.review);
  await assert.rejects(()=>read(B),/unavailable/);
 });
 await test('completed together progress groups each player score by the two source decks',async()=>{
  await db.exec('begin');
  const left=draft(10),right=draft(10);await save(A,left);await save(B,right);
  const a=await start(A,left,'random');await half(A,a.id,10,false);
  const available=async()=> (await ok(B,'list')).open.find(offer=>offer.id===a.id);
  assert.equal((await available()).count,20);
  const tooSmall=draft(9);await save(B,tooSmall);
  await bad(B,'start',{request_id:randomUUID(),deck_id:tooSmall.id,mode:'random',count:20,consent:true,join_id:a.id});
  assert.equal((await available()).count,20,'The rejected join must leave the offer available');
  const b=await start(B,right,'random',{join_id:a.id});await half(B,b.id,6,true);await half(B,b.id,4,false);
  assert.equal(await available(),undefined,'A claimed session leaves the open list');
  await half(A,a.id,10,true);await half(B,b.id,10,false);
  await who(A);const summary=(await db.query('select study_session_progress($1) r',[a.id])).rows[0].r;
  assert.equal(summary.deck_name,'Study finance');assert.equal(summary.partner_username,'Bob');
  assert.deepEqual([summary.own_deck_score,summary.partner_deck_score],[10,0]);
  // Both rows use the viewer’s deck first. Bob got ten right on Alice’s deck and four on his.
  assert.deepEqual([summary.partner_own_deck_score,summary.partner_partner_deck_score],[10,4]);
  // Recover safely if an older client persisted all answers but missed the
  // final session-state update. The completed pair may immediately start again.
  await admin("update study_sessions set finished_at=null,state='paired' where id in ($1,$2)",[a.id,b.id]);
  const replacement=await start(A,left,'random');assert.ok(replacement.id);
  await db.exec('rollback');
 });
 await test('calculator permission persists, defaults off and stays fixed in active snapshots',async()=>{
  const d=draft(1);d.cards[0].allow_calculator=true;await save(A,d);
  assert.equal((await ok(A,'deck',{id:d.id})).cards[0].allow_calculator,true);
  const first=await start(A,d,'solo',{count:1});
  assert.equal((await ok(A,'round',{id:first.id})).allow_calculator,true);
  d.cards[0].allow_calculator=false;await save(A,d,1);
  assert.equal((await ok(A,'round',{id:first.id})).allow_calculator,true);
  const second=await start(A,d,'solo',{count:1});assert.equal((await ok(A,'round',{id:second.id})).allow_calculator,false);
  const old=draft(1);await save(A,old);const third=await start(A,old,'solo',{count:1});
  assert.equal((await ok(A,'round',{id:third.id})).allow_calculator,false);
  d.cards[0].allow_calculator='true';await bad(A,'review_deck',{draft:d,revision:2});
 });
 const da=draft(),dbb=draft(),dc=draft();await save(A,da);await save(B,dbb);await save(C,dc);
 await test('Study friends must share the course; old override cannot bypass eligibility',async()=>{
  assert.equal((await ok(A,'friend_options',{deck_id:da.id})).friends.length,1);
  await admin("update profile_private set courses=array['Other'] where user_id=$1",[B]);
  assert.equal((await ok(A,'friend_options',{deck_id:da.id})).friends.length,0);
  await bad(A,'start',{request_id:randomUUID(),deck_id:da.id,mode:'friend',friend_id:B,count:20,consent:true,confirm_missing_course:true});
  await admin("update profile_private set courses=array['Finance'] where user_id=$1",[B]);
 });
 await test('only friends with a compatible authored deck for this session size may be invited',async()=>{
  const options=async count=>(await ok(A,'friend_options',{deck_id:da.id,count})).friends;
  const before=(await admin('select snapshot from study_decks where id=$1',[dbb.id])).rows[0].snapshot;
  for(const change of [{cards:before.cards.slice(0,19)},{course:'History'},{language:'French'}]){
   await admin('update study_decks set snapshot=$1 where id=$2',[{...before,...change},dbb.id]);
   assert.equal((await options(40)).length,0);
   await bad(A,'start',{request_id:randomUUID(),deck_id:da.id,mode:'friend',friend_id:B,count:40,consent:true});
  }
  await admin('update study_decks set snapshot=$1 where id=$2',[before,dbb.id]);
  assert.equal((await options(100)).length,1);
 });
 await test('an edited deck cannot receive an incompatible invitation after the sender finishes',async()=>{
  await db.exec('begin');
  try{
   const session=await start(A,da,'friend',{friend_id:B});
   await admin("update study_decks set snapshot=jsonb_set(snapshot,'{language}',to_jsonb('French'::text)) where id=$1",[dbb.id]);
   await half(A,session.id);
   assert.equal((await ok(B,'list')).invites.length,0);
   assert.equal((await dashboard(A,session.id)).state,'cancelled');
   assert.equal((await dashboard(A,session.id)).answered,10);
  }finally{await db.exec('rollback');}
 });
 await test('private decks and mandatory reviewed revision',async()=>{await bad(B,'deck',{id:da.id});await bad(A,'save_deck',{draft:da,revision:1,review_id:randomUUID()});const changed=structuredClone(da);changed.cards[0].question='Edited';await bad(A,'save_deck',{draft:changed,revision:1});await save(A,changed,1);await assert.rejects(()=>save(A,da,1));await save(A,da,2);});
 await test('authors see their published Study decks and compatible students can copy them privately',async()=>{
  await publicationOk(A,'publish',{id:da.id});
  const authorList=await publicationOk(A,'list');
  assert.equal(authorList.decks.find(deck=>deck.id===da.id).owned,true);
  assert.ok(authorList.decks.find(deck=>deck.id===da.id).published_at);
  assert.equal((await publicationOk(B,'list')).decks.some(deck=>deck.id===da.id),true);
  assert.equal((await publicationOk(C,'list')).decks.some(deck=>deck.id===da.id),false);
  const visible=await publicationOk(B,'deck',{id:da.id});
  assert.equal(visible.name,da.name);
  const copied=await publicationOk(B,'copy',{id:da.id});
  const ownedIds=async()=>(await ok(B,'list')).decks.map(deck=>deck.id).sort();
  const beforeUnpublish=await ownedIds();
  assert.ok(beforeUnpublish.includes(copied.id));

  await publicationOk(A,'unpublish',{id:da.id});
  assert.equal((await publicationOk(B,'list')).decks.some(deck=>deck.id===da.id),false);
  await assert.rejects(()=>publication(B,'copy',{id:da.id}),/Published Study deck unavailable/);
  assert.deepEqual(await ownedIds(),beforeUnpublish);
 });
 let solo;
 await test('solo filters, locked immediate feedback, idempotence and private notes',async()=>{
  solo=await start(A,da,'solo',{chapters:['Lecture 1'],levels:['new'],count:1});let q=await ok(A,'round',{id:solo.id});assert.ok(!JSON.stringify(q).includes('correct_answer_id'));await bad(B,'round',{id:solo.id});
  const c=(await admin('select cards from study_sessions where id=$1',[solo.id])).rows[0].cards[0];await ok(A,'answer',{id:solo.id,index:0,answer_id:c.correct_answer_id});await ok(A,'answer',{id:solo.id,index:0,answer_id:c.answers[1].id});
  await who(A);const progress=(await db.query('select study_session_progress($1) r',[solo.id])).rows[0].r;assert.deepEqual(progress.answers,[{index:0,correct:true}]);await who(B);await assert.rejects(()=>db.query('select study_session_progress($1)',[solo.id]));
  assert.equal((await ok(A,'round',{id:solo.id})).state,'feedback');await ok(A,'annotate',{id:solo.id,index:0,note:'Private thought',feedback:'Explain please'});assert.equal((await admin('select count(*)::int n from study_answers where session_id=$1',[solo.id])).rows[0].n,1);await ok(A,'next',{id:solo.id,index:0});assert.equal((await ok(A,'round',{id:solo.id})).state,'completed');
 });
 await test('unmatched first half expires after 48 hours of inactivity and keeps learning progress',async()=>{
  const session=await start(A,da,'friend',{friend_id:B});
  await admin("update study_sessions set expires_at=now()+interval '1 minute' where id=$1",[session.id]);
  await half(A,session.id,1);
  const remaining=(await admin("select extract(epoch from expires_at-now())/3600 hours from study_sessions where id=$1",[session.id])).rows[0].hours;
  assert.ok(remaining>47.99 && remaining<=48);
  const before=(await admin("select count(*)::int n from study_progress where user_id=$1",[A])).rows[0].n;
  await admin("update study_sessions set expires_at=now() where id=$1",[session.id]);
  assert.equal(await dashboard(A,session.id),undefined);assert.ok(!(await ok(A,'list')).sessions.some(s=>s.id===session.id));
  assert.equal((await admin("select count(*)::int n from study_progress where user_id=$1",[A])).rows[0].n,before);
 });
 await test('size requires enough distinct questions and consent',async()=>{const small=draft(10);await save(A,small);await bad(A,'start',{request_id:randomUUID(),deck_id:small.id,mode:'random',count:100,consent:true});await bad(A,'start',{request_id:randomUUID(),deck_id:da.id,mode:'random',count:20,consent:false});});
 let sa,sb;
 await test('mutual queue starts only after own half and enforces university',async()=>{
  sa=await start(A,da,'random');assert.equal((await ok(B,'list')).open.length,0);assert.equal((await dashboard(A,sa.id)).state,'own');await half(A,sa.id);assert.equal((await dashboard(A,sa.id)).state,'waiting');assert.equal(await dashboard(C,sa.id),undefined);assert.equal((await ok(B,'list')).open.length,1);assert.equal((await ok(C,'list')).open.length,0);await bad(A,'start',{request_id:randomUUID(),deck_id:da.id,mode:'random',count:20,consent:true});
  sb=await start(B,dbb,'random');assert.equal((await ok(A,'round',{id:sa.id})).state,'waiting');await half(B,sb.id);assert.equal((await ok(A,'round',{id:sa.id})).state,'question');
 });
 await test('same questions, hidden full decks, completion grants only finisher immutable copy',async()=>{
  const rows=(await admin('select cards from study_sessions where id in ($1,$2)',[sa.id,sb.id])).rows;assert.deepEqual(rows[0].cards.map(x=>x.id).sort(),rows[1].cards.map(x=>x.id).sort());assert.equal((await ok(A,'list')).shared.length,0);
  const timing=(await admin("select bool_and(deadline between now()+interval '47 hours 59 minutes' and now()+interval '48 hours' and expires_at is null) valid from study_sessions where id in ($1,$2)",[sa.id,sb.id])).rows[0];
  assert.ok(timing.valid);
  assert.equal((await dashboard(A,sa.id)).state,'paired');await half(A,sa.id);const waiting=await dashboard(A,sa.id);assert.equal(waiting.state,'waiting_for_finish');assert.equal(waiting.opponent_score,null);assert.equal((await dashboard(B,sb.id)).state,'paired');assert.equal((await ok(A,'list')).shared.length,1);assert.equal((await ok(B,'list')).shared.length,0);assert.equal((await ok(A,'round',{id:sa.id})).result,'Waiting for your study partner');
  const changed=structuredClone(dbb);changed.cards[0].question='New content';await save(B,changed,1);const shared=(await ok(A,'list')).shared[0];const received=await ok(A,'deck',{id:shared.id,shared:true});assert.equal(received.cards[0].question,dbb.cards[0].question);
  await half(B,sb.id,10,true);const settled=await dashboard(A,sa.id);assert.equal(settled.state,'completed');assert.equal(settled.result,'Win');assert.equal(settled.score,20);assert.equal(settled.opponent_score,10);assert.equal((await ok(A,'round',{id:sa.id})).result,'Win');assert.equal((await ok(B,'round',{id:sb.id})).result,'Loss');assert.equal((await admin('select xp from profiles where id=$1',[A])).rows[0].xp,123);
 });
 await test('open sessions reserve once and expiry awards no unearned copy',async()=>{
  const a=await start(A,da,'random');await half(A,a.id);const b=await start(B,dbb,'random',{join_id:a.id});assert.equal((await ok(A,'round',{id:a.id})).state,'question');await bad(C,'start',{request_id:randomUUID(),deck_id:dc.id,mode:'random',count:20,consent:true,join_id:a.id});await half(A,a.id);await admin("update study_sessions set deadline=now()-interval '1 second' where id in ($1,$2)",[a.id,b.id]);assert.equal((await ok(A,'round',{id:a.id})).result,'Win');
  const loss=await ok(B,'round',{id:b.id});assert.equal(loss.result,'Loss');assert.equal(loss.shared,false);assert.equal((await dashboard(B,b.id)).result,'Loss');
  assert.equal((await ok(B,'list')).sessions.find(s=>s.id===b.id).state,'completed');await bad(B,'answer',{id:b.id,index:0,answer_id:dbb.cards[0].correct_answer_id});
 });
 await test('friend recipient accepts or declines, no unsolicited random invite',async()=>{
  const a=await start(A,da,'friend',{friend_id:B});await half(A,a.id);const senderDashboard=await dashboard(A,a.id);assert.equal(senderDashboard.friend_username,'Bob');assert.equal(senderDashboard.course,'Finance');assert.equal(senderDashboard.language,'English');assert.equal(senderDashboard.count,20);assert.equal((await ok(B,'list')).invites.length,1);await admin("update profile_private set courses=array['Other course'] where user_id=$1",[B]);assert.equal((await ok(B,'list')).invites.length,1);await admin("update profile_private set courses=array['Finance'] where user_id=$1",[B]);await bad(C,'decline',{id:a.id});await ok(B,'decline',{id:a.id});assert.equal((await ok(A,'round',{id:a.id})).state,'cancelled');
  const a2=await start(A,da,'friend',{friend_id:B});await half(A,a2.id);const b=await start(B,dbb,'friend',{join_id:a2.id});assert.ok(b.id);
 });
 await test('different friends may have concurrent sessions, but a friend pair has one open session',async()=>{
  await admin("update study_sessions set state='cancelled' where user_id=$1 and finished_at is null",[A]);
  await admin("insert into friend_edges values(least($1::uuid,$2::uuid),greatest($1::uuid,$2::uuid),'accepted')",[A,C]);
  const withBob=await start(A,da,'friend',{friend_id:B});await half(A,withBob.id);
  const withChris=await start(A,da,'friend',{friend_id:C});await half(A,withChris.id);
  await bad(A,'start',{request_id:randomUUID(),deck_id:da.id,mode:'friend',friend_id:B,count:20,consent:true});
 });
 await test('expired search cannot be joined and cancellation preserves progress',async()=>{await admin("update study_sessions set deadline=now()-interval '1 second' where deadline is not null");const a=await start(A,da,'random');await half(A,a.id);await admin("update study_sessions set expires_at=now()-interval '1 second' where id=$1",[a.id]);await bad(B,'start',{request_id:randomUUID(),deck_id:dbb.id,mode:'random',count:20,consent:true,join_id:a.id});assert.ok(!(await ok(A,'list')).sessions.some(s=>s.id===a.id));await bad(A,'round',{id:a.id});});
 await test('both unfinished friends receive completed losses',async()=>{
  await admin("update study_sessions set state='cancelled' where finished_at is null");
  const a=await start(A,da,'friend',{friend_id:B});await half(A,a.id);
  const b=await start(B,dbb,'friend',{join_id:a.id});
  await admin("update study_sessions set deadline=now() where id in ($1,$2)",[a.id,b.id]);
  for(const [user,id] of [[A,a.id],[B,b.id]]){
   const row=(await ok(user,'list')).sessions.find(s=>s.id===id);
   assert.equal(row.state,'completed');assert.equal(row.result,'Loss');
   const round=await ok(user,'round',{id});
   assert.equal(round.result,'Loss');assert.equal(round.shared,false);
   await bad(user,'next',{id,index:0});
  }
 });
 await test('together prefers learning levels, fills shortages, and matches different preferences',async()=>{
  const freshA=draft(30),freshB=draft(30);await save(A,freshA);await save(B,freshB);
  for(const card of freshA.cards.slice(15))await admin('insert into study_progress values($1,$2,$3,study_version($4::jsonb),1)',[A,freshA.id,card.id,JSON.stringify(card)]);
  const a=await start(A,freshA,'random',{count:40,levels:['new']});
  const chosen=(await admin('select cards from study_sessions where id=$1',[a.id])).rows[0].cards;
  assert.equal(chosen.length,20);assert.equal(new Set(chosen.map(c=>c.id)).size,20);
  assert.equal(chosen.filter(c=>freshA.cards.slice(0,15).some(q=>q.id===c.id)).length,15);
  await half(A,a.id,20);
  const b=await start(B,freshB,'random',{count:40,levels:['3']});await half(B,b.id,20);
  assert.equal((await ok(A,'round',{id:a.id})).state,'question');
  const both=(await admin('select cards from study_sessions where id in ($1,$2)',[a.id,b.id])).rows;
  assert.deepEqual(both[0].cards.map(c=>c.id).sort(),both[1].cards.map(c=>c.id).sort());
  await admin("update study_sessions set deadline=now()-interval '1 second' where id in ($1,$2)",[a.id,b.id]);
 });
 await test('database progress levels, chapter-only edits and content reset',async()=>{
  const one=draft(1);await save(A,one);
  for(const [wrong,expected] of [[true,0],[false,1],[false,2],[false,3],[false,3],[true,2],[true,1],[true,0]]){
   const r=await start(A,one,'solo',{count:1});await half(A,r.id,1,wrong);assert.equal((await ok(A,'deck',{id:one.id})).cards[0].level,expected);
  }
  one.cards[0].chapter='Renamed lecture';await save(A,one,1);assert.equal((await ok(A,'deck',{id:one.id})).cards[0].level,0);
  one.cards[0].question='Changed meaning';await save(A,one,2);assert.equal((await ok(A,'deck',{id:one.id})).cards[0].level,null);
 });
 await test('different volumes do not auto-match; join rejection rolls back; 100 uses 50 unique from each',async()=>{
  const a=await start(A,da,'random',{count:100});await half(A,a.id,50);
  const b=await start(B,dbb,'random',{count:20});await half(B,b.id,10);assert.equal((await ok(A,'round',{id:a.id})).state,'waiting');await ok(B,'cancel',{id:b.id});
  const before=(await admin('select count(*)::int n from study_sessions')).rows[0].n;
  await bad(B,'start',{request_id:randomUUID(),deck_id:dbb.id,mode:'random',count:20,consent:true,join_id:a.id});assert.equal((await admin('select count(*)::int n from study_sessions')).rows[0].n,before);
  const joined=await start(B,dbb,'random',{count:100,join_id:a.id});const cards=(await admin('select cards from study_sessions where id=$1',[joined.id])).rows[0].cards;
  assert.equal(cards.length,100);assert.equal(new Set(cards.map(c=>c.id)).size,100);
  await admin("update study_sessions set deadline=now()-interval '1 second' where id in ($1,$2)",[a.id,joined.id]);
 });
 await test('deck snapshots, notes and author feedback have separate visibility',async()=>{
  const shared=(await ok(A,'list')).shared[0];const session=await start(A,{id:shared.id},'solo',{count:1,shared:true});const card=(await admin('select cards from study_sessions where id=$1',[session.id])).rows[0].cards[0];
  await ok(A,'answer',{id:session.id,index:0,answer_id:card.correct_answer_id});await ok(A,'annotate',{id:session.id,index:0,note:'Only Alice can see this',feedback:'Please clarify this example'});
  const bob=await ok(B,'list');assert.ok(bob.feedback.some(f=>f.body==='Please clarify this example'));assert.ok(!JSON.stringify(bob).includes('Only Alice'));assert.ok((await ok(A,'deck',{id:shared.id,shared:true})).cards.some(c=>c.note==='Only Alice can see this'));
  await bad(B,'deck',{id:shared.id,shared:true});await bad(C,'annotate',{id:session.id,index:0,note:'tamper'});
 });
 await test('existing duel answers update learning progress exactly once',async()=>{
  const draftA=draft(15),draftB=draft(15);let published=[];
  for(const [u,d] of [[A,draftA],[B,draftB]]){await who(u);const rev=(await db.query('select review_deck($1::jsonb) r',[JSON.stringify(d)])).rows[0].r;const r=(await db.query('select publish_deck($1,$2::jsonb) r',[rev.id,JSON.stringify(d)])).rows[0].r;published.push(r.id);}
  const duel=(await admin('select play_create($1,$2,$3,$4) id',[A,B,...published])).rows[0].id;
  await who(A);await db.query("select play_action('round',$1::jsonb)",[JSON.stringify({duel_id:duel})]);
  for(let i=0;i<2;i++)await db.query("select play_action('answer',$1::jsonb)",[JSON.stringify({duel_id:duel,index:0,answer_id:draftA.cards[0].correct_answer_id})]);
  assert.equal((await ok(A,'deck',{id:published[0]})).cards[0].level,1);
 });
 await test('stopping frees the slot, preserves progress and only finishers receive a deck',async()=>{
  const a=await start(A,da,'random');await half(A,a.id);
  const b=await start(B,dbb,'random',{join_id:a.id});
  const copiesA=(await ok(A,'list')).shared.length, copiesB=(await ok(B,'list')).shared.length;
  await bad(C,'stop',{id:a.id});
  await bad(A,'start',{request_id:randomUUID(),deck_id:da.id,mode:'random',count:20,consent:true});
  await ok(A,'stop',{id:a.id});await ok(A,'stop',{id:a.id});
  assert.equal((await dashboard(A,a.id)).result,'Loss');
  assert.equal((await dashboard(A,a.id)).opponent_score,null);
  assert.equal((await ok(A,'round',{id:a.id})).opponent_score,null);
  await bad(A,'next',{id:a.id,index:10});
  const next=await start(A,da,'random');await half(A,next.id,1);
  await ok(A,'stop',{id:next.id});assert.equal((await dashboard(A,next.id)).answered,1);
  assert.equal((await dashboard(A,next.id)).state,'cancelled');
  await half(B,b.id,20);
  assert.equal((await dashboard(B,b.id)).result,'Win');
  assert.equal((await ok(B,'round',{id:b.id})).result,'Win');
  assert.equal((await ok(A,'list')).shared.length,copiesA);
  assert.equal((await ok(B,'list')).shared.length,copiesB+1);
 });
 await test('a finisher can start again while their partner decides whether to stop',async()=>{
  const a=await start(A,da,'random');await half(A,a.id);
  const b=await start(B,dbb,'random',{join_id:a.id});await half(A,a.id);
  assert.equal((await dashboard(A,a.id)).state,'waiting_for_finish');
  const next=await start(A,da,'random');
  await bad(A,'stop',{id:a.id});await ok(B,'stop',{id:b.id});
  assert.equal((await dashboard(A,a.id)).result,'Win');
  assert.equal((await ok(A,'round',{id:a.id})).result,'Win');
  await half(A,next.id);const b2=await start(B,dbb,'random',{join_id:next.id});
  await ok(B,'stop',{id:b2.id});await ok(A,'stop',{id:next.id});
  for(const [u,id] of [[A,next.id],[B,b2.id]]){
   assert.equal((await dashboard(u,id)).result,'Loss');
   assert.equal((await ok(u,'round',{id})).shared,false);
  }
 });
 await test('raw tables and internal helpers are inaccessible',async()=>{await who(B);for(const t of ['study_sessions','study_answers','study_progress','study_notes','study_feedback','study_shared'])await assert.rejects(()=>db.query('select * from '+t));await assert.rejects(()=>db.query('select study_pair($1,$2)',[sa.id,sb.id]));await who('','anon');await assert.rejects(()=>db.query("select study_action('list')"));});
 const n=(await admin('select count(*)::int n from study_answers')).rows[0].n;await db.close();const child=spawnSync(process.execPath,[new URL(import.meta.url).pathname,'reload',path.join(dir,'db'),String(n)],{encoding:'utf8',env:process.env});assert.equal(child.status,0,child.stderr);console.log(child.stdout.trim());console.log(`${passed+1} isolated Study checks passed`);
}catch(e){console.error(e.stack,e.where||'');process.exitCode=1;}finally{await db.close().catch(()=>{});await fs.rm(dir,{recursive:true,force:true});}
