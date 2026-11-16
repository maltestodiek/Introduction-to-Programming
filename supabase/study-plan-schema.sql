-- Study plans. Apply after the profile and Study migrations.
-- Plans and the identifiers of calendar events created for them are private to their owner.
-- Access is only through study_plan_action; no Google token is stored here.
begin;
create table public.study_plans (
 id uuid primary key default gen_random_uuid(),
 owner_id uuid not null references public.profiles(id) on delete cascade,
 plan jsonb not null check(jsonb_typeof(plan)='object'),
 calendar_events jsonb not null default '[]'::jsonb check(jsonb_typeof(calendar_events)='array'),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create index study_plans_owner on public.study_plans(owner_id,created_at);
alter table public.study_plans enable row level security;
revoke all on public.study_plans from public, anon, authenticated;

create function public.study_plan_action(p_action text, p_data jsonb)
returns jsonb language plpgsql security definer set search_path='' as $$
declare me uuid:=auth.uid(); target uuid; item jsonb;
begin
 if me is null or not exists(select 1 from public.profiles where id=me) then return jsonb_build_object('error','Sign in and complete your profile first.'); end if;
 if p_action='list' then
  return jsonb_build_object('plans',coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'plan',p.plan,'calendar_events',p.calendar_events) order by p.created_at) from public.study_plans p where p.owner_id=me),'[]'::jsonb));
 end if;
 if p_action='save' then
  item:=p_data->'plan';
  if jsonb_typeof(item) is distinct from 'object' or length(item::text)>20000 then return jsonb_build_object('error','This study plan could not be saved.'); end if;
  item:=item-'id';
  if p_data?'id' then
   update public.study_plans set plan=item, updated_at=now() where id=(p_data->>'id')::uuid and owner_id=me returning id into target;
   if target is null then return jsonb_build_object('error','This study plan is no longer available.'); end if;
  else
   if (select count(*) from public.study_plans where owner_id=me)>=20 then return jsonb_build_object('error','You can keep at most 20 study plans.'); end if;
   insert into public.study_plans(owner_id,plan) values(me,item) returning id into target;
  end if;
  return jsonb_build_object('id',target);
 end if;
 if p_action='events' then
  item:=p_data->'events';
  if jsonb_typeof(item) is distinct from 'array' or length(item::text)>100000 then return jsonb_build_object('error','The calendar entries could not be recorded.'); end if;
  update public.study_plans set calendar_events=item, updated_at=now() where id=(p_data->>'id')::uuid and owner_id=me returning id into target;
  if target is null then return jsonb_build_object('error','This study plan is no longer available.'); end if;
  return jsonb_build_object('id',target);
 end if;
 if p_action='delete' then
  delete from public.study_plans where id=(p_data->>'id')::uuid and owner_id=me returning id into target;
  if target is null then return jsonb_build_object('error','This study plan is no longer available.'); end if;
  return jsonb_build_object('id',target);
 end if;
 return jsonb_build_object('error','Unknown study plan action.');
end $$;
revoke all on function public.study_plan_action(text,jsonb) from public, anon;
grant execute on function public.study_plan_action(text,jsonb) to authenticated;
commit;
