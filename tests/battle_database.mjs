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
async function action(id,name,data={}){
  await asUser(id);
  return (await db.query('select battle_action($1,$2::jsonb) result',[name,JSON.stringify(data)])).rows[0].result;
}
async function ok(id,name,data={}){const result=await action(id,name,data);assert.ok(!result.error,result.error);return result;}
async function fail(id,name,data={}){await assert.rejects(()=>action(id,name,data));}
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
    create table public.profiles(id uuid primary key,username text,university text,languages text[],xp integer not null default 0,win_streak integer not null default 0);
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
  const source=sourceDeck();const sourceId=randomUUID();
  await db.query('insert into public.study_decks(id,creator_id,snapshot) values($1,$2,$3::jsonb)',[sourceId,A,JSON.stringify(source)]);

  const listed=await ok(A,'sources');assert.equal(listed.sources[0].battle_capable,true);
  await fail(B,'source',{id:sourceId});
  await fail(A,'create_deck',{source_deck_id:sourceId,card_ids:source.cards.slice(0,15).map(card=>card.id),consent:false});
  await fail(A,'create_deck',{source_deck_id:sourceId,card_ids:source.cards.slice(0,14).map(card=>card.id),consent:true});
  const created=await ok(A,'create_deck',{source_deck_id:sourceId,card_ids:source.cards.slice(0,15).map(card=>card.id),consent:true,name:'Battle snapshot'});
  const stored=(await db.query('select cards,public_consent_at from public.battle_decks where id=$1',[created.id])).rows[0];
  assert.equal(stored.cards.length,15);assert.ok(stored.public_consent_at);
  source.cards[0].question='Changed source';
  await db.query('update public.study_decks set snapshot=$2::jsonb where id=$1',[sourceId,JSON.stringify(source)]);
  assert.notEqual((await db.query('select cards from public.battle_decks where id=$1',[created.id])).rows[0].cards[0].question,'Changed source');
  await db.query("insert into public.battle_daily_ratings values((now() at time zone 'Europe/Berlin')::date,$1,2,3,2,1,0,0)",[created.id]);
  const top=await ok(B,'top',{course:'Finance',language:'English'});assert.equal(top.decks[0].id,created.id);
  await db.exec('reset role');
  await db.query("select battle_rate($1,$2,'good',false,false)",[created.id,B]);
  await db.query("select battle_rate($1,$2,'good',false,false)",[created.id,B]);
  assert.equal((await db.query('select count(*)::int n from public.battle_ratings where battle_deck_id=$1 and reviewer_id=$2',[created.id,B])).rows[0].n,1);
  assert.deepEqual((await db.query('select game_xp,xp from public.profiles where id=$1',[A])).rows[0],{game_xp:0,xp:0});
  assert.equal((await db.query("select count(*)::int n from information_schema.columns where table_schema='public' and table_name='profiles' and column_name='creator_xp'")).rows[0].n,0);
  const sessionId=randomUUID();
  await db.exec('reset role');
  await db.query('insert into public.battle_sessions(id,p1,p2,battle_deck_id,source_kind,cards,course,language) values($1,$2,$3,$4,$5,$6::jsonb,$7,$8)',[sessionId,A,B,created.id,'random',JSON.stringify(stored.cards),'Finance','English']);
  await db.query("insert into public.battle_rounds(session_id,user_id,answers,cursor,score) values($1,$2,$3::jsonb,2,1),($1,$4,'[]',0,0)",[sessionId,A,JSON.stringify([{index:0,correct:true},{index:1,correct:false,timed_out:true}]),B]);
  await asUser(A);const progress=(await db.query('select battle_round_progress($1) result',[sessionId])).rows[0].result;
  assert.deepEqual(progress.answers.map(answer=>answer.correct),[true,false]);
  await asUser(C);await assert.rejects(()=>db.query('select battle_round_progress($1)',[sessionId]));
  console.log('PASS Battle Deck creation, immutable snapshots, eligibility and rating without extra XP');
}catch(error){console.error(error.stack||error);process.exitCode=1;}finally{await db.close().catch(()=>{});await fs.rm(directory,{recursive:true,force:true});}
