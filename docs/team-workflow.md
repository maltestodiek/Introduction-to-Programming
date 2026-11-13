# Team Git workflow

## What a branch means
A feature is a product capability; a branch is a temporary working copy of the entire repository. Every branch contains the whole app at that point in history, not just one feature. A feature can have several small implementation/fix branches. Naming a branch first-feature does not mean the app only has one feature.

## Stable baseline
Use `main` for the reviewed shared application. It was already GitHub's default branch but had fallen behind the deployed app. The organization update incorporates the deployed history into main without removing prior main commits. The existing open Battle/Study proposal remains a separate team review; it is not silently merged or discarded.

## One task at a time
1. Fetch the latest team work and start from current main with a clean working tree.
2. Write or update the relevant topic spec, keeping Why / What / Out of scope / Done when. For substantial changes, add a focused task under specs/tasks/ and link it to the parent feature.
3. Create a descriptive branch, for example `feature/study-session-filters`, `fix/appearance-contrast`, `feature/social-chat-search` or `docs/project-organization`.
4. Review expected outcomes; write behavioral acceptance tests before implementation. Keep allowed/rejected/restart expectations fixed.
5. Build the task, run relevant checks, inspect the diff and manually verify the workflow.
6. Open a pull request into main, review it, then merge. Do not overwrite other students' commits or force-push shared branches.
7. Release reviewed main to the hosted branch as described below. Begin the next task on a new branch from main.

## Temporary hosting exception
Streamlit currently deploys `app.py` from `first-feature`. Keep this branch as a deployment compatibility pointer only; no new feature work starts there. After main is reviewed, fast-forward the deployment branch to that main commit. If it has diverged, stop and inspect the difference rather than forcing it.

Moving the existing app to main requires a planned Streamlit redeployment; see [deployment](deployment.md). Once migrated, main can deploy directly and the old branch can be retired after checking team dependencies.

## Existing branch names
Old branches such as dark-mode, dark-avatar-background and fix-dark-university-lookup are historical steps within Appearance and Navigation, not three different product features. The same applies to play-mode-buttons/play-mode-design and improve-study-design. Keep their commits and names for now to avoid disrupting teammates' checkouts and open reviews; they do not define the current feature catalogue. Do not squash or rewrite shared history just to rename a feature.

The open `fifth-feature-battle-study-modes` proposal remains untouched. Its descriptive product topic is Battle Mode; its old Study rules were superseded by the approved Study specification. Coordinate with its author before changing its branch or PR.
