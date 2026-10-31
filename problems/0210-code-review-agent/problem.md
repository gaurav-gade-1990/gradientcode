### Context

A software company with 2,000 engineers in 40 teams wants an AI reviewer on every pull request in GitHub Enterprise Cloud. A pilot with an off-the-shelf bot was switched off after three weeks: it posted 14 comments per PR on average, most of them style nits the linters already caught, and engineers started ignoring all of it, including the two real SQL injection findings. Human first review takes a median of 2 hours, and leadership believes a good first pass could cut that while catching the bugs that slip through. The VP of Engineering will only roll it out if the false-positive rate is measured, not guessed.

### Requirements

- Review every non-draft PR on open and on each new push, commenting inline on the diff plus one summary.
- Use repository context beyond the diff: callers, definitions, tests, and the team's conventions.
- Run company policy checks: no secrets, no PII in logs, migrations that lock large tables, new endpoints without auth.
- A per-PR comment budget, no repeated comments after a dismissal, and nits off by default.
- Teams configure the reviewer per repo; 12 restricted repos (security, M&A) are excluded.
- Measure precision and usefulness per comment category, and switch off categories that fall below target.

### Scale and constraints

- 1,200 PRs a day and about 3,000 review runs a day including re-pushes; peak 600 runs an hour on weekday mornings.
- A 40M-line monorepo plus 600 service repos; median diff 180 lines, p95 1,800 lines.
- First review comment within 5 minutes of the PR opening, at p90.
- GitHub App limit: 15,000 REST requests per hour for the installation.
- Model prices per million tokens: Sonnet 5.5 at $2 input, $10 output and $0.20 cache reads; Opus 5.5 at $4 and $20.
- Budget: $60,000 a month. Team: 5 engineers, 4 months. The provider contract has zero data retention.
- Targets: at most 15 percent of comments judged wrong, at least 35 percent of comments addressed with a code change.

### What a strong answer covers

- How the agent decides what to say and, more importantly, what not to say.
- How a false positive is defined and measured honestly, at what sample size.
- What the agent may and may not do in the repository and on GitHub.
- The cost per review run and per month, including large PRs.
- How bursts at 10 a.m. and the shared GitHub API limit are handled.
- What happens when the PR itself contains text written to manipulate the reviewer.
