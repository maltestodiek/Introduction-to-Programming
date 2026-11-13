// Isolated database: current and historical matched partners use normal friend consent.
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
const {PGlite}=await import(process.env.PGLITE_MODULE || '@electric-sql/pglite');
const db=new PGlite();
const [a,b,c]=[randomUUID(),randomUUID(),randomUUID()];
try {
 await db.exec(`create role anon; create role authenticated; create schema auth;
 create table auth.users(id uuid primary key);
 create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
 create table profiles(id uuid primary key,username text,image_path text);
 create table chat_threads(low_id uuid,high_id uuid);
 create table play_duels(id uuid,p1 uuid,p2 uuid);
 create table study_sessions(id uuid,user_id uuid,partner_id uuid,finished_at timestamptz);`);
 for(const u of [a,b,c]){await db.query('insert into auth.users values($1)',[u]);await db.query("insert into profiles values($1,'student',null)",[u]);}
 await db.exec(await fs.readFile(new URL('../supabase/friends-schema.sql',import.meta.url),'utf8'));
 await db.exec(await fs.readFile(new URL('../supabase/session-friend-update.sql',import.meta.url),'utf8'));
 async function action(u,k,v){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[u]);await db.exec('set role authenticated');return(await db.query('select friends_action($1,$2) r',[k,v])).rows[0].r;}
 assert.ok((await action(a,'request_user',c)).error);
 assert.ok((await action(a,'request_user',a)).error);
 await db.exec('reset role');const s1=randomUUID(),s2=randomUUID();
 await db.query('insert into study_sessions values($1,$2,$3,now()),($3,$4,$1,now())',[s1,a,s2,b]);
 assert.equal((await action(a,'request_user',b)).message,'Friend request sent.');
 assert.match((await action(a,'request_user',b)).error,/already pending/);
 await db.exec('reset role');let edge=(await db.query('select * from friend_edges')).rows[0];assert.equal(edge.state,'pending');
 assert.ok((await action(c,'accept',edge.id)).error);
 assert.ok(!(await action(b,'accept',edge.id)).error);
 await db.exec('reset role');assert.equal((await db.query('select state from friend_edges')).rows[0].state,'accepted');
 await db.query('insert into play_duels values($1,$2,$3)',[randomUUID(),b,c]);
 assert.equal((await action(b,'request_user',c)).message,'Friend request sent.');
 assert.ok((await action(a,'request_user',b)).error);
 assert.match((await action(a,'request_user',b)).error,/Too many/);
 await db.exec('reset role');
 await db.query('insert into chat_threads values(least($1::uuid,$2::uuid),greatest($1::uuid,$2::uuid))',[a,c]);
 assert.equal((await action(c,'request_user',a)).message,'Friend request sent.');
 console.log('PASS historical Study and Battle partner requests, consent, duplicates, stranger rejection and shared rate limit');
} finally {await db.close();}
