# Applied AI Engineering catalog (Track 1, ids 101–180)

These are problems from a forward-deployed engineer's day: agents, tools, gateways, monitoring and enterprise platforms. Each one is graded against the deterministic fakes in `harness/gc_runtime.py`. Writers keep the id, slug and difficulty, and sharpen each spec until it's unambiguous.

## agents: Agents & Orchestration (101–112)
- 0101 react-tool-loop, Easy. `run_agent(llm, tools, user_msg, max_steps)`: call the model, run each tool call, append `tool` results with matching ids, stop on `end_turn` or at max_steps (return a fixed sentinel). Graded on the message list sent each turn.
- 0102 agent-loop-detection, Easy. Stop the agent when the same (tool, canonical-JSON args) repeats N times in a row or a cycle of length ≤ 3 repeats; return the step it stopped at and why.
- 0103 parallel-tool-dag, Medium. Run a dependency DAG of tool calls on `EventLoop` with `max_concurrency`; ready tasks start in id order; return the start/finish times and total makespan. A failed node cancels its descendants only.
- 0104 supervisor-worker-routing, Medium. A supervisor assigns subtasks to workers by capability tags and load (fewest active, then name); collect results in order; reassign once if a worker errors.
- 0105 agent-handoff-context, Medium. Hand a conversation from a triage agent to a specialist: carry the user turns and tool results the specialist may see, drop private scratchpad and tools it lacks, and add a handoff summary message. Graded on the exact transferred transcript.
- 0106 plan-and-execute-replan, Hard. Execute a plan step by step; on a tool failure call the planner with the failure and the completed steps, then splice the new plan in. Cap replans and never redo a completed step.
- 0107 memory-under-token-budget, Medium. Build the context: pin the system prompt and the last K turns, then add older turns newest-first while they fit, and replace the rest with a summary from `summarize()`; never split a tool call from its result.
- 0108 multi-agent-vote, Easy. Aggregate N agents' answers: normalize, weighted majority by confidence, tie-break rules, abstain below a quorum.
- 0109 map-reduce-documents, Medium. Summarize a list of docs with an LLM under a concurrency limit and a per-call token cap: chunk, map, then reduce in batches until one summary remains. Graded on call count, order and virtual time.
- 0110 human-approval-gates, Medium. A state machine where risky tools (by policy) pause the run with a pending approval; resume on approve or reject, and expire after a TTL. Return the event trail.
- 0111 durable-workflow-replay, Hard. An event-sourced workflow: on resume, replay the recorded step results instead of re-calling side-effecting steps, then continue live. A non-deterministic step order raises.
- 0112 trace-critical-path, Medium. Build a span tree from flat spans (id, parent, start, end) and return the critical path, self time per span, and total LLM vs tool time.

## tools-mcp: Tools & MCP (113–122)
- 0113 tool-args-schema-validation, Medium. Validate tool-call arguments against a JSON Schema subset (type, properties, required, enum, min/max, items, additionalProperties) and return all errors with JSON-pointer paths, sorted.
- 0114 mcp-jsonrpc-dispatch, Medium. An MCP server handler for `initialize`, `tools/list` and `tools/call`, notifications (no id means no response), batch requests, and the JSON-RPC error codes -32700/-32600/-32601/-32602. A tool's own failure is returned as `isError: true` content, not a protocol error.
- 0115 streaming-tool-call-assembly, Medium. Assemble streamed deltas (content and tool-call argument fragments by index) into final messages; parse arguments at stop; report malformed JSON per call.
- 0116 structured-output-repair, Medium. Extract JSON from model text (code fences, leading prose, trailing commas, single quotes in keys) and validate it; if still invalid, re-ask the model once with the error, then fail.
- 0117 tool-permission-scopes, Medium. Given user roles, the agent's allowed tools, and per-tool required scopes plus resource ownership, decide which tool calls are allowed. The effective permission is the intersection of user and agent; return denials with reasons.
- 0118 prompt-injection-quarantine, Medium. Wrap untrusted tool output in a data envelope, strip or flag instruction-like spans by the given rules, and make sure no later tool call takes arguments copied from quarantined spans without approval.
- 0119 idempotent-tool-execution, Easy. Run side-effecting tools with idempotency keys: a retry with the same key and args returns the stored result, the same key with different args is a conflict, and stored entries expire after a TTL.
- 0120 oauth-single-flight-refresh, Medium. Many concurrent tool calls (on `EventLoop`) hit a 401 together. Exactly one token refresh runs; the others wait and then retry once with the new token. A refresh failure fails them all.
- 0121 tool-registry-versioning, Easy. Register tools with semver; resolve `name@^1.2` style requests to the highest compatible version; deprecated versions resolve with a warning, and removed versions error.
- 0122 tool-result-budgeting, Easy. Fit tool results into a token budget: truncate large results with a marker, paginate lists with a cursor, and keep the error results whole.

## serving: Serving, Cost & Infra (123–134)
- 0123 token-bucket-rate-limiter, Medium. Per-tenant RPM and TPM buckets with refill on a virtual clock; `acquire(tenant, tokens)` returns the wait time or a rejection; requests are admitted only when both buckets allow.
- 0124 retry-with-backoff, Easy. Done (seed).
- 0125 circuit-breaker, Medium. Closed, open and half-open states, with a failure-rate threshold over a rolling window, a min-calls rule, an open timeout, and N half-open probes. Graded on the state timeline.
- 0126 model-router, Medium. Pick the cheapest model that meets quality ≥ q and p95 latency ≤ L for each request's tier, falling back in a ranked order on errors; return the choices and the total cost.
- 0127 semantic-cache, Medium. A cache keyed by (tenant, model, system-prompt hash) and embedding similarity ≥ threshold, with TTL, LRU eviction at capacity, and no cross-tenant hits. Graded on hits, misses and evictions.
- 0128 prompt-caching-cost, Easy. Compute the cost of a sequence of calls under prefix caching: a cache write premium, discounted reads, a TTL, and a minimum cacheable length. Compare to the no-cache cost.
- 0129 continuous-batching-scheduler, Hard. Simulate an LLM server: requests arrive with prompt and output lengths, prefill and decode run per step, a KV-cache token budget limits admission, and the newest request is preempted on OOM. Return per-request TTFT and latency.
- 0130 gpu-capacity-planner, Medium. From the model size, layers, KV heads, head dim, dtype, GPU memory and target QPS, compute the KV bytes per token, the max concurrent sequences, and the GPUs needed with a utilization headroom.
- 0131 tenant-cost-attribution, Easy. Attribute token costs by tenant, feature and model, with price tables by date, cached-token discounts, shared costs allocated pro rata, and budget alerts at 50/80/100% that fire once each.
- 0132 load-balancer-p2c, Medium. Least-outstanding-requests and power-of-two-choices (choice draws provided) across replicas with different speeds on `EventLoop`; compare the p99 for both.
- 0133 autoscaler-policy, Medium. Target-utilization scaling with min/max replicas, scale-up and scale-down cooldowns, and stabilization windows. Return the replica timeline for a load trace.
- 0134 gateway-failover-hedging, Hard. Send to the primary provider; if there's no response by the hedge delay, also send to the secondary; take the first success, cancel the loser, and count the cost of both. Fail over on errors, respecting per-provider circuit state.

## monitoring: Data & Model Monitoring (135–142)
- 0135 population-stability-index, Easy. PSI with quantile bins from the reference data, epsilon for empty bins, and the severity bands.
- 0136 ks-drift-detector, Medium. The two-sample KS statistic per feature, plus the asymptotic p-value formula given in the statement and a Bonferroni correction across features. Return the drifted features.
- 0137 data-quality-validator, Easy. Validate records against expectations (types, nulls, ranges, regex, uniqueness, foreign keys) and return a report with counts and sample failing row ids.
- 0138 streaming-latency-percentiles, Medium. A fixed log-bucket histogram (HDR-lite) with bounded relative error; merge histograms across replicas; answer p50/p95/p99 queries.
- 0139 slo-burn-rate-alerts, Medium. Multi-window, multi-burn-rate alerting (the Google SRE workbook rules): page when both the 1 h and 5 min windows exceed 14.4×, open a ticket at 6× over 6 h and 30 min; return the alert intervals.
- 0140 ewma-anomaly-detection, Easy. EWMA mean and variance; flag when |z| > k after the warmup; anomalous points don't update the baseline.
- 0141 embedding-drift, Medium. Centroid cosine shift plus MMD with an RBF kernel (bandwidth by the median heuristic) between the reference and current embedding windows.
- 0142 citation-hallucination-check, Medium. For an answer with `[n]` citations, check each sentence's claim tokens against the cited passage by token overlap ≥ τ; flag missing, out-of-range and unsupported citations.

## prod-ml: Production ML & Evals (143–152)
- 0143 point-in-time-feature-join, Hard. Join feature snapshots to label events as of event time minus a lag, with no future leakage, a per-feature TTL, and the latest version on equal timestamps.
- 0144 pass-at-k, Easy. The unbiased pass@k estimator (Chen et al.) per problem and averaged, stable for large n.
- 0145 llm-judge-position-swap, Medium. Run the pairwise judge in both orders; an inconsistent pair counts as a tie; compute the win rates, the position-bias rate, and Cohen's kappa against human labels.
- 0146 ab-test-significance, Medium. A two-proportion z-test, a confidence interval, and the per-arm sample size for a given MDE, alpha and power, using normal quantiles from a given table or `math.erf` inversion via bisection.
- 0147 canary-analysis, Medium. Compare the canary to the baseline on error rate and latency over windows; promote, rollback or extend using thresholds and min-sample rules. Return the decision and the reasons.
- 0148 shadow-deployment-diff, Easy. Compare shadow and primary outputs per request: exact match, normalized match, and numeric tolerance; summarize the disagreement by segment.
- 0149 prompt-regression-gate, Easy. A golden-set gate: block the prompt change if any must-pass case regresses, or if the pass rate drops more than δ overall or in any tagged slice with at least m cases.
- 0150 train-serve-skew, Medium. Compare per-feature distributions and per-row values for the same entity ids between training and serving logs; report mismatched rates and the top offending features.
- 0151 model-registry-stages, Medium. Stage transitions (None→Staging→Production→Archived) with rules: one Production per alias, approval required, and promotion archives the old version. Lineage queries return the data and code versions.
- 0152 thompson-prompt-variants, Medium. Beta-Bernoulli Thompson sampling over prompt variants with the given beta draws; a new variant gets a warm start; return the allocations and the posteriors.

## rag: RAG & Knowledge Systems (153–158)
- 0153 recursive-chunker, Medium. Split on separators in priority order (paragraph, line, sentence, word) to chunks ≤ max_tokens with an overlap; keep the source offsets.
- 0154 hybrid-search-rrf, Easy. Fuse BM25 and vector rankings with reciprocal rank fusion (k=60), plus a weighted variant and deterministic ties.
- 0155 acl-aware-retrieval, Medium. Filter retrieval by document ACLs (users, groups, nested groups, deny overrides) before ranking, so top-k never leaks restricted docs, and fill k from the allowed docs.
- 0156 incremental-index-sync, Medium. Diff the source docs against the index by content hash: return the upserts, the deletes (tombstones), and the unchanged docs; re-chunk only changed docs and keep chunk ids stable.
- 0157 context-packing, Medium. Pick chunks for the prompt under a token budget: dedupe near-duplicates (Jaccard ≥ τ), keep at most m per doc, greedy by score per token, then order by doc position.
- 0158 grounded-answer-check, Medium. Verify that an answer's quoted spans exist verbatim (after normalization) in the cited sources, and compute groundedness = supported sentences / all sentences.

## enterprise: Enterprise Agent Platforms (159–168)
- 0159 tenant-isolated-memory, Medium. An agent memory store keyed by tenant, user and agent, with sharing scopes (private, team, org); reads must never cross a tenant; deletion requests cascade.
- 0160 policy-engine, Medium. Evaluate allow/deny rules with wildcards, conditions on attributes, explicit deny wins, the most specific match, and a default deny. Return the decision with the matching rule id.
- 0161 hash-chained-audit-log, Easy. Append audit events with `sha256(prev_hash + canonical_json(event))`; verify the chain and return the first tampered index.
- 0162 pii-redaction-vault, Medium. Detect PII (emails, phones, card numbers with a Luhn check, SSNs) by the given patterns, replace them with stable tokens per value, store the originals in a vault, and re-identify only for authorized roles.
- 0163 agent-task-queue-leases, Hard. A priority task queue for agent workers: leases with a visibility timeout, heartbeats extend them, an expired lease redelivers the task, max deliveries sends it to the DLQ, and acks are idempotent. Graded on the event log over virtual time.
- 0164 ai-coworker-inbox-triage, Medium. Assign incoming requests to AI coworkers by skill and capacity under SLA deadlines (earliest deadline first); escalate to a human when no coworker can make the deadline.
- 0165 skill-dependency-resolver, Hard. Resolve a shared skills/tools marketplace manifest: semver ranges, transitive deps, conflict detection with an explanation, and the highest satisfying versions found by backtracking.
- 0166 usage-metering-invoice, Easy. Aggregate metered usage events (dedupe by event id) into tiered pricing with included quotas and proration for mid-cycle plan changes.
- 0167 signed-webhook-delivery, Medium. Sign payloads with HMAC-SHA256 over `timestamp.body`, verify with a tolerance window and a constant-time compare, and retry deliveries with a backoff schedule. Receivers dedupe by event id.
- 0168 feature-flag-rollout, Easy. Sticky percentage rollouts via `stable_hash(flag:user) % 10000`, with targeting rules, an allowlist and a kill switch. Increasing the percentage never flips users out.

## fullstack: Full Stack & Architecture (169–180)
- 0169 sse-stream-parser, Easy. Parse a Server-Sent Events byte stream split at arbitrary chunk boundaries: `event:`, `data:` multi-line, `id:`, `retry:`, comments and `[DONE]`.
- 0170 cursor-pagination, Easy. Keyset pagination over (created_at, id) with opaque base64 cursors, stable under inserts, in both directions.
- 0171 request-coalescing, Medium. Single-flight concurrent identical requests on `EventLoop`: one upstream call, every waiter gets the result or the error, and no stale reuse after completion.
- 0172 transactional-outbox, Medium. Write the state change and the outbox row in one transaction (simulated); a relay publishes in order with at-least-once delivery, and the consumer dedupes. Survives crashes at each step.
- 0173 saga-compensation, Hard. A multi-step agent action (book, charge, notify) with compensations run in reverse on failure; compensations retry; return the final state and the step log.
- 0174 bounded-queue-backpressure, Medium. A producer/consumer pipeline on `EventLoop` with a bounded queue: block, drop-oldest or reject policies; return the throughput, drops and max queue depth.
- 0175 consistent-hashing-sessions, Medium. A hash ring with virtual nodes for sticky agent sessions; adding or removing a node moves only the affected keys; return the movement stats.
- 0176 lww-conversation-merge, Medium. Merge conversation edits from devices with Lamport clocks (last-writer-wins, ties by device id) and tombstones; the merge must be commutative.
- 0177 rate-limited-fanout, Medium. Notify N subscribers over channels with per-channel rate limits and retries on `EventLoop`; return the delivery times and failures.
- 0178 llm-capacity-cost-estimator, Medium. Turn a design into numbers: DAU, turns per user, tokens per turn, cache hit rate, model mix and prices give the peak QPS, monthly tokens, monthly cost and the GPUs needed for self-hosting. Return the breakdown dict.
- 0179 websocket-reconnect-resume, Medium. A client reconnect policy with backoff, and resuming a chat stream from the last acked event id without duplicates or gaps.
- 0180 api-idempotent-create, Easy. A POST /runs handler with an `Idempotency-Key` header: concurrent duplicates return the same run, a different body gives 422, and the key is scoped per user.
