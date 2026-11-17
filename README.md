# StudyDuel

StudyDuel is a Python/Streamlit app for creating course decks, studying alone or together, and connecting with classmates. Supabase provides authentication, shared PostgreSQL data and private image storage. The live app is [studyduel-nova-main.streamlit.app](https://studyduel-nova-main.streamlit.app/).

## Start here

- [Feature index and current status](docs/features.md)
- [Topic-based specifications](specs/README.md)
- [Current product brief](docs/product-brief.md)
- [Team branch workflow](docs/team-workflow.md)
- [Deployment and storage](docs/deployment.md)
- [Project instructions](AGENTS.md)

## Run and test

Use `uv sync`, `uv run pytest -q` and `uv run streamlit run app.py`. Open http://localhost:8501.

On this Mac, `sh run-app.sh` and `sh run-tests.sh` use the locked dependencies with an environment/cache under `~/Library/Caches/StudyDuel`, avoiding the stalled Desktop environment. Teammates copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and configure their approved Supabase URL and publishable key. Never commit the filled secrets file.

## Lecture structure

- `app.py`: Streamlit screens and UI orchestration.
- `logic.py`: validation, learning rules, image processing and safe calculator arithmetic.
- `db.py`: authenticated database repositories. Supabase SQL also enforces server-side authorization and transactional multiplayer rules.
- `tests/`: pytest checks, isolated PostgreSQL-compatible checks and SQL acceptance scenarios.
- `specs/`: named feature specifications using Why / What / Out of scope / Done when.
- `docs/`: product, privacy, verification, deployment and team guidance; old proposals are explicitly archived.
- `supabase/`: versioned schema/update scripts. Applied SQL files must not be renamed or blindly rerun.
- `assets/`: images, vector icons and styles.

Focused helpers remain at the root: `auth.py` and `recovery.py` for account access; `launch.py` for welcome/restoration; `appearance.py` for themes; `avatar_picker.py`, `universities.py` and `sharing.py` for their respective UI/services. They support the lecture's separation without introducing React or another frontend framework.

## What works now

Accounts and profiles, friends and invitations, private chat, flexible reviewed decks with subsections/calculator permissions, solo and asynchronous Together Study, learning progress, fixed shared deck copies, session history and light/dark appearance. AI and Anki import, Leaderboard, Study Plan and the redesigned Battle Mode are placeholders. Saved classic duels can still be resumed/reviewed; they are distinct from the future Battle Pool design.

## Data and verification

Supabase stores durable user data; Streamlit's local disk is not the shared production database. SQLite was the lecture starting point, but the group chose Supabase for shared accounts and multiplayer. Browser storage retains verified session tokens and minimal navigation state, never passwords. See [restoration](docs/launch-and-resume.md) and [profile privacy](docs/profile-requirements.md).

Python tests use temporary files/databases or fake providers. The `tests/*_database.mjs` scripts run actual SQL in isolated PGlite instances, with `PGLITE_MODULE` pointing to an installation of `@electric-sql/pglite@0.5.16`. Node is test tooling only. Never run acceptance tests against real students or production conversations. For features that store data, check an allowed action, a rejected action and a full process restart; browser refresh alone is insufficient.

## Branches

`main` is the shared stable baseline. Start each change on a descriptive short-lived branch such as `feature/study-session-filters` or `fix/appearance-contrast`, review it and merge it into `main`. Streamlit deploys `app.py` directly from `main`. Merging a reviewed change into `main` updates the live app; no push to `first-feature` is needed. See [workflow](docs/team-workflow.md) and [deployment](docs/deployment.md).
