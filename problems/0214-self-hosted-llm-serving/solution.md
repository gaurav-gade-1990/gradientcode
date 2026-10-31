# Self-Hosted LLM Serving for a Regulated Insurer: model answer

## 1. Scenario

The users are 14 use-case teams who need a model endpoint they are allowed to send claims data to, and finance, who need a cost per token to compare with the hosted API. The platform is a shared, on-premises inference service in three data centers with one gateway, run like a regulated utility.

| What | Number | What it forces |
|---|---|---|
| Requests | 1.2M a day, 13.9/s average, 55.6/s peak | Capacity is sized for peak on a fleet that cannot grow in minutes |
| Tokens | 108B input and 12.6B output a month | The prefill side is 9 times the decode side by count |
| Large-model share | 35 percent, 19.4 requests/s at peak | Most of the GPUs go to the 70B |
| SLO | TTFT p95 800 ms, TPOT p95 50 ms | Chunked prefill and a cap on batch size per replica |
| Residency | US 80 percent, EU 20 percent, separate fleets | The EU fleet needs its own spare |

**How:**
1. Inventory the 14 use cases: data class, entity, model size needed, interactive or batch, tokens per request.
2. Baselines: 9 use cases blocked, 5 running on a hosted API with public data only.
3. Agree the data-class rule with legal: restricted never leaves the insurer; public and internal may use the API.
4. Out of scope: training base models; fine-tuning beyond LoRA adapters.

**Decision.** Self-hosting is justified by data control, DORA concentration risk and EU AI Act oversight, and the cost case is made honestly per model size, because for the small model the hosted price is lower.

**Trap.** Selling the project as cheaper than the API. Finance will check, and on the 8B path it is not.

## 2. Single View

| Layer | What runs here and what it hands over | Why we need it |
|---|---|---|
| Clients | Team apps, Guidewire ClaimCenter, mainframe batch through MQ. Hand over an OpenAI-style request with use-case id and data class | One contract for every consumer |
| Gateway | LiteLLM behind Envoy per data center. Hands over an authenticated, classified request | Auth, quotas and the data-class rule in one place |
| Admission | Per-use-case token buckets, three priority classes, queue-depth shedding. Hands over an admitted request or a 429 with retry-after | A fixed fleet must say no early |
| Router | Prefix-aware routing across replicas (vLLM production-stack router or llm-d). Hands over the replica likely to hold the prefix in KV | Prefix hits only pay off if requests land where the cache is |
| Engines | vLLM: 70B FP8 at tensor parallel 2, 8B BF16 with 24 LoRA adapters per GPU. Hands over streamed tokens | Continuous batching keeps GPUs busy |
| Fleet | 5 HGX H100 servers: 3 in the US across Ohio and Texas, 2 in Dublin. Hands over GPU capacity per region | Residency and failover are physical |
| Fallback | Hosted API in region for public and internal classes only. Hands over tokens when the fleet is full or down | Burst and disaster capacity without buying for the worst day |
| Model registry | MLflow registry with model cards, eval results, approvals and signed artifact hashes. Hands over the only versions engines may load | Model risk management |
| Telemetry | Prometheus and Grafana: TTFT, TPOT, KV use, queue depth, tokens per use case. Hands over SLOs and chargeback | Cost per token and capacity planning |

**The one idea to hold:** the GPU count comes from peak tokens per second, and everything else (quantization, model mix, prefix caching, batch shifting) is a lever that lowers it.

## 3. Data Sources

The platform's inputs are traffic, model artifacts and evaluation sets.

**How:**
1. **Traffic** from 14 use cases, each registered with entity, data class, priority, model and token quota.
2. **Model artifacts**: base weights and adapters in safetensors only, pulled from the vendor, checked against published hashes, scanned, signed with Sigstore cosign, and mirrored into an internal Artifactory per region.
3. **Eval sets** per use case, owned by the team and approved by model risk.
4. **Load traces**: a week of real request sizes replayed for capacity tests.

**Decision.** Engines load only signed artifacts from the internal mirror, so a weight file that changed upstream cannot reach production.

**Trap.** Pulling weights from a public hub at deploy time. A pickle file or a swapped revision becomes code running next to claims data.

## 4. Processing

Processing is the serving engine; the KV cache sets concurrency and the token rates set the GPU count.

| Model | KV bytes per token | KV space per replica | Concurrent sequences at 3,350 tokens |
|---|---|---|---|
| 70B, 80 layers, 8 KV heads, head dim 128, FP8 KV | 2 x 80 x 8 x 128 x 1 = 160 KB | 2 H100: 144 GB at 0.9 use, less 70 GB weights and 4 GB activations, about 70 GB | About 127 |
| 8B, 32 layers, 8 KV heads, head dim 128, BF16 KV | 2 x 32 x 8 x 128 x 2 = 128 KB | 1 H100: 72 GB less 16 GB weights, 4 GB activations, adapters, about 52 GB | About 118 |

**How:**
1. Planning throughput, assumed until load-tested: a 70B FP8 TP2 replica does 2,000 output and 12,000 prefill tokens/s; an 8B GPU does 5,000 and 40,000.
2. 70B at peak: 19.4 requests/s give 6,800 output tokens/s and, after a 40 percent prefix hit, 35,000 prefill tokens/s: 3.4 + 2.9 = 6.3 replicas busy, 9 at 70 percent.
3. 8B at peak: 36.1 requests/s give 12,600 output and, after a 20 percent hit, 86,700 prefill tokens/s: 2.5 + 2.2 = 4.7 GPUs, 6.7 at 70 percent.
4. Chunked prefill at 2,048 tokens keeps TPOT under 50 ms while long prompts load.

**Decision.** FP8 weights and KV for the 70B, validated on each use case's eval set, because it halves GPUs per replica at a measured quality cost under 1 point.

**Trap.** Sizing from average load. Average is 13.9 requests/s; peak is four times that.

## 5. Agents

Not an agent: serving is deterministic infrastructure, and routing is a rule on use case and data class. We would add a model-based router only if teams could not say which model size they need. The cost levers are applied in this order, priced at an assumed $1.41k per H100-month (5 servers for $56.5k).

| Lever, in order | H100s at peak | Cost a month | Saving a month |
|---|---|---|---|
| Start: everything on 70B BF16 at TP4, no prefix caching | 136 | $192k | |
| FP8 weights and KV, TP2 | 68 | $96k | $96k |
| Model mix: 65 percent to the 8B with LoRA adapters | 32 | $45k | $51k |
| Prefix caching, 40 and 20 percent hits | 25 | $35k | $10k |
| Batching: claims backlog summaries moved overnight | 23 | $32k | $3k |

**How:**
1. Each use case registers its model; the gateway enforces it.
2. Residency and spares then raise the active count to 31: US 16 for the 70B and 6 for the 8B, EU 6 and 3.

**Decision.** Multi-LoRA on one 8B base instead of 24 deployments, because 24 adapters at about 160 MB each fit beside one copy of the weights.

**Trap.** One dedicated GPU per fine-tune. 24 adapters become 48 mostly idle GPUs with failover.

## 6. Memory

Not an agent memory: the only state is the KV cache, which is managed as a tier.

**How:**
1. HBM holds active sequences' KV; vLLM's automatic prefix caching keeps shared system prompts and policy blocks resident.
2. LMCache offloads hot prefixes to CPU memory (1 TB per server), so a prefix evicted from HBM reloads faster than it recomputes.
3. The router hashes the first 1,024 tokens to send repeat prefixes to the same replica.
4. No prompts or outputs are kept by the engines; logging is the gateway's job.

**Decision.** Teams put stable text first and variable text last, enforced by a gateway lint, because prefix hits depend on byte-identical prefixes.

**Trap.** Timestamps or user names at the top of the system prompt. The prefix hit rate falls to zero and the fleet needs 2 more replicas.

## 7. MCP Tool Servers

Not an agent: no MCP servers sit in the serving path. Tool calling belongs to the clients; the platform supports it with structured output.

**How:**
1. Guided decoding with xgrammar in vLLM for JSON schemas, so extraction adapters always return valid JSON.
2. A read-only MCP server for internal agents: `get_quota(use_case)`, `get_model_versions()`, `get_slo_status()`.
3. Tool definitions sent by clients count against their token quota like any prompt.

**Decision.** Constrained decoding is a platform feature, because 14 teams writing JSON repair loops is 14 sources of retries.

**Trap.** Letting the model call tools from inside the serving layer. The platform then owns other teams' side effects.

## 8. Endpoints

The gateway is OpenAI-compatible and sits in front of every engine; the interactive budget is spent mostly on prefill.

| Stage, interactive 70B request | p50 | p95 |
|---|---|---|
| Envoy, auth, data-class check | 3 ms | 8 ms |
| Admission and routing | 2 ms | 5 ms |
| Queue wait | 20 ms | 150 ms |
| Prefill, 3,000 tokens, 40 percent cached | 180 ms | 450 ms |
| First token out | 30 ms | 60 ms |
| **Time to first token** | **about 235 ms** | **about 675 ms** |
| Decode, 350 tokens at 35 ms | 12 s streamed | TPOT under 50 ms |

**How:**
1. `POST /v1/chat/completions` and `/v1/completions`, with `model` as an alias (`large-reasoning`, `small-extract:claims-fnol`) mapped to a pinned version.
2. Priority classes: interactive, near-real-time, batch; batch is admitted only below 60 percent KV use.
3. `POST /v1/batches` for mainframe and Guidewire jobs, finished within 8 hours.
4. Fallback: a request marked public or internal goes to the hosted API in region when queue wait passes 400 ms; restricted requests get a 429.

**Decision.** Aliases, not raw model names, so a model upgrade is a registry change, not 14 code changes.

**Trap.** Failing over restricted traffic to the API "just during the outage". That is the exact disclosure the platform exists to prevent.

## 9. Caching

The cache that matters is the KV prefix cache; response caching is narrow.

**How:**
1. Prefix caching on every engine, with prefix-aware routing.
2. An exact-match response cache per use case for deterministic extraction (temperature 0), keyed by model version, adapter version and input hash, 24 hours.
3. No cross-use-case or semantic caching of restricted data.
4. Adapters stay resident on each 8B GPU; the most used 8 are pinned.

**Decision.** Response caching is opt-in per use case, because only deterministic extraction is safe to reuse.

**Trap.** A semantic cache across the copilot. Two claims with similar wording get each other's summaries.

## 10. Data Stores

Weights live next to the GPUs; logs and records live in the region whose law governs them.

| Store | Holds | Size |
|---|---|---|
| Local NVMe per server | Weights and adapters | 70B FP8 70 GB, 8B 16 GB, adapters 4 GB |
| Artifactory per region | Signed artifacts, all versions | About 2 TB |
| MLflow and Postgres | Registry, model cards, evals, approvals | Under 50 GB |
| Gateway logs, in region | Metadata for all requests; prompts for EU high-risk use 6 months | About 1 TB a month |
| WORM archive | Decision records and approvals, 7 years | Under 5 TB |

**How:**
1. Cost: 5 servers at an assumed $11.3k a month each is $56.5k, plus an assumed $5k for network and storage: $61.5k a month for 120.6B tokens, about $0.51 per million.
2. By model: the 70B path costs about $1.03 per million tokens against about $2.84 on Sonnet 5.5 ($119.7k a month at list price); the 8B path about $0.23 against about $0.14 on Haiku 5.5 ($11.1k).

**Decision.** Report both comparisons to finance, because the honest result is that the 70B saves money and the 8B is bought for data control.

**Trap.** Comparing against the most expensive API model only. Finance will find the cheaper one.

## 11. Output

The platform returns tokens to teams and numbers to finance and model risk.

**How:**
1. Streamed tokens with usage (prompt, cached, output) on every response.
2. Monthly chargeback per use case at the internal rate per million tokens.
3. Capacity report: peak tokens/s per model against fleet capacity, with months of headroom left.
4. A model card per version: evals, known limits, approved use cases.

**Decision.** Chargeback at a single internal rate per model, so teams can compare the large and small paths in dollars.

**Trap.** Free tokens for internal teams. Demand grows until the fleet is full and nobody knows who filled it.

## 12. Guardrails

Data-class and residency rules live in the gateway's code, never in a prompt or a team's configuration file.

**How:**
1. Every request carries an entity and a data class from the calling service's registration; the gateway refuses mismatches.
2. EU gateways route only to Dublin; US gateways only to Ohio and Texas.
3. Model changes: offline evals per use case, bias tests for EU underwriting, model risk approval, then a 5 percent canary for 7 days.
4. Per-use-case token quotas and output caps; batch never preempts interactive.

**Decision.** The EU high-risk use case keeps prompts and outputs for 6 months and a named human reviewer, as the AI Act requires of deployers, and every model change there is a documented change.

**Trap.** Treating a quantized or new adapter build as "the same model". To a validator it is a new model.

## 13. Key Impact

Five numbers show the platform unblocked the work and runs as a utility.

| Metric | Baseline | Target | How measured |
|---|---|---|---|
| Use cases in production | 5 public-only | 14 | Registry |
| Interactive SLO met | None | 99 percent of minutes | TTFT and TPOT from Prometheus |
| Cost per million tokens | Hosted only | $0.51 blended | Fleet cost over tokens served |
| GPU utilization at peak | None | 60 to 75 percent | DCGM exporter |
| Model change lead time | None | Under 4 weeks | Registry approval timestamps |

**How:**
1. Publish cost per token monthly with the API comparison beside it.
2. Track tokens per use case, to forecast the next server purchase 6 months ahead.

**Decision.** Headline unblocked use cases, because the business case was the 9 blocked ones.

**Trap.** Reporting GPU utilization as success. 95 percent utilization means the SLO is about to break.

## 14. Failure Modes

A fixed fleet fails by losing capacity, so every failure is planned as a capacity problem.

**How:**
1. **One US data center fails**: Texas carries 4 of 8 large replicas at about 126 percent of peak; batch is shed and public and internal traffic goes to the API.
2. **EU server fails**: the spare replica takes it; restricted EU traffic queues, never crosses to the US.
3. **KV pressure**: vLLM preempts the newest sequences; admission sheds batch at 85 percent KV use.
4. **Bad model version**: alias rollback in the registry in under 5 minutes; weights of the last version stay on local NVMe.
5. **GPU failure**: DCGM health checks drain the replica; a cold 70B load from NVMe takes about 90 s.

**Decision.** Degrade by priority, then by data class, so restricted interactive work is the last thing to slow down.

**Trap.** Planning failover as if GPUs scale out like web servers. Buying a server takes months.

## 15. Build Order

Nine months, one data center at a time, buying the last servers only after a load test.

**How:**
1. **Months 1-2**: servers racked, vLLM with the 70B in one US data center, gateway, data-class rule. Measure: TTFT p95 on replayed traffic.
2. **Months 3-4**: 8B with LoRA, prefix routing, admission. Measure: GPUs needed at peak against the plan.
3. **Months 5-6**: second US data center, failover drills, API fallback. Measure: drill recovery time.
4. **Months 7-8**: Dublin fleet, EU logging and AI Act controls. Measure: EU use cases live.
5. **Month 9**: chargeback and capacity forecasting. Measure: cost per million tokens.

**Decision.** Load-test before buying the last servers, because the planning throughputs are assumptions until real prompts run.

**Trap.** Buying the whole fleet on vendor benchmarks. Those use short prompts with no prefix structure.
