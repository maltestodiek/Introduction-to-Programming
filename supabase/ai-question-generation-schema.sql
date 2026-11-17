-- AI-generated multiple-choice drafts from private source cards.
-- Apply after anki-import-schema.sql. This migration is intentionally separate
-- because the earlier import schema may already be applied in production.
begin;

create table public.ai_question_drafts (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.profiles(id) on delete cascade,
  import_id uuid not null references public.anki_imports(id) on delete cascade,
  source_card_id uuid not null references public.anki_source_cards(id) on delete cascade,
  question text not null check (length(trim(question)) > 0),
  options jsonb not null,
  correct_option_index smallint not null check (correct_option_index between 0 and 3),
  explanation text not null check (length(trim(explanation)) > 0),
  status text not null default 'draft' check (status in ('draft', 'discarded', 'published')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index ai_question_drafts_owner_import_idx
  on public.ai_question_drafts(owner_id, import_id, created_at);

create table public.ai_generation_locks (
  owner_id uuid primary key references public.profiles(id) on delete cascade,
  locked_at timestamptz not null default now()
);

alter table public.ai_question_drafts enable row level security;
alter table public.ai_generation_locks enable row level security;

revoke all on public.ai_question_drafts, public.ai_generation_locks
  from public, anon, authenticated;
grant select on public.ai_question_drafts to authenticated;

create policy ai_question_drafts_owner_read
  on public.ai_question_drafts for select to authenticated
  using (owner_id = auth.uid());

create function public.claim_ai_generation_lock()
returns boolean
language plpgsql security definer set search_path='' as $$
declare me uuid := auth.uid();
begin
  if me is null then raise exception 'Sign in first'; end if;
  delete from public.ai_generation_locks
    where owner_id = me and locked_at < now() - interval '20 minutes';
  insert into public.ai_generation_locks(owner_id)
    values (me)
    on conflict (owner_id) do nothing;
  return found;
end $$;

create function public.release_ai_generation_lock()
returns void
language plpgsql security definer set search_path='' as $$
declare me uuid := auth.uid();
begin
  if me is null then raise exception 'Sign in first'; end if;
  delete from public.ai_generation_locks where owner_id = me;
end $$;

create function public.save_ai_question_drafts(p_import_id uuid, p_drafts jsonb)
returns jsonb
language plpgsql security definer set search_path='' as $$
declare
  me uuid := auth.uid();
  item jsonb;
  source_id uuid;
  question_text text;
  explanation_text text;
  option_values jsonb;
  option_count integer;
  distinct_option_count integer;
  correct_index smallint;
  seen_source_ids uuid[] := '{}';
begin
  if me is null then raise exception 'Sign in first'; end if;
  if not exists (
    select 1 from public.anki_imports
    where id = p_import_id and owner_id = me
  ) then
    raise exception 'This import is unavailable';
  end if;
  if jsonb_typeof(p_drafts) is distinct from 'array'
     or jsonb_array_length(p_drafts) not between 1 and 100 then
    raise exception 'Generate between 1 and 100 questions';
  end if;

  -- Validate every item before inserting any draft.
  for item in select value from jsonb_array_elements(p_drafts) loop
    if jsonb_typeof(item) is distinct from 'object'
       or jsonb_typeof(item->'sourceCardId') is distinct from 'string'
       or jsonb_typeof(item->'question') is distinct from 'string'
       or jsonb_typeof(item->'explanation') is distinct from 'string'
       or jsonb_typeof(item->'options') is distinct from 'array'
       or jsonb_typeof(item->'correctOptionIndex') is distinct from 'number' then
      raise exception 'Generated question has an invalid format';
    end if;

    source_id := (item->>'sourceCardId')::uuid;
    question_text := trim(item->>'question');
    explanation_text := trim(item->>'explanation');
    option_values := item->'options';

    if source_id = any(seen_source_ids) then
      raise exception 'Generated questions must use each source card once';
    end if;
    seen_source_ids := array_append(seen_source_ids, source_id);

    if length(question_text) = 0 or length(explanation_text) = 0
       or jsonb_array_length(option_values) <> 4 then
      raise exception 'Generated question is incomplete';
    end if;
    if exists (
      select 1 from jsonb_array_elements(option_values) option_value
      where jsonb_typeof(option_value) is distinct from 'string'
        or length(trim(option_value #>> '{}')) = 0
    ) then
      raise exception 'Generated options must be non-empty text';
    end if;
    select count(*), count(distinct lower(trim(option_value #>> '{}')))
      into option_count, distinct_option_count
      from jsonb_array_elements(option_values) option_value;
    if option_count <> 4 or distinct_option_count <> 4 then
      raise exception 'Generated options must be unique';
    end if;

    if (item->>'correctOptionIndex') !~ '^[0-3]$' then
      raise exception 'Generated correct option is invalid';
    end if;
    correct_index := (item->>'correctOptionIndex')::smallint;

    if not exists (
      select 1
      from public.anki_source_cards source_card
      join public.anki_imports import_record on import_record.id = source_card.import_id
      where source_card.id = source_id
        and source_card.import_id = p_import_id
        and import_record.owner_id = me
    ) then
      raise exception 'Generated source card is unavailable';
    end if;
  end loop;

  for item in select value from jsonb_array_elements(p_drafts) loop
    insert into public.ai_question_drafts (
      owner_id, import_id, source_card_id, question, options,
      correct_option_index, explanation, status
    ) values (
      me, p_import_id, (item->>'sourceCardId')::uuid, trim(item->>'question'),
      item->'options', (item->>'correctOptionIndex')::smallint,
      trim(item->>'explanation'), 'draft'
    );
  end loop;

  return jsonb_build_object('count', jsonb_array_length(p_drafts));
end $$;

revoke all on function public.claim_ai_generation_lock() from public, anon;
revoke all on function public.release_ai_generation_lock() from public, anon;
revoke all on function public.save_ai_question_drafts(uuid, jsonb) from public, anon;
grant execute on function public.claim_ai_generation_lock() to authenticated;
grant execute on function public.release_ai_generation_lock() to authenticated;
grant execute on function public.save_ai_question_drafts(uuid, jsonb) to authenticated;

commit;
