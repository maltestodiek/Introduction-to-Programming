-- Reports for individual questions in completed Battle snapshots.
-- Apply after battle-mode-schema.sql and battle-xp-only.sql.
begin;

create table if not exists public.battle_question_reports(
 session_id uuid not null references public.battle_sessions(id) on delete cascade,
 card_index integer not null check(card_index between 0 and 14),
 reporter_id uuid not null references public.profiles(id),
 reason text not null check(reason in ('incorrect_answer','unclear_question','other')),
 note text not null default '' check(char_length(note)<=500),
 created_at timestamptz not null default now(),
 primary key(session_id,card_index,reporter_id)
);
alter table public.battle_question_reports enable row level security;
revoke all on public.battle_question_reports from public,anon,authenticated;

create or replace function public.report_battle_question(
 p_session uuid,p_card_index integer,p_reason text,p_note text default ''
) returns jsonb language plpgsql security definer set search_path='' as $$
declare me uuid:=auth.uid(); battle public.battle_sessions; saved boolean:=false;
begin
 if me is null then raise exception 'Sign in first'; end if;
 if p_card_index not between 0 and 14 then raise exception 'Choose a valid Battle question'; end if;
 if p_reason not in ('incorrect_answer','unclear_question','other') then raise exception 'Choose a report reason'; end if;
 if char_length(coalesce(p_note,''))>500 then raise exception 'Keep the report comment to 500 characters'; end if;
 select * into battle from public.battle_sessions
  where id=p_session and me in(p1,p2) and settled_at is not null;
 if battle.id is null then raise exception 'Reports are available only to participants after the Battle is completed'; end if;
 insert into public.battle_question_reports(session_id,card_index,reporter_id,reason,note)
 values(p_session,p_card_index,me,p_reason,coalesce(p_note,''))
 on conflict do nothing returning true into saved;
 return jsonb_build_object('reported',coalesce(saved,false));
end $$;

revoke all on function public.report_battle_question(uuid,integer,text,text) from public,anon;
grant execute on function public.report_battle_question(uuid,integer,text,text) to authenticated;
commit;
