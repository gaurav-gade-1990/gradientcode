### Context
A 1,500-person software company lives in meetings: Zoom for customers, Google Meet internally, a few teams on Microsoft Teams. Notes are taken by whoever volunteers, and a sample of 200 meetings showed that 38% of agreed action items never reached Jira or Linear. The COO wants an AI coworker that joins meetings, posts notes and action items within minutes of the meeting ending, and files tickets for the people who own them. Legal has one condition: nothing is recorded or shared that the participants did not agree to.

### Requirements
- Join scheduled meetings on Zoom, Meet and Teams when the organizer has turned it on, and announce itself.
- Within minutes of the end, post notes (summary, decisions, open questions, action items with owners) to the meeting's Slack channel or the organizer's DM and to a Google Doc.
- For each action item, ask its owner to approve, edit or discard it in Slack; on approval, create a Jira or Linear ticket in a project they can access.
- Only invitees can read a meeting's notes and transcript.
- Never file a ticket nobody approved.

### Scale and constraints
- 600 recorded meetings a workday, average 40 minutes; 120 run at once at the 10:00 peak.
- About 12,600 meetings and 8,400 meeting hours a month.
- 25% of meetings include someone outside the company; offices in California, New York and Berlin.
- Notes posted within 5 minutes of the meeting ending, p95.
- Budget: $8,000 a month all in. Team: three engineers, no GPUs.
- Audio kept no more than 7 days, transcripts 90 days. 1:1s, interviews and HR meetings are excluded by default.

### What a strong answer covers
- How the bot gets consent, and what happens when an outside participant joins.
- How speech is attributed to the right person, and what happens when it cannot be.
- Whether to summarize a long transcript in one call or in pieces, decided with numbers.
- Why a wrong ticket is worse than a missed one, and how the design reflects that.
- A cost breakdown across the bot, transcription and the model, and the time from meeting end to notes.
