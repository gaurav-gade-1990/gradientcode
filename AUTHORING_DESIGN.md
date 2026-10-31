# Writing a GradientCode System Design problem

Design problems have no judge. Learners write an answer section by section, then reveal the model answer and score themselves against the rubric. They use the **Unified framework**: fifteen sections under four pillars, about five minutes per pillar, so a full answer takes 20–25 minutes to say out loud.

| Pillar | Sections |
|---|---|
| A. Scope and architecture | 1 Scenario · 2 Single View |
| B. Agents, retrieval, processing | 3 Data Sources · 4 Processing · 5 Agents · 6 Memory · 7 MCP Tool Servers |
| C. Data, infra, serving | 8 Endpoints · 9 Caching · 10 Data Stores · 11 Output |
| D. Health, quality, execution | 12 Guardrails · 13 Key Impact · 14 Failure Modes · 15 Build Order |

Difficulty ladder:
- **Easy:** one company, three engineers, no GPUs.
- **Medium:** tenants, scale, admission control, a durable workflow, and a feature store or event log.
- **Hard (complex):** regulators, legacy systems, several legal entities, data residency.

## Folder: `problems/<id>-<slug>/`

**`meta.json`**
```json
{"id": 201, "slug": "returns-refunds-agent", "title": "Returns & Refunds Agent", "type": "design",
 "difficulty": "Easy", "category": "design-easy", "tags": ["Customer Support", "RAG", "Human Handoff"],
 "time_minutes": 45, "related": ["react-tool-loop", "idempotent-tool-execution"]}
```
`related` links to Applied AI coding problems (slugs from `problems/CATALOG_APPLIED.md`) that build a piece of this design. Link 3–6.

**`problem.md`** is the prompt, written the way an interviewer or customer would hand it over. Do not number its headings like the solution's `## 1. Scenario`.
- `### Context`: who the customer is and what hurts today, in 3–5 sentences.
- `### Requirements`: functional bullets.
- `### Scale and constraints`: real numbers (users, requests per day, documents, latency SLO, budget, team size, compliance).
- `### What a strong answer covers`: 4–6 bullets that hint at the hard parts without giving the answers.

**`rubric.json`**
```json
{"sections": [
  {"n": 1, "pillar": "A", "title": "Scenario",
   "prompt": "Who is the user, what is the job to be done, and what number proves it works?",
   "criteria": ["States the primary user and the job in one sentence", "Names a measurable success metric with a target", "Lists what is explicitly out of scope"]},
  ... all 15, in order, 3-4 criteria each ...
]}
```
Each criterion is a concrete, checkable statement ("Puts the refund limit in code, not in the prompt"), never a vague one like "good security".

**`solution.md`** is the model answer, a `# <Title>: model answer` heading, then exactly these 15 headings in order: `## 1. Scenario`, `## 2. Single View`, … `## 15. Build Order`.
- **Every section except 2 follows the same shape:**
  - Open with what it is and why it's needed in 1–3 sentences.
  - Then **How:** 3–5 implementation steps that name real tools (Postgres + pgvector, Temporal, Redis, Kafka, OPA, LiteLLM, vLLM, the MCP SDK, Datadog, and so on).
  - Then `**Decision.**` (the choice and the reason, against the alternative).
  - Then `**Trap.**` (the mistake most candidates make here).
- **Section 2 (Single View)** is a three-column table: `| Layer | What runs here and what it hands over | Why we need it |`, followed by a line starting `**The one idea to hold:**`.
- **Order inside a section:** the opener, then any table, then **How:**, then `**Decision.**`, then `**Trap.**` directly after it.
- **Single View rows:** 6–8 for Easy and up to 10 for Medium and Hard, so admission control, the workflow engine and the event log can each have a row.
- **Sections 5–7 may say "not an agent".** For a pipeline or infrastructure design, "this step is deterministic code, and here is why" is a full answer. Say what would make you add an agent later.
- **Cost table:** list each cost lever in the order you apply it (model mix, caching, batching, retrieval trimming), with the dollar saving per month. Don't force a "with vs without cache" table when caching isn't the main lever. Prices are Anthropic list prices as of 2026-10 (Haiku 5.5 $0.10/$0.50, Sonnet 5.5 $2/$10 with $0.20 cache reads, Opus 5.5 $4/$20 per MTok). Label any non-model price as assumed.
- **Pillar B holds five sections,** so keep each of them to about 180 words.
- **Numbers everywhere.** Requests per second from the prompt's scale, token costs per month, latency budgets split by stage, and storage sizes. Section 13 (Key Impact) states the business metric and how it is measured.
- **Limits that protect money, permissions or privacy live in code, never in a prompt.** Say so wherever it applies.
- **Each pillar is at most 1000 words**, aiming for about 700–900. This is the most important style rule: tight bullets and tables, no walls of text, no filler, no emoji.

## Check

```
python3 scripts/check.py 201
```
This verifies the files, the meta, the 15 rubric sections in order (each with a prompt and ≥ 2 criteria), the 15 solution headings in order, a Decision and a Trap in every section except 2, and the pillar word caps.
