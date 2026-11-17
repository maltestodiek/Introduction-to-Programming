# Hosting, durable storage and releases

## Current deployment
The app is https://studyduel-nova-main.streamlit.app/. Streamlit Community Cloud runs `app.py` from `maltestodiek/Introduction-to-Programming`, branch `main`, with Python 3.13 and dependencies from pyproject.toml/uv.lock.

Merge reviewed and verified task branches into main to deploy. The previous first-feature branch is no longer a hosting dependency. Do not push releases there.

## Migration record — 13 November 2026
A replacement app was deployed from main and started at a temporary preview URL. After startup, the previous deployment moved to a temporary fallback URL and the main deployment took over studyduel-nova.streamlit.app. The same Supabase URL/publishable key and public APP_URL were configured. No database migration or data reset was performed. The initially transferred URL later stalled before the embedded app loaded; see the repair below.

For future source-coordinate changes, see Streamlit's [official instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/rename-your-app). Prepare and verify a replacement before retiring a running deployment. Obtain explicit confirmation before permanently deleting a hosted app.

## Secrets and persistence
Configure SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY and APP_URL in Streamlit secrets; APP_URL must be the assigned HTTPS URL. Supabase Auth Site URL and allowed redirects must match the deployed app and approved local development URL. Never commit secrets.toml, database passwords, service-role keys, private student data or local databases.

Supabase stores accounts, profiles/images, friendships, decks, progress, sessions and messages independently of Streamlit's temporary disk. Restarting/redeploying Streamlit must not reset those records. Browser storage is limited to the documented session restoration behavior; it is not the shared database.

## Database changes
The SQL files in supabase/ are versioned setup and incremental update scripts. Many are already applied and some are not safe to rerun. Preserve filenames, review the exact migration and apply only the missing change. Never infer the production migration state merely from file existence. Tests use isolated databases; no production reset or data deletion is part of deployment.

## Public URL repair — 13 November 2026
The transferred studyduel-nova.streamlit.app address stayed on the outer loading spinner. Rebooting reached the manager startup stage without exposing a Python exception. The same main deployment loaded normally at a temporary alternate address, while reassigning the old address still failed. This points to a hosting-route problem; the provider-internal cause was not confirmed.

The working permanent URL is now https://studyduel-nova-main.streamlit.app/. APP_URL and PUBLIC_APP_URL in hosting configuration, Supabase Site URL, and the exact root/invitation redirects were updated. Localhost development remains allowed. Old public redirects were removed. Accounts, credentials, decks, messages and database tables were not changed. Users must sign in at the new origin; existing bookmarks and previously shared invitation URLs need the new hostname (the invitation token itself is unchanged). Request a fresh confirmation/recovery email if an old email points to the retired hostname.

Verification: the welcome and sign-in screens load at the new URL, including a fresh reload. No application code change was needed; real email delivery and a signed-in session at the new origin remain user checks.
