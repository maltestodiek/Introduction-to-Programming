# Working on StudyDuel

Use English for UI, docs and tests. Read docs/product-brief.md, docs/features.md, the relevant named spec from specs/README.md, and its verification notes before implementation. Archived proposals are historical evidence, not current instructions.

Keep the class structure: screens in app.py, business rules in logic.py, database adapters in db.py, tests in tests/, feature plans in specs/, product/verification guidance in docs/. Focused Python helpers may support these files. Use Python, Streamlit, uv and pytest; no React frontend. Supabase Auth, PostgreSQL and private Storage are the approved persistence choice for the shared app; SQLite is only appropriate for isolated local exercises/tests.

Commands: uv sync; uv run pytest -q; uv run streamlit run app.py. On this Mac use sh run-tests.sh and sh run-app.sh when the Desktop environment stalls. SQL checks use tests/*_database.mjs with isolated PGlite; Node is test tooling only. Never use real users, messages or production data in tests. Each persistence test must use a temporary/local database. Reset test data by rerunning the isolated test setup; do not reset production.

Use main as the stable shared baseline. Fetch and check team changes first. Work on a named branch: feature/<topic>, fix/<topic>, or docs/<topic>. The live Streamlit app deploys directly from main. After review and verification, merge into main to release; do not push releases to first-feature. Never force-push, delete team branches or replace a teammate's work. See docs/team-workflow.md.

Every task spec uses Why, What, Out of scope, Done when. Group visual changes under Appearance and Navigation, social changes under Social Connections, and deck/subsection/calculator changes under Deck Authoring. Write behavioral tests first for new workflows, review expected outcomes, and preserve them during implementation. Do not weaken, skip or remove tests to get green output. Correct mistaken expectations explicitly against the approved spec.

Run appropriate tests; check allowed and rejected actions and a full process restart for persistence changes. Review the diff before merging. Report results, changed files and any unverified manual steps accurately. Verify remote ownership and visibility before pushing. Keep secrets, local databases and private student data out of Git. Preserve applied SQL filenames and document a new migration for production schema/rule changes.
