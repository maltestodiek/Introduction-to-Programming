import fs from 'node:fs/promises';import os from 'node:os';import path from 'node:path';import assert from 'node:assert/strict';import {randomUUID} from 'node:crypto';import {spawnSync} from 'node:child_process';import {fileURLToPath} from 'node:url';
const {PGlite}=await import(process.env.PGLITE_MODULE||'@electric-sql/pglite');
if(process.argv[2]==='reload'){const db=new PGlite(process.argv[3]);assert.equal((await db.query('select count(*)::int n from study_plans')).rows[0].n,Number(process.argv[4]));await db.close();console.log('PASS restart keeps study plans');process.exit(0);}
const dir=await fs.mkdtemp(path.join(os.tmpdir(),'uniarena-plan-'));const db=new PGlite(path.join(dir,'db'));const A=randomUUID(),B=randomUUID(),NOPROFILE=randomUUID();let passed=0;
async function who(u,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[u]);await db.exec('set role '+role);}
async function act(u,a,d={}){await who(u);return(await db.query('select study_plan_action($1,$2::jsonb) r',[a,JSON.stringify(d)])).rows[0].r;}
async function ok(u,a,d={}){const r=await act(u,a,d);assert.ok(!r.error,r.error);return r;}
async function bad(u,a,d={}){assert.ok((await act(u,a,d)).error);}
async function admin(sql,args=[]){await db.exec('reset role');return db.query(sql,args);}
async function test(name,f){await f();passed++;console.log('PASS '+name);}
const plan={name:'Winter exams',target:2,sessions:2,times:['09:00','14:00'],weekdays_off:[5,6],dates_off:[],courses:[{course:'Finance',end:'2026-12-10',decks:[randomUUID()]}]};
try{
 await db.exec(`create role anon;create role authenticated;create schema auth;create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
 create table profiles(id uuid primary key,username text);`);
 for(const [u,n] of [[A,'Alice'],[B,'Bob']])await db.query('insert into profiles values($1,$2)',[u,n]);
 await db.exec(await fs.readFile(new URL('../supabase/study-plan-schema.sql',import.meta.url),'utf8'));
 let id;
 await test('owner saves, lists and edits a plan',async()=>{
  id=(await ok(A,'save',{plan})).id;assert.deepEqual((await ok(A,'list')).plans.map(p=>p.plan.name),['Winter exams']);
  assert.equal((await ok(A,'save',{id,plan:{...plan,name:'Edited',id:'ignored'}})).id,id);
  const stored=(await ok(A,'list')).plans[0];assert.equal(stored.plan.name,'Edited');assert.equal(stored.plan.id,undefined);assert.deepEqual(stored.calendar_events,[]);
 });
 await test('several plans per student are allowed up to the limit',async()=>{
  const second=(await ok(A,'save',{plan:{...plan,name:'Second'}})).id;assert.equal((await ok(A,'list')).plans.length,2);await ok(A,'delete',{id:second});
  for(let i=0;i<19;i++)await ok(B,'save',{plan});await ok(B,'save',{plan});await bad(B,'save',{plan});assert.equal((await ok(B,'list')).plans.length,20);
 });
 await test('another student cannot read, change or delete the plan or its calendar entries',async()=>{
  assert.ok(!(await ok(B,'list')).plans.some(p=>p.id===id));
  await bad(B,'save',{id,plan:{...plan,name:'Hijacked'}});await bad(B,'events',{id,events:['x']});await bad(B,'delete',{id});
  assert.equal((await ok(A,'list')).plans[0].plan.name,'Edited');
  await who(A);await assert.rejects(()=>db.query('select * from study_plans'));
  await who('','anon');await assert.rejects(()=>db.query("select study_plan_action('list','{}'::jsonb)"));
  await bad(NOPROFILE,'list');
 });
 await test('rejected writes leave stored data unchanged',async()=>{
  await bad(A,'save',{});await bad(A,'save',{plan:'text'});await bad(A,'save',{plan:{name:'x'.repeat(20001)}});await bad(A,'events',{id,events:{}});await bad(A,'save',{id:randomUUID(),plan});await bad(A,'unknown');
  const stored=(await ok(A,'list')).plans;assert.equal(stored.length,1);assert.equal(stored[0].plan.name,'Edited');
 });
 await test('calendar entry identifiers are recorded per plan and removed with it',async()=>{
  await ok(A,'events',{id,events:[{uid:'u1',event_id:'g1'}]});assert.deepEqual((await ok(A,'list')).plans[0].calendar_events,[{uid:'u1',event_id:'g1'}]);
  const other=(await ok(A,'save',{plan})).id;await ok(A,'delete',{id:other});assert.equal((await ok(A,'list')).plans.length,1);
 });
 const n=(await admin('select count(*)::int n from study_plans')).rows[0].n;await db.close();
 const r=spawnSync(process.execPath,[fileURLToPath(import.meta.url),'reload',path.join(dir,'db'),String(n)],{encoding:'utf8',env:process.env});process.stdout.write(r.stdout);assert.equal(r.status,0,r.stderr);passed++;
 console.log(`${passed} study plan database checks passed`);
}finally{await fs.rm(dir,{recursive:true,force:true});}
