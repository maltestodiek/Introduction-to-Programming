// Run against an isolated PostgreSQL engine; never connects to production.
// PGLITE_MODULE points to an installed @electric-sql/pglite module.
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import {spawnSync} from 'node:child_process';
const {PGlite}=await import(process.env.PGLITE_MODULE || '@electric-sql/pglite');
if(process.argv[2]==='reload'){
 const db=new PGlite(process.argv[3]);
 const rows=(await db.query('select snapshot from public.decks order by created_at')).rows;
 assert.equal(rows.length,2);
 assert.deepEqual(rows[0].snapshot,JSON.parse(await fs.readFile(process.argv[4],'utf8')));
 await db.close();console.log('PASS full process restart preserves the exact published snapshot');
 process.exit(0);
}
const dir=await fs.mkdtemp(path.join(os.tmpdir(),'studyduel-decks-'));
const db=new PGlite(path.join(dir,'db'));
const owner=randomUUID(),peer=randomUUID(),outsider=randomUUID();
let passed=0;
async function test(name,fn){await fn();passed++;console.log('PASS '+name);}
async function identity(id,role='authenticated'){
 await db.exec('reset role');
 await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id]);
 await db.exec('set role '+role);
}
const draft={id:randomUUID(),course:'Finance',name:'Original deck',cards:Array.from({length:15},(_,i)=>{
 const answers=Array.from({length:4},(_,j)=>({id:randomUUID(),text:`Answer ${i+1}.${j+1}`}));
 return {id:randomUUID(),question:`Question ${i+1}?`,answers,correct_answer_id:answers[i%4].id};
})};
async function review(d=draft){return (await db.query('select public.review_deck($1::jsonb) as r',[JSON.stringify(d)])).rows[0].r.id;}
async function publish(r,d=draft){return (await db.query('select public.publish_deck($1::uuid,$2::jsonb) as r',[r,JSON.stringify(d)])).rows[0].r.id;}
try{
 await db.exec(`create role anon;create role authenticated;create schema auth;
 create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
 grant usage on schema auth to authenticated,anon;
 create table public.profiles(id uuid primary key,username text,university text);
 create table public.profile_private(user_id uuid primary key references public.profiles(id),courses text[]);
 grant select on public.profiles to authenticated;
 grant select on public.profile_private to authenticated;
 alter table public.profile_private enable row level security;
 create policy owner_read on public.profile_private for select to authenticated using(user_id=auth.uid());`);
 for(const [id,name,campus] of [[owner,'owner','University A'],[peer,'peer','University A'],[outsider,'outsider','University B']]){
  await db.query('insert into public.profiles values($1,$2,$3)',[id,name,campus]);
  await db.query("insert into public.profile_private values($1,array['Finance'])",[id]);
 }
 await db.exec(await fs.readFile(new URL('../supabase/decks-schema.sql',import.meta.url),'utf8'));
 await identity(owner);
 let rid,id;
 await test('review creates no published deck',async()=>{rid=await review();assert.equal((await db.query('select * from public.decks')).rows.length,0);});
 await test('publish keeps 15 cards, 60 answer identities and solutions',async()=>{id=await publish(rid);const row=(await db.query('select * from public.decks')).rows[0];assert.deepEqual(row.snapshot,draft);assert.equal(row.creator_id,owner);assert.equal(row.cards.flatMap(c=>c.answers).length,60);});
 await test('retry is idempotent',async()=>{assert.equal(await publish(rid),id);assert.equal((await db.query('select * from public.decks')).rows.length,1);});
 await test('changed content cannot reuse a review',async()=>{await assert.rejects(()=>publish(rid,{...draft,name:'Changed'}));});
 await test('invalid deck sizes and incomplete answers reject atomically',async()=>{
  for(const n of [0,14,16]){const d=structuredClone(draft);d.id=randomUUID();d.cards=Array.from({length:n},(_,i)=>draft.cards[i%15]);await assert.rejects(()=>review(d));}
  const d=structuredClone(draft);d.cards[2].answers[3].text=' ';await assert.rejects(()=>review(d));
  d.cards[2].answers[3].text='ok';d.cards[2].correct_answer_id=null;await assert.rejects(()=>review(d));
  assert.equal((await db.query('select * from public.decks')).rows.length,1);
 });
 await test('unselected course rejects',async()=>{await assert.rejects(()=>review({...draft,course:'Other course'}));});
 await test('raw writes and updates/deletes are denied',async()=>{
  await assert.rejects(()=>db.query("update public.decks set name='Changed'"));
  await assert.rejects(()=>db.query('delete from public.decks'));
  await assert.rejects(()=>db.query('insert into public.decks select * from public.decks'));
  await assert.rejects(()=>db.query('select * from public.deck_reviews'));
 });
 await test('same university reads but cannot use another creator review',async()=>{
  await identity(peer);assert.equal((await db.query('select * from public.decks')).rows.length,1);await assert.rejects(()=>publish(rid));
 });
 await test('another university cannot read deck content',async()=>{await identity(outsider);assert.equal((await db.query('select * from public.decks')).rows.length,0);});
 await test('anonymous access fails',async()=>{await identity('', 'anon');await assert.rejects(()=>db.query('select * from public.decks'));await assert.rejects(()=>review());});
 await identity(owner);
 await test('a separate draft may reuse the name',async()=>{const d={...draft,id:randomUUID()};const r=await review(d);await publish(r,d);assert.equal((await db.query('select * from public.decks')).rows.length,2);});
 await test('failed publication leaves no partial deck',async()=>{
  const d={...draft,id:randomUUID()};const r=await review(d);
  await db.exec('reset role');
  await db.exec("create function public.test_fail() returns trigger language plpgsql as $$begin raise exception 'Injected failure';end$$;create trigger test_fail before insert on public.decks for each row execute function public.test_fail();");
  await identity(owner);await assert.rejects(()=>publish(r,d));assert.equal((await db.query('select * from public.decks')).rows.length,2);
  await db.exec('reset role');await db.exec('drop trigger test_fail on public.decks;drop function public.test_fail();');
 });
 await db.close();const fixture=path.join(dir,'expected.json');await fs.writeFile(fixture,JSON.stringify(draft));
 const child=spawnSync(process.execPath,[new URL(import.meta.url).pathname,'reload',path.join(dir,'db'),fixture],{encoding:'utf8',env:process.env});
 assert.equal(child.status,0,child.stderr);console.log(child.stdout.trim());
 console.log(`${passed+1} isolated database checks passed`);
}finally{await db.close().catch(()=>{});await fs.rm(dir,{recursive:true,force:true});}
