### Context
A 1,800-person B2B software company keeps its knowledge in Confluence, Google Drive and Jira, and nobody can find anything. Six help channels (#ask-it, #ask-people, #eng-help and others) get about 3,100 questions a month, and the median wait for a human answer is 47 minutes. Most answers already exist in a runbook, an HR page or a closed ticket. The CTO wants a Slack bot that answers from those sources with links, without ever showing someone a document they could not open themselves.

### Requirements
- Answer questions asked by @mention in channels, in DMs, and through an `/ask` command, replying in the thread.
- Search Confluence, Google Drive and Jira, and cite the documents used with links.
- Respect each source's permissions: a user only gets answers from documents they can open today.
- Follow up inside a thread ("what about contractors?") using the earlier messages.
- Say "I don't know" with the closest links rather than guess.
- Collect thumbs-up and thumbs-down feedback on every answer.

### Scale and constraints
- 1,800 employees plus 150 contractors with limited access; about 40% expected to use it weekly.
- Expected 25,000 questions a month, nearly all on weekdays between 9:00 and 18:00 across two time zones.
- Confluence: 38,000 pages in 210 spaces. Google Drive: 220,000 files, of which 120,000 are Docs, Sheets, Slides and PDFs in shared drives. Jira: 400,000 issues, 150,000 from the last two years.
- About 1% of content changes each day; a permission revocation must take effect within 15 minutes.
- Slack requires an acknowledgement within 3 seconds; first answer text within 4 s at p95.
- HR case files, Legal and Finance compensation folders must never be searchable. Slack Connect channels with external members are out of scope.
- Budget: $1,500 a month for model, embedding and rerank APIs. Team: three engineers, no GPUs. SOC 2 Type II; bot transcripts kept 30 days.

### What a strong answer covers
- How permissions from three systems are mirrored, applied during retrieval, and kept fresh after a revocation.
- What changes when the bot answers in a public channel instead of a DM.
- How the bot meets Slack's 3-second rule while the answer takes several seconds to generate.
- How you keep 1.5 million chunks fresh without re-embedding everything.
- How citations are checked, and what the bot does when the sources do not support an answer.
- A cost and latency estimate, and a way to show the bot actually saves time.
