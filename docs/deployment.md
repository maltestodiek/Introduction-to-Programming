# Hosting, durable storage and releases

## Current deployment
Open [uniarena.net](https://uniarena.net) to reach [the hosted UniArena app](https://uniarena.streamlit.app/). Streamlit Community Cloud runs `app.py` from `maltestodiek/Introduction-to-Programming`, branch `main`, with Python 3.13 and dependencies from pyproject.toml/uv.lock.

Merge reviewed and verified task branches into main to deploy. The previous first-feature branch is no longer a hosting dependency. Do not push releases there.

## Migration record — 13 November 2026
A replacement app was deployed from main and started at a temporary preview URL. After startup, the previous deployment moved to a temporary fallback URL and the main deployment took over studyduel-nova.streamlit.app. The same Supabase URL/publishable key and public APP_URL were configured. No database migration or data reset was performed. The initially transferred URL later stalled before the embedded app loaded; see the repair below.

For future source-coordinate changes, see Streamlit's [official instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/rename-your-app). Prepare and verify a replacement before retiring a running deployment. Obtain explicit confirmation before permanently deleting a hosted app.

## Secrets and persistence
Configure SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY and APP_URL in Streamlit secrets; APP_URL must be the assigned HTTPS URL. Supabase Auth Site URL and allowed redirects must match the deployed app and approved local development URL. Never commit secrets.toml, database passwords, service-role keys, private student data or local databases.

Supabase stores accounts, profiles/images, friendships, decks, progress, sessions and messages independently of Streamlit's temporary disk. Restarting/redeploying Streamlit must not reset those records. Browser storage is limited to the documented session restoration behavior; it is not the shared database.

### If a credential leaks

1. Immediately tell the teammate who manages the issuing provider which credential was exposed, where and when. Identify it by service and setting name. Keep the value private. The owner revokes the exposed credential at the provider immediately and creates a replacement. Removing a post or Git commit alone leaves copied credentials usable.
2. Update each place that uses the credential, including the team password manager and any affected local configuration. Use these destinations for the hosted app.

   | Exposed credential | Where to revoke and replace it | Where UniArena reads the replacement |
   | --- | --- | --- |
   | Requesty API key | Requesty workspace, through the teammate who owns it | Supabase Edge Function secret `REQUESTY_API_KEY` |
   | Google OAuth client secret | Google Cloud project for Calendar sync | Streamlit Community Cloud Secrets and local `.streamlit/secrets.toml` for developers using Calendar sync |
   | Resend SMTP credential | Resend account for the sending domain | Supabase Auth custom SMTP password |
   | Supabase privileged key or database password | Supabase project, coordinated by Jan-Malte Stodiek | Each authorized administrative tool or deployment job that uses it. The Streamlit app uses the publishable key. |

3. Check provider access, usage and billing records from the earliest possible exposure through revocation. Investigate unexpected requests, email sends or database access with the provider owner. Verify the affected feature with a demo account and record the outcome without credentials or private student data.
4. Remove exposed copies from the repository, issues, logs or shared media where possible. Coordinate any Git history cleanup with the team so other clones and branches are accounted for.

### Sharing credentials and presenting UniArena

Give teammates individual provider access with the minimum permissions their task needs. When a credential must be shared, use a password-manager item restricted to those teammates. Use setting names and placeholders in GitHub, chat, coding-agent prompts, logs and screenshots.

For the presentation, use a demo account with fictional data and share the app window. Close provider dashboards, terminals displaying configuration, inboxes and the password manager before sharing. To explain configuration, show the [committed secrets template](../.streamlit/secrets.toml.example). If a credential appears on screen or in a recording, stop sharing and follow the leak response above.

## Database changes
The SQL files in supabase/ are versioned setup and incremental update scripts. Many are already applied and some are not safe to rerun. Preserve filenames, review the exact migration and apply only the missing change. Never infer the production migration state merely from file existence. Tests use isolated databases; no production reset or data deletion is part of deployment.

## Public URL repair — 13 November 2026
The transferred studyduel-nova.streamlit.app address stayed on the outer loading spinner. Rebooting reached the manager startup stage without exposing a Python exception. The same main deployment loaded normally at a temporary alternate address, while reassigning the old address still failed. This points to a hosting-route problem; the provider-internal cause was not confirmed.

From 13 to 18 November, the app used `https://studyduel-nova-main.streamlit.app/`. APP_URL and PUBLIC_APP_URL in hosting configuration, Supabase Site URL, and the exact root/invitation redirects were updated. Localhost development remains allowed. Old public redirects were removed. Accounts, credentials, decks, messages and database tables were not changed. Users must sign in at the new origin; existing bookmarks and previously shared invitation URLs need the new hostname (the invitation token itself is unchanged). Request a fresh confirmation/recovery email if an old email points to the retired hostname.

Verification: the welcome and sign-in screens load at the new URL, including a fresh reload. No application code change was needed; real email delivery and a signed-in session at the new origin remain user checks.

## Public URL change — 18 November 2026
The app address is now https://uniarena.streamlit.app/. The domain uniarena.net forwards to it, keeping the path and query, so invitation links can use either address. APP_URL and PUBLIC_APP_URL in the hosting configuration, the Supabase Site URL, and the root/invitation redirects were updated to the new address. The previous studyduel-nova-main address no longer opens the app; bookmarks, shared invitation links and unopened confirmation or recovery emails that point to it need the new hostname or a fresh email. Accounts, decks, messages and database tables were not changed.

Authentication emails are sent through the same mail provider from the uniarena.net domain (DKIM, SPF and DMARC records are set at the domain's DNS). The Google Calendar sign-in must list the new address as an authorised redirect URI in the Google Cloud project.

### Deck Studio migration history repair, 23 November 2026

The production deployment for [PR #152](https://github.com/maltestodiek/Introduction-to-Programming/pull/152) stopped at `20261122220000_study_sessions_per_friend.sql`. The live Study Together function already contained its replacement rule, but the migration history ended at `20261122210000`. Replaying the old migration stopped when it could not find the original rule.

We compared the live function definitions, permissions and Battle search key with the merged SQL. Six updates were already in place. Four still needed to run: the random Study session completion rule (`20261123020000`), personal Studio removal (`20261123030000`), saving published course decks (`20261123040000`) and earned decks with author credits (`20261123100000`). We ran those four updates and reconciled the ten history entries in one transaction on the UniArena production project. Checks before commit compared the resulting functions with the release and verified Studio access permissions.

After commit, a separate read confirmed all ten history entries, the Studio and course-deck functions, signed-in-only Studio access, the completed-session rule and the presence of earned snapshots with an author. For a future manual deployment, record the migration version together with the schema change. If deployment reports an expected rule is missing, compare the live definition and migration history before retrying.
