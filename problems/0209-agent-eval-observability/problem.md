### Context

A B2B SaaS company runs 30 production agents (support, billing, onboarding, data questions) built by 12 teams and used by 1,800 customer tenants. Last month a model upgrade dropped the support agent's resolution rate by 9 points, and nobody noticed for eight days because the only signal was a weekly CSAT export. Offline evals live in notebooks, each team grades differently, and 0.8 percent of runs get a thumbs-down that no one reads. Leadership wants one platform for tracing, online and offline evals, regression gates and drift alerts that every agent team uses.

### Requirements

- Trace every agent run end to end: model calls, tool calls, retrieval, tokens, cost and latency, linked by one run id.
- Online evals on production traffic: cheap checks on every run, LLM-as-judge on a sample, and human review on what matters.
- Offline evals: golden sets per agent, run on every prompt, model or tool change, with a pass or block gate in CI.
- Drift dashboards and alerts on inputs, outputs, tool use and quality, per agent and per tenant segment.
- A feedback loop: thumbs-down, escalations and judge failures become labeled cases in the golden sets.
- Tenants can opt out of content storage, and a GDPR erasure request must purge a user's content within 30 days.

### Scale and constraints

- 3.5 million agent runs a day, about 12 spans per run: 42 million spans a day, peak 1,500 spans per second.
- Average span with prompt and completion content: 6 KB.
- 40 prompt, model or tool changes a week across the 30 agents; a CI gate must finish in under 20 minutes.
- Agents run on Sonnet 5.5 ($2 input, $10 output, $0.20 cache reads per million tokens); Haiku 5.5 costs $0.10 and $0.50.
- Eval and observability budget: $50,000 a month all in. Team: 6 engineers, 6 months.
- A quality regression must page within 30 minutes of starting, not eight days.

### What a strong answer covers

- How tracing stays cheap enough to run on every request, and what is sampled.
- How you know the LLM judge agrees with humans, and what you do when it does not.
- What exactly blocks a merge, and why the threshold is not noise.
- The monthly cost of judging, broken down so it fits the budget.
- How one tenant's runaway agent or one team's eval storm is kept from hurting everyone else.
- How content opt-outs and erasure work in a store built for append-only traces.
