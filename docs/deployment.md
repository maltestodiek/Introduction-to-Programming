# Hosting, durable storage and releases

## Current deployment
The app is https://studyduel-nova.streamlit.app/. Streamlit Community Cloud runs `app.py` from `maltestodiek/Introduction-to-Programming`, branch `main`, with Python 3.13 and dependencies from pyproject.toml/uv.lock.

Merge reviewed and verified task branches into main to deploy. The previous first-feature branch is no longer a hosting dependency. Do not push releases there.

## Migration record — 13 November 2026
A replacement app was deployed from main and started at a temporary preview URL. After startup, the previous deployment moved to a temporary fallback URL and the main deployment took over studyduel-nova.streamlit.app. The same Supabase URL/publishable key and public APP_URL were configured. No database migration or data reset was performed. Existing production redirect URLs remain valid because the public URL is unchanged.

For future source-coordinate changes, see Streamlit's [official instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/rename-your-app). Prepare and verify a replacement before retiring a running deployment. Obtain explicit confirmation before permanently deleting a hosted app.

## Secrets and persistence
Configure SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY and APP_URL in Streamlit secrets; APP_URL must be the assigned HTTPS URL. Supabase Auth Site URL and allowed redirects must match the deployed app and approved local development URL. Never commit secrets.toml, database passwords, service-role keys, private student data or local databases.

Supabase stores accounts, profiles/images, friendships, decks, progress, sessions and messages independently of Streamlit's temporary disk. Restarting/redeploying Streamlit must not reset those records. Browser storage is limited to the documented session restoration behavior; it is not the shared database.

## Database changes
The SQL files in supabase/ are versioned setup and incremental update scripts. Many are already applied and some are not safe to rerun. Preserve filenames, review the exact migration and apply only the missing change. Never infer the production migration state merely from file existence. Tests use isolated databases; no production reset or data deletion is part of deployment.
