### Context
A 9,000-person financial software company has 40 internal teams calling LLMs, each with its own provider keys, SDK settings and retry logic. Spend reached $500,000 last month and grows about 12% a month, and finance cannot say which team or feature spent it. Last quarter one provider outage took down four customer-facing features for 90 minutes, a runaway agent loop burned $38,000 over a weekend, and a support tool sent unredacted customer account numbers to a provider without a zero-retention agreement. The platform team has been asked to put one gateway in front of every model call.

### Requirements
- One endpoint for all teams, compatible with the OpenAI and Anthropic SDKs, covering chat, embeddings and batch.
- Per-team virtual keys; no team ever holds a raw provider key.
- Per-team rate limits (requests and tokens per minute), monthly budgets with alerts, and a hard stop that finance controls.
- Routing to cheaper models where a team opts in and its evals still pass; failover across providers when one degrades.
- PII redaction before any request reaches a provider that is not approved for that data class.
- Cost attributed to team, feature and model, reconciled against provider invoices; a trace for every call.

### Scale and constraints
- 45 million requests a month; 155 billion input and 19 billion output tokens.
- Peak is 4 times the average during US business hours.
- Current mix by requests: Claude Opus 5.5 3M, Claude Sonnet 5.5 20M, Claude Haiku 5.5 15M, and a second provider's mid model 7M.
- About 20% of traffic is offline: nightly enrichment, eval runs and backfills.
- 12 teams run customer-facing features with a 99.95% availability target.
- The gateway may add at most 25 ms at p99 to a request; streaming must pass through token by token.
- Target: cut spend at least 35% at equal eval scores within two quarters.
- Platform team of six engineers. SOC 2 Type II; restricted data must stay with providers under zero data retention in US regions.

### What a strong answer covers
- How token-per-minute limits are enforced when output length is unknown at admission.
- Which cost levers save the most, with numbers, and which ones are not worth it.
- What happens to customer-facing traffic when a provider starts returning 429s or 500s.
- Where budgets are enforced, and what happens at 100% for a customer-facing team.
- How you make sure every team actually goes through the gateway.
- What the gateway must not do to requests, so teams can still use provider features.
