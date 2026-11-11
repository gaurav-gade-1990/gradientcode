# Writing a GradientCode AI Leadership case

AI Leadership cases are interview prep for principal engineers, AI architects, directors and executives. They use the design-problem machinery: there is no judge, there is a timer and a hidden model answer, learners score themselves against the rubric, and checking 70% of the criteria completes the case. Ids run from 301 to 399. The track is set by the category.

A leadership answer is graded on **scope, cost, people and risk**, not on tools. The candidate makes a call with incomplete information, says what it costs and who pays, and says how they will know if it was wrong.

## The framework: ten sections under four pillars

| Pillar | Sections |
|---|---|
| A. Frame | 1 Situation · 2 Stakeholders |
| B. Decide | 3 Options · 4 Decision and Trade-offs · 5 Economics |
| C. Execute | 6 Org and Ownership · 7 Plan and Milestones · 8 Risk and Governance |
| D. Land | 9 Metrics · 10 Communication |

About five minutes per pillar, so a full answer takes 20–25 minutes to say out loud.

## Difficulty ladder

- **Easy:** one team. The decision sits with you and your manager.
- **Medium:** cross-org. Product, finance, legal and sales each want something different, and you have to bring them along.
- **Hard:** exec or board level, with regulators, a reorg, or a decision that can't be undone.

## Categories

| Key | Covers |
|---|---|
| `lead-strategy` | Build, buy or fine-tune; roadmaps; portfolio and ROI; kill or scale; platform vs embedded teams |
| `lead-org` | Org design, hiring and leveling, performance, retention |
| `lead-governance` | Governance operating models, incidents, model risk, vendor concentration |
| `lead-comms` | Board and exec updates, pushing back, explaining to non-technical leaders, story banks |

## Folder: `problems/<id>-<slug>/`

**`meta.json`**
```json
{"id": 301, "slug": "build-buy-fine-tune", "title": "Build vs Buy vs Fine-tune", "type": "design",
 "difficulty": "Medium", "category": "lead-strategy", "tags": ["Build vs Buy", "TCO", "Vendor Risk"],
 "time_minutes": 45, "related": ["llm-capacity-cost-estimator", "self-hosted-llm-serving"]}
```
`type` is `"design"`, because the case reuses the design workspace. `related` links 3–6 existing design or applied slugs that hold the technical depth behind the case.

**`problem.md`** is the brief, written the way a CTO or CEO would hand it to you. Don't number its headings.
- `### Context`: a named company type (e.g. "a mid-market accounting SaaS", never a real brand), your role, and what is happening, in 3–5 sentences.
- `### What you have`: options, budget, headcount, timeline, data and contracts, as bullets with real numbers.
- `### The constraint`: the one fact that forces a trade-off. Without it there is no case.
- `### What a strong answer covers`: 4–6 bullets that point at the hard parts without answering them.

Every number the model answer needs must be in the brief or derived from it. Label assumed figures in the brief as assumed (e.g. "fully loaded engineer cost, assumed $250k a year").

**`rubric.json`**: the 10 sections in order (`n`, `pillar`, `title`, `prompt`, `criteria`), with 3–4 criteria each. Every criterion is concrete and checkable, e.g. "Compares 3-year cost, not first-year cost", never "shows good judgment".

**`solution.md`**: a `# <Title>: model answer` heading, then exactly `## 1. Situation` … `## 10. Communication` in order.
- **Every section except 2** opens with 1–3 sentences, then an optional table or **How:** steps, then `**Decision.**` (the call and why, against the alternative), then `**Trap.**` directly after it (what most candidates get wrong here).
- **Section 2 (Stakeholders)** is a table, `| Stakeholder | What they want | How you bring them along |`, followed by a line starting `**The one idea to hold:**`.
- **Show level.** Write about scope, money, people and risk. Name tools only when the decision turns on them.
- **Derive every number.** Show the arithmetic once, in the section that needs it, e.g. "16.8M × $0.004 = $67.2k a month". Label every assumption. A figure with no derivation and no label fails review.
- **Economics** compares options over the same horizon (usually 3 years), separates new spend from people already on payroll, and states the opportunity cost.
- **Decision and Trade-offs** says what you give up, whether the decision is reversible, and the trigger that would make you revisit it.
- **Metrics** pairs each success metric with a guard metric that catches the harm it could hide.
- **Communication** gives the one-line message for each audience and the cadence.
- **Each pillar is at most 1000 words**, aiming for about 600–900. Tight bullets and tables, no filler, no emoji.

Model prices are Anthropic list prices as of 2026-10, per MTok: Haiku 5.5 $0.10/$0.50, Sonnet 5.5 $2/$10 with $0.20 cache reads, Opus 5.5 $4/$20 with $0.20 cache reads. Label every other price as assumed.

**`walkthrough.md`** follows the design shape in [WALKTHROUGH.md](WALKTHROUGH.md), using the leadership section names:
1. What the problem is really asking.
2. The numbers that drive the decision.
3. How to spend your time.
4. Pillar A: Frame.
5. Pillar B: Decide.
6. Pillar C: Execute.
7. Pillar D: Land.
8. The decisions that separate strong answers.
9. Common mistakes.
10. Follow-ups an interviewer might ask.

Sections 4–7 have a `### <Section name>` subsection for each of the ten framework sections.

## Check

```
python3 scripts/check.py 301
```
The checker verifies:
- the files and the meta;
- the 10 rubric sections, in order and numbered 1–10, each with a prompt and at least 2 criteria;
- the 10 solution headings, in order;
- the Stakeholders table and its one-idea line;
- a Decision and a Trap in every other section, in the right order;
- the pillar word caps;
- the walkthrough: its required sections, a heading for every framework section, and at least 900 words.
