# CLAUDE.md — reddit-market-intel

Modular Python pipeline that scrapes niche subreddits for user complaints and requests, identifies market gaps for SaaS/apps/tools, clusters similar pain points into opportunities, and scores them by potential. Phase: MVP (initial build, untested end-to-end). No LLM API required — regex/heuristic analysis locally, structured exports designed for Claude Code analysis sessions.

## Stack

Python · praw · pandas · scikit-learn · sqlite-utils · click · SQLite

## Layout

```
reddit-market-intel/
├── main.py          ← CLI entry point (click)
├── config.py        ← all tunable params + seed subreddits
├── schema.sql       ← SQLite schema (source of truth for DB structure)
├── requirements.txt
├── scraper/         ← PRAW + JSON API scrapers, rate limiter, comment classifier
├── analysis/        ← classifier, validator, scorer, clustering (TF-IDF)
├── discovery/       ← subreddit finder via sidebar/crosspost parsing
├── storage/         ← SQLite CRUD (db.py)
├── export/          ← markdown opportunity report generator
├── data/            ← SQLite DB (gitignored)
└── tests/
```

## Hard rules

- **Secrets:** Reddit credentials (`REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`) via env vars only. Never commit `.env*` or credentials to git.
- **DB:** all schema changes go through `schema.sql`. No ad-hoc table creation outside migrations.
- **No-auth first:** dual-mode scraper (JSON fallback + PRAW primary). JSON mode must keep working — don't break zero-credential operation.
- **Tests:** colocated in `tests/`. Before shipping any pipeline change, run against a small subreddit (≤50 posts) to verify end-to-end.
- **Config:** all tunable parameters in `config.py`. No magic numbers inline in pipeline code.

## Run

```bash
pip install -r requirements.txt

# Smoke test — scrape without credentials
python main.py scrape --subreddit smallbusiness --limit 10

# Full pipeline
python main.py scrape --category smb_saas --limit 100
python main.py analyze
python main.py export --top 20 --output report.md

# Status check
python main.py status
```

<!-- SHARED-STANDARDS:START — synced across: reddit-market-intel only (single repo) -->

## Tool efficiency discipline

Tool calls are not free. Apply these rules every session — they cut tool count ~50% with no quality loss.

- **Batch reads upfront.** Start of a task: identify every file needed, then Read them in a single parallel tool batch. Sequential reads are the #1 source of bloat.
- **Grep/Glob before Read.** If you don't already know the path, narrow with Grep or Glob first. Don't open files blind.
- **Don't re-read what you already have.** The harness tracks file state. If you Read or Edit'd a file in this session and nothing else has touched it, you have it — don't re-Read to "verify."
- **No verification reads after Edit/Write.** Both fail loudly if `old_string` doesn't match. A successful tool result IS the verification. Skip the follow-up Read.
- **Combine Edits where possible.** Multiple edits in the same file can often be one Edit with a larger `old_string`/`new_string`, or `replace_all: true` for a rename.
- **Targeted Reads for large files.** Use `offset`/`limit` instead of grabbing the first 2000 lines.
- **Delegate breadth to subagents.** Single grep → main thread. 3+ query exploration → read-only explore subagent. Multi-file edit → builder subagent. Diff review → reviewer subagent. Subagents protect main context.
- **Plan tool batches.** Before invoking: can these go parallel? Are any redundant? Edits are sequential by necessity; Reads/Greps/Globs aren't.

Bad: 8 sequential `Read` calls to load context. Good: 1 message with 8 parallel `Read` calls.

## Plan mode gate

Before writing code for any task that meets one or more of these conditions, enter plan mode first — describe the approach, surface risks, get explicit approval before touching files:

- **3+ files will change** (not counting tests or docs)
- **New feature** (not a bug fix or mechanical refactor)
- **Irreversible or hard-to-reverse changes:** schema migrations, auth refactors, payment flows, data model changes, environment config, CI/CD changes
- **Cross-cutting:** changes that touch multiple layers (DB + API + UI) or multiple services
- **First-of-its-kind in this codebase:** no existing pattern to follow

In plan mode: write the approach as bullet points — what files change, what the new behavior is, what could break, what approaches were rejected and why. Don't write code until the plan is approved.

Skip plan mode for: bug fixes under 3 files, test additions, doc updates, mechanical renames, formatting, dependency bumps with no API changes.

## Model selection heuristic

**Default:** smaller/faster model for CRUD, UI, forms, boilerplate, mechanical refactors, test expansion, schema additions. Switch to **larger/stronger model** when the task involves money/financial correctness, FSMs/state machines, security/auth design, calc engines that need penny-exact output, multi-file refactors with subtle invariants, or first-of-its-kind architectural decisions in the codebase.

Rule of thumb: **money touches the strong model, pixels touch the fast one.** Each project may add a per-week overlay (see project-specific sections); this heuristic is the floor.

## Context lifecycle (/compact suggestions)

Long sessions accumulate tool results, file dumps, and review output that no longer matter once the work has landed. The harness auto-compacts before overflow, but proactive compaction at natural breakpoints keeps responses sharp and lowers cost. Suggest `/compact` to the user when:

- A major milestone closes (sprint complete, EOW review done, multi-phase plan executed)
- The conversation has accumulated 20+ tool results no longer load-bearing for the next task
- About to switch context (e.g. finishing one week's work, about to start next-week plan mode)
- Roughly 60+ minutes into a session with multiple unrelated phases
- Tool count crosses ~50 in a session (rough proxy for context bloat)

Phrase it as a one-line offer ("Suggest `/compact` before next phase — clears stale tool output"), not a demand. The user decides. Don't suggest immediately after a prior `/compact` or while actively mid-task.

## Git workflow rules

- **Push cadence.** Push after each committed milestone. No weekly batching. Uncommitted/unpushed = lost on disk failure.
- **Branch hygiene.** Solo phase: main only. Feature branches when collaborators join.
- **Tags at milestones.** After EOW review passes: annotated tag with a 1–2 line message. Push tags separately (gated — see AI guardrails).
- **Conventional Commits with domain scope.** Subject ≤72 char + imperative. Body explains WHY, not WHAT (the diff already shows WHAT). Co-author trailer when AI-assisted.
- **Pre-commit secret grep.** `git diff --staged | grep -iE "secret|key|token|password|\.env"` before every commit. Zero matches = proceed.
- **Never commit:** `.env*`, `*.local.json`, `data/` (DB files), credential files. Verify `.gitignore` covers these before first commit.
- **No blind `git add -A` / `git add .`.** Always `git status` + `git diff` first, then add explicit paths.

## AI guardrails (mandatory approval gates)

AI must request explicit user approval before any of the following — **even if the user previously authorized similar operations.** Approval is per-action, not session-wide.

- `git push` (any branch, any remote)
- `git push --force` / `--force-with-lease`
- `git reset --hard`, `git reset --merge`
- `git rebase`, `git rebase --interactive`
- `git branch -D`, `git tag -d`
- `git checkout -- <file>` / `git restore <file>` (destroys uncommitted work)
- `git clean -f`, `git clean -fd`
- Any `gh` command that mutates remote state

## Working discipline (don't be lazy)

- **Don't be lazy.** "Done" means committed, pushed, milestone tagged, EOW review run, typecheck/lint green. Half-finished is worse than not started — it ages into ghost code.
- **No band-aids on root causes.** Test fails → find why. Query slow → fix the query. Edge case → handle it.
- **Read the file before editing it.** Memory of a file from earlier in the session ≠ the file now.
- **No silent skipping.** If a subtask hits a blocker, surface it — don't quietly drop it.
- **Push at every milestone.** Local commits don't survive disk failure.

## Why this exists

You're building things to escape salaried dependence. Every shipped week compounds. Half-finished features are not progress; they're future cleanup. The CLAUDE.md / TODO.md / agent / model-selection / EOW-review stack exists to **amplify** execution, not to **perform** execution. You ship. Tools accelerate the shipping.

## Mid-session wrap-up reminder

Skill `/wrap-up` exists for clean session shutdown. Source: `~/.claude/skills/wrap-up/SKILL.md`. Surface proactively every 2–3 prompts during active working sessions: `(/wrap-up available when ready to close)`. Skip on read-only sessions, mid-blocker turns, and the first prompt.

## Cross-repo sync rule

This is a single-repo project. No SHARED-STANDARDS sync needed. If additional repos are added to this stack, add their paths here and mirror this block verbatim.

<!-- SHARED-STANDARDS:END -->

## Gaming-niche gate

Before writing any brief or scoping any build on a gaming-niche tool opportunity surfaced by RIM, run the 5-step gate. Parallel to plan mode gate: process-level, not advisory.

1. **Franchise leader TAM ceiling.** Identify the 8+ year incumbent leader tool. Pull SimilarWeb traffic for its domain. That number is the realistic ceiling for any new entrant.
2. **Required-pageviews reality check.** `required_pageviews_per_mo = target_monthly_revenue / $4` (gaming RPM, blended pessimistic). Compare to (leader_traffic × 5 PV/visit) via the play ladder:

   | Play | Realistic ceiling vs leader | When |
   |---|---|---|
   | Win the niche (better UX/SEO, same product) | 2-5x leader | Default |
   | Expand the niche (new geo / platform / format) | 5-10x leader | Specific latent-audience thesis |
   | Create a category (new use case) | Uncapped | Discovery play, no leader to benchmark |

   For "win the niche": required > leader × 25 → KILL. Required > leader × 10 → MARGINAL. Else PROCEED. For "expand the niche": multiply leader_traffic by 5x before comparing, document the latent-audience thesis. For "create a category": gate doesn't apply — substitute adjacent-category benchmarks + qualitative demand signals.
3. **Saturation count.** 4+ live competitors launched in last 12 months AND one well-funded or 5K+ Discord members → high saturation, expect compressed margins. If an existing player already covers ALL planned scope, the "first to scrape" wedge is mooted.
4. **Reddit API ToS check.** PRAW free tier is non-commercial only since 2023. Ad-monetized scrapers are the banned use case. If ad-monetized + Reddit-scraped, default to submission-driven architecture.
5. **Behavioral signal density.** Gaming demand expresses behaviorally, not verbally. Count share-code postings per 1000 comments, Discord-invite density, repeat-question frequency. Low density → audience may not exist or existing tools absorbed it.

**Hard rule: if step 1, 2, or 3 fails, no brief gets written. No exceptions.** Launch-window urgency and incumbent weakness do not override the TAM math.

Full methodology + leader benchmarks: `~/.claude/projects/-Users-eva0012-Projects-reddit-market-intel/memory/reference-gaming-niche-preflight-checklist.md` and `reference-gaming-tam-ceiling-methodology.md`.

## Model selection by task

| Task | Model |
|---|---|
| Regex patterns, config edits, test expansion, CLI flags | fast |
| Scoring algorithm changes, clustering tuning, multi-file pipeline refactors | strong |
| First-of-its-kind features (LLM classifier, new storage backend) | strong |
