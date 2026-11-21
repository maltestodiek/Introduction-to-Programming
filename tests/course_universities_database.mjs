import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';

const { PGlite } = await import(process.env.PGLITE_MODULE || '@electric-sql/pglite');
const sql = name => readFile(new URL('../supabase/' + name, import.meta.url), 'utf8');

test('campus transfers preserve private courses across restart and restrict new matches', async () => {
    const dir = await mkdtemp(path.join(tmpdir(), 'uniarena-transfer-'));
    let db = new PGlite(dir);
    const owner = randomUUID(), peer = randomUUID();
    const avatar = {skin:'Light', hair:'Short', hair_color:'Brown', clothing:'Indigo', accessory:'None'};
    const login = async id => {
        await db.exec('reset role');
        await db.query("select set_config('request.jwt.claim.sub',$1,false)", [id]);
        await db.exec('set role authenticated');
    };
    const save = (from, to, courses, year=2028) =>
        db.query('select save_profile_v4($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)',
            ['student',to,['English'],courses,JSON.stringify(avatar),'Avatar',owner+'/a.png','Other','',year,from]);
    const profile = async () => (await db.query('select courses, course_history from profile_private')).rows;
    try {
        await db.exec(`create role anon; create role authenticated; create schema auth;
            create table auth.users(id uuid primary key);
            create function auth.uid() returns uuid language sql stable as $$
                select current_setting('request.jwt.claim.sub')::uuid $$;
            grant usage on schema auth to authenticated;
            create table battle_searches(user_id uuid);
            create table battle_invites(sender uuid, recipient uuid,state text);
            create table study_sessions(user_id uuid, friend_id uuid, partner_id uuid, mode text,
                                        state text, course text, university text);`);
        await db.exec((await sql('profile-schema.sql')).split('insert into storage.buckets')[0]+'commit;');
        await db.exec(await sql('profile-options-update.sql'));
        await db.exec(await sql('graduation-year.sql'));
        await db.query('insert into auth.users values($1),($2)',[owner,peer]);
        await login(owner);
        await db.query('select save_profile_v3($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)',
            ['student','North',['English'],['Law','Finance'],JSON.stringify(avatar),'Avatar',owner+'/a.png','Other','',null]);
        await db.exec('reset role');
        await db.exec(await sql('migrations/20261121180000_course_universities.sql'));
        await db.query('insert into battle_searches values ($1)',[owner]);
        await db.query("insert into battle_invites values ($1,$2,'pending')",[peer,owner]);
        await db.query("insert into study_sessions values ($1,null,null,'random','waiting','Law','North'),($1,null,$2,'random','paired','Law','North')",[owner,peer]);
        await login(owner);
        await assert.rejects(save('North','South',[],3000), /graduation year/);
        assert.deepEqual(await profile(),[{courses:['Law','Finance'],course_history:{}}]);
        await save('North','South',[]);
        await db.close();
        db = new PGlite(dir);
        await login(owner);
        assert.deepEqual(await profile(),[{courses:[],course_history:{North:['Law','Finance']}}]);
        await assert.rejects(save('North','South',['Law']), /university changed/);
        await login(peer);
        assert.deepEqual(await profile(),[]);
        await db.exec('reset role');
        assert.equal((await db.query('select * from battle_searches')).rows.length,0);
        assert.equal((await db.query('select state from battle_invites')).rows[0].state,'cancelled');
        assert.deepEqual((await db.query('select state from study_sessions order by state')).rows.map(r=>r.state),['cancelled','paired']);
        const start = (mode,course) => db.query("insert into study_sessions(user_id,mode,state,university,course) values ($1,$2,'own','South',$3)",[owner,mode,course]);
        await start('solo','Law');
        for (const mode of ['friend','random']) await assert.rejects(start(mode,'Law'),/current university/);
        await login(owner);
        await save('South','South',['Finance']);
        await db.exec('reset role');
        await start('friend','Finance');
        await login(owner);
        await save('South','North',['Law','Finance']);
        assert.deepEqual(await profile(),[{courses:['Law','Finance'],course_history:{South:['Finance']}}]);
        await db.exec('reset role; set role anon');
        await assert.rejects(save('North','South',[]), /permission denied/);
    } finally {
        await db.close();
        await rm(dir,{recursive:true,force:true});
    }
});
