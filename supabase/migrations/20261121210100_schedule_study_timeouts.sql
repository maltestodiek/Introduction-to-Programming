-- Supabase Cron handles deadlines even when the app has no visitors.
begin;
create extension if not exists pg_cron;
select cron.schedule('uniarena-study-timeouts', '* * * * *', 'select public.settle_study_timeouts()');
commit;
