# UniArena Supabase setup

Verified on 11 November 2026:
- Organization: Nova - ITP, Free plan
- Project: StudyDuel (the project name in the Supabase dashboard)
- Project reference: lhqqgyirhtjdwieizxjf
- Project URL: https://lhqqgyirhtjdwieizxjf.supabase.co
- Status: Healthy
- Region: Central EU (Frankfurt)
- Email provider enabled; signups enabled; email confirmation enabled.

For the later public signup, recovery and sign-out results, see the [live account tests from 21 November](verification.md#live-account-tests).

Before live testing:
1. Retrieve the publishable API key; never use a service-role key.
2. Configure the project URL and publishable key in ignored Streamlit secrets.
3. Set the allowed local confirmation destination to the running app URL (planned http://localhost:8501).
4. Verify email delivery configuration and recipient restrictions for testing.
5. Follow docs/verification-proposal.md for signup, confirmation, login, logout, and full restart tests.

Account records belong to Supabase Auth. Do not create a custom password table. No schema migration is needed for this first authentication-only feature.

## Password recovery
Use **Sign in → Forgot password?** and open the newest email in the same browser profile. Supabase redirects to the configured `APP_URL`. Production uses `https://uniarena.streamlit.app` and local development uses `http://localhost:8501`. The requesting browser temporarily keeps the proof for the reset link so the link can open in a new tab. UniArena exchanges the one-time code with Supabase, verifies the user, and opens **Choose a new password**. After updating, sign in with the new password. If the link expired or you switched browsers, request a fresh email in the browser you intend to use.

## Shared university courses
Apply `supabase/university-courses.sql` in the Supabase SQL Editor after the profile migrations. It adds the read-only `university_courses(p_university)` function, which returns the course names saved by students at one university and nothing else. It creates no table and changes no data. Verify with `tests/university_courses_database.mjs`.

## AI question generation
The Edge Function `supabase/functions/extract-image-text` reads the text on Anki card images. It uses the existing secret `REQUESTY_API_KEY` and the optional secret `REQUESTY_VISION_MODEL` (default `openai/gpt-4o-mini`); it stores nothing. Verify with `deno test` in its folder.

Apply `supabase/deck-studio.sql` after `battle-deck-catalog.sql`. It adds `study_decks.created_at` (backfilled from each deck's first review, otherwise left empty) and the read-only `deck_studio()` function that returns the caller's own Study and Battle decks with their times and no questions. Verify with `tests/deck_studio_database.mjs`.

Apply `supabase/study-deck-publication-sort-time.sql` after `study-deck-publication-course-variable.sql`. It adds the public publication timestamp to the already-authorized Study deck listing so the Decks page can sort a course's published Study decks by **Recently added**. It does not expose cards or alter deck visibility. Verify with `tests/study_database.mjs`.

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
