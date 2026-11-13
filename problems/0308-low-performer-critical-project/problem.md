### Context

You are the engineering manager of a 6-engineer applied AI team at a restaurant online-ordering platform: $340M of annual net revenue, 2,800 restaurant brand customers. The team is building automated menu onboarding: an LLM pipeline that extracts items, prices and modifiers from a chain's menus and checks them against the chain's point-of-sale price book. A 900-location restaurant chain, the largest customer the platform has signed, agreed a statement of work that requires its menus to go live in 10 weeks. One of your senior engineers, Dana, has been falling behind for six weeks, and Dana owns the part of the system that decides whether the project can go live.

### What you have

- **The customer.** The chain's contract is worth $4.8M a year of net revenue. The SOW carries a $40k SLA credit for each week go-live is late, and if it is more than 4 weeks late the chain may terminate at its renewal, 5 months from now.
- **The go-live gate.** 97% field-level accuracy on the chain's 2,000-menu-page test set, measured by the evaluation harness. Dana built the harness and is the only person who knows it well. It has 15 engineer-days of work left, all assigned to Dana, and it has to be done by week 6 so the team can tune accuracy in weeks 7–9 and go live in week 10.
- **The plan.** 150 engineer-days of work remain. Each engineer has 50 working days in the window at an assumed 60% focus after meetings and on-call, and the team has 20 engineer-days committed to on-call and other customers.
- **Dana.** Senior engineer (L5), 3 years on the team, rated above expectations in the last two annual reviews and "meets" at mid-year. In the last 6 weeks: 4 of 11 committed tickets delivered, 2 pull requests reverted after breaking the nightly build, and 2 standups and 1 customer call missed without notice. Two peers each spend about 3 hours a week re-reviewing Dana's work.
- **Lee.** Another senior engineer on the team. Lee owns the price-matching rules, which aren't on the critical path, and has run the harness but didn't build it.
- **What you've said so far.** You mentioned "falling behind" once in a 1:1. Nothing is in writing. Two months ago Dana mentioned that a parent is seriously ill.
- **Money.** You have a $40k discretionary contractor budget this quarter. A contractor who knows document extraction is quoted at $150 an hour (assumed), would need about 3 days to onboard, and works at an assumed 80% focus. Fully loaded cost is assumed at $230k per engineer a year. A backfill is assumed to take 4 months to hire and cost half a year's loaded cost.
- **HR policy.** A formal performance improvement plan needs documented feedback first, lasts at least 45 days, and requires the HR partner to be involved before it starts. The company offers an employee assistance program and job-protected family leave for eligible employees.

### The constraint

The only person who knows the go-live gate is the person who is struggling. A fair process can't skip the steps you haven't taken yet, documented feedback and real support, and it takes longer than the 10 weeks you have. Waiting puts the chain at risk; acting fast and formally would be unfair to Dana and still leave the harness in one person's head.

### What a strong answer covers

- How far behind the project really is if nothing changes, in engineer-days and in dollars.
- What you say to Dana first, what you put in writing, and what support you offer.
- How you protect the go-live without making the project depend on the outcome of Dana's situation.
- How you keep the process fair and documented, and when HR comes in.
- What the team, your manager and the customer hear, and what they don't.
