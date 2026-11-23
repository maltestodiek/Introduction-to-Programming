// Isolated check of the Deck studio function and Study deck creation times. Never contacts Supabase or real users.
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';

const {PGlite}=await import(process.env.PGLITE_MODULE||'@electric-sql/pglite');
const directory=await fs.mkdtemp(path.join(os.tmpdir(),'uniarena-deck-studio-'));
let db=new PGlite(path.join(directory,'db'));
const A=randomUUID(),B=randomUUID();
const reviewed=randomUUID(),copied=randomUUID(),other=randomUUID(),battle=randomUUID();
const snapshot=(name,count=3)=>JSON.stringify({name,course:'Finance',language:'English',cards:Array.from({length:count},(_,index)=>({id:randomUUID(),question:`Q${index}`}))});

async function asUser(id){
  await db.exec('reset role');
  await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id]);
  await db.exec('set role authenticated');
}
async function studio(id){await asUser(id);return (await db.query('select deck_studio() result')).rows[0].result.decks;}

try{
  await db.exec(`
    create role anon; create role authenticated; create schema auth;
    create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
    grant usage on schema auth to anon,authenticated;
    create table public.profiles(id uuid primary key,username text);
    create table public.study_decks(id uuid primary key,creator_id uuid not null references public.profiles(id),snapshot jsonb not null,revision integer not null default 1,updated_at timestamptz not null default now(),published_at timestamptz);
    create table public.study_reviews(id uuid primary key default gen_random_uuid(),user_id uuid not null,deck_id uuid not null,snapshot jsonb not null,revision integer not null,created_at timestamptz not null default now());
    create table public.battle_decks(id uuid primary key,creator_id uuid not null,source_deck_id uuid not null,course text not null,language text not null,name text not null,cards jsonb not null,created_at timestamptz not null default now());
    revoke all on public.study_decks,public.study_reviews,public.battle_decks from public,anon,authenticated;
  `);
  await db.query("insert into public.profiles values($1,'Alice'),($2,'Bob')",[A,B]);
  // Existing decks before the migration: one reviewed before its first save, one copied without review.
  await db.query("insert into public.study_decks(id,creator_id,snapshot,updated_at,published_at) values($1,$2,$3::jsonb,'2026-11-19 19:25:38+00',null)",[reviewed,A,snapshot('Reviewed deck',18)]);
  await db.query("insert into public.study_reviews(user_id,deck_id,snapshot,revision,created_at) values($1,$2,'{}',1,'2026-11-19 19:20:00+00'),($1,$2,'{}',2,'2026-11-19 19:24:00+00')",[A,reviewed]);
  await db.query("insert into public.study_decks(id,creator_id,snapshot,updated_at,published_at) values($1,$2,$3::jsonb,'2026-11-18 10:00:00+00','2026-11-18 11:00:00+00')",[copied,A,snapshot('Copied deck')]);
  await db.query("insert into public.study_decks(id,creator_id,snapshot) values($1,$2,$3::jsonb)",[other,B,snapshot("Bob's deck")]);
  await db.query("insert into public.battle_decks(id,creator_id,source_deck_id,course,language,name,cards,created_at) values($1,$2,$3,'Finance','English','Battle snapshot',$4::jsonb,'2026-11-19 18:41:00+00')",[battle,A,reviewed,JSON.stringify(Array.from({length:15},(_,index)=>({id:String(index)})))]);

  await db.exec(await fs.readFile(new URL('../supabase/deck-studio.sql',import.meta.url),'utf8'));

  await db.exec(await fs.readFile(new URL('../supabase/migrations/20261123030000_personal_deck_studio_removal.sql',import.meta.url),'utf8'));

  const times=(await db.query('select id,created_at from public.study_decks')).rows;
  const createdOf=id=>times.find(row=>row.id===id).created_at;
  assert.equal(createdOf(reviewed).toISOString(),'2026-11-19T19:20:00.000Z','earliest review before saving is the creation time');
  assert.equal(createdOf(copied),null,'a deck without review keeps an unknown creation time');
  await db.query("insert into public.study_decks(id,creator_id,snapshot) values($1,$2,$3::jsonb)",[randomUUID(),A,snapshot('New deck')]);
  assert.ok((await db.query("select created_at from public.study_decks where snapshot->>'name'='New deck'")).rows[0].created_at,'new decks get a creation time automatically');
  // Saving an edited deck uses the same upsert as study_action and must keep the creation time.
  await db.query("insert into public.study_decks(id,creator_id,snapshot) values($1,$2,$3::jsonb) on conflict(id) do update set snapshot=excluded.snapshot,revision=public.study_decks.revision+1,updated_at=now()",[reviewed,A,snapshot('Reviewed deck',18)]);
  const resaved=(await db.query('select created_at,revision from public.study_decks where id=$1',[reviewed])).rows[0];
  assert.deepEqual([resaved.created_at.toISOString(),resaved.revision],['2026-11-19T19:20:00.000Z',2],'editing keeps the creation time');

  const decks=await studio(A);
  assert.deepEqual(decks.map(deck=>[deck.kind,deck.name]),[['study','New deck'],['study','Reviewed deck'],['battle','Battle snapshot'],['study','Copied deck']]);
  const own=decks.find(deck=>deck.name==='Reviewed deck');
  assert.deepEqual([own.course,own.language,own.count,own.published_at],['Finance','English',18,null]);
  assert.ok(own.created_at && own.updated_at);
  assert.ok(decks.find(deck=>deck.name==='Copied deck').published_at);
  const snapshotDeck=decks.find(deck=>deck.kind==='battle');
  assert.deepEqual([snapshotDeck.count,snapshotDeck.source_deck_id],[15,reviewed]);
  assert.ok(decks.every(deck=>deck.cards===undefined),'questions are not returned');
  assert.deepEqual((await studio(B)).map(deck=>deck.name),["Bob's deck"],'students see only their own decks');

  const remove=id=>db.query('select remove_study_deck_from_studio($1)',[id]);
  await asUser(B);
  await assert.rejects(()=>remove(reviewed),/unavailable/i);
  await asUser(A);
  await assert.rejects(()=>remove(battle),/unavailable/i);
  await remove(copied);await remove(copied);
  await remove(reviewed);
  assert.deepEqual((await studio(A)).map(d=>d.name),['New deck','Battle snapshot']);
  assert.deepEqual((await studio(B)).map(d=>d.id),[other]);
  await db.exec('reset role');
  const preserved=(await db.query('select published_at, snapshot, revision from study_decks where id=$1',[copied])).rows[0];
  assert.ok(preserved.published_at);
  assert.equal(preserved.snapshot.name,'Copied deck');
  assert.equal((await db.query('select source_deck_id from battle_decks where id=$1',[battle])).rows[0].source_deck_id,reviewed);
  await db.close();
  db=new PGlite(path.join(directory,'db'));
  assert.deepEqual((await studio(A)).map(d=>d.name),['New deck','Battle snapshot'],'personal removal persists after reopening the database');
  await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub','',false)");await db.exec('set role anon');
  await assert.rejects(()=>db.query('select deck_studio()'));
  await assert.rejects(()=>remove(other));
  console.log('PASS personal removal persists, checks ownership and preserves publication and Battle snapshots');
  console.log('PASS Deck studio lists only own decks with creation, edit and publication times');
}catch(error){console.error(error.stack||error);process.exitCode=1;}finally{await db.close().catch(()=>{});await fs.rm(directory,{recursive:true,force:true});}
