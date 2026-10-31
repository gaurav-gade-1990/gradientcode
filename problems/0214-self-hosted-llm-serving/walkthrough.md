## 1. What the problem is really asking

This is a **capacity-planning problem with a compliance boundary**. Legal has ruled that claims files, health information and policyholder data can't go to an external model provider, so 14 use cases are blocked or limited to public data. The CIO has approved GPUs. Your job is to work out how many, show how batching, prefix caching, quantization and multi-LoRA bring that number down, and run the fleet as a shared utility with a cost per token finance can check.

The core tension is **a fixed fleet against a variable load**. On-premises GPUs can't scale out in minutes. Buying a server takes months. So you size for peak, protect capacity with admission control and priorities, and accept a hosted API as overflow only for data that's allowed to leave.

Three decisions carry the design:

- **The GPU count comes from peak tokens per second.** You compute KV cache bytes per token, concurrent sequences per replica, and replicas from peak prefill and decode rates at a utilization target. Every optimization is then a lever that lowers that count.
- **One gateway enforces the data-class rule in code.** Restricted data never goes to the fallback API, EU data never leaves Dublin, and model aliases map to pinned, signed versions from a registry.
- **The cost case is honest.** Self-hosting the 70B is cheaper than Sonnet 5.5 at list price. Self-hosting the 8B is *more* expensive than Haiku 5.5. The project is justified by data control and regulation, and the answer says so.

The model answer's one idea: the GPU count comes from peak tokens per second, and everything else is a lever that lowers it.

## 2. The numbers that drive the design

This problem is graded heavily on arithmetic. Work through it in this order.

**Request rate.**

- 1.2M requests / 86,400 s = **13.9 requests/s average**.
- Peak is 4 times that: **55.6 requests/s**.
- Large model (35 percent): 0.35 × 55.6 = **19.4 requests/s at peak**. Small model (65 percent): **36.1 requests/s**.

**Tokens a month.** 1.2M × 30 days × 3,000 prompt tokens = **108B input**; × 350 output tokens = **12.6B output**. Total 120.6B. The prefill side is about 9 times the decode side by count, which is why prefix caching matters.

**KV cache bytes per token.** The formula is 2 (K and V) × layers × KV heads × head dim × bytes per element.

| Model | Arithmetic | KV per token |
|---|---|---|
| 70B: 80 layers, 8 KV heads, head dim 128, FP8 (1 byte) | 2 × 80 × 8 × 128 × 1 | **160 KB** |
| 8B: 32 layers, 8 KV heads, head dim 128, BF16 (2 bytes) | 2 × 32 × 8 × 128 × 2 | **128 KB** |

**Concurrent sequences per replica.** A sequence is 3,000 prompt + 350 output = 3,350 tokens.

- 70B on 2 H100s: 160 GB × 0.9 = 144 GB usable, minus 70 GB of FP8 weights and 4 GB of activations, leaves **about 70 GB** for KV. 70 GB / (160 KB × 3,350) ≈ **127 sequences**.
- 8B on 1 H100: 72 GB usable, minus 16 GB weights, 4 GB activations and adapters, leaves **about 52 GB**. 52 GB / (128 KB × 3,350) ≈ **118 sequences**.

**Replicas from peak tokens per second.** The model answer's planning throughputs are **assumed until load-tested**: a 70B FP8 TP2 replica does 2,000 output and 12,000 prefill tokens/s; an 8B GPU does 5,000 and 40,000.

| | 70B | 8B |
|---|---|---|
| Output tokens/s at peak | 19.4 × 350 ≈ 6,800 | 36.1 × 350 ≈ 12,600 |
| Prefill tokens/s after prefix hits | 19.4 × 3,000 × (1 − 0.40) ≈ 35,000 | 36.1 × 3,000 × (1 − 0.20) ≈ 86,700 |
| Decode replicas | 6,800 / 2,000 = 3.4 | 12,600 / 5,000 = 2.5 |
| Prefill replicas | 35,000 / 12,000 = 2.9 | 86,700 / 40,000 = 2.2 |
| Busy | 6.3 replicas | 4.7 GPUs |
| At 70 percent utilization | **9 replicas (18 GPUs)** | **6.7 GPUs** |

**Cost per GPU.** Each 8-GPU server is assumed at $300,000 over 3 years ($8.3k a month) plus $3,000 for power, space and support, about **$11.3k a month**. Five servers are $56.5k, about **$1.41k per H100-month**.

**The lever table.** Reveal the model answer for its full table. Each row recomputes the GPU count above with one more lever:

| Lever | H100s | Cost a month |
|---|---|---|
| Everything on 70B BF16 at TP4, no prefix caching | 136 | $192k |
| FP8 weights and KV, TP2: same throughput on half the GPUs | 68 | $96k |
| Model mix: 65 percent to the 8B with LoRA | 32 | $45k |
| Prefix caching, 40 and 20 percent hits (the table above) | 25 | $35k |
| Batching: claims backlog summaries moved overnight | 23 | $32k |

Then residency and spares push the active count to **31**: US 16 GPUs for the 70B and 6 for the 8B, EU 6 and 3. That's why the fleet is 5 servers: 3 in the US across Ohio and Texas, 2 in Dublin.

**Cost per million tokens.** $56.5k for servers + an assumed $5k for network and storage = $61.5k a month over 120.6B tokens ≈ **$0.51 per million** blended.

**The honest comparison.** Split by path:

| Path | Self-hosted | Hosted at list price | Who wins |
|---|---|---|---|
| 70B vs Sonnet 5.5 | about $1.03/M | 37.8B × $2 + 4.41B × $10 = $119.7k a month, about $2.84/M | Self-hosted |
| 8B vs Haiku 5.5 | about $0.23/M | 70.2B × $0.10 + 8.19B × $0.50 = $11.1k a month, about $0.14/M | Hosted |

**TTFT budget.** At p95: Envoy and auth 8 ms + admission 5 ms + queue 150 ms + prefill 450 ms + first token 60 ms ≈ **675 ms**, under 800 ms. Decode of 350 tokens at 35 ms each is about 12 s streamed, with TPOT under 50 ms.

## 3. How to spend your time

| Minutes | What you do |
|---|---|
| 0–10 | Read the prompt. Do request rates, tokens a month, KV bytes per token, sequences per replica. Write them down; you'll reuse all of them. |
| 10–18 | **Pillar A.** Why self-host (data control, not cost), US and EU apart, the nine layers. |
| 18–40 | **Pillar B.** Artifact signing, the replica table, the lever table with GPU counts. Processing and Agents carry most of the marks. |
| 40–55 | **Pillar C.** The TTFT table, aliases and priority classes, narrow response caching, cost per million with both comparisons. |
| 55–70 | **Pillar D.** Gateway enforcement, model change process and the AI Act, losing a data center, load test before buying. |
| 70–75 | Recheck the arithmetic. A wrong KV formula or average-instead-of-peak sinks the answer. |

## 4. Pillar A: Frame

### Scenario

**The question:** why self-host, for whom, and which numbers shape the fleet?

The users are 14 use-case teams who need an endpoint they're allowed to send claims data to, and finance, who need a cost per token. The platform is a shared on-premises inference service in three data centers with one gateway.

How to reason about *why*: the tempting pitch is "self-hosting is cheaper." Section 2 shows that's only half true. The real justification is **data control, DORA concentration risk and EU AI Act oversight**. Make the cost case honestly per model size.

Convert the scale up front: 13.9 and 55.6 requests/s, 108B and 12.6B tokens a month. **Separate US and EU from the start**, because the EU fleet needs its own spare. Baselines: 9 use cases blocked, 5 on a hosted API with public data only. Agree the data-class rule with legal: restricted never leaves; public and internal may use the API. Out of scope: training base models, and fine-tuning beyond LoRA.

**The trap:** selling the project as cheaper than the API. Finance will check, and on the 8B path it isn't.

**Rubric:** average and peak requests per second (1.1), monthly tokens (1.2), justification by data control and regulation (1.3), and US and EU separate (1.4).

### Single View

**The question:** draw the path from a client to a GPU and to the fallback API.

Nine layers: Clients (team apps, Guidewire, mainframe batch through MQ) → Gateway (LiteLLM behind Envoy) → Admission (token buckets, three priority classes, queue-depth shedding) → Router (prefix-aware, vLLM production-stack router or llm-d) → Engines (vLLM, 70B FP8 TP2 and 8B BF16 with 24 LoRA adapters) → Fleet → Fallback (hosted API, public and internal only) → Model registry (MLflow with signed hashes) → Telemetry.

The reasoning for separating admission from routing: admission decides *whether* a request runs (a fixed fleet must say no early, with a 429 and retry-after); routing decides *where* it runs (prefix hits only pay off if requests land where the cache is). Merging them loses one of the two.

**The trap:** a load balancer in front of vLLM and nothing else. No quotas, no data-class rule, no prefix routing.

**Rubric:** one gateway with auth, quotas and the data-class rule (2.1), admission and a prefix-aware router as distinct steps (2.2), an engine with continuous batching and multi-LoRA (2.3), and a registry of signed versions (2.4).

## 5. Pillar B: Build the core

### Data Sources

**The question:** what are the platform's inputs, and how do model artifacts arrive safely?

Four inputs: traffic from 14 use cases, **each registered with entity, data class, priority, model and token quota**; model artifacts; eval sets per use case approved by model risk; and a week of real request sizes replayed for capacity tests.

For artifacts: **safetensors only**, checked against the vendor's published hashes, scanned, **signed with Sigstore cosign**, and mirrored into an internal Artifactory per region. Engines load only signed artifacts from that mirror.

The reasoning: a pickle file can execute code on load, and a public hub revision can change under you. Pulling at deploy time puts unvetted code next to claims data.

**The trap:** pulling weights from a public hub at deploy time.

**Rubric:** use-case registration (3.1), safetensors, hashes, scanning and signing (3.2), and an internal mirror (3.3).

### Processing

**The question:** how many concurrent sequences fit per replica, and how many GPUs does peak need?

This is the arithmetic section. Show the KV formula, the sequences per replica, and the replica table from section 2. Say clearly that the per-replica throughputs are **assumptions to be load-tested**.

Two further decisions:

- **FP8 weights and KV for the 70B**, validated on each use case's eval set, because it halves GPUs per replica at a measured quality cost under 1 point.
- **Chunked prefill at 2,048 tokens**, so long prompts loading don't stall decode for other sequences and TPOT stays under 50 ms.

**The trap:** sizing from average load. Average is 13.9 requests/s; peak is four times that.

**Rubric:** the KV formula with all factors (4.1), sequences from free HBM (4.2), GPU count from peak tokens/s at a utilization target (4.3), and throughput labeled as an assumption (4.4).

### Agents

**The question:** is there an agent here, and which levers reduce the fleet?

**Not an agent.** Serving is deterministic infrastructure, and routing is a rule on use case and data class. Say what would change that: you'd add a model-based router only if teams couldn't say which model size they need (problem model-router).

Then the lever table, in order: quantization (136 → 68), model mix (→ 32), prefix caching (→ 25), batch shifting (→ 23), with dollar savings of $96k, $51k, $10k and $3k a month. Notice that quantization and model mix together do almost all of the work.

The multi-LoRA decision: one 8B base serving 24 adapters at about 160 MB each (about 4 GB in all) beside one copy of the weights. The alternative, one deployment per fine-tune, makes 24 adapters into 48 mostly idle GPUs once you add failover.

**The trap:** one dedicated GPU per fine-tune.

**Rubric:** "not an agent" with what would justify one (5.1), levers in order with monthly savings (5.2), and multi-LoRA on one base (5.3).

### Memory

**The question:** what state does the serving layer keep?

**Not an agent memory: the only state is the KV cache**, managed as a tier. HBM holds active sequences, with vLLM's automatic prefix caching keeping shared system prompts resident. LMCache offloads hot prefixes to CPU memory (1 TB per server), so an evicted prefix reloads faster than it recomputes. The router hashes the first 1,024 tokens to send repeat prefixes to the same replica. Engines keep no prompts or outputs.

The decision: teams put **stable text first and variable text last**, enforced by a gateway lint, because prefix hits need byte-identical prefixes.

**The trap:** a timestamp or user name at the top of the system prompt. The prefix hit rate falls to zero and the fleet needs 2 more replicas.

**Rubric:** KV cache as the only state (6.1), offloading hot prefixes (6.2), and stable text first (6.3).

### MCP Tool Servers

**The question:** what's the platform's role in tool use?

**Not an agent: no MCP servers sit in the serving path.** Tool calling belongs to the clients. The platform supports it with **guided decoding** (xgrammar in vLLM) for JSON schemas, so extraction adapters always return valid JSON. A small read-only MCP server lets internal agents ask about quotas, versions and SLO status. Tool definitions count against the caller's token quota like any prompt.

The reasoning: 14 teams writing JSON repair loops is 14 sources of retries, so constrained decoding belongs in the platform. But executing tools would make the platform own other teams' side effects.

**The trap:** letting the model call tools from inside the serving layer.

**Rubric:** tool execution stays with clients (7.1), constrained decoding (7.2), and tool definitions counted against quotas (7.3).

## 6. Pillar C: Serve and store

### Endpoints

**The question:** what's the API, and how is the TTFT budget spent?

`POST /v1/chat/completions` and `/v1/completions`, OpenAI-compatible, with `model` as an **alias** (`large-reasoning`, `small-extract:claims-fnol`) mapped to a pinned version. Three priority classes: interactive, near-real-time and batch, with batch admitted only below 60 percent KV use. `POST /v1/batches` for mainframe and Guidewire jobs, finished within 8 hours.

Show the TTFT table: about 675 ms at p95, mostly prefill (section 2).

Fallback: a request marked public or internal goes to the hosted API in region when queue wait passes 400 ms. **Restricted requests get a 429.**

**The trap:** failing over restricted traffic to the API "just during the outage." That's the exact disclosure the platform exists to prevent.

**Rubric:** a TTFT budget under 800 ms (8.1), aliases to pinned versions (8.2), priority classes and a batch endpoint (8.3), and restricted data never to the fallback (8.4).

### Caching

**The question:** beyond the KV cache, what's safe to cache?

Prefix caching on every engine with prefix-aware routing is the cache that matters. Response caching is narrow: an **exact-match cache per use case for deterministic extraction** (temperature 0), keyed by model version, adapter version and input hash, kept 24 hours, opt-in per use case. No cross-use-case or semantic caching of restricted data. The 8 most used adapters are pinned resident on each 8B GPU.

**The trap:** a semantic cache across the copilot. Two claims with similar wording get each other's summaries.

**Rubric:** response caching only for deterministic requests keyed on versions (9.1), no semantic caching of restricted data (9.2), and resident adapters (9.3).

### Data Stores

**The question:** what's stored where, and what does a million tokens cost?

Weights on local NVMe per server (70B FP8 70 GB, 8B 16 GB, adapters 4 GB). Signed artifacts in Artifactory per region (about 2 TB). Registry, cards, evals and approvals in MLflow and Postgres. Gateway logs in region (about 1 TB a month, with prompts kept 6 months for the EU high-risk use case). Decision records in a WORM archive for 7 years.

Then the cost: $61.5k a month, about $0.51 per million blended, with hardware and facility prices labeled assumed. And the honest split from section 2: 70B about $1.03 vs $2.84 on Sonnet 5.5; 8B about $0.23 vs $0.14 on Haiku 5.5.

**The trap:** comparing against the most expensive API model only. Finance will find the cheaper one.

**Rubric:** cost per million from fleet cost and tokens (10.1), each path compared with a similar hosted model (10.2), saying where hosted is cheaper (10.3), and assumed labels (10.4).

### Output

**The question:** what do teams, finance and model risk receive?

Streamed tokens with **usage including cached tokens** on every response. Monthly **chargeback per use case at a single internal rate per model**. A capacity report: peak tokens/s per model against fleet capacity, with months of headroom left. **A model card per version**: evals, known limits, approved use cases.

The reasoning for chargeback: free tokens grow demand until the fleet is full and nobody knows who filled it.

**The trap:** free tokens for internal teams.

**Rubric:** usage with cached tokens (11.1), chargeback (11.2), and a model card per version (11.3).

## 7. Pillar D: Run it safely

### Guardrails

**The question:** how are residency, data class and model change controlled?

- Every request carries an entity and data class from the caller's registration; **the gateway refuses mismatches**.
- EU gateways route only to Dublin; US gateways only to Ohio and Texas.
- Model changes: offline evals per use case, bias tests for EU underwriting, model risk approval, then a **5 percent canary for 7 days**.
- Per-use-case token quotas and output caps; batch never preempts interactive.

The EU high-risk use case keeps prompts and outputs for 6 months and has a named human reviewer, the deployer duties under the AI Act. And **a quantized model or rebuilt adapter is a new model** to a validator, so it goes through the same process.

**The trap:** treating a quantized or new adapter build as "the same model."

**Rubric:** data class and region in gateway code (12.1), evals, approval and canary for changes (12.2), quantized or retrained as new (12.3), and AI Act deployer duties (12.4).

### Key Impact

**The question:** what proves the platform worked?

Five metrics: use cases in production (5 public-only → 14), interactive SLO met (99 percent of minutes), cost per million tokens ($0.51 blended, published monthly beside the API comparison), GPU utilization at peak (60 to 75 percent), and model change lead time (under 4 weeks).

Headline unblocked use cases, because the business case was the 9 blocked ones.

**The trap:** reporting GPU utilization as success. 95 percent utilization means the SLO is about to break.

**Rubric:** use cases unblocked (13.1), TTFT and TPOT attainment (13.2), and cost per token beside the API (13.3).

### Failure Modes

**The question:** what happens when capacity is lost?

- **One US data center fails:** Texas carries 4 of 8 large replicas. US peak needs about 80 percent of the 6.3 busy replicas, about 5, so 4 replicas run at **about 126 percent of peak**. Batch is shed and public and internal traffic goes to the API.
- **EU server fails:** the spare takes it; restricted EU traffic queues and **never crosses to the US**.
- **KV pressure:** vLLM preempts the newest sequences; admission sheds batch at 85 percent KV use.
- **Bad model version:** alias rollback in the registry in under 5 minutes, with the last version's weights still on local NVMe.
- **GPU failure:** DCGM drains the replica; a cold 70B load from NVMe takes about 90 s.

The order of degradation: by priority, then by data class, so restricted interactive work is the last to slow down.

**The trap:** planning failover as if GPUs scale out like web servers.

**Rubric:** surviving-DC load computed (14.1), shedding by priority and class with EU data kept in the EU (14.2), and registry rollback with local weights (14.3).

### Build Order

**The question:** how do you bring the fleet up in 9 months?

One US data center with the 70B, gateway and data-class rule (months 1–2, TTFT p95 on replayed traffic); 8B with LoRA, prefix routing and admission (3–4, GPUs needed at peak vs the plan); the second US data center with failover drills (5–6, drill recovery time); Dublin with EU logging and AI Act controls (7–8, EU use cases live); chargeback and forecasting (9, cost per million).

**Load-test before buying the last servers**, because the planning throughputs are assumptions until real prompts run.

**The trap:** buying the whole fleet on vendor benchmarks, which use short prompts with no prefix structure.

**Rubric:** load test before buying (15.1), one region at a time with drills (15.2), and a number per phase (15.3).

## 8. The decisions that separate strong answers

**Computing the GPU count vs quoting one.** Weak answers say "we'll start with 4 servers." Strong answers show KV bytes per token, sequences per replica, decode and prefill replicas at peak, a 70 percent utilization target, and then residency and spares. Every lever is a recomputation of the same table, so the examiner can follow why each one saves what it does.

**Honest cost vs flattering cost.** It's tempting to compare the whole fleet to Sonnet 5.5 and claim a big saving. The strong answer splits by path, admits the 8B loses to Haiku 5.5 at $0.23 vs $0.14 per million, and justifies that path by data control. That honesty is what makes finance trust the 70B number.

**Fixed-fleet degradation vs cloud-style failover.** On a fixed fleet, losing a data center means running at about 126 percent of peak on what's left. The strong answer sheds batch, sends only public and internal traffic to the API, and never moves restricted or EU data. The weak answer assumes more GPUs appear.

## 9. Common mistakes

- Sizing from average load instead of peak.
- Getting the KV formula wrong: forgetting the factor of 2 for K and V, or using attention heads instead of KV heads.
- Ignoring prefill. With 3,000-token prompts, prefill is a large share of GPU time.
- One deployment per LoRA adapter.
- Letting restricted data fail over to the API during an outage.
- Comparing only against the most expensive hosted model.
- Treating a quantized model as the same validated model.
- Pulling weights from a public hub at deploy time.
- Buying the full fleet before any load test.

## 10. Follow-ups an interviewer might ask

- *Prefix hit rate drops from 40 percent to 10 percent after a team changes its prompt.* The 70B prefill load rises, the router metrics show it, and the gateway lint should have caught variable text at the top. Recompute replicas from the new prefill rate (problem gpu-capacity-planner).
- *Why continuous batching rather than static batches?* Sequences finish at different lengths; continuous batching admits new ones as slots free up, keeping GPUs busy without waiting for the slowest (problem continuous-batching-scheduler).
- *A team wants a dedicated GPU for its fine-tune.* Serve it as a LoRA adapter on the shared 8B unless its eval shows the adapter can't reach quality.
- *Could you autoscale?* Only within the fixed fleet, by moving batch to off-peak and shifting replicas between models. You can't add GPUs in minutes (problem autoscaler-policy).
- *How do you stop one team's batch job starving interactive traffic?* Per-use-case token buckets, batch admitted only below 60 percent KV use, and batch never preempts interactive (problem token-bucket-rate-limiter).
