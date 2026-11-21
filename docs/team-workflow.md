# Team Git workflow

## Switching coding agents

1. Open your UniArena clone or worktree in the coding tool. If you are unsure which folder is open, run `git rev-parse --show-toplevel` and open the folder it prints. The instructions at its root should be headed **Working on UniArena**. Have the incoming agent read them before editing. [AGENTS.md](../AGENTS.md)
2. Keep one active coding agent per working folder. To work in parallel, use separate clones or Git worktrees, each on its own branch.
3. When handing over the same folder, stop the outgoing agent, inspect `git diff` and the staged changes, and commit the reviewed work. Give the incoming agent the branch, commit, last test results and any unfinished work.

## Coordinating shared files

Use one GitHub issue per feature or bug. Before starting, claim the issue and link the relevant spec. The assignee coordinates the feature from screen to storage and links the pull request to the issue.

- For `app.py` and `AGENTS.md`, the issue assignee coordinates the sections their change touches. Name the screen, function or rule in the issue. If another open issue or PR touches the same section, agree with its owner on who edits it first and pull the merged change before continuing.
- Jan-Malte Stodiek coordinates changes to the Supabase schema and shared data formats. Bring proposed table, migration or data-contract changes to him while planning the issue.

## When main breaks

1. Whoever spots a new failure on `main` opens or updates a GitHub issue with the commit, the failing test or public-app steps, the expected result and the actual result. Check existing issues for previously reported failures.
2. Pause unrelated merges while the new regression is investigated. The person who merged the change coordinates recovery. If the responsible change is unclear, the reporter coordinates until someone takes over in the issue.
3. Reproduce the failure and submit a focused fix or a PR reverting the responsible change. Coordinate any database recovery with Jan-Malte before changing shared data.
4. After merging the recovery, rerun the failing check on `main` and check the affected workflow on the public app if it was impacted. Record the results in the issue, then resume unrelated merges.

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
6. Open a pull request into main. The person merging checks the diff and test results. Peer review is optional. Do not overwrite other students' commits or force-push shared branches.
7. Streamlit deploys the merged main commit automatically. Check the live app, then begin the next task on a new branch from main.

## Hosting from main
Streamlit deploys `app.py` directly from `main` at https://uniarena.streamlit.app/ (https://uniarena.net forwards there). The address changed on 18 November 2026; the Supabase connection is the same. There is no deployment dependency on `first-feature` and no extra release push to it.

## Existing branch names
Old branches such as dark-mode, dark-avatar-background and fix-dark-university-lookup are historical steps within Appearance and Navigation, not three different product features. The same applies to play-mode-buttons/play-mode-design and improve-study-design. Keep their commits and names for now to avoid disrupting teammates' checkouts and open reviews; they do not define the current feature catalogue. Do not squash or rewrite shared history just to rename a feature.

The open `fifth-feature-battle-study-modes` proposal remains untouched. Its descriptive product topic is Battle Mode; its old Study rules were superseded by the approved Study specification. Coordinate with its author before changing its branch or PR.
