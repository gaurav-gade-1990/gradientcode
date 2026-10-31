### Context
A B2B payroll and HR software company sells to companies with 50 to 5,000 employees. Inbound leads arrive from HubSpot forms and sit in a shared queue until one of 8 SDRs researches them by hand, which takes about 12 minutes per lead. Median time from a demo request to first contact is 26 hours, and 35% of demo requests are not contacted within two days. Reps also complain that half the "hot" leads they get are students, competitors or 10-person shops the company does not serve. Sales leadership wants an agent that enriches, scores and routes every lead in minutes, and explains why.

### Requirements
- Enrich each lead with company and contact data, plus a short read of the company's website.
- Score each lead against the ideal customer profile (ICP) and explain the top reasons.
- Match the lead to an existing Salesforce account or contact instead of creating duplicates.
- Route qualified leads to the right rep by territory, segment and account ownership, and alert them in Slack with a short brief.
- Write results back to Salesforce without clobbering anything a rep has edited.
- Send low-fit leads to marketing nurture instead of a rep.

### Scale and constraints
- 12,000 leads a month; 25% are demo requests, the rest content downloads, webinar sign-ups and trials. A webinar can produce 1,500 leads in one hour.
- Salesforce holds 180,000 accounts and 600,000 contacts; two years of history has 4,200 opportunities, 610 of them won.
- Demo requests must reach a rep within 5 minutes at p95; other leads within 1 hour.
- Enrichment budget: $2,000 a month. LLM budget: $1,000 a month.
- 20% of leads are in the EU; marketing consent is captured on the form. Do not use protected attributes in scoring.
- Team: three engineers, no GPUs, no ML platform. Salesforce is the system of record and stays that way.

### What a strong answer covers
- Where the score comes from, why a rep should trust it, and how you check that it is calibrated.
- How you avoid creating duplicate accounts, including when many leads from one company arrive at once.
- What the agent may write to the CRM, and what it must never overwrite.
- How enrichment spend and consent are enforced, not just intended.
- A speed-to-lead latency budget by stage and a monthly cost estimate covering both LLM and enrichment calls.
- How you would prove the agent creates more pipeline than the current SDR process.
