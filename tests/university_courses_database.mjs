import fs from 'node:fs/promises';import os from 'node:os';import path from 'node:path';import assert from 'node:assert/strict';import {randomUUID} from 'node:crypto';
const {PGlite}=await import(process.env.PGLITE_MODULE||'@electric-sql/pglite');
const dir=await fs.mkdtemp(path.join(os.tmpdir(),'uniarena-courses-'));const db=new PGlite(path.join(dir,'db'));let passed=0;
const A=randomUUID(),B=randomUUID(),C=randomUUID(),D=randomUUID(),E=randomUUID(),NOPROFILE=randomUUID();
async function who(u,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[u]);await db.exec('set role '+role);}
async function courses(user,university){await who(user);return(await db.query('select university_courses($1) r',[university])).rows[0].r;}
async function test(name,f){await f();passed++;console.log('PASS '+name);}
try{
 await db.exec(`create role anon;create role authenticated;create schema auth;create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
 create table profiles(id uuid primary key,username text,university text,email text);
 create table profile_private(user_id uuid primary key references profiles(id),courses text[] not null);
 alter table profile_private enable row level security;
 create policy private_read on profile_private for select to authenticated using(user_id=(select auth.uid()));
 grant select on profile_private,profiles to authenticated;`);
 const add=async(id,name,university,list)=>{await db.query('insert into profiles values($1,$2,$3,$4)',[id,name,university,name+'@example.com']);await db.query('insert into profile_private values($1,$2)',[id,list]);};
 await add(A,'anna','North University — Portugal',['Corporate Finance','Investments']);
 await add(B,'ben','North University — Portugal',['corporate finance','Derivatives']);
 await add(C,'cleo','North University — Portugal',['Corporate  Finance ','Investments']);
 await add(D,'dan','South College — Italy',['Roman Law']);
 await add(E,'eva','north university — portugal',['Statistics']);
 await db.exec(await fs.readFile(new URL('../supabase/university-courses.sql',import.meta.url),'utf8'));
 await test('lists the courses saved by students at the same university, sorted',async()=>{
  assert.deepEqual(await courses(A,'North University — Portugal'),['Corporate Finance','Derivatives','Investments','Statistics']);
 });
 await test('one course in several spellings appears once, in the most used spelling',async()=>{
  const list=await courses(B,'North University — Portugal');
  assert.equal(list.filter(n=>n.toLowerCase().replace(/\s+/g,' ')==='corporate finance').length,1);assert.ok(list.includes('Corporate Finance'));
 });
 await test('the university name is matched without regard to case or outer spaces',async()=>{
  assert.deepEqual(await courses(A,'  NORTH UNIVERSITY — PORTUGAL '),await courses(A,'North University — Portugal'));
 });
 await test('courses from another university are not included',async()=>{
  assert.ok(!(await courses(A,'North University — Portugal')).includes('Roman Law'));
  assert.deepEqual(await courses(A,'South College — Italy'),['Roman Law']);
 });
 await test('a student without a profile can read the list for the university they are choosing',async()=>{
  assert.deepEqual(await courses(NOPROFILE,'South College — Italy'),['Roman Law']);
 });
 await test('unknown, blank or missing universities return an empty list',async()=>{
  assert.deepEqual(await courses(A,'Nowhere Institute'),[]);assert.deepEqual(await courses(A,' '),[]);assert.deepEqual(await courses(A,null),[]);
 });
 await test('the result holds names only: no ids, usernames, emails or counts',async()=>{
  const list=await courses(A,'North University — Portugal');assert.ok(Array.isArray(list)&&list.every(n=>typeof n==='string'));
  assert.ok(!/anna|ben|cleo|eva|@example\.com|[0-9a-f]{8}-[0-9a-f]{4}/.test(JSON.stringify(list)));
 });
 await test('anonymous callers cannot read course lists',async()=>{
  await who('','anon');await assert.rejects(()=>db.query('select university_courses($1)',['North University — Portugal']));
 });
 await test('the private table itself stays closed to other students',async()=>{
  await who(A);const rows=(await db.query('select user_id from profile_private')).rows;assert.deepEqual(rows.map(r=>r.user_id),[A]);
 });
 await test('reading the list changes no data',async()=>{
  await db.exec('reset role');const before=JSON.stringify((await db.query('select * from profile_private order by user_id')).rows);
  await courses(A,'North University — Portugal');await db.exec('reset role');
  assert.equal(JSON.stringify((await db.query('select * from profile_private order by user_id')).rows),before);
 });
 console.log(passed+' checks passed');
}finally{await db.close();await fs.rm(dir,{recursive:true,force:true});}
