### Context

A bank operates three legal entities: a US national bank, a UK subsidiary and a German subsidiary. Its 450 financial-crime analysts work two queues: KYC cases (new customers and periodic reviews) and AML alerts from a 12-year-old NICE Actimize rules engine, where 95 percent of alerts are closed as false positives after about 25 minutes of manual evidence gathering each. The alert backlog in the US hit 41 days last year, and the bank's regulator flagged it in an exam. The Chief Compliance Officer wants agents that gather evidence and draft case narratives so analysts decide faster, without the bank losing its ability to explain any decision to any of its three regulators years later.

### Requirements

- For each AML alert and KYC case, gather the evidence (customer profile, transactions, screening hits, ownership chain, adverse media, prior cases), draft a narrative and a recommendation with reasons.
- Analysts make every disposition: close, escalate, exit the customer, or file a suspicious activity report. The agent never files a SAR and never contacts the customer.
- Low-risk onboarding with no screening hits may be approved straight through by the bank's validated risk-rating rules.
- Each entity's customer data stays in its jurisdiction: US in the US, UK in the UK, German in the EU.
- Integrate with what exists: Actimize alerts and case manager, a US core banking mainframe (z/OS, DB2), Temenos in the UK and Germany, and screening vendors.
- Model risk management: the system must pass validation under the Fed and OCC's SR 11-7, the PRA's SS1/23 and BaFin's MaRisk before production.
- An examiner can ask for any case from the last 7 years and see the inputs, the agent's draft, the model and prompt versions, and the analyst's decision.

### Scale and constraints

- 6,000 AML alerts a day across entities (US 60 percent, UK 25, Germany 15).
- 1.5 million KYC cases a year: 600,000 onboardings and 900,000 periodic reviews.
- Low-risk onboarding decision in under 10 minutes; US SAR filing within 30 calendar days of initial detection.
- Raw evidence for a case is about 80,000 tokens (90 days of transactions, profile, hits, prior notes).
- Models via an in-region cloud endpoint with no data retention, at Anthropic list prices per million tokens: Sonnet 5.5 $2 input, $10 output, $0.20 cache reads; Opus 5.5 $4 and $20; batch jobs at half price.
- Team: 25 engineers across the three regions, 12 months. Retention: at least 5 years after the relationship ends in all three jurisdictions; the bank keeps 7.

### What a strong answer covers

- Which decisions the model may influence, which it may not, and how that is enforced.
- How three residency boundaries and a legacy mainframe shape the architecture.
- What the model risk validators will ask for, and what you hand them.
- How you show the agent does not miss suspicious activity that analysts would have caught.
- The monthly model and infrastructure cost, with the levers that bring it down.
- How a case from 2027 is reconstructed for an examiner in 2033.
