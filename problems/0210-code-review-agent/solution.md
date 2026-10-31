# PR Code Review Agent: model answer

## 1. Scenario

The user is the PR author, who wants the real problems pointed out before a human looks, and the reviewer, who wants less to read. The job is a first-pass review that engineers trust enough to read, which means saying little and being right.

| What | Number | What it forces |
|---|---|---|
| Review runs | 3,000 a day, peak 600 an hour (10 a minute) | A queue with priorities, not a webhook that calls a model inline |
| First comment | p90 under 5 minutes | Parallel analysis per file group; the code index must already be warm |
| Precision target | At most 15 percent wrong | A measured audit, plus fewer and better comments |
| Usefulness target | At least 35 percent addressed | Nits and linter duplicates are off |
| GitHub API | 15,000 requests an hour | About 12 calls a run x 600 runs = 7,200 an hour at peak, so code comes from a git mirror, not REST |

**How:**
1. Baseline from the pilot: 14 comments per PR, 9 percent addressed, 2 hour median to first human review.
2. Agree definitions with the VP: "addressed" means the commented lines changed in a later commit and the thread was resolved; "wrong" means a staff engineer judged the claim false.
3. Out of scope: approving or blocking merges on model judgment, and auto-fixing code.

**Decision.** The agent is advisory; only deterministic policy checks can fail a required status, because a model false positive that blocks a merge costs more trust than ten misses.

**Trap.** Optimizing for bugs found. The pilot found real bugs and was still switched off because they were buried in nits.

## 2. Single View

| Layer | What runs here and what it hands over | Why we need it |
|---|---|---|
| GitHub App | Webhooks for PR opened, synchronize and review comments, signed with HMAC. Hands over a verified PR event | One identity with read-only contents and write-only reviews |
| Intake and queue | Webhook receiver into Temporal, with priority and per-team concurrency. Hands over a review run, superseding older runs of the same PR | Bursts and re-pushes do not pile up |
| Code context | Local git mirrors, Zoekt search, SCIP code-intel indexes. Hands over diff hunks plus definitions, callers and tests | The diff alone hides most real bugs |
| Policy engine | Semgrep and gitleaks rules and migration checks in code. Hands over deterministic findings | Policy is a rule, not an opinion |
| Review agents | Finder per file group, verifier per finding, on Sonnet 5.5 through LiteLLM. Hands over scored, evidenced findings | Separation of finding and checking is where precision comes from |
| Ranker | Dedupe against linters and past dismissals, comment budget. Hands over at most 5 inline comments and a summary | The budget is what keeps people reading |
| Event log | Kafka topic of comment outcomes into ClickHouse. Hands over precision and addressed rate per category | False-positive rate is measured, not guessed |

**The one idea to hold:** the model proposes findings; evidence, dedupe and a hard comment budget in code decide which ones a human ever sees.

## 3. Data Sources

A review reads five sources, all pinned to the PR's head SHA.

**How:**
1. **The PR**: diff, description, linked issue, existing review comments and CI check results, fetched once per run.
2. **Code**: local bare mirrors updated on each push webhook; worktrees at the PR head SHA, no REST file fetches.
3. **Code intelligence**: SCIP indexes rebuilt incrementally on merge to main; Zoekt trigram search across 600 repos.
4. **Conventions**: each repo's `REVIEW.md` and approved rules from past dismissals.
5. **Existing tools**: annotations already posted by ESLint, golangci-lint, CodeQL, so the agent never repeats them.

**Decision.** Read code from mirrors at the exact head SHA, because the model must comment on the code the human sees, and REST fetches would spend half the API budget.

**Trap.** Indexing only the default branch and reading the PR's new symbols from it. The definition the PR added does not exist there, and the agent invents one.

## 4. Processing

Each run is a durable Temporal workflow with five steps.

**How:**
1. **Plan**: split the diff into file groups under 30k tokens each, by directory and import graph; a 1,800-line PR becomes about 6 groups.
2. **Context**: for each changed symbol, pull its definition, up to 5 callers and the nearest test file, then pack by relevance under the group budget.
3. **Policy**: run Semgrep, gitleaks and the migration checker (an `ALTER TABLE` on a table with over 10M rows from the schema registry) on the diff.
4. **Incremental**: on a new push, review only hunks changed since the last reviewed SHA.
5. A new push cancels the in-flight run for that PR.

**Decision.** Plan by file group with a fixed token budget, because one 150k-token prompt for a large PR is slow, expensive and loses details in the middle.

**Trap.** Re-reviewing the whole PR on every push. Authors see the same comments return and costs triple.

## 5. Agents

Two roles, bounded loops, no free-form autonomy. Model cost for 66,000 runs a month comes down by three levers in order.

| Lever, in order | Model cost a month | Saving a month |
|---|---|---|
| Start: Opus 5.5 on every run, no caching, full re-review on each push | $28.4k | |
| Model mix: Sonnet 5.5, Opus 5.5 only on the 10 percent of risky paths | $15.6k | $12.8k |
| Prompt caching of the PR prefix across six verifier calls | $10.9k | $4.7k |
| Incremental review of re-pushes, about half the tokens | $7.7k | $3.2k |

**How:**
1. **Finder** per file group: reads the packed context, may make up to 8 read-only tool calls, emits candidate findings as JSON with file, line, category, severity, claim and evidence lines.
2. **Verifier** per candidate: a fresh call that sees the claim and the cited code and must answer confirmed, refuted or unsure with a quote; only confirmed findings continue.
3. **Routing**: changes under `auth/`, `payments/` and `migrations/` (about 10 percent of runs) use Opus 5.5.
4. **Per run on Sonnet 5.5**: finder 25k input and 1.5k output is $0.065; six verifier calls with a cached 4k prefix are $0.035; a median run is $0.10.

**Decision.** Verification is a separate call that sees only the claim and the code, because a finder grading its own output agrees with itself.

**Trap.** Asking one prompt to "only report high-confidence issues". Self-reported confidence does not track correctness.

## 6. Memory

The reviewer remembers what it already said and what each repo has told it, never code across repos.

**How:**
1. **Per PR**: reviewed SHAs and comment fingerprints (rule, symbol, normalized code line) in Postgres, so a dismissed finding never returns.
2. **Per repo**: conventions in `REVIEW.md` plus rules proposed from repeated dismissals ("we allow raw SQL in `scripts/`"), merged only when a CODEOWNER approves.
3. **Per category**: rolling precision and addressed rate from the event log, read by the ranker each run.
4. No memory across repos of code content.

**Decision.** Learned conventions are pull requests to `REVIEW.md`, because a rule a human approved can be read and reverted; a silently learned one cannot.

**Trap.** Auto-learning from every dismissal. One annoyed engineer can teach the reviewer to ignore SQL injection for a whole repo.

## 7. MCP Tool Servers

One code-intel MCP server, read-only, pinned to the run's head SHA.

**How:**
1. Tools: `read_file(path, start, end)`, `find_definition(symbol)`, `find_references(symbol, limit)`, `search_code(query, repo)`, `get_ci_annotations()`.
2. Every call is scoped to repos the PR author can read; restricted repos are not indexed at all.
3. Results capped at 4k tokens with cursors; code is wrapped as untrusted data.
4. Built on the MCP Python SDK, running beside the worker.

**Decision.** Posting comments is not a tool; the orchestrator posts after ranking, because a model with a write tool can bypass the budget.

**Trap.** Giving the agent a shell to "run the tests". It turns PR code, which is untrusted, into code running with the reviewer's credentials.

## 8. Endpoints

GitHub drives everything by webhook; the service answers fast and posts one review per run.

| Stage | p50 | p90 |
|---|---|---|
| Webhook to worker | 5 s | 20 s |
| Worktree at head SHA | 10 s | 25 s |
| Context packing | 15 s | 35 s |
| Policy checks | 10 s | 20 s, in parallel |
| Finder, groups in parallel | 50 s | 100 s |
| Verifier, findings in parallel | 30 s | 60 s |
| Rank and post | 5 s | 10 s |
| **First comment** | **about 2 min** | **about 4.2 min** |

**How:**
1. `POST /webhooks/github` verifies `X-Hub-Signature-256`, dedupes by delivery id and returns 202 in under 100 ms.
2. Results post as one GitHub review with up to 5 inline comments plus a check run with the summary, so a run costs one write call.
3. PR commands: `@reviewer explain`, `@reviewer wrong <reason>`, `@reviewer skip`.
4. `GET /v1/repos/{repo}/stats` returns precision and addressed rate per category.
5. Admission: priority PR opened over new push over re-request; per-team concurrency of 20 runs; LLM peak about 10 runs a minute x 55k tokens = 550k tokens a minute against a 2M quota.

**Decision.** One review per run, not one call per comment, because 2,160 comments a day as single calls would burn the API budget and spam notifications.

**Trap.** Calling the model inside the webhook handler. GitHub times out at 10 s and redelivers, and the PR gets reviewed twice.

## 9. Caching

Caching saves model cost on re-runs and keeps context building inside the latency budget.

**How:**
1. Prompt-cache the system prompt, repo conventions and the PR context prefix shared by all verifier calls.
2. Cache SCIP lookups per (repo, SHA, symbol) for the life of the run.
3. Cache finder output per (file group hash, model, prompt version), so a re-run with no code change costs nothing.
4. Keep warm worktrees for the 50 most active repos.

**Decision.** Cache keys include the prompt version, so a prompt change re-reviews instead of serving old findings.

**Trap.** Caching on file path. A changed file with the same path returns comments on code that no longer exists.

## 10. Data Stores

Most storage is code mirrors and indexes; the outcome stream is small but is the most important.

| Store | Holds | Size |
|---|---|---|
| Git mirrors on NVMe | Bare mirrors of the monorepo and 600 repos | About 400 GB |
| Zoekt and SCIP | Search and code-intel indexes | About 60 GB |
| Postgres | Runs, findings, fingerprints, repo config | About 50 GB a year |
| Kafka and ClickHouse | Comment outcome events and analytics | 2,160 comments a day, under 5 GB a year |
| S3 | Prompts and responses for audit, 30 days | About 1 TB |

**How:**
1. Monthly cost: models $7.7k from the lever table, plus assumed infra prices of index and worker nodes $5k, Postgres $1k, Kafka and ClickHouse $3k, Temporal Cloud $1k, Datadog $2k: about $20k against $60k.
2. No GPUs: the models are API calls and indexing is CPU.

**Decision.** Keep the outcome stream separate from run storage, so precision is a query, not a project.

**Trap.** Keeping prompts forever "for debugging". They contain the company's source code; 30 days covers every investigation.

## 11. Output

The author sees a few inline comments, one summary and a policy check, nothing else.

**How:**
1. **Inline comment**: one sentence claim, the evidence lines, a suggested change block when it is small, and a category tag.
2. **Summary**: risk areas touched, policy results, and "N other low-severity notes" collapsed.
3. **Policy findings** as a check run that can be a required status.
4. Ranking: severity times verified confidence times category precision; post at most 5 and 0 nits unless the repo opts in.

**Decision.** At most 5 comments, average 1.8, because each extra comment lowers the chance any of them is read.

**Trap.** Posting a summary that restates the PR description. It costs reading time and adds nothing.

## 12. Guardrails

Permissions, budgets and blocking rules are enforced in code, never in the prompt.

**How:**
1. The GitHub App has contents read, pull requests write, checks write; no merge, no push, no admin.
2. Prompt injection: code, comments and PR text are data; a finding whose text contains instructions or URLs not in the diff is dropped.
3. The comment budget and nit filter run in the ranker, after the model.
4. Restricted repos are excluded at the webhook; the provider has zero retention; secrets in diffs are masked before any model call.

**Decision.** Categories below 70 percent audited precision over 50 or more samples are switched off automatically, because one bad category drags the whole reviewer's credibility down.

**Trap.** "Do not post more than 5 comments" in the prompt. The model complies on average, not always.

## 13. Key Impact

Five numbers decide whether the reviewer stays switched on.

| Metric | Baseline | Target | How measured |
|---|---|---|---|
| Comments judged wrong | Unknown | At most 15 percent | 200 random comments a week audited by staff engineers |
| Comments addressed | 9 percent | At least 35 percent | Lines changed after the comment and thread resolved |
| Comments per PR | 14 | Under 2 average, 5 max | Event log |
| Time to merge | Baseline from holdout | 20 percent lower | 10 percent random holdout of PRs for 8 weeks |
| Post-merge reverts | Baseline from holdout | 10 percent lower | Reverts within 14 days, holdout vs reviewed |

**How:**
1. At 200 audits a week, a precision of 85 percent has a 95 percent interval of about plus or minus 5 points.
2. The holdout gives about 4,800 unreviewed PRs over 8 weeks, enough to see a 20 percent change in time to merge.

**Decision.** Use a holdout, because adoption alone cannot tell whether reviews got faster because of the agent or because of the quarter.

**Trap.** Using thumbs-up reactions as precision. Few people react, and polite ones react to everything.

## 14. Failure Modes

Each degraded path makes the reviewer quieter, never louder.

**How:**
1. **10 a.m. burst**: Temporal queues by priority; drafts and re-requests wait first.
2. **GitHub API limit**: a token bucket at 12,000 requests an hour leaves headroom for other apps.
3. **Index lag after a large merge**: runs fall back to Zoekt search and mark the review "partial context".
4. **Model outage**: LiteLLM fails over to a second provider with the same contract terms, or the run skips with a check note.
5. **Precision regression after a prompt change**: an offline set of 400 labeled historical findings gates every prompt or model change.

**Decision.** When context or model is degraded, post less, never guess, because a wrong comment costs more than a missing one.

**Trap.** Retrying failed runs hours later. A comment on an already-merged PR is noise.

## 15. Build Order

Five phases over 17 weeks for 5 engineers, shadow first.

**How:**
1. **Weeks 1-3**: GitHub App, mirrors, Temporal, policy checks only. Measure: policy findings with zero false alarms on 2 weeks of PRs.
2. **Weeks 4-7**: finder and verifier in shadow mode, comments stored but not posted. Measure: audited precision on 500 shadow findings.
3. **Weeks 8-10**: post to 5 volunteer teams with the budget. Measure: addressed rate.
4. **Weeks 11-13**: event log, category auto-off, holdout. Measure: precision per category.
5. **Weeks 14-17**: rollout to 40 teams. Measure: time to merge vs holdout.

**Decision.** Shadow first, because precision can be measured before a single engineer is annoyed.

**Trap.** Launching to all 2,000 engineers to "get data". First impressions are what killed the pilot.
