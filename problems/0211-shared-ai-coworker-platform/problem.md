### Context

A 6,000-person professional services firm has 25 teams that each want an AI coworker: an accounts-payable clerk, an IT helpdesk, a recruiting coordinator, a sales-ops analyst and more. Three teams already built their own; each took about 10 weeks, each has its own memory store, and two of them disagree about the firm's travel policy because they learned it from different emails. The CIO wants one platform where a team assembles a coworker from shared skills in two weeks, where coworkers share what the firm knows without leaking what individuals or HR know, and where a human approves anything that spends money or leaves the building.

### Requirements

- Coworkers live in Slack, email (Microsoft 365) and tickets (ServiceNow and Jira), and one task can move across all three.
- A shared memory: firm-wide facts, team facts, per-user preferences, and each coworker's own history, with clear scopes.
- A skills marketplace: teams publish versioned skills (instructions, tools, tests) and other coworkers reuse them.
- Permissions: a coworker never does more for a user than that user could do, and HR and finance data stay in their teams.
- Human-in-the-loop: approvals for payments over $1,000, any external email, and any change to HR records, answered from Slack, email or the ticket.
- Tasks can wait days for people; they must survive deploys and restarts.

### Scale and constraints

- 25 coworkers at launch, 80 within a year; 30,000 tasks a day, peak 3 times the average rate on Monday mornings.
- About 4 model calls and 3 tool calls per task; 20 percent of tasks wait on a human for over an hour, some for 5 days.
- Knowledge: 400,000 documents in SharePoint and Confluence with ACLs.
- Slack needs an acknowledgment within 3 seconds; a simple answer should land in under 20 seconds at p95.
- Models per million tokens: Sonnet 5.5 at $2 input, $10 output and $0.20 cache reads; Haiku 5.5 at $0.10 and $0.50.
- Budget: $80,000 a month all in. Team: 10 engineers, 6 months. 1,200 employees are in the EU (GDPR); SOC 2 Type II.

### What a strong answer covers

- How memory is scoped and written so one bad email cannot rewrite what every coworker believes.
- What a skill is, how it is approved, versioned and reused, and who is paid or blamed when it breaks.
- Whose identity a coworker uses for each action.
- How an approval in Slack resumes a task that started in email four days earlier.
- The monthly model bill, and how one team's coworker is kept from spending everyone's budget.
- How you prove a coworker saves time rather than just doing things.
