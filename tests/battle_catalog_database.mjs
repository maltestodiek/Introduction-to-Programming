// Isolated check of the Battle Deck catalogue on the Decks page. Never contacts Supabase or real users.
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';

const {PGlite}=await import(process.env.PGLITE_MODULE||'@electric-sql/pglite');
const directory=await fs.mkdtemp(path.join(os.tmpdir(),'uniarena-battle-catalog-'));
const db=new PGlite(path.join(directory,'db'));
const A=randomUUID(),B=randomUUID(),C=randomUUID(),D=randomUUID();

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
  for(const [id,name,university,course] of [[A,'Alice','Nova','Finance'],[B,'Bob','Nova',' finance '],[C,'Chris','Other','Finance'],[D,'Dana','Nova','Statistics']]){
    await db.query("insert into public.profiles(id,username,university,languages) values($1,$2,$3,array['English'])",[id,name,university]);
    await db.query("insert into public.profile_private values($1,array[$2])",[id,course]);
  }
  await db.exec(await fs.readFile(new URL('../supabase/battle-mode-schema.sql',import.meta.url),'utf8'));
  await db.exec(await fs.readFile(new URL('../supabase/battle-round-progress.sql',import.meta.url),'utf8'));
  await db.exec(await fs.readFile(new URL('../supabase/battle-xp-only.sql',import.meta.url),'utf8'));
  await db.exec(await fs.readFile(new URL('../supabase/battle-question-reports.sql',import.meta.url),'utf8'));
  await db.exec(await fs.readFile(new URL('../supabase/battle-deck-availability.sql',import.meta.url),'utf8'));
  await db.exec(await fs.readFile(new URL('../supabase/battle-search-controls.sql',import.meta.url),'utf8'));
  await db.exec(await fs.readFile(new URL('../supabase/battle-deck-catalog.sql',import.meta.url),'utf8'));
  async function catalog(id){await asUser(id);return (await db.query('select battle_deck_catalog() result')).rows[0].result.decks;}

  assert.deepEqual(await catalog(A),[]);
  const source=sourceDeck();const sourceId=randomUUID();
  await db.exec('reset role');
  await db.query('insert into public.study_decks(id,creator_id,snapshot) values($1,$2,$3::jsonb)',[sourceId,A,JSON.stringify(source)]);
  // Insert the snapshot directly: this test covers only the catalogue, not battle_action.
  const created={id:randomUUID()};
  await db.query("insert into public.battle_decks(id,creator_id,source_deck_id,source_revision,source_origin,university,course,language,name,cards,public_consent_at) values($1,$2,$3,1,'human','Nova','Finance','English','Battle snapshot',$4::jsonb,now())",[created.id,A,sourceId,JSON.stringify(source.cards.slice(0,15))]);
  await db.query("insert into public.battle_decks(id,creator_id,source_deck_id,source_revision,source_origin,university,course,language,name,cards,public_consent_at) values($1,$2,$3,1,'human','Other','Finance','English','Elsewhere',$4::jsonb,now())",[randomUUID(),C,sourceId,JSON.stringify(source.cards.slice(0,15))]);

  const own=await catalog(A);
  assert.equal(own.length,1);
  assert.deepEqual([own[0].id,own[0].name,own[0].course,own[0].language,own[0].author,own[0].count,own[0].owned],[created.id,'Battle snapshot','Finance','English','Alice',15,true]);
  assert.equal(own[0].cards,undefined,'the catalogue must not reveal Battle questions');

  const classmate=await catalog(B);
  assert.deepEqual([classmate.length,classmate[0].id,classmate[0].owned],[1,created.id,false]);
  assert.deepEqual((await catalog(C)).map(deck=>deck.name),['Elsewhere'],'another university sees only its own decks');
  assert.deepEqual(await catalog(D),[],'a student without the course must not see the deck');

  await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub','',false)");await db.exec('set role anon');
  await assert.rejects(()=>db.query('select battle_deck_catalog()'));
  await asUser(B);await assert.rejects(()=>db.query('select * from public.battle_decks'));
  console.log('PASS Battle Deck catalogue lists same-university course decks without questions');
}catch(error){console.error(error.stack||error);process.exitCode=1;}finally{await db.close().catch(()=>{});await fs.rm(directory,{recursive:true,force:true});}
