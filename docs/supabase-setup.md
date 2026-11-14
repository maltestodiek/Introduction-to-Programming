# StudyDuel Supabase setup

Verified on 11 November 2026:
- Organization: Nova - ITP, Free plan
- Project: StudyDuel
- Project reference: lhqqgyirhtjdwieizxjf
- Project URL: https://lhqqgyirhtjdwieizxjf.supabase.co
- Status: Healthy
- Region: Central EU (Frankfurt)
- Email provider enabled; signups enabled; email confirmation enabled.
- No app connection or live signup test has been completed.

Before live testing:
1. Retrieve the publishable API key; never use a service-role key.
2. Configure the project URL and publishable key in ignored Streamlit secrets.
3. Set the allowed local confirmation destination to the running app URL (planned http://localhost:8501).
4. Verify email delivery configuration and recipient restrictions for testing.
5. Follow docs/verification-proposal.md for signup, confirmation, login, logout, and full restart tests.

Account records belong to Supabase Auth. Do not create a custom password table. No schema migration is needed for this first authentication-only feature.

## Password recovery
The login screen now sends Supabase reset emails. The default Supabase recovery link redirects to http://localhost:8501; keep this URL allowed and the local app running. The app consumes the recovery fragment, removes it from the browser URL, verifies the session with Supabase, and displays the new-password form. Password changes use Supabase Auth only. No real recovery email or account password was changed during automated checks; verify delivery and a complete reset with your own test account. Expired-link UI and token removal were manually verified.

## AI question generation
Apply `supabase/ai-question-generation-schema.sql` in the Supabase SQL Editor after `anki-import-schema.sql`. The SQL creates private AI drafts, validates every save atomically, and adds a per-user generation lock.

Deploy the Edge Function from the repository root:

```sh
supabase functions deploy generate-questions
```

Then set the provider secret in the Supabase Dashboard under Edge Functions → Secrets:

```text
REQUESTY_API_KEY=your-requesty-key
```

The optional `REQUESTY_MODEL` secret overrides the default model (`openai/gpt-4o-mini`). Never place either secret in Git or Streamlit secrets. The function verifies the calling user's JWT and uses that identity to load only the user's private source cards.
