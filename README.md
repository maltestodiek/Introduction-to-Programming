# UniArena

We built UniArena for students who want to turn their course material into quizzes. You can use the same material to prepare for an exam at your own pace or challenge a classmate. Your decks and progress are saved between visits.

**Open UniArena:** [uniarena.streamlit.app](https://uniarena.streamlit.app/) · [uniarena.net](https://uniarena.net)

## How to play

Create an account with a **personal email address**. Verification emails may not reach NOVA SBE inboxes (`@novasbe.pt`). Once you confirm your email, open **Profile** and add your university, at least one course at that university, and your languages.

In **Play**, choose **Study Mode** to practise alone or with a partner, or **Battle Mode** to compete against another student for XP. Both modes use decks of quiz questions. For Study Mode, create a deck or add a published course deck to your library. In Battle Mode, choose **Random Deck** to let UniArena pick a deck, or **Top Decks** to pick a top-rated deck yourself. Both options use published Battle decks for your university, course and language. With **Random player**, you can start answering while UniArena finds an opponent.

### Decks

A deck is a set of quiz questions for one course. To find one, open **Decks**. Under **Your courses**, choose **Study** on a published deck to save your own copy and open **Study alone**. If your course has no published deck, or you want to practise your own material, choose **Create deck → Create Study Deck**. Add questions with four answer choices, mark the correct answer, then review and save. You can also start from an Anki deck or text-based PDF slides and review the AI-generated drafts.

### Study Mode

Open **Play → Study Mode** with a deck in your library, then choose how you want to practise.

- **Study alone.** Select your course and deck, and choose the whole deck or specific chapters and learning levels. Pick a question count or practise all matching questions. After each answer you see the correct answer and can review it before moving on. Your learning levels are saved for your next session.
- **Study together.** Each student needs a deck for the same course and language at their current university. Choose a friend, look for a random partner, or join an open search. For a 20-question session, each deck needs at least 10 questions. You answer your own 10 first and your partner’s 10 after matching. Both of you answer the same 20 questions, so you can compare scores. Larger sessions follow the same half-from-each-deck rule.

### Battle Mode

You can play your first Battle without creating a deck yourself. Open **Play → Battle Mode → New Battle**, select your course and language, then choose **Random Deck** or **Top Decks**. At least one eligible Battle deck must be available for that combination at your university. If there are none, choose another combination or publish a Battle deck through **Decks → Create deck → Create Battle Mode Deck**.

- **Random player.** Choose **Start random Battle** to answer the 15 questions immediately. You have one hour from the first question. If a compatible player is already waiting, you match immediately. Otherwise UniArena searches for up to 48 hours. After you finish, you can follow the match in **Active battles**. Leaving an unfinished Battle counts as a loss.
- **Friend.** Choose an eligible friend and send a **Battle invitation**. Your friend accepts the invitation to play. Once the outcome is known, **Recent results** shows the score and Battle XP.

### Leaderboard

After a Battle, open **Leaderboard**. **Global top 10** shows the highest-ranked players across UniArena and your own place if you fall outside the top ten. **University top 10** ranks players at the university in your profile. **Friends** shows how you rank among your accepted friends. All three count Battle XP from results settled in the last 30 days. Study sessions earn no Battle XP. You can find your lifetime Battle XP in **Profile**.

### Friends

Open **Friends** and enter a classmate’s friend code, or share your invitation link with them. Once the request is accepted, you can message each other in **Chats** and invite each other to a Study session or Battle when your courses and languages match.

### Study Plan

Open **Study Plan → Create study plan**, choose the courses and decks you want to revise, and enter your exam dates. UniArena spreads your practice across the days available. Open today’s session to work through the scheduled questions and track your progress toward each exam.

**Calendar export.** UniArena's Google Calendar integration uses a Google OAuth app in **Testing**. Only Google accounts the team has added to its test-user list can authorize direct sync. Everyone else can open a saved **Study Plan**, choose **Calendar file**, and import the downloaded `.ics` file on a computer under **Google Calendar → Settings → Import & export**. The file contains the sessions as scheduled when you downloaded it. [Google OAuth testing rules](https://support.google.com/cloud/answer/15549945?hl=en) · [Calendar import instructions](https://support.google.com/calendar/answer/37118?hl=en)

## Team and GitHub contributors

| Team member | Student number | GitHub accounts |
| --- | --- | --- |
| Jan-Malte Stodiek | 83912 | [maltestodiek](https://github.com/maltestodiek), [malte1001](https://github.com/malte1001) |
| Penelope Erhard | 81555 | [8155503](https://github.com/8155503) |
| Paul Timm Kriehuber | 81548 | [PaulNOVA26](https://github.com/PaulNOVA26), [Paulemann187](https://github.com/Paulemann187) |
| Vincent Jonathan Bachmann | 71010 | [VincentBach719](https://github.com/VincentBach719) |

Jan-Malte and Paul also used Claude when they needed additional coding credits. Before they corrected the Git author settings, some of their commits were recorded under the author name **Claude**. [GitHub contributor history](https://github.com/maltestodiek/Introduction-to-Programming/graphs/contributors?all=1)

## Run and test

You can use the hosted app by signing in with a UniArena account. We configure its connection to Supabase for you.

### Run the tests

Anyone can run the automated tests from a clone of this repository. They use test data and simulated services, so you do not need a Supabase account, an API key or a local secrets file. Install [uv](https://docs.astral.sh/uv/getting-started/installation/), open a terminal in the repository root, and run:

```sh
uv sync --locked
uv run pytest -q
```

For the remaining GitHub checks, install Node.js 24 (with npm) and Deno 2.5.6. From the same directory, these macOS/Linux commands install the isolated database engine inside the ignored virtual environment, run the university search and database tests, and run the AI tests with simulated responses. [Test setup and examples](docs/verification.md)

```sh
npm install --prefix .venv/pglite --ignore-scripts --no-audit --no-fund @electric-sql/pglite@0.5.16
export PGLITE_MODULE="$PWD/.venv/pglite/node_modules/@electric-sql/pglite/dist/index.js"
node --test tests/university_picker.mjs
node --test --test-concurrency=2 tests/*_database.mjs
deno test --deny-net supabase/functions
```

### Run the app locally with sign-in and saved decks

For sign-in and saved decks to work locally, your copy needs the URL and publishable key of a Supabase project configured for UniArena. Cloning the repository gives you a settings template with placeholders. Ask our team for the project URL and publishable key for local development. If you already have dashboard access to that project, you can copy both values from **Connect**. The publishable key identifies the app, and each student's sign-in determines which data they can access. [Supabase's guide to API keys](https://supabase.com/docs/guides/getting-started/api-keys)

1. Install the dependencies with `uv sync --locked` if you have not already done so.
2. Copy [the settings template](.streamlit/secrets.toml.example) to `.streamlit/secrets.toml`. Fill in `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` and keep `APP_URL` set to `http://localhost:8501`. Git ignores this local file.
3. From the repository root, run the command below and open [localhost:8501](http://localhost:8501).

```sh
uv run streamlit run app.py
```

## Repository guide

If you contribute to UniArena, open the repository root in your coding tool and have your agent read our project instructions before editing. [AGENTS.md](AGENTS.md)

- [Feature index and current status](docs/features.md)
- [Topic-based specifications](specs/README.md)
- [Current product brief](docs/product-brief.md)
- [Team branch workflow](docs/team-workflow.md)
- [Deployment and storage](docs/deployment.md)
- [External APIs and what to do during an outage](docs/external-apis.md)

## How the stack fits together

- **Python and Streamlit** run the screens on Streamlit Community Cloud. CSS supplies the themes and session animations. Small JavaScript components handle interactions that need the browser, such as avatar swiping and copying a friend invitation link.
- **Supabase** provides login, private file storage and a shared PostgreSQL database. Each player has a separate Streamlit session. SQL checks permissions and applies shared game updates, so a Battle result is available to both players.
- **TypeScript and Deno** power two Supabase Edge Functions. When a student requests AI questions, `db.py` calls `generate-questions` with the selected source card IDs. The function reads the cards with the student's permissions, calls Requesty, validates the questions and saves drafts for review. The second function, `extract-image-text`, returns a transcription of an Anki card image for the student to review. Both functions read the Requesty API key from Supabase secrets. [Function source](supabase/functions) · [Supabase setup](docs/supabase-setup.md)

## Structure

- `app.py`: Streamlit screens and UI orchestration.
- `logic.py`: validation, learning rules, image processing and safe calculator arithmetic.
- `db.py`: authenticated database repositories. Supabase SQL also enforces server-side authorization and transactional multiplayer rules.
- `tests/`: pytest checks, isolated PostgreSQL-compatible checks and SQL acceptance scenarios.
- `specs/`: named feature specifications using Why / What / Out of scope / Done when.
- `docs/`: product, privacy, verification, deployment and team guidance; old proposals are explicitly archived.
- `supabase/`: versioned schema/update scripts. Applied SQL files must not be renamed or blindly rerun.
- `assets/`: images, vector icons and styles.

Focused helpers remain at the root: `auth.py` and `recovery.py` for account access; `launch.py` for welcome/restoration; `appearance.py` for themes; `avatar_picker.py`, `universities.py` and `sharing.py` for their respective UI/services. These modules support the Streamlit interface.

## Data and verification

**Database administrator:** Jan-Malte Stodiek coordinates and reviews changes to the UniArena database structure.

- **Where is my data stored?** Supabase Auth manages accounts, PostgreSQL stores profiles, decks, answers, messages and plans, and private Supabase Storage holds uploaded profile photos. The browser remembers the session and navigation. These records survive a Streamlit restart. [Deployment and storage](docs/deployment.md) · [Session restoration](docs/launch-and-resume.md)
- **What do the tests cover?** The automated suites exercise screens, quiz rules, database permissions and rejected actions, including duplicate requests and expired matches. They use fictional students and simulated providers. Real inbox delivery, Google consent, live model responses, usability and class-sized load are outside those automated checks. The verification guide records which workflows we also exercised on the public app. [Test coverage and live results](docs/verification.md)
- **What if a service is unavailable?** You can type a university manually, download a calendar file, or write questions yourself if the corresponding service is down. A full Supabase outage blocks sign-in and saving. Email delivery problems can delay verification and recovery. [Fallbacks for each external service](docs/external-apis.md)

## Branches

`main` is the shared stable baseline. Start each change on a descriptive short-lived branch such as `feature/study-session-filters` or `fix/appearance-contrast`, review it and merge it into `main`. Streamlit deploys `app.py` directly from `main`. Merging a reviewed change into `main` updates the live app; no push to `first-feature` is needed. See [workflow](docs/team-workflow.md) and [deployment](docs/deployment.md).
