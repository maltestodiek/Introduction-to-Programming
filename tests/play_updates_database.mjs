// Isolate the inbox projection, including cross-account reads and retrying acknowledgements.
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
const {PGlite}=await import(process.env.PGLITE_MODULE || '@electric-sql/pglite');
const db=new PGlite();
const [a,b,invite,study,peer,battle]=Array.from({length:6},()=>randomUUID());
async function updates(user,seen=[]) {
  await db.exec('reset role');
  await db.query("select set_config('app.viewer',$1,false)",[user]);
  await db.exec('set role authenticated');
  return (await db.query('select play_unread_updates($1) as unread',[seen])).rows[0].unread;
}
try {
  await db.exec(`create role authenticated; create role anon; create schema auth;
    create function auth.uid() returns uuid language sql as $$select current_setting('app.viewer')::uuid$$;
    create table profiles(id uuid primary key);
    create table battle_rounds(user_id uuid,session_id uuid);
    create table battle_sessions(id uuid,p2 uuid,settled_at timestamptz);
    create table battle_invites(id uuid,recipient uuid,state text,expires_at timestamptz);
    create table study_sessions(id uuid,user_id uuid,friend_id uuid,mode text,state text,expires_at timestamptz,
      course text,language text,total int,partner_id uuid,finished_at timestamptz,left_at timestamptz,timeout_result text);
    create function has_study_invite_deck(uuid,text,text,int) returns boolean language sql as $$select true$$;`);
  await db.query('insert into profiles values($1),($2)',[a,b]);
  await db.exec(await fs.readFile(new URL('../supabase/migrations/20261122200000_play_updates.sql',import.meta.url),'utf8'));
  await db.query("insert into battle_invites values($1,$2,'pending',now()+interval '1 day')",[invite,a]);
  await db.query("insert into study_sessions(id,user_id,friend_id,mode,state,expires_at) values($1,$2,$3,'friend','waiting',now()+interval '1 day')",[study,b,a]);
  const battleInvite='battle:invite:'+invite,studyInvite='study:invite:'+study;
  assert.deepEqual(await updates(a),[battleInvite,studyInvite]);
  assert.deepEqual(await updates(b,[studyInvite]),[]);
  assert.deepEqual(await updates(a,[studyInvite]),[battleInvite]);
  assert.deepEqual(await updates(a,[studyInvite]),[battleInvite]);
  assert.deepEqual(await updates(a),[battleInvite]);
  await db.exec('reset role');
  await db.query("update battle_invites set state='accepted' where id=$1",[invite]);
  await db.query("insert into battle_sessions values($1,$2,null)",[battle,b]);
  await db.query("insert into battle_rounds values($1,$3),($2,$3)",[a,b,battle]);
  await db.query("update study_sessions set state='paired',partner_id=$1 where id=$2",[peer,study]);
  await db.query("insert into study_sessions(id,user_id,partner_id) values($1,$2,$3)",[peer,a,study]);
  assert.deepEqual(await updates(a),['battle:match:'+battle,'study:match:'+peer]);
  assert.deepEqual(await updates(a,['battle:match:'+battle]),['study:match:'+peer]);
  assert.deepEqual(await updates(b),['battle:match:'+battle,'study:match:'+study]);
  await db.exec('reset role');
  await db.query("update battle_sessions set settled_at=now() where id=$1",[battle]);
  await db.exec("update study_sessions set finished_at=now()");
  assert.deepEqual(await updates(a),['battle:result:'+battle,'study:result:'+peer]);
  await assert.rejects(()=>db.query('select * from play_update_reads'));
  await db.exec('set role anon');
  await assert.rejects(()=>db.query('select play_unread_updates()'));
  console.log('PASS mixed counts, per-player acknowledgements, expired events, match and result transitions, protected reads');
} finally {await db.close();}
