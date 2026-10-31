## 1. What the problem is really asking

Meeting summaries are a solved demo. What the COO is paying for is **follow-through**: 38% of agreed action items never reach Jira or Linear, and the coworker exists to close that gap. So the product is not "notes"; it's "the right ticket, owned by the right person, filed only after they said yes".

The core tension is between recall and trust. The more action items the model extracts, the more get tracked, but every ticket nobody agreed to teaches the company to ignore the bot. Layered on top is Legal's condition: nothing recorded or shared without consent, across California, New York and Berlin, with outside participants in a quarter of meetings.

Three decisions carry the design:

- **Precision over recall on action items.** Every item needs an owner who is a resolved invitee, a quote that exists in the transcript, and a Haiku veto check. Then the owner approves it in Slack before any ticket exists.
- **The invitee list at meeting time is the access list.** It decides who reads the notes, enforced with Postgres row-level security, and it's the only source the access rule reads.
- **One long-context call, not map-reduce.** A 40-minute meeting is about 8,000 tokens. Splitting it costs more and loses decisions that span segments.

## 2. The numbers that drive the design

**Volume.**

| Step | Arithmetic | Result |
|---|---|---|
| Meetings a month | 600 a workday × 21 workdays | 12,600 |
| Meeting minutes | 12,600 × 40 min | 504,000 min = 8,400 hours |
| Concurrent bots | given | 120 at the 10:00 peak |
| End-of-hour burst | about 100 meetings end within 5 minutes | 20 jobs a minute |

**Transcript size.** About 200 tokens a minute, so a 40-minute meeting is about 8,000 tokens and 3 hours is about 36,000. Both fit comfortably in one call; the model answer only map-reduces above 100,000 tokens.

**Time from end to notes.** The target is 5 minutes at p95:

| Stage | p95 |
|---|---|
| Recall.ai recording finalized | 60 s |
| Deepgram batch transcription | 30 s |
| Speaker alignment and redaction | 5 s |
| Notes call, 1,200 output tokens | 30 s |
| Action-item call and Haiku checks | 15 s |
| Grounding check and posting | 5 s |
| Total | 145 s |

60 + 30 + 5 + 30 + 15 + 5 = 145 s, well under 300 s. That's why batch transcription is good enough.

**Model cost per meeting.** Both Sonnet calls send the same 11,000 tokens (3,000 prefix + 8,000 transcript). The model answer prices the first call's transcript as a cache write at $2.50 per MTok, so the second call can read all 11,000 at $0.20.

| Call | Without cache | With cache |
|---|---|---|
| Notes: 11,000 in, 1,200 out | 11,000 × $2/1M + 1,200 × $10/1M = $0.034 | 3,000 × $0.20/1M + 8,000 × $2.50/1M + $0.012 = $0.033 |
| Action items: 11,000 in, 600 out | 11,000 × $2/1M + 600 × $10/1M = $0.028 | 11,000 × $0.20/1M + $0.006 = $0.008 |
| Haiku item checks | $0.001 | $0.001 |
| Per meeting | $0.063 | $0.042 |
| Per month (× 12,600) | about $794 | about $527 |

**All-in cost.** This is the table that reorders your priorities.

| Monthly | Arithmetic | Cost |
|---|---|---|
| Recall.ai bot | 8,400 h × assumed $0.50/h | $4,200 |
| Deepgram batch | 504,000 min × $0.0043 | about $2,170 |
| Model calls | from above | about $530 |
| AWS | from the model answer | $400 |
| Total | about $0.58 a meeting | about $7,300 of $8,000 |

The model is the smallest line. If an interviewer pushes on cost, the levers are the bot and transcription, not prompts.

**Storage and impact.** Audio at about 30 MB an hour is 8,400 × 30 MB ≈ 250 GB written a month; with a 7-day lifecycle about 60 GB is live. 15 minutes of note-taking saved per meeting × 12,600 = 3,150 hours a month.

## 3. How to spend your time

| Minutes | What you do |
|---|---|
| 0–3 | Restate the job as follow-through; write meetings, hours, the hourly burst and the budget |
| 3–8 | **Pillar A:** two metrics (ticketed and precision); the Single View with an approval step |
| 8–16 | **Pillar B:** invitees as access list, speaker events not diarization, one long call, carry-over memory, tools under the user's OAuth |
| 16–22 | **Pillar C:** the 145 s budget, the all-in cost table, row-level security, timestamp-linked notes |
| 22–27 | **Pillar D:** consent and outsiders, impact with a rollout comparison, failure modes, consent-first build order |
| 27–45 | Follow-ups, usually consent edge cases |

The prompt's five "strong answer" bullets map almost one-to-one to Guardrails, Processing, Agents, Scenario and Caching. Make sure each gets its own spoken minute.

## 4. Pillar A: Frame

### Scenario

**The question:** who is the user, what is the job, and which numbers shape the design?

**How to reason.** The users are meeting organizers and the people who own action items; the job is "agreed work ends up tracked". Write the volume and burst numbers. Build an eval set by hand-labelling 100 past meetings (decisions, items, owners, due dates), and take the baseline from the prompt's 200-meeting sample: 38% untracked, so 62% tracked.

Two targets, agreed with the COO: **ticketed action items above 85%**, and **approved-item precision above 90%**. The second is the guard: a ticket nobody agreed to costs trust; a missed one costs one manual ticket. Out of scope for v1: live in-meeting answers, cross-meeting search, and 1:1s, interviews and HR meetings.

**The trap.** Measuring summary quality with a judge score alone.

**Rubric criteria earned:** job as tracked actions; monthly meetings, hours and the hourly peak; follow-through and precision targets; v1 scope.

### Single View

**The question:** what are the layers?

**How to reason.** Follow one meeting: calendar sync decides eligibility before anything joins; a Recall.ai bot joins all three platforms and records audio with per-participant speaker events; Deepgram transcribes with keyterm boosting; SQS plus ECS workers run six idempotent steps with status in Postgres; Sonnet and Haiku produce JSON notes and checks; a grounding check drops anything without a real quote; the Slack app posts notes and DMs owners with Approve, Edit, Discard; a workspace MCP server files tickets under the approving user's OAuth; Langfuse runs the 100 labelled meetings in CI.

The rubric wants the **owner approval step between item and ticket** to be visible. The one idea: the model drafts and proposes; code decides who may see; the owner decides what's filed.

**The trap.** A diagram where the model writes straight to Jira.

**Rubric criteria earned:** separate calendar, bot, transcription, model and ticket layers; owner approval visible; the drafts-versus-decides idea.

## 5. Pillar B: Build the core

### Data Sources

**The question:** which inputs, and which one decides who may see the notes?

**How to reason.** Four inputs: calendar events (title, invitees, organizer, recurrence id, opt-in), audio with speaker events (deleted after 7 days), the Google Workspace directory (to map speakers to people), and open tickets from the last occurrence of a recurring meeting. Subscribe to Google Calendar push and Microsoft Graph change notifications. Schedule a bot 1 minute before start **only if the organizer opted in** and title and calendar rules allow it. Pull a team glossary nightly for transcription keyterms.

The decision: the **invitee list at meeting time** is the access list. Someone forwarded the invite later doesn't inherit the transcript.

**The trap.** Joining every meeting on any calendar the bot can see. Opt-in per organizer, with HR, interview and 1:1 titles excluded by a code rule.

**Rubric criteria earned:** invitee list as access list; opt-in with exclusions by rule; audio retention limit.

### Processing

**The question:** how does audio become a transcript with the right names on it?

**How to reason.** Two ways to know who spoke: audio diarization, or the platforms' own active-speaker events. Zoom, Meet and Teams already know who is talking; diarization guesses and mislabels crosstalk. So align Deepgram's timed words (40 minutes returns in about 30 s) to Recall's per-participant timeline. Then map display names to directory emails **through the invitee list**: exact email first, then a name match above 0.9. Anyone unmatched becomes "Speaker 3" and is never given an action item. That's the answer to the prompt's "what happens when it can't be attributed".

Redact spoken card numbers and national ids with Presidio before any model call. State the size: about 8,000 tokens per 40-minute meeting.

**The trap.** Trusting display names. "iPhone (2)" and shared conference-room accounts are common.

**Rubric criteria earned:** speaker events with a reason; mapping through invitee emails; unresolved speakers unassigned; transcript size in tokens.

### Agents

**The question:** what's the control flow from transcript to notes and action items?

**How to reason.** The steps are fixed, so it's a pipeline, not a tool-using agent. Two Sonnet calls against Pydantic schemas: notes (summary, decisions, open questions; 11,000 in, 1,200 out) and action items (owner, text, due date, quote, timestamp; 11,000 in, 600 out). Then Haiku per item (2,000 in, 20 out): "is this a commitment someone made?" Repair malformed JSON once, then fail the step.

Now the prompt's explicit question: **one call or pieces?** Decide with numbers. A 40-minute meeting is 8,000 tokens; even 3 hours is about 36,000. One call keeps cross-segment decisions intact and costs fewer calls. Map-reduce by 20-minute segments only above 100,000 tokens (problem map-reduce-documents).

Drop any item whose quote isn't in the transcript or whose owner is unresolved, and send those to the organizer as "unassigned" (problem grounded-answer-check).

**The trap.** Treating every "we should" as an action item. Require an owner and a commitment verb, and let Haiku veto the rest.

**Rubric criteria earned:** fixed pipeline with a reason; one-call-versus-map-reduce by token count; owner and quote on every item; a veto step.

### Memory

**The question:** what does the coworker remember, and what does it deliberately forget?

**How to reason.** Four tiers, each with a store and expiry: the run (transcript and step outputs, Postgres, transcript 90 days), the series (open items from the last occurrence, keyed by recurrence id, until the series ends), the team glossary (a sheet, synced nightly), and approvals (pending items expire after 72 h). For recurring meetings, carry over **only the open items and their ticket status**, about 300 tokens, after the cache breakpoint. Store every owner edit as a new labelled example. The organizer can purge audio, transcript and notes with one button.

The deliberate forgetting: **no vector memory of past meetings in v1.** Cross-meeting search widens who can see what, and nobody asked for it.

**The trap.** Feeding the full previous transcript to every recurring meeting.

**Rubric criteria earned:** carry-over without the old transcript; tiers with store and expiry; deletion on request.

### MCP Tool Servers

**The question:** which tools write to Slack, Docs and the tracker, and under whose identity?

**How to reason.** One workspace server with four tools: `post_notes(meeting_id, target)` (target must be an invitee DM or a channel the organizer chose), `request_approval(item_id, owner)` (owner must be a resolved invitee), `create_ticket(item_id, project, idempotency_key)` (requires an approval row and a project the user can see), and read-only `get_ticket_status`.

The key identity choice: **file tickets as the approving user via OAuth**, not as a bot account. Then Jira's own permissions decide which projects are allowed, and you don't rebuild a permission model. Store refresh tokens encrypted with KMS and refresh single-flight per user so 30 parallel approvals don't race (problem oauth-single-flight-refresh). Use `meeting_id + item_hash` as the idempotency key with a unique index, so a double click files one ticket.

**The trap.** Letting the model choose the Jira project from the transcript. The owner picks it on the card, defaulting to their team.

**Rubric criteria earned:** tickets only with an approval record; writes as the user; idempotency key; owner chooses the destination.

## 6. Pillar C: Serve and store

### Endpoints

**The question:** what's the API surface, and how is the 5-minute budget spent?

**How to reason.** Webhooks in: `POST /hooks/calendar` and `POST /hooks/recall`, signature-verified, deduped on event id, enqueued. `POST /slack/interactions` acks inside Slack's 3 s and processes the approval on a worker. `GET /meetings/{id}` serves notes only to invitees after Google sign-in, and `DELETE /meetings/{id}` is the organizer purge. Show the 145 s stage table.

Batch versus streaming transcription is the decision the rubric wants argued: batch is $0.0043 a minute against about $0.0077 streaming, more accurate, and still lands in 145 s. Nobody needs live captions for a post-meeting summary.

**The trap.** Doing approval work inside the Slack request. Over 3 s, Slack shows an error and retries, filing twice without the idempotency key.

**Rubric criteria earned:** a stage budget under 5 minutes; Slack ack within 3 s; signatures and dedupe; batch transcription with a reason.

### Caching

**The question:** what can be cached when every meeting is unique, and what does it cost?

**How to reason.** There's no result cache to speak of: two meetings never share a transcript, and a cached summary would be a privacy bug. The useful cache is **the transcript reused between the two Sonnet calls**. Order the prompt as 3,000 tokens of system prompt, schemas and three worked examples, a breakpoint, the transcript, a second breakpoint, then the step instruction. Run both calls back to back inside the 5-minute cache window. That takes the action-item call from $0.028 to $0.008, and the month from about $794 to $527. Then show the all-in table, about $7,300 of $8,000, so the interviewer sees you know where the money actually goes.

**The trap.** Putting the step instruction before the transcript. The second call then misses the cache on 8,000 tokens.

**Rubric criteria earned:** transcript cached across the two calls; per-meeting and monthly model cost with and without; all-in cost within budget.

### Data Stores

**The question:** where do audio, transcripts and notes live, how big are they, and how is access enforced?

**How to reason.** S3 with SSE-KMS for audio: 250 GB written a month, about 60 GB live under a 7-day lifecycle rule. RDS Postgres for meetings, invitees, transcripts, notes, items and approvals: about 630 MB of transcripts a month, 2 GB at 90 days, with a nightly purge. Redis for directory caches and OAuth refresh locks. Langfuse traces, redacted, with the same 90-day retention. A `pipeline_step` table (meeting, step, status, attempt) lets a retry skip finished steps.

The decision: **enforce invitee-only access with Postgres row-level security** on `invitee_email`, not a check in the web handler. A new endpoint written next quarter can't forget it.

**The trap.** Keeping raw transcripts in the tracing tool forever.

**Rubric criteria earned:** audio and transcript sizes; lifecycle and purge; access enforced in the data layer.

### Output

**The question:** what does the coworker produce, and how can a reader check it?

**How to reason.** Three typed outputs: notes (summary, decisions with timestamps, open questions, items) as a Google Doc shared with invitees and a Slack post; an approval card per item (owner, due date, quote with a timestamp link, project picker) in the owner's DM; and, after approval, a ticket linking back to the moment in the recording. Render notes from JSON with a fixed template so every meeting reads the same.

The decision: **every claim carries a timestamp link**, so checking a quote takes 10 s. Trust comes from checking, and checking has to be one click.

Post to a channel only if every member was an invitee or the organizer explicitly chose it; otherwise DM invitees.

**The trap.** Posting notes to the channel named in the invite, which often contains people who weren't in the room.

**Rubric criteria earned:** fixed template from structured data; timestamp links; no posting to channels with non-invitees.

## 7. Pillar D: Run it safely

### Guardrails

**The question:** what enforces consent, access and no-unapproved-tickets if the model or a participant pushes on them?

**How to reason.** Build the rule table. Consent: the bot joins only on organizer opt-in, names itself "Notetaker (recording)" and posts a notice in chat. Outside participants: if an external email is invited, the organizer confirms in Slack before the bot joins, and notes stay internal. Excluded meetings: title and calendar rules in code. Who reads: invitee list plus row-level security. No unapproved tickets: `create_ticket` refuses without an approval row. Retention: lifecycle and purge jobs.

Then the edge cases the prompt hints at. When someone from a two-party-consent state or the EU joins late, the bot reposts its notice, and anyone typing "stop recording" ends it for everyone. Treat the transcript as data: someone saying "file a ticket giving me admin" produces at most a card the owner can discard. Log every transcript access with user and time.

**The trap.** Relying on the platform's recording banner as consent. A bot is a participant, and California and Germany expect a clear notice from it.

**Rubric criteria earned:** consent and notice including outsiders and two-party consent; transcript as untrusted data; rules in code; transcript access logged.

### Key Impact

**The question:** what moves, and how do you know the coworker moved it?

**How to reason.** Headline: agreed action items ticketed, 62% to above 85%, measured on a monthly hand-labelled sample of 50 meetings. Guard: approved-item precision above 90%, plus per-team discard rate (above 15% flags a prompt or speaker-mapping problem). Supporting: notes within 5 minutes 95% of the time, 70% of eligible meetings opted in by week 8, cost per meeting under $0.65. Attribution: compare first-wave teams against teams not yet enabled. Time saved: about 3,150 hours a month.

**The trap.** Counting tickets created. Volume goes up when precision goes down.

**Rubric criteria earned:** baseline and target for ticketed items; a precision or discard guard; enabled versus not-yet-enabled comparison.

### Failure Modes

**The question:** what breaks, and what catches it?

**How to reason.** Meetings fail physically. Bot stuck in the waiting room: Recall reports `waiting_room` for 2 minutes, so DM the organizer to admit it. Speaker unresolved: items go to the organizer as unassigned, never to a guess. Invented action: the quote check drops it; drops above 5% a day alert. Jira or Linear down: the approved item stays queued and retries with the same idempotency key for 24 h (problem idempotent-tool-execution). On-the-hour pile-up: about 100 meetings end within 5 minutes, two Sonnet calls each at 11,000 input tokens, so the model answer sizes the API tier for 500,000 input tokens a minute and lets SQS absorb the burst.

Alert on pipeline age over 10 minutes, drop rate and join failures; keep a per-team kill switch for ticket filing.

**The trap.** Retrying the whole pipeline on a late failure, which re-posts the notes. Retry only the failed step.

**Rubric criteria earned:** bot stuck in a lobby; invented or unattributable items; tracker down with idempotent retry; the burst with a capacity number.

### Build Order

**The question:** in what order, and what number unlocks each step?

**How to reason.** Consent and access first, model quality second, ticket writes last. Week 1: 100 labelled meetings. Week 2: calendar, opt-in, bot and transcription for one team (95% join success, name error under 3% on the glossary), with legal reviewing consent rules before it goes live. Week 3: notes with timestamp links (decision recall above 80%). Week 4: action items with the quote check and Haiku veto, shown but not filed (precision above 90%). Week 5: approvals and filing for two teams (zero unapproved tickets, discard under 15%). Week 6: company rollout behind per-team LaunchDarkly flags (85% ticketed).

**The trap.** Shipping ticket filing in week 2 because it demos well.

**Rubric criteria earned:** labelled set first; a number per step; consent and access first, tickets last.

## 8. The decisions that separate strong answers

| Decision | Weak answer | Strong answer |
|---|---|---|
| What counts as an action item | Anything the model lists | Owner is a resolved invitee, quote exists in the transcript, Haiku confirms a commitment, owner approves |
| Long transcripts | Map-reduce by default | One call: 8,000 tokens for 40 minutes; map-reduce only above 100,000 |
| Who can read notes | The channel in the invite, checked in the handler | Invitees at meeting time, enforced by row-level security |

## 9. Common mistakes

- Optimising summary quality and never measuring how many agreed items got tracked.
- Filing tickets from a bot account, so permissions have to be reinvented.
- Diarization guesses or display names deciding who owns a task.
- Treating the platform recording banner as consent.
- A cost estimate that covers only the model, missing the bot and transcription that make up most of the budget.
- Retrying the whole pipeline and posting notes twice.

## 10. Follow-ups an interviewer might ask

- *A Berlin customer joins 10 minutes late. What happens?* The bot reposts its recording notice; if they type "stop recording" it stops for everyone. Because an external email was on the invite, the organizer already confirmed the bot in Slack, and the notes stay internal.
- *Two people with the same first name are in the room. Who gets the item?* Mapping goes through invitee emails with a name match above 0.9. If it's still ambiguous, the speaker is unresolved and the item goes to the organizer as unassigned.
- *The owner double-clicks Approve.* The idempotency key `meeting_id + item_hash` and its unique index mean one ticket.
- *A 3-hour workshop arrives. One call or pieces?* About 36,000 tokens, still well under the 100,000-token threshold, so one call.
- *Leadership wants search across all past meetings. What changes?* It widens who can see what, so every result has to be filtered by the invitee list per meeting, the same pre-filter pattern as problem 202 (internal-knowledge-slack-bot).
