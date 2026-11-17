# Verify GitHub database deployment

## Why
Confirm the connected GitHub main branch actually deploys migrations to Supabase.

## What
Add a single constant SELECT migration under supabase/migrations. Verify it locally,
merge through a reviewed PR, and inspect the production migration history.
Disable seeding and leave production configuration managed by the dashboard.

## Out of scope
No reads or writes to application records, schema changes, authentication changes,
resets, seed data, or replay of the existing SQL scripts in supabase/.
This does not establish a complete schema baseline for fresh databases.

## Done when
The constant SELECT succeeds locally. GitHub reports a successful Supabase deployment,
and the exact migration version appears in the live migration history. The migration
contains no application-data or schema mutations; only deployment metadata is recorded.
