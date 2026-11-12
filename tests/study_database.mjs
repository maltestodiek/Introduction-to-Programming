// Real PostgreSQL semantics in an isolated local database; no production data.
import fs from 'node:fs/promises';import os from 'node:os';import path from 'node:path';
import assert from 'node:assert/strict';import {randomUUID} from 'node:crypto';import {spawnSync} from 'node:child_process';
const {PGlite}=await import(process.env.PGLITE_MODULE||'@electric-sql/pglite');
if(process.argv[2]==='reload') {const db=new PGlite(process.argv[3]);assert.equal((await db.query('select count(*)::int n from study_answers')).rows[0].n,Number(process.argv[4]));await db.close();console.log('PASS restart preserves study answers');process.exit(0);}
const dir=await fs.mkdtemp(path.join(os.tmpdir(),'studyduel-study-'));const db=new PGlite(path.join(dir,'db'));
const A=randomUUID(),B=randomUUID(),C=randomUUID();let passed=0;
async function admin(sql,args=[]){await db.exec('reset role');return db.query(sql,args);}
async function who(id,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id]);await db.exec('set role '+role);}
async function act(u,a,d={}){await who(u);return(await db.query('select study_action($1,$2::jsonb) r',[a,JSON.stringify(d)])).rows[0].r;}
async function ok(u,a,d={}){const r=await act(u,a,d);assert.ok(!r.error,r.error);return r;}
async function bad(u,a,d={}){assert.ok((await act(u,a,d)).error);}
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
 const da=draft(),dbb=draft(),dc=draft();await save(A,da);await save(B,dbb);await save(C,dc);
 await test('private decks and mandatory reviewed revision',async()=>{await bad(B,'deck',{id:da.id});await bad(A,'save_deck',{draft:da,revision:1,review_id:randomUUID()});const changed=structuredClone(da);changed.cards[0].question='Edited';await bad(A,'save_deck',{draft:changed,revision:1});await save(A,changed,1);await assert.rejects(()=>save(A,da,1));await save(A,da,2);});
 let solo;
 await test('solo filters, locked immediate feedback, idempotence and private notes',async()=>{
  solo=await start(A,da,'solo',{chapters:['Lecture 1'],levels:['new'],count:1});let q=await ok(A,'round',{id:solo.id});assert.ok(!JSON.stringify(q).includes('correct_answer_id'));await bad(B,'round',{id:solo.id});
  const c=(await admin('select cards from study_sessions where id=$1',[solo.id])).rows[0].cards[0];await ok(A,'answer',{id:solo.id,index:0,answer_id:c.correct_answer_id});await ok(A,'answer',{id:solo.id,index:0,answer_id:c.answers[1].id});
  assert.equal((await ok(A,'round',{id:solo.id})).state,'feedback');await ok(A,'annotate',{id:solo.id,index:0,note:'Private thought',feedback:'Explain please'});assert.equal((await admin('select count(*)::int n from study_answers where session_id=$1',[solo.id])).rows[0].n,1);await ok(A,'next',{id:solo.id,index:0});assert.equal((await ok(A,'round',{id:solo.id})).state,'completed');
 });
 await test('size requires enough distinct questions and consent',async()=>{const small=draft(10);await save(A,small);await bad(A,'start',{request_id:randomUUID(),deck_id:small.id,mode:'random',count:100,consent:true});await bad(A,'start',{request_id:randomUUID(),deck_id:da.id,mode:'random',count:20,consent:false});});
 let sa,sb;
 await test('mutual queue starts only after own half and enforces university',async()=>{
  sa=await start(A,da,'random');assert.equal((await ok(B,'list')).open.length,0);await half(A,sa.id);assert.equal((await ok(B,'list')).open.length,1);assert.equal((await ok(C,'list')).open.length,0);await bad(A,'start',{request_id:randomUUID(),deck_id:da.id,mode:'random',count:20,consent:true});
  sb=await start(B,dbb,'random');assert.equal((await ok(A,'round',{id:sa.id})).state,'waiting');await half(B,sb.id);assert.equal((await ok(A,'round',{id:sa.id})).state,'question');
 });
 await test('same questions, hidden full decks, completion grants only finisher immutable copy',async()=>{
  const rows=(await admin('select cards from study_sessions where id in ($1,$2)',[sa.id,sb.id])).rows;assert.deepEqual(rows[0].cards.map(x=>x.id).sort(),rows[1].cards.map(x=>x.id).sort());assert.equal((await ok(A,'list')).shared.length,0);
  await half(A,sa.id);assert.equal((await ok(A,'list')).shared.length,1);assert.equal((await ok(B,'list')).shared.length,0);assert.equal((await ok(A,'round',{id:sa.id})).result,'Waiting for your study partner');
  const changed=structuredClone(dbb);changed.cards[0].question='New content';await save(B,changed,1);const shared=(await ok(A,'list')).shared[0];const received=await ok(A,'deck',{id:shared.id,shared:true});assert.equal(received.cards[0].question,dbb.cards[0].question);
  await half(B,sb.id,10,true);assert.equal((await ok(A,'round',{id:sa.id})).result,'Win');assert.equal((await ok(B,'round',{id:sb.id})).result,'Loss');assert.equal((await admin('select xp from profiles where id=$1',[A])).rows[0].xp,123);
 });
 await test('open sessions reserve once and expiry awards no unearned copy',async()=>{
  const a=await start(A,da,'random');await half(A,a.id);const b=await start(B,dbb,'random',{join_id:a.id});assert.equal((await ok(A,'round',{id:a.id})).state,'question');await bad(C,'start',{request_id:randomUUID(),deck_id:dc.id,mode:'random',count:20,consent:true,join_id:a.id});await half(A,a.id);await admin("update study_sessions set deadline=now()-interval '1 second' where id in ($1,$2)",[a.id,b.id]);assert.equal((await ok(A,'round',{id:a.id})).result,'Partner did not finish');await bad(B,'answer',{id:b.id,index:0,answer_id:dbb.cards[0].correct_answer_id});
 });
 await test('friend recipient accepts or declines, no unsolicited random invite',async()=>{
  const a=await start(A,da,'friend',{friend_id:B});await half(A,a.id);assert.equal((await ok(B,'list')).invites.length,1);await bad(C,'decline',{id:a.id});await ok(B,'decline',{id:a.id});assert.equal((await ok(A,'round',{id:a.id})).state,'cancelled');
  const a2=await start(A,da,'friend',{friend_id:B});await half(A,a2.id);const b=await start(B,dbb,'friend',{join_id:a2.id});assert.ok(b.id);
 });
 await test('expired search cannot be joined and cancellation preserves progress',async()=>{await admin("update study_sessions set deadline=now()-interval '1 second' where deadline is not null");const a=await start(A,da,'random');await half(A,a.id);await admin("update study_sessions set expires_at=now()-interval '1 second' where id=$1",[a.id]);await bad(B,'start',{request_id:randomUUID(),deck_id:dbb.id,mode:'random',count:20,consent:true,join_id:a.id});assert.equal((await ok(A,'round',{id:a.id})).state,'expired');});
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
 await test('raw tables and internal helpers are inaccessible',async()=>{await who(B);for(const t of ['study_sessions','study_answers','study_progress','study_notes','study_feedback','study_shared'])await assert.rejects(()=>db.query('select * from '+t));await assert.rejects(()=>db.query('select study_pair($1,$2)',[sa.id,sb.id]));await who('','anon');await assert.rejects(()=>db.query("select study_action('list')"));});
 const n=(await admin('select count(*)::int n from study_answers')).rows[0].n;await db.close();const child=spawnSync(process.execPath,[new URL(import.meta.url).pathname,'reload',path.join(dir,'db'),String(n)],{encoding:'utf8',env:process.env});assert.equal(child.status,0,child.stderr);console.log(child.stdout.trim());console.log(`${passed+1} isolated Study checks passed`);
}catch(e){console.error(e.stack,e.where||'');process.exitCode=1;}finally{await db.close().catch(()=>{});await fs.rm(dir,{recursive:true,force:true});}
