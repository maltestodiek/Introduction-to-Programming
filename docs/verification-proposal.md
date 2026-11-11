# Login acceptance review

These are proposed expectations for review before implementation. The draft tests in tests/test_auth_acceptance.py intentionally target a not-yet-implemented AuthService in auth.py. They have not been run and are not passing test evidence.

## Files
app.py: authentication, profile setup, and profile display/editing.
logic.py: input checks.
auth.py: Supabase Auth adapter and per-session authentication service.
db.py: Supabase profile persistence and privacy-safe reads; no password or token storage.
tests/test_auth_acceptance.py: fake-provider acceptance cases.
tests/test_auth_ui.py: to be written after approval; missing configuration, confirmation prompt, password field clearing, logout and separate Streamlit sessions.
pyproject.toml/uv.lock: dependencies added after review.
docs/supabase-setup.md: project and manual verification instructions.

## Review checklist
- Signup pending email confirmation never authenticates.
- Wrong credentials and provider errors never reveal raw error details or authenticate.
- Blank input and password mismatch never call the provider.
- Session presence alone is insufficient; identity must be verified remotely.
- Two service/session instances cannot share auth state.
- Sign-out removes local identity even if provider sign-out fails.
- A restart clears login state but leaves the Supabase account usable.
- Use one auth client per Streamlit session, not a shared cached client.
- Draft tests use no real project or emails.

## Live verification after implementation
Configure a dedicated Supabase project, email/password provider and confirmation. Set localhost redirect URL. Check email delivery settings before signup; the default email sender has recipient/rate restrictions, so team-wide testing may require custom SMTP.
Register a user with their own email, complete confirmation, sign in, try wrong credentials, sign out, and repeat after stopping and restarting Streamlit. Use a second independent browser session to check identity separation. Report live checks separately from automated tests.

## Sources
- https://supabase.com/docs/reference/python/auth-signup
- https://supabase.com/docs/reference/python/auth-signinwithpassword
- https://supabase.com/docs/reference/python/auth-getuser
- https://supabase.com/docs/reference/python/auth-signout
- https://supabase.com/docs/guides/auth/passwords
- https://supabase.com/docs/guides/getting-started/api-keys


## Expanded profile acceptance checks

Preserve the existing auth checks. Extend signup tests to include unique usernames before implementing the expanded workflow; the current draft tests cover authentication only.

Add tests for required university/course/language selections, persistence across fresh connections and restart, default avatar, deterministic customization, cropping, valid/invalid image uploads, active image switching, failed-save preservation, and university changes that invalidate course choices.

Use two authenticated test identities to exercise database and Storage access rules directly. Verify an owner can update only permitted profile fields, another user sees only allowed profile fields and the active image, and anonymous requests see no profile. Check that private email, course choices, raw avatar settings, and inactive images are inaccessible, not merely hidden by UI controls. Verify profile updates cannot alter XP, streak, or friendships.

These tests are still to be written and run. The original auth draft tests are not sufficient evidence for the expanded profile feature.
