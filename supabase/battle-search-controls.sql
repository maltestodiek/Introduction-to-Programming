-- Controls and cleanup for pending random Battle searches.
-- Apply after battle-deck-availability.sql.
begin;

create or replace function public.cancel_battle_search()
returns jsonb language plpgsql security definer set search_path='' as $$
declare me uuid:=auth.uid(); cancelled boolean:=false;
begin
 if me is null then raise exception 'Sign in first'; end if;
 delete from public.battle_searches where user_id=me returning true into cancelled;
 return jsonb_build_object('cancelled',coalesce(cancelled,false));
end $$;

create or replace function public.expire_battle_searches()
returns jsonb language plpgsql security definer set search_path='' as $$
declare expired integer;
begin
 delete from public.battle_searches where expires_at<=now();
 get diagnostics expired=row_count;
 return jsonb_build_object('expired',expired);
end $$;

revoke all on function public.cancel_battle_search(),public.expire_battle_searches() from public,anon,authenticated;
grant execute on function public.cancel_battle_search() to authenticated;

-- Supabase projects with pg_cron enabled remove expired searches every minute,
-- including while no student has the app open. The UI also removes its own
-- expired card immediately through the server-owned status check.
do $$
declare already_scheduled boolean;
begin
 if exists(select 1 from pg_extension where extname='pg_cron') then
  execute 'select exists(select 1 from cron.job where jobname=''expire-battle-searches'')' into already_scheduled;
  if not already_scheduled then
   execute format('select cron.schedule(%L,%L,%L)',
    'expire-battle-searches','* * * * *','select public.expire_battle_searches()');
  end if;
 end if;
end $$;
commit;
