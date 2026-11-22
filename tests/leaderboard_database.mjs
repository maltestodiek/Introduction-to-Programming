import fs from 'node:fs/promises';import os from 'node:os';import path from 'node:path';import assert from 'node:assert/strict';import {randomUUID} from 'node:crypto';import {spawnSync} from 'node:child_process';import {fileURLToPath} from 'node:url';
const {PGlite}=await import(process.env.PGLITE_MODULE||'@electric-sql/pglite');
if(process.argv[2]==='reload'){const db=new PGlite(process.argv[3]);await db.query("select set_config('request.jwt.claim.sub',$1,false)",[process.argv[4]]);const r=(await db.query('select leaderboard() r')).rows[0].r;assert.equal(r.me.rank,Number(process.argv[5]));const rolling=(await db.query('select leaderboard_30_days() r')).rows[0].r;assert.equal(rolling.me.xp,30);await db.close();console.log('PASS restart keeps the ranking');process.exit(0);}
const dir=await fs.mkdtemp(path.join(os.tmpdir(),'uniarena-leaderboard-'));const db=new PGlite(path.join(dir,'db'));let passed=0;
const users=Object.fromEntries(['anna','ben','cleo','dan','eva','finn','gus','hana','ivo','jule','kai','lea','mo'].map(n=>[n,randomUUID()]));const NOPROFILE=randomUUID();
const xp={anna:500,ben:400,cleo:400,dan:300,eva:250,finn:200,gus:150,hana:120,ivo:100,jule:90,kai:80,lea:10,mo:0};
async function who(u,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[u]);await db.exec('set role '+role);}
async function board(name){await who(users[name]??name);return(await db.query('select leaderboard() r')).rows[0].r;}
async function admin(sql,args=[]){await db.exec('reset role');return db.query(sql,args);}
async function test(name,f){await f();passed++;console.log('PASS '+name);}
try{
 await db.exec(`create role anon;create role authenticated;create schema auth;create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
 create table profiles(id uuid primary key,username text,university text,image_path text,xp integer not null default 0,game_xp integer not null default 0,email text);
 create table friend_edges(id uuid primary key default gen_random_uuid(),low_id uuid,high_id uuid,sender uuid,state text);create table friend_codes(user_id uuid,code text);`);
 for(const [n,u] of Object.entries(users)){await db.query('insert into profiles values($1,$2,$3,$4,$5,$6,$7)',[u,n,n==='mo'?'University of Porto':'Nova SBE',u+'/avatar.png',xp[n],xp[n],n+'@example.com']);await db.query('insert into friend_codes values($1,$2)',[u,'CODE'+n]);}
 const edge=async(a,b,state)=>{const [low,high]=[users[a],users[b]].sort();await db.query('insert into friend_edges(low_id,high_id,sender,state) values($1,$2,$3,$4)',[low,high,users[a],state]);};
 await edge('lea','anna','accepted');await edge('mo','lea','accepted');await edge('lea','ben','pending');
 await db.exec(await fs.readFile(new URL('../supabase/leaderboard-game-xp.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/leaderboard-university-visibility.sql',import.meta.url),'utf8'));
 await test('global top ten with shared places and own row marked',async()=>{
  const r=await board('anna');assert.equal(r.top.length,10);
  assert.deepEqual(r.top.map(x=>[x.rank,x.username,x.xp]).slice(0,4),[[1,'anna',500],[2,'ben',400],[2,'cleo',400],[4,'dan',300]]);
  assert.deepEqual(r.top.filter(x=>x.me).map(x=>x.username),['anna']);assert.equal(r.top[9].username,'jule');assert.deepEqual([r.me.rank,r.me.xp],[1,500]);
 });
 await test('a student outside the top ten gets their real place',async()=>{
  const r=await board('lea');assert.ok(!r.top.some(x=>x.me));assert.deepEqual([r.me.rank,r.me.username,r.me.xp,r.me.me],[12,'lea',10,true]);
  assert.equal((await board('mo')).me.rank,13);assert.equal((await board('kai')).me.rank,11);
 });
 await test('friends ranking holds only the student and accepted friends',async()=>{
  assert.deepEqual((await board('lea')).friends.map(x=>[x.rank,x.username,x.me]),[[1,'anna',false],[2,'lea',true],[3,'mo',false]]);
  assert.deepEqual((await board('ben')).friends.map(x=>x.username),['ben']);assert.deepEqual((await board('anna')).friends.map(x=>x.username),['anna','lea']);
 });
 await test('university is visible but codes, emails and other private data are not returned',async()=>{
  const text=JSON.stringify(await board('lea'));
  assert.ok(!/CODE|@example\.com|"id"|"email"|"code"/.test(text));
  const result=await board('lea');assert.equal(result.top[0].university,'Nova SBE');
  const keys=new Set(result.top.flatMap(x=>Object.keys(x)));assert.deepEqual([...keys].sort(),['image_path','me','rank','university','username','xp']);
 });
 await test('anonymous callers and students without a profile get nothing',async()=>{
  await who('','anon');await assert.rejects(()=>db.query('select leaderboard()'));
  const r=await board(NOPROFILE);assert.ok(r.error);assert.equal(r.top,undefined);
 });
 await test('only stored Battle XP moves a place',async()=>{
  await admin('update profiles set game_xp=450 where username=$1',['lea']);const r=await board('lea');assert.deepEqual([r.me.rank,r.top.find(x=>x.me).rank],[2,2]);assert.equal(r.top.length,10);
 });
 await admin('create table battle_sessions(id uuid primary key, settled_at timestamptz)');
 await admin('create table battle_rounds(session_id uuid, user_id uuid, game_xp_delta integer, primary key(session_id,user_id))');
 await db.exec(await fs.readFile(new URL('../supabase/migrations/20261121230000_rolling_leaderboard.sql',import.meta.url),'utf8'));
 async function points(user,delta,age) {
  const id=randomUUID();
  await admin('insert into battle_sessions values ($1,now()-$2::interval)',[id,age]);
  await admin('insert into battle_rounds values ($1,$2,$3)',[id,users[user],delta]);
 }
 async function rolling(id) {
  await who(id);
  return (await db.query('select leaderboard_30_days() r')).rows[0].r;
 }
 await test('rolling Global, University and Friends use the same settlement window',async()=>{
  await admin('begin');
  await points('lea',40,'719 hours 59 minutes');
  await points('lea',-10,'1 day');
  await points('lea',80,'720 hours');
  await points('lea',40,'31 days');
  await points('lea',40,null);
  await points('anna',30,'1 day');
  await points('mo',80,'1 day');
  await points('ben',40,'1 day');
  const r=await rolling(users.lea);
  for(const list of [r.top,r.university,r.friends]) assert.equal(list.find(row=>row.me).xp,30);
  assert.deepEqual([r.me.rank,r.university.find(row=>row.me).rank,r.friends.find(row=>row.me).rank],[3,2,2]);
  assert.deepEqual(r.friends.map(row=>row.username),['mo','anna','lea']);
  assert.equal(r.university.length,10);
  assert.ok(r.university.every(row=>row.university==='Nova SBE'));
  assert.deepEqual((await rolling(users.mo)).university.map(row=>row.username),['mo']);
  assert.deepEqual(Object.keys(r.me).sort(),['image_path','me','rank','university','username','xp']);
  assert.equal((await rolling(users.cleo)).me.xp,0);
  assert.equal((await admin('select game_xp from profiles where id=$1',[users.lea])).rows[0].game_xp,450);
  await admin('commit');
 });
 await test('rolling rankings require a signed-in profile',async()=>{
  await who('','anon');await assert.rejects(()=>db.query('select leaderboard_30_days()'));
  assert.ok((await rolling(NOPROFILE)).error);
 });
 await db.exec('reset role');await db.close();
 const r=spawnSync(process.execPath,[fileURLToPath(import.meta.url),'reload',path.join(dir,'db'),users.lea,'2'],{encoding:'utf8',env:process.env});process.stdout.write(r.stdout);assert.equal(r.status,0,r.stderr);passed++;
 console.log(`${passed} leaderboard database checks passed`);
}finally{await fs.rm(dir,{recursive:true,force:true});}
