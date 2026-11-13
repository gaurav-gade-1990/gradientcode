# AI Leadership catalog (ids 301–318)

AI Leadership cases are interview prep for principal engineers, AI architects, directors and executives. They reuse the design workspace: a timer, a hidden model answer, and a self-scored rubric where checking 70% completes the case. Answers use ten sections under four pillars:

| Pillar | Sections |
|---|---|
| A. Frame | 1 Situation · 2 Stakeholders |
| B. Decide | 3 Options · 4 Decision and Trade-offs · 5 Economics |
| C. Execute | 6 Org and Ownership · 7 Plan and Milestones · 8 Risk and Governance |
| D. Land | 9 Metrics · 10 Communication |

Difficulty:
- **Easy:** one team.
- **Medium:** cross-org.
- **Hard:** exec or board level, with regulators or a reorg.

See [AUTHORING_LEADERSHIP.md](../AUTHORING_LEADERSHIP.md) to write a new case.

## lead-strategy (Strategy & Portfolio)
- 0301 build-buy-fine-tune (Medium): an accounting SaaS has 16.8M transactions a month to categorize by hand, with $12M of renewals 6 months out. Its enterprise contracts forbid training on customer data and require notice before adding a sub-processor.
- 0302 ai-roadmap-business-unit (Medium): a 12-month AI roadmap for a $640M contractor-sales unit of an industrial distributor. Six leaders each want something, and an ERP freeze blocks anything that writes quotes or orders in months 4–9.
- 0303 ai-portfolio-roi (Medium): a wireless carrier's AI council gets eight proposals claiming $39M a year. The limit is data-engineer time on customer data, not money.
- 0304 kill-or-scale-pilot (Easy): an AI leasing assistant at an apartment manager missed its target, and only the after-hours effect is real. Legal has fair-housing findings, and half the team leaves in 8 weeks.
- 0305 platform-vs-embedded-teams (Hard): a five-business classifieds group with 150 embedded AI staff has had a data leak and has 90 days to satisfy its audit committee. The largest unit can't move anyone before its launch.

## lead-org (Org & People)
- 0306 design-ai-org-40 (Hard): 40 AI people across four reporting lines at an electric and gas utility, with a utility commission review in 9 months. Headcount is frozen, and validators must be independent of the builders.
- 0307 ai-hiring-plan-leveling (Medium): 12 AI hires for a K-12 learning platform on a fixed budget, against a back-to-school launch. Any AI pay premium must also cover internal transfers.
- 0308 low-performer-critical-project (Easy): a senior engineer at 36% of plan on a 900-location restaurant chain's onboarding, with a $4.8M contract and SLA credits at risk. They hold the only knowledge of the go-live harness, and nothing is documented yet.
- 0309 retaining-principal-engineer (Easy): an email-security company's principal ML engineer has an offer for $520k against $360k and 10 days to answer. The pay committee meets in 6 weeks, and she alone knows the model refresh due in 10.

## lead-governance (Risk & Governance)
- 0310 ai-governance-operating-model (Hard): a European life and health insurer with 212 AI systems, 72 of them unknown to the centre. The supervisor's review is 6 months out, and the countries won't wait in a central queue.
- 0311 hallucination-incident-response (Medium): on day 3 of open enrollment, a benefits assistant is giving wrong dependent-eligibility answers. Switching it off would swamp the contact center, and sales wants to tell only the customer who complained.
- 0312 model-risk-signoff (Hard): a consumer lender with a bank charter has six GenAI use cases worth $21M stuck behind independent validation, and the validators have only 500 free hours.
- 0313 vendor-concentration-exit-plan (Hard): an EU payment institution sends 92% of its LLM traffic to one provider. The board requires a 90-day exit, but the CFO has booked a discount that needs a larger commitment to that same provider.

## lead-comms (Communication & Influence)
- 0314 board-update-ai-spend (Hard): a listed retailer's AI spend is forecast at $24.6M against an $18M plan, and the CFO's margin guidance has 10 bp of cushion. You have 10 minutes with the board.
- 0315 pushing-back-ceo-deadline (Medium): a freight brokerage CEO plans to announce autonomous booking for all shippers in 8 weeks, but carrier vetting needs 10 weeks from signature.
- 0316 explaining-eval-regression (Medium): a privacy-required change cut a fraud model's recall from 33/40 to 29/40 while accuracy rose. Rolling back is illegal, and the sample is small.
- 0317 influence-without-authority-stories (Medium): a story bank built on an online grocer whose substitution rejections come from another VP's catalog data. That VP has said no twice.
- 0318 conflict-and-failure-stories (Medium): a STAR story bank built on an online travel agency's rebooking assistant, which made 2,480 wrong rebookings in 9 days. Includes a scope check per level, from senior engineer to executive.

## Study plans

`problems/study-plans.json` has two plans for this track:
- **Principal / AI Architect Loop:** the five strategy cases, the four governance cases and the four Hard system designs (212–215).
- **Director / Executive Loop:** all 18 cases, plus four designs: 207 llm-gateway-cost-controls, 209 agent-eval-observability, 211 shared-ai-coworker-platform and 214 self-hosted-llm-serving.
