-- Review and publication actions for private AI question drafts.
-- Apply after ai-question-generation-no-explanations.sql and study-level-preferences-update.sql.
begin;

create or replace function public.update_ai_question_draft(
  p_draft_id uuid, p_question text, p_options jsonb, p_correct_option_index smallint
) returns jsonb language plpgsql security definer set search_path='' as $$
declare me uuid := auth.uid(); distinct_options integer;
begin
  if me is null then raise exception 'Sign in first'; end if;
  if not exists(select 1 from public.ai_question_drafts where id=p_draft_id and owner_id=me and status='draft') then
    raise exception 'This draft is unavailable';
  end if;
  if coalesce(length(trim(p_question)),0)=0 or jsonb_typeof(p_options) is distinct from 'array' or jsonb_array_length(p_options)<>4 or p_correct_option_index not between 0 and 3 then
    raise exception 'Complete one question, four answers and one correct answer';
  end if;
  if exists(select 1 from jsonb_array_elements(p_options) option_value where jsonb_typeof(option_value) is distinct from 'string' or coalesce(length(trim(option_value #>> '{}')),0)=0) then
    raise exception 'Generated options must be non-empty text';
  end if;
  select count(distinct lower(trim(option_value #>> '{}'))) into distinct_options from jsonb_array_elements(p_options) option_value;
  if distinct_options<>4 then raise exception 'Generated options must be unique'; end if;
  update public.ai_question_drafts set question=trim(p_question),options=p_options,correct_option_index=p_correct_option_index,updated_at=now() where id=p_draft_id and owner_id=me;
  return jsonb_build_object('id',p_draft_id);
end $$;

create or replace function public.discard_ai_question_draft(p_draft_id uuid)
returns void language plpgsql security definer set search_path='' as $$
begin
  if auth.uid() is null then raise exception 'Sign in first'; end if;
  update public.ai_question_drafts set status='discarded',updated_at=now() where id=p_draft_id and owner_id=auth.uid() and status='draft';
  if not found then raise exception 'This draft is unavailable'; end if;
end $$;

create or replace function public.publish_ai_question_drafts(p_draft_ids uuid[])
returns void language plpgsql security definer set search_path='' as $$
declare me uuid := auth.uid(); expected integer;
begin
  if me is null then raise exception 'Sign in first'; end if;
  expected:=coalesce(array_length(p_draft_ids,1),0);
  if expected not between 1 and 100 then raise exception 'Choose between 1 and 100 drafts'; end if;
  update public.ai_question_drafts set status='published',updated_at=now() where owner_id=me and status='draft' and id=any(p_draft_ids);
  if not found or (select count(*) from public.ai_question_drafts where owner_id=me and status='published' and id=any(p_draft_ids))<>expected then raise exception 'One or more drafts are unavailable'; end if;
end $$;

revoke all on function public.update_ai_question_draft(uuid,text,jsonb,smallint), public.discard_ai_question_draft(uuid), public.publish_ai_question_drafts(uuid[]) from public, anon;
grant execute on function public.update_ai_question_draft(uuid,text,jsonb,smallint), public.discard_ai_question_draft(uuid), public.publish_ai_question_drafts(uuid[]) to authenticated;
commit;
