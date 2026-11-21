// Isolated Battle Mode migration checks. Never contacts Supabase or real users.
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';

const {PGlite}=await import(process.env.PGLITE_MODULE||'@electric-sql/pglite');
const directory=await fs.mkdtemp(path.join(os.tmpdir(),'uniarena-battle-'));
const db=new PGlite(path.join(directory,'db'));
const A=randomUUID(),B=randomUUID(),C=randomUUID();

async function asUser(id){
  await db.exec('reset role');
  await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id]);
  await db.exec('set role authenticated');
}
// Inspect or change the isolated fixture as its owner for this statement only.
async function fixtureQuery(sql, params) {
  return db.transaction(async tx => {
    await tx.exec('set local role none');
    return tx.query(sql, params);
  });
}
async function action(id,name,data={}){
  await asUser(id);
  return (await db.query('select battle_action($1,$2::jsonb) result',[name,JSON.stringify(data)])).rows[0].result;
}
async function ok(id,name,data={}){const result=await action(id,name,data);assert.ok(!result.error,result.error);return result;}
async function fail(id,name,data={}){await assert.rejects(()=>action(id,name,data));}
async function cancelSearch(id){
  await asUser(id);
  return (await db.query('select cancel_battle_search() result')).rows[0].result;
}
function sourceDeck(course='Finance',language='English',count=20){
  return {name:'Corporate Finance essentials',course,language,cards:Array.from({length:count},(_,index)=>{
    const answers=Array.from({length:4},(_,answer)=>({id:randomUUID(),text:`Answer ${answer}`}));
    return {id:randomUUID(),question:`Question ${index}`,answers,correct_answer_id:answers[0].id,allow_calculator:false};
  })};
}

try{
  await db.exec(`
    create role anon; create role authenticated; create schema auth;
    create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
    grant usage on schema auth to anon,authenticated;
    create table public.profiles(id uuid primary key,username text,university text,languages text[],image_path text,xp integer not null default 0,win_streak integer not null default 0);
    create table public.profile_private(user_id uuid primary key,courses text[]);
    create table public.study_decks(id uuid primary key,creator_id uuid not null references public.profiles(id),snapshot jsonb not null,revision integer not null default 1,updated_at timestamptz not null default now());
    create table public.ai_question_drafts(id uuid primary key default gen_random_uuid(),owner_id uuid,status text,question text);
    grant select on public.profiles,public.profile_private to authenticated;
  `);
  for(const [id,name,university] of [[A,'Alice','Nova'],[B,'Bob','Nova'],[C,'Chris','Other']]){
    await db.query("insert into public.profiles(id,username,university,languages) values($1,$2,$3,array['English'])",[id,name,university]);
    await db.query("insert into public.profile_private values($1,array['Finance'])",[id]);
  }
  await db.exec(await fs.readFile(new URL('../supabase/battle-mode-schema.sql',import.meta.url),'utf8'));
  await db.exec(await fs.readFile(new URL('../supabase/battle-round-progress.sql',import.meta.url),'utf8'));
  await db.exec(await fs.readFile(new URL('../supabase/battle-xp-only.sql',import.meta.url),'utf8'));
  await db.exec(await fs.readFile(new URL('../supabase/battle-question-reports.sql',import.meta.url),'utf8'));
  await db.exec(await fs.readFile(new URL('../supabase/battle-deck-availability.sql',import.meta.url),'utf8'));
  await db.exec(await fs.readFile(new URL('../supabase/battle-search-controls.sql',import.meta.url),'utf8'));
  await db.exec(await fs.readFile(new URL('../supabase/battle-top-decks-immediate.sql',import.meta.url),'utf8'));
  await db.exec(await fs.readFile(new URL('../supabase/battle-top-decks-lifetime-ranking.sql',import.meta.url),'utf8'));
  const source=sourceDeck();const sourceId=randomUUID();
  await db.query('insert into public.study_decks(id,creator_id,snapshot) values($1,$2,$3::jsonb)',[sourceId,A,JSON.stringify(source)]);

  await asUser(A);
  const unavailable=(await db.query("select battle_deck_availability('Finance','English') result")).rows[0].result;
  assert.equal(unavailable.available,false);
  await fail(A,'join',{course:'Finance',language:'English',source_kind:'random'});
  const listed=await ok(A,'sources');assert.equal(listed.sources[0].battle_capable,true);
  await fail(B,'source',{id:sourceId});
  await fail(A,'create_deck',{source_deck_id:sourceId,card_ids:source.cards.slice(0,15).map(card=>card.id),consent:false});
  await fail(A,'create_deck',{source_deck_id:sourceId,card_ids:source.cards.slice(0,14).map(card=>card.id),consent:true});
  const created=await ok(A,'create_deck',{source_deck_id:sourceId,card_ids:source.cards.slice(0,15).map(card=>card.id),consent:true,name:'Battle snapshot'});
  const stored=(await fixtureQuery('select cards,public_consent_at from public.battle_decks where id=$1',[created.id])).rows[0];
  assert.equal(stored.cards.length,15);assert.ok(stored.public_consent_at);
  const timeoutSessionId=randomUUID();
  await db.exec('reset role');
  await db.query('insert into public.battle_sessions(id,p1,p2,battle_deck_id,source_kind,cards,course,language) values($1,$2,$3,$4,$5,$6::jsonb,$7,$8)',[timeoutSessionId,A,B,created.id,'random',JSON.stringify(stored.cards),'Finance','English']);
  await db.query("insert into public.battle_rounds(session_id,user_id) values($1,$2),($1,$3)",[timeoutSessionId,A,B]);
  const started=await ok(A,'round',{id:timeoutSessionId});assert.equal(started.state,'question');
  await db.exec('reset role');await db.query("update public.battle_rounds set question_started=now()-interval '31 seconds' where session_id=$1 and user_id=$2",[timeoutSessionId,A]);
  const timedOut=await ok(A,'round',{id:timeoutSessionId});
  assert.deepEqual([timedOut.state,timedOut.feedback.timed_out,timedOut.feedback.answer_id],['feedback',true,null]);
  const nextQuestion=await ok(A,'round',{id:timeoutSessionId});assert.deepEqual([nextQuestion.state,nextQuestion.index],['question',1]);
  await asUser(B);
  const available=(await db.query("select battle_deck_availability('Finance','English') result")).rows[0].result;
  assert.equal(available.available,true);
  const queued=await ok(B,'join',{course:'Finance',language:'English',source_kind:'random'});
  assert.equal(queued.message,'Searching for one hour.');
  assert.equal((await cancelSearch(A)).cancelled,false);
  assert.equal((await cancelSearch(B)).cancelled,true);
  assert.equal((await ok(B,'list')).search,null);
  await ok(B,'join',{course:'Finance',language:'English',source_kind:'random'});
  await db.exec('reset role');await db.query("update public.battle_searches set expires_at=now()-interval '1 second' where user_id=$1",[B]);
  assert.equal((await db.query('select expire_battle_searches() result')).rows[0].result.expired,1);
  assert.equal((await ok(B,'list')).search,null);
  source.cards[0].question='Changed source';
  await fixtureQuery('update public.study_decks set snapshot=$2::jsonb where id=$1',[sourceId,JSON.stringify(source)]);
  assert.notEqual((await fixtureQuery('select cards from public.battle_decks where id=$1',[created.id])).rows[0].cards[0].question,'Changed source');
  const immediateTop=await ok(B,'top',{course:'Finance',language:'English'});
  assert.deepEqual(immediateTop.decks[0].id,created.id);
  assert.deepEqual([immediateTop.decks[0].score,immediateTop.decks[0].rating_count],[0,0]);
  await db.exec('reset role');
  await db.query("select battle_rate($1,$2,'good',false,false)",[created.id,B]);
  const top=await ok(B,'top',{course:'Finance',language:'English'});
  assert.deepEqual([top.decks[0].id,top.decks[0].score,top.decks[0].rating_count],[created.id,1,1]);
  await db.exec('reset role');
  await db.query("select battle_rate($1,$2,'good',false,false)",[created.id,B]);
  assert.equal((await fixtureQuery('select count(*)::int n from public.battle_ratings where battle_deck_id=$1 and reviewer_id=$2',[created.id,B])).rows[0].n,1);
  assert.deepEqual((await db.query('select game_xp,xp from public.profiles where id=$1',[A])).rows[0],{game_xp:0,xp:0});
  assert.equal((await db.query("select count(*)::int n from information_schema.columns where table_schema='public' and table_name='profiles' and column_name='creator_xp'")).rows[0].n,0);
  const abandonedSessionId=randomUUID();
  await db.exec('reset role');
  await db.query('insert into public.battle_sessions(id,p1,p2,battle_deck_id,source_kind,cards,course,language) values($1,$2,$3,$4,$5,$6::jsonb,$7,$8)',[abandonedSessionId,A,B,created.id,'random',JSON.stringify(stored.cards),'Finance','English']);
  await db.query("insert into public.battle_rounds(session_id,user_id) values($1,$2),($1,$3)",[abandonedSessionId,A,B]);
  await fail(A,'abandon',{id:abandonedSessionId});
  assert.equal((await ok(A,'abandon',{id:abandonedSessionId,confirmed:true})).state,'completed');
  assert.equal((await ok(A,'round',{id:abandonedSessionId})).state,'completed','an abandoned Battle cannot be resumed');
  const abandoned=(await ok(A,'list')).sessions.find(session=>session.id===abandonedSessionId);
  assert.deepEqual([abandoned.status,abandoned.result],['completed','loss']);
  assert.equal((await fixtureQuery('select count(*)::int n from public.battle_ratings where battle_deck_id=$1 and reviewer_id=$2',[created.id,A])).rows[0].n,1);
  const sessionId=randomUUID();
  await db.exec('reset role');
  await db.query('insert into public.battle_sessions(id,p1,p2,battle_deck_id,source_kind,cards,course,language) values($1,$2,$3,$4,$5,$6::jsonb,$7,$8)',[sessionId,A,B,created.id,'random',JSON.stringify(stored.cards),'Finance','English']);
  await db.query("insert into public.battle_rounds(session_id,user_id,answers,cursor,score) values($1,$2,$3::jsonb,2,1),($1,$4,'[]',0,0)",[sessionId,A,JSON.stringify([{index:0,correct:true},{index:1,correct:false,timed_out:true}]),B]);
  await asUser(A);const progress=(await db.query('select battle_round_progress($1) result',[sessionId])).rows[0].result;
  assert.deepEqual(progress.answers.map(answer=>answer.correct),[true,false]);
  await assert.rejects(()=>db.query("select report_battle_question($1,0,'unclear_question','Needs context')",[sessionId]));
  await db.exec('reset role');await db.query('update public.battle_sessions set settled_at=now() where id=$1',[sessionId]);
  await asUser(A);const sessions=(await db.query('select battle_sessions_list() sessions')).rows[0].sessions;
  const reviewable=sessions.find(session=>session.id===sessionId);
  assert.deepEqual([reviewable.opponent_username,reviewable.score,reviewable.opponent_score],['Bob',1,0]);
  const report=(await db.query("select report_battle_question($1,0,'unclear_question','Needs context') result",[sessionId])).rows[0].result;
  assert.equal(report.reported,true);
  const duplicate=(await db.query("select report_battle_question($1,0,'unclear_question','Needs context') result",[sessionId])).rows[0].result;
  assert.equal(duplicate.reported,false);
  assert.equal((await fixtureQuery('select count(*)::int n from public.battle_question_reports where session_id=$1',[sessionId])).rows[0].n,1);
  await asUser(B);const secondParticipant=(await db.query("select report_battle_question($1,0,'incorrect_answer','Wrong solution') result",[sessionId])).rows[0].result;
  assert.equal(secondParticipant.reported,true);
  await asUser(C);await assert.rejects(()=>db.query('select battle_round_progress($1)',[sessionId]));
  await assert.rejects(()=>db.query("select report_battle_question($1,0,'other','Not a participant')",[sessionId]));
  console.log('PASS Battle Deck creation, immutable snapshots, eligibility and rating without extra XP');
}catch(error){console.error(error.stack||error);process.exitCode=1;}finally{await db.close().catch(()=>{});await fs.rm(directory,{recursive:true,force:true});}
