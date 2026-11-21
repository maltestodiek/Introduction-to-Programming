-- Rank every eligible Battle Deck by its lifetime rating score.
-- Apply after battle-top-decks-immediate.sql; this preserves already-applied migrations.
begin;

do $migration$
declare definition text;
declare patched text;
begin
 select pg_get_functiondef('public.battle_action(text,jsonb)'::regprocedure) into definition;
 patched:=regexp_replace(definition,
  $pattern$elsif p_action='top' then.*?elsif p_action='friend_options' then$pattern$,
  $replacement$elsif p_action='top' then
  if not exists(select 1 from unnest(profile_courses)c where lower(trim(c))=lower(trim(p_data->>'course'))) or not coalesce((p_data->>'language')=any(langs),false) then raise exception 'Choose one of your courses and languages'; end if;
  return jsonb_build_object('decks',coalesce((select jsonb_agg(jsonb_build_object('id',x.id,'name',x.name,'score',x.score,'rating_count',x.rating_count,'creator',x.username) order by x.score desc,x.rating_count desc,x.id) from (select b.id,b.name,coalesce(sum(case r.rating when 'good' then 1 when 'bad' then -1 else 0 end) filter(where coalesce(r.non_scoring,false)=false),0)::integer score,coalesce(count(r.battle_deck_id) filter(where coalesce(r.non_scoring,false)=false),0)::integer rating_count,p.username from public.battle_decks b join public.profiles p on p.id=b.creator_id left join public.battle_ratings r on r.battle_deck_id=b.id where b.university=campus and lower(trim(b.course))=lower(trim(p_data->>'course')) and b.language=p_data->>'language' group by b.id,b.name,p.username order by coalesce(sum(case r.rating when 'good' then 1 when 'bad' then -1 else 0 end) filter(where coalesce(r.non_scoring,false)=false),0) desc,coalesce(count(r.battle_deck_id) filter(where coalesce(r.non_scoring,false)=false),0) desc,b.id limit 10)x),'[]'::jsonb));
 elsif p_action='friend_options' then$replacement$,
  's');
 if patched=definition then
  raise exception 'Cannot install lifetime Top Deck ranking: unexpected battle_action version';
 end if;
 execute patched;
end $migration$;

grant execute on function public.battle_action(text,jsonb) to authenticated;
commit;
