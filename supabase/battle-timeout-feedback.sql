-- Show a dedicated timeout result before moving on to the next Battle question.
-- This patches the deployed battle_action routine without changing any existing
-- answers, scores, or elapsed-time records.
do $migration$
declare
  definition text;
  old_timeout text := 'if r.question_started is not null and r.question_started+interval ''30 seconds''<=now() and r.cursor<15 and not exists(select 1 from jsonb_array_elements(r.answers)x where (x->>''index'')::int=r.cursor) then update public.battle_rounds set answers=answers||jsonb_build_array(jsonb_build_object(''index'',r.cursor,''answer_id'',null,''correct'',false,''timed_out'',true)),cursor=cursor+1,question_started=null where session_id=s.id and user_id=me returning * into r;end if;';
  new_timeout text := 'if r.question_started is not null and r.question_started+interval ''30 seconds''<=now() and r.cursor<15 and not exists(select 1 from jsonb_array_elements(r.answers)x where (x->>''index'')::int=r.cursor) then idx:=r.cursor;card:=s.cards->idx;update public.battle_rounds set answers=answers||jsonb_build_array(jsonb_build_object(''index'',idx,''answer_id'',null,''correct'',false,''timed_out'',true)),cursor=cursor+1,question_started=null where session_id=s.id and user_id=me returning * into r;if p_action in (''round'',''answer'') then return jsonb_build_object(''state'',''feedback'',''card'',card,''feedback'',jsonb_build_object(''index'',idx,''answer_id'',null,''correct'',false,''timed_out'',true));end if;end if;';
begin
  select pg_get_functiondef('public.battle_action(text,jsonb)'::regprocedure) into definition;
  if position(old_timeout in definition)=0 then
    raise exception 'Cannot install Battle timeout feedback: unexpected battle_action version';
  end if;
  execute replace(definition,old_timeout,new_timeout);
end $migration$;

grant execute on function public.battle_action(text,jsonb) to authenticated;
