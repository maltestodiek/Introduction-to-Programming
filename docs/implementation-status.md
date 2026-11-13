# Current implementation and verification

As of 13 November 2026, the live app includes profiles/authentication, friends, private chat, deck authoring, Study Mode, learning progress, calculator permissions and adaptive appearance/navigation. See [features](features.md) for ownership and explicit placeholders.

The chronological [implementation journal](archive/implementation-journal.md) preserves prior test runs and original limitations. Its early phrases such as not deployed or later feature describe that point in time, not today's status.

## Latest social checks
Three chat UI checks pass, including failed-send draft retention, participant menus and friendship states inside chat. Isolated database checks cover historical Study/Battle partner requests, existing-chat requests, stranger rejection, required acceptance, duplicate protection and request rate limits. Chat database tests additionally cover participant-only access, idempotent sends, history pagination/read markers and a separate-process restart. No real-user message was sent during these tests.

## Organization change
Named topic specs replace chronological filenames. Related appearance work is one feature; friends and chat are one feature; subsections and the calculator belong to Deck Authoring. Historical proposals and applied SQL filenames are preserved. Runtime application files, data and dependencies are unchanged by this cleanup.

## Remaining manual acceptance
The group should verify email confirmation/recovery delivery and multi-account workflows using their own authorized test accounts. The current signed-in account has no historical completed sessions, so live history verification showed its empty state; isolated UI tests cover populated history. A clearly labelled demo_alex conversation demonstrates chat and does not represent a real student.

Organization verification: `sh run-tests.sh -q` passed all 151 existing Python checks. Current-document relative links and the six specifications’ required lecture headings were checked; `git diff --check` passed. No runtime source, schema, asset or dependency change is part of the organization commit.
