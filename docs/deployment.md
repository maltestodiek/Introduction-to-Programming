# Hosting, durable storage and releases

## Current deployment
The app is https://studyduel-nova.streamlit.app/. Streamlit Community Cloud runs `app.py` from `maltestodiek/Introduction-to-Programming`, branch `first-feature`, with Python 3.13 and dependencies from pyproject.toml/uv.lock.

`main` is the development team's stable baseline. `first-feature` is retained only as the current host connection. Release reviewed main commits to that branch by fast-forward; never develop new features there or force-push over team work.

## Moving hosting to main
Streamlit identifies an app by repository, branch and entrypoint. Its [official instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/rename-your-app) require deleting and redeploying an app to change those coordinates. Do not rename/delete the connected branch while the current app depends on it.

A separate migration should record current settings privately, confirm the public URL and Supabase redirect requirements, deploy main, restore approved secrets and verify sign-in, recovery, invitations, stored decks, sessions and chat. Obtain approval before deleting the existing hosted app. This organization cleanup does not delete or recreate the hosted application.

## Secrets and persistence
Configure SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY and APP_URL in Streamlit secrets; APP_URL must be the assigned HTTPS URL. Supabase Auth Site URL and allowed redirects must match the deployed app and approved local development URL. Never commit secrets.toml, database passwords, service-role keys, private student data or local databases.

Supabase stores accounts, profiles/images, friendships, decks, progress, sessions and messages independently of Streamlit's temporary disk. Restarting/redeploying Streamlit must not reset those records. Browser storage is limited to the documented session restoration behavior; it is not the shared database.

## Database changes
The SQL files in supabase/ are versioned setup and incremental update scripts. Many are already applied and some are not safe to rerun. Preserve filenames, review the exact migration and apply only the missing change. Never infer the production migration state merely from file existence. Tests use isolated databases; no production reset or data deletion is part of deployment.
