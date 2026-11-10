# StudyDuel

A class project for creating course quiz decks and playing asynchronous study duels.

## Current status

Planning only. The English product brief is in docs/product-brief.md, the proposed first workflow in specs/first-feature.md, and proposed tests in docs/verification-proposal.md. The feature checklist is in docs/features.md. The original concept is retained in docs/source/. There is no running app yet.

The first proposed feature lets a demo student create exactly 15 complete questions, review and confirm the deck, and reopen it after restarting the app. Review the plan and expected outcomes before implementation.

## Structure

- app.py — Streamlit screens
- logic.py — business rules
- db.py — SQLite persistence
- tests/ — pytest tests
- docs/ — product brief, source, and verification proposal
- specs/ — task specifications
- AGENTS.md — class workflow and verification rules

## Planned commands

Use Python, Streamlit, SQLite, pytest, and uv. Dependencies and application code are not implemented yet.

Once implemented:
- uv sync
- uv run pytest -q
- uv run streamlit run app.py
