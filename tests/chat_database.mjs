import fs from 'node:fs/promises';import os from 'node:os';import path from 'node:path';import assert from 'node:assert/strict';import {randomUUID} from 'node:crypto';import {spawnSync} from 'node:child_process';
const {PGlite}=await import(process.env.PGLITE_MODULE||'@electric-sql/pglite');
if(process.argv[2]==='reload'){const db=new PGlite(process.argv[3]);assert.equal((await db.query('select count(*)::int n from chat_messages')).rows[0].n,Number(process.argv[4]));await db.close();console.log('PASS restart preserves chat history');process.exit(0);}
const dir=await fs.mkdtemp(path.join(os.tmpdir(),'studyduel-chat-'));const db=new PGlite(path.join(dir,'db'));const A=randomUUID(),B=randomUUID(),C=randomUUID();let passed=0;
async function who(u,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[u]);await db.exec('set role '+role);}
async function act(u,a,d={}){await who(u);return(await db.query('select chat_action($1,$2::jsonb) r',[a,JSON.stringify(d)])).rows[0].r;}
async function ok(u,a,d={}){const r=await act(u,a,d);assert.ok(!r.error,r.error);return r;}
async function bad(u,a,d={}){assert.ok((await act(u,a,d)).error);}
async function admin(sql,args=[]){await db.exec('reset role');return db.query(sql,args);}
async function test(name,f){await f();passed++;console.log('PASS '+name);}
try{
 await db.exec(`create role anon;create role authenticated;create schema auth;create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
 create table profiles(id uuid primary key,username text,image_path text);create table friend_edges(low_id uuid,high_id uuid,state text);create table play_duels(id uuid,p1 uuid,p2 uuid);create table study_sessions(id uuid,user_id uuid,partner_id uuid);`);
 for(const [u,n] of [[A,'Alice'],[B,'Bob'],[C,'Chris']])await db.query('insert into profiles values($1,$2,$3)',[u,n,u+'/avatar.png']);
 await db.exec(await fs.readFile(new URL('../supabase/chat-schema.sql',import.meta.url),'utf8'));
 let tid,mid;
 await test('strangers and self cannot create a chat; a battle partner can',async()=>{
  await bad(A,'open',{user_id:B});await bad(A,'open',{user_id:A});const duel=randomUUID();await admin('insert into play_duels values($1,$2,$3)',[duel,A,B]);
  assert.equal((await ok(A,'partner',{kind:'battle',id:duel})).partner.id,B);assert.equal((await ok(C,'partner',{kind:'battle',id:duel})).partner,null);
  tid=(await ok(A,'open',{user_id:B})).id;assert.equal((await ok(B,'open',{user_id:A})).id,tid);
 });
 await test('participant-only history, sending and read markers',async()=>{
  for(const action of ['read','send','seen'])await bad(C,action,{id:tid,body:'intrusion',request_id:randomUUID(),through:1});
  assert.deepEqual((await ok(C,'list')).threads,[]);await who(A);for(const table of ['chat_threads','chat_messages','chat_reads'])await assert.rejects(()=>db.query('select * from '+table));
  await who('','anon');await assert.rejects(()=>db.query("select chat_action('list')"));
 });
 await test('messages persist, retries are idempotent and invalid messages do not write',async()=>{
  const request_id=randomUUID();mid=(await ok(A,'send',{id:tid,body:'Hello Bob',request_id})).id;
  assert.equal((await ok(A,'send',{id:tid,body:'Hello Bob',request_id})).id,mid);
  await bad(A,'send',{id:tid,body:'Changed',request_id});for(const body of ['', '  ', 'x'.repeat(2001)])await bad(A,'send',{id:tid,body,request_id:randomUUID()});
  const r=await ok(B,'read',{id:tid});assert.equal(r.messages.length,1);assert.equal(r.messages[0].body,'Hello Bob');assert.equal(r.messages[0].from_me,false);
  assert.equal((await ok(A,'list')).threads[0].unread,0);assert.equal((await ok(B,'list')).threads[0].unread,1);
  assert.ok(!('email' in r.partner));assert.ok(!('avatar' in r.partner));
 });
 await test('read marks only acknowledge the delivered message and never move backwards',async()=>{
  const second=(await ok(A,'send',{id:tid,body:'Second message',request_id:randomUUID()})).id;
  await ok(B,'seen',{id:tid,through:mid});assert.equal((await ok(B,'list')).threads[0].unread,1);
  await ok(B,'seen',{id:tid,through:second});await ok(B,'seen',{id:tid,through:mid});assert.equal((await ok(B,'list')).threads[0].unread,0);
 });
 await test('matched Study partners and friends can start chat; waiting alone cannot',async()=>{
  const a=randomUUID(),b=randomUUID();await admin('insert into study_sessions values($1,$2,null)',[a,A]);assert.equal((await ok(A,'partner',{kind:'study',id:a})).partner,null);
  await admin('insert into study_sessions values($1,$2,$3)',[b,C,a]);await admin('update study_sessions set partner_id=$1 where id=$2',[b,a]);
  assert.equal((await ok(A,'partner',{kind:'study',id:a})).partner.id,C);await ok(A,'open',{user_id:C});
  await admin("insert into friend_edges values(least($1::uuid,$2::uuid),greatest($1::uuid,$2::uuid),'accepted')",[B,C]);await ok(B,'open',{user_id:C});
 });
 await test('rate limits reject excess sends and history pages have no duplicates',async()=>{
  for(let i=2;i<20;i++)await ok(A,'send',{id:tid,body:'Message '+i,request_id:randomUUID()});await bad(A,'send',{id:tid,body:'Too fast',request_id:randomUUID()});
  for(let i=0;i<101;i++)await admin('insert into chat_messages(thread_id,sender,request_id,body) values($1,$2,$3,$4)',[tid,B,randomUUID(),'History '+i]);
  const recent=await ok(A,'read',{id:tid});assert.equal(recent.messages.length,100);assert.equal(recent.has_older,true);
  const old=await ok(A,'read',{id:tid,before:recent.messages[0].id});assert.equal(old.messages.length,21);assert.ok(old.messages.at(-1).id<recent.messages[0].id);
 });
 const count=(await admin('select count(*)::int n from chat_messages')).rows[0].n;await db.close();const re=spawnSync(process.execPath,[process.argv[1],'reload',path.join(dir,'db'),String(count)],{encoding:'utf8',env:process.env});assert.equal(re.status,0,re.stderr);console.log(re.stdout.trim());console.log(`${passed+1} isolated chat checks passed`);
}finally{try{await db.close();}catch{}await fs.rm(dir,{recursive:true,force:true});}
