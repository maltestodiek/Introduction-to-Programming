-- Deployment smoke check: reads no application tables and changes no user data.
-- Supabase records this version in its own migration history after success.
SELECT 'studyduel_github_deployment_verified' AS deployment_check;
