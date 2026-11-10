# Working on StudyDuel

Use English for the interface, documentation, and tests. Read docs/product-brief.md, specs/first-feature.md, and docs/verification-proposal.md before implementation. The group explicitly chose the class stack over the source document’s React recommendation. This is planning only until the first feature and expected test outcomes are reviewed.

For the class release, use uv with Python, Streamlit, SQLite, and pytest. Planned commands once implemented: uv sync, uv run pytest -q, and uv run streamlit run app.py. Put screens in app.py, business rules in logic.py, persistence in db.py, and tests in tests/. Use a temporary database per persistence test.

Start with a reviewed planning commit on main. Verify the remote and repository visibility before pushing. Create first-feature for implementation. Write the tests first, review expected outcomes with the group, then implement only this workflow. Do not weaken, skip, or remove tests to pass. Correct an incorrect expectation explicitly against the brief. Report test output and changed files. Manually check acceptance, rejection, and a full process restart. Review the diff before merging. Do not commit local databases, private student data, or secrets.
