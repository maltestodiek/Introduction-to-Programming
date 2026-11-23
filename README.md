# UniArena

We built UniArena for students who want to turn their course material into quizzes. You can use the same material to prepare for an exam at your own pace or challenge a classmate. Your decks and progress are saved between visits.

**Open UniArena:** [uniarena.streamlit.app](https://uniarena.streamlit.app/) · [uniarena.net](https://uniarena.net)

## How to play

Create an account with a **personal email address**. Verification emails may not reach NOVA SBE inboxes (`@novasbe.pt`). Once you confirm your email, open **Profile** and add your university, at least one course at that university, and your languages.

In **Play**, choose **Study Mode** for untimed practice alone or with a partner, or **Battle Mode** for a timed, 15-question competition that awards Battle XP. To study, you need a Study deck in your library. To play a Battle, you can use a Battle deck someone at your university has already published.

### Decks

**Create a Study deck.** Open **Decks → Study deck** and choose where your questions will come from.

- **From scratch → Write questions.** Name your deck, select its course and language, then write a question with four answer choices and mark the correct one. Give it a subsection such as “Lecture 2” if you want to practise that lecture separately. For a calculation, tick **Allow calculator for this question**. Add up to 100 questions in total. Choose **Review Study deck**, check the questions and solutions, then **Confirm and save Study deck**.
- **From Anki cards → Import Anki deck.** Upload your Anki deck, preview the cards and save the source material. Select the cards you want UniArena to turn into multiple-choice questions. Check the wording, answer choices and correct answer of each AI draft, choose which drafts to include, then publish the reviewed selection as a Study deck.
- **From PDF slides → Import PDF slides.** Upload a PDF with selectable text and preview what UniArena extracted. Save the material, choose what to generate questions from and review the drafts just as you would for an Anki import. Check the suggested answers against your slides before including them.

**Use or share a Study deck.** If a classmate has already made a deck, open **Decks → Your courses**, find the published deck and choose **Study** to save a copy and open Study alone. Your own saved Study decks start private. In **Deck studio**, you can edit a deck or choose **Publish** to make it available to students at your university with the matching course and language.

**Create a Battle deck.** Open **Decks → Battle deck → Create Battle Mode Deck**, or open one of your saved Study decks and choose **Publish as Battle deck**. Select exactly 15 questions from that deck, name the Battle deck, confirm that other players can use it and choose **Submit Battle Deck**. This is the step that makes questions eligible for **Random Deck** and **Top Decks**, including questions originally imported from Anki or PDF. The published 15 questions stay fixed when you edit the original Study deck.

### Study Mode

Open **Play → Study Mode**. Both options give feedback after each answer and let you choose when to move to the next question. Study sessions track learning progress and award no Battle XP.

#### Study alone

1. Choose **Study alone → Create a new study session**, then select your course and deck. Leave chapters empty to use the whole deck, or pick one or more lectures.
2. Choose the learning levels you want to practise. **New** (grey) means unanswered. **Needs practice** (red) means you have answered the question and it is at level zero. A correct answer moves it up one level: **Level 1** (orange), **Level 2** (yellow), then **Level 3** (green). A wrong answer moves it down one level, to a minimum of zero. You can combine levels, for example to practise new questions alongside ones you missed.
3. Pick a number of questions or **All matching questions**. Questions appear once per session, without a timer. After answering, check the solution before selecting **Next question**. Use **Save and leave** to pause and return through **Continue session**.

#### Study together

1. Choose **Study together → Create a new study session**. Select your deck and a total of **20, 40, 60, 80 or 100 questions**. Each player contributes half from a different deck for the same university, course and language. For 40 questions, both decks need at least 20. Learning levels guide the choice from your deck. If only 15 questions match your chosen levels, UniArena fills the remaining five from the same deck.
2. Choose an eligible **Friend**, opt in to **Random player**, or join an open search for the session size you want. You can answer your own half straight away. A friend receives the invitation once you finish that half. A random search pairs students who have both opted in.
3. After matching, answer your partner’s half. Both players answer the same combined set, so the final scores are comparable. Finishing both halves earns you a full copy of your partner’s deck as it was when they started. Later edits stay with the author. Your partner earns your deck by finishing their own session.
4. Under **Study sessions**, **Your turn** means you have questions to answer. **Waiting** means you are waiting for a match, an invitation response or your partner’s result. **Completed** holds the final results. An unmatched search stays open for 48 hours after you finish your half. Once matched, both players have 48 hours to finish. **Save and leave** pauses your session. **Stop session** frees your place immediately. Stopping or timing out after matching counts as a loss for the unfinished player, who does not earn the partner’s deck.

### Battle Mode

1. **Choose the deck.** Open **Play → Battle Mode → New Battle**, then pick a course and language. **Random Deck** chooses an eligible published Battle deck at your university. **Top Decks** lets you choose from the highest-rated eligible decks. If none are available, choose a different course or language, or publish a Battle deck using the steps above.
2. **Choose your opponent.** With **Random player**, select **Start random Battle** to begin immediately. UniArena matches you with a compatible waiting player or keeps the search open for up to 48 hours. With **Friend**, choose an eligible classmate and send a **Battle invitation**. They can accept it from their Battle page. Neither player needs to create a personal deck to enter.
3. **Play the round.** Both players answer the same 15 questions from one deck. Each question has a **30-second timer**, and each player has **one hour** from opening their first question to finish the round. A correct answer scores one point. If your connection drops, reopen the Battle before your deadline. The clock keeps running. Confirming **Leave and lose** ends your round immediately and records a loss, even if you are still waiting for a random opponent.
4. **Find the result.** **Battle invitations** holds unanswered friend invitations. **Active battles** includes rounds you can play and finished rounds still waiting for a match or an opponent to finish. Once the outcome is known, **Recent results** shows the score and Battle XP. A finished random round that finds no opponent within 48 hours expires without XP. After playing someone else’s deck, you can rate it to help other students choose from **Top Decks**.

### Leaderboard

After a Battle, open **Leaderboard**. **Global top 10** shows the highest-ranked players across UniArena and your own place if you fall outside the top ten. **University top 10** ranks players at the university in your profile. **Friends** shows how you rank among your accepted friends. All three count Battle XP from results settled in the last 30 days. Study sessions earn no Battle XP. You can find your lifetime Battle XP in **Profile**.

### Friends

Open **Friends** and enter a classmate’s friend code, or share your invitation link with them. Once the request is accepted, you can message each other in **Chats** and invite each other to a Study session or Battle when your courses and languages match.

### Study Plan

Open **Study Plan → Create study plan**, choose the courses and decks you want to revise, and choose a target date for each course. This is the last day you want to study. UniArena spreads your practice across the days available. Open today’s session to work through the scheduled questions and track your progress toward each exam.

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
