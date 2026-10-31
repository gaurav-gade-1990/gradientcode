# Meeting Notes Coworker: model answer

## 1. Scenario
Employees lose agreed work between the meeting and the tracker. The coworker records meetings people opted into, writes notes they can trust, and turns action items into tickets only after the owner says yes.

| What | Number | What it drives |
|---|---|---|
| Volume | 600 meetings a workday, 12,600 and 8,400 hours a month | Batch pipeline per meeting; no streaming model calls |
| Peak | 120 bots at once at 10:00; about 100 meetings end within 5 minutes on the hour | Worker pool sized for 20 jobs a minute |
| Freshness | Notes within 5 minutes of the end, p95 | Batch transcription is fast enough |
| Outsiders | 25% of meetings; California and Berlin participants | Consent rules in code, per meeting |
| Budget | $8,000 a month | The bot and transcription cost more than the model |

**How:**
1. Label 100 past recorded meetings by hand: decisions, action items, owners, due dates. This is the eval set.
2. Measure the baseline from the 200-meeting sample: 38% of action items never ticketed.
3. Agree two targets with the COO: ticketed action items above 85%, and approved-item precision above 90%.
4. Out of scope for v1: live in-meeting answers, search across past meetings, and 1:1s, interviews and HR meetings.

**Decision.** Optimize for precision over recall on action items. A ticket nobody agreed to costs trust; a missed one costs one manual ticket.

**Trap.** Measuring "summary quality" with a judge score alone. The business number is how many agreed actions end up tracked.

## 2. Single View

| Layer | What runs here and what it hands over | Why we need it |
|---|---|---|
| Calendar sync | Google Calendar and Microsoft Graph webhooks. Hands over meetings with invitees, organizer and opt-in flag | Decides which meetings are eligible before anything joins |
| Meeting bot (Recall.ai) | Joins Zoom, Meet, Teams; records audio with per-participant speaker events. Hands over audio and a speaker timeline | One API across three platforms |
| Transcription (Deepgram) | Batch speech-to-text with keyterm boosting. Hands over timed words | Names and product terms must be spelled right |
| Pipeline workers (SQS + ECS) | Six idempotent steps per meeting, status in Postgres. Hands over a notes record | Each step retries alone; a crash never re-posts notes |
| Model (Claude Sonnet 5.5, Haiku 5.5) | Notes and action items as JSON; a Haiku check per item. Hands over structured notes | The only steps that need language understanding |
| Grounding check | Each decision and action must quote a span that exists in the transcript. Hands over pass or drop | Invented action items never reach a person |
| Slack app | Posts notes, DMs owners with Approve, Edit, Discard. Hands over approvals | The owner, not the model, decides a ticket exists |
| Workspace MCP server | Jira, Linear, Google Docs, Slack tools under the approving user's OAuth. Hands over ticket ids | Tickets land only where the owner has access |
| Evals and traces (Langfuse) | 100 labeled meetings in CI; every run traced | Prompt changes ship on precision and recall |

**The one idea to hold:** the model drafts notes and proposes actions; code decides who may see them and the owner decides what gets filed.

## 3. Data Sources
Four inputs, each with its own owner and its own rules.

| Source | What it gives | Rule |
|---|---|---|
| Calendar events | Title, invitees, organizer, recurrence id, opt-in flag | Read via webhook; the only source of who may see notes |
| Meeting audio and speaker events | 40 minutes average, per-participant active-speaker events | Deleted from S3 after 7 days |
| Company directory (Google Workspace) | Names, emails, teams, manager | Maps speakers to people |
| Open tickets for recurring meetings | Last meeting's action items and their status | Lets notes say "carried over" |

**How:**
1. Subscribe to Google Calendar push notifications and Microsoft Graph change notifications; store each event with its invitee list.
2. Schedule a Recall.ai bot 1 minute before start only if the organizer opted in and the title and calendar rules allow it.
3. Pull the team glossary (project names, customer names) from a shared sheet nightly for transcription keyterms.

**Decision.** The invitee list at meeting time is the access list. Someone forwarded the invite later does not inherit the transcript.

**Trap.** Joining every meeting on a calendar the bot can see. Opt-in per organizer, with HR, interview and 1:1 titles excluded by a code rule.

## 4. Processing
Audio becomes a speaker-labeled transcript the model can quote from.

**How:**
1. On `recording.done` from Recall.ai, send audio to Deepgram Nova batch with the team's keyterms and smart formatting; 40 minutes returns in about 30 s.
2. Align words to Recall's per-participant speaker timeline; map display names to directory emails through the invitee list (exact email first, then name match above 0.9).
3. Label unmatched voices "Speaker 3" and never assign them an action item.
4. Redact spoken card numbers and national ids with Presidio before any model call; a 40-minute meeting is about 8,000 tokens.

**Decision.** Use platform speaker events, not audio diarization. Zoom, Meet and Teams already know who is talking; diarization guesses and mislabels crosstalk.

**Trap.** Trusting display names. "iPhone (2)" and a shared conference-room account are common; resolve through invitee emails or leave the speaker unknown.

## 5. Agents
This is a pipeline with the model in two steps, not a tool-using agent. The steps are fixed, so code owns the order.

| Step | Model | In / out tokens |
|---|---|---|
| Notes: summary, decisions, open questions | Sonnet 5.5 | 11,000 / 1,200 |
| Action items: owner, text, due date, quote, timestamp | Sonnet 5.5 (same cached transcript) | 11,000 / 600 |
| Item check: "is this a commitment someone made?" | Haiku 5.5, per item | 2,000 / 20 |

**How:**
1. Run both Sonnet calls with structured output against Pydantic schemas; repair malformed JSON once, then fail the step.
2. Drop any item whose quote is not found in the transcript or whose owner is an unresolved speaker; send the organizer those as "unassigned".
3. Summarize in one call up to 3 hours (about 36,000 tokens); map-reduce by 20-minute segments only above 100,000 tokens.

**Decision.** One long-context call beats map-reduce here. A 40-minute meeting is 8,000 tokens; splitting it loses decisions that span segments and costs more calls.

**Trap.** Treating every "we should" as an action item. Require an owner and a commitment verb, and let Haiku veto the rest.

## 6. Memory
Most memory belongs to other systems; the coworker keeps meeting records and series context.

| Tier | Holds | Lives in | Expires |
|---|---|---|---|
| Run | Transcript, step outputs | Postgres row per meeting | Transcript 90 days |
| Series | Open action items from the last occurrence | Postgres, keyed by recurrence id | When the series ends |
| Team | Glossary of names and projects | Sheet, synced nightly | Edited by the team |
| Approvals | Pending, approved, discarded items | Postgres | 72 h pending, then expired |

**How:**
1. For a recurring meeting, add last time's open items and their ticket status after the cache breakpoint.
2. Store every edit an owner makes to an item; edits become new labeled examples each week.
3. Purge on request: the organizer can delete a meeting's audio, transcript and notes from one button.

**Decision.** No vector memory of past meetings in v1. Search across meetings widens who can see what, and nobody has asked for it yet.

**Trap.** Feeding the full previous transcript to every recurring meeting. Carry over the open items only, about 300 tokens.

## 7. MCP Tool Servers
One workspace server built with the Python MCP SDK; every write runs under the approving user's OAuth token.

| Tool | Does | Guard in code |
|---|---|---|
| `post_notes(meeting_id, target)` | Slack message plus Google Doc | Target must be a DM to an invitee or a channel the organizer chose |
| `request_approval(item_id, owner)` | Slack DM with three buttons | Owner must be a resolved invitee |
| `create_ticket(item_id, project, idempotency_key)` | Jira or Linear issue | Requires an approval record; project must be visible to the user |
| `get_ticket_status(ticket_id)` | Status for carry-over | Read only |

**How:**
1. Store refresh tokens encrypted with AWS KMS; refresh single-flight per user so 30 parallel approvals do not race.
2. Use `meeting_id + item_hash` as the idempotency key and a unique index on it, so a double click files one ticket.
3. Return typed errors (`no_access`, `approval_missing`, `rate_limited`) that the pipeline maps to a Slack reply.

**Decision.** File tickets as the approving user, not as a bot account. Jira's own permissions then decide which projects are allowed.

**Trap.** Letting the model choose the Jira project from the transcript. The owner picks it on the approval card, with a default from their team.

## 8. Endpoints
Webhooks in, one Slack interactions route, and a notes page.

| Stage (meeting end to notes posted) | p95 |
|---|---|
| Recall.ai recording finalized | 60 s |
| Deepgram batch transcription | 30 s |
| Speaker alignment and redaction | 5 s |
| Notes call (1,200 output tokens) | 30 s |
| Action-item call and Haiku checks | 15 s |
| Grounding check, post to Slack and Docs | 5 s |
| **Total** | **145 s, under the 5 min target** |

**How:**
1. `POST /hooks/calendar`, `POST /hooks/recall`: verify signatures, dedupe on event id, enqueue to SQS.
2. `POST /slack/interactions`: acknowledge within Slack's 3 s limit, then process the approval on a worker.
3. `GET /meetings/{id}`: notes and transcript, served only to invitees after Google sign-in.
4. `DELETE /meetings/{id}`: organizer purge of audio, transcript and notes.

**Decision.** Batch transcription after the meeting instead of streaming. It costs $0.0043 a minute against about $0.0077 for streaming, is more accurate, and still lands in 145 s.

**Trap.** Doing the approval work inside the Slack request. Anything over 3 s shows the user an error and Slack retries, filing twice without the idempotency key.

## 9. Caching
Every meeting is unique, so the useful cache is the prompt, and the transcript reused between the two calls.

| Per meeting | Without cache | With cache |
|---|---|---|
| Notes call: 3,000 prefix + 8,000 transcript in, 1,200 out | $0.034 | $0.033 (prefix read at $0.20, transcript written at $2.50) |
| Action-item call: same 11,000 in, 600 out | $0.028 | $0.008 (all 11,000 read at $0.20) |
| Haiku item checks | $0.001 | $0.001 |
| **Per meeting / per month at 12,600** | **$0.063 / $794** | **$0.042 / $527** |

All in, the model is the smallest line:

| Monthly | Cost |
|---|---|
| Recall.ai bot, 8,400 h at an assumed $0.50/h | $4,200 |
| Deepgram batch, 504,000 min at $0.0043 | $2,170 |
| Model calls | $530 |
| AWS (ECS, RDS, S3, SQS) | $400 |
| **Total, about $0.58 a meeting** | **$7,300 of the $8,000 budget** |

**How:**
1. Put the system prompt, schemas and three worked examples (3,000 tokens) first, then a breakpoint, then the transcript and a second breakpoint, then the step instruction.
2. Run the two Sonnet calls back to back within the 5-minute cache window.
3. Cache directory lookups and calendar events in Redis for 10 minutes.

**Decision.** No semantic or result cache. Two meetings never share a transcript, and a cached summary would be a privacy bug.

**Trap.** Putting the step instruction before the transcript. The second call then misses the cache on 8,000 tokens.

## 10. Data Stores
S3 for audio, Postgres for everything else.

| Store | Holds | Size |
|---|---|---|
| S3 (SSE-KMS) | Audio, about 30 MB an hour | 250 GB written a month, about 60 GB live with 7-day lifecycle |
| RDS Postgres | Meetings, invitees, transcripts, notes, items, approvals | About 630 MB of transcripts a month, 2 GB at 90 days |
| Redis | Directory and calendar cache, OAuth refresh locks | Under 1 GB |
| Langfuse | Traces, with transcripts redacted | About 2 GB a month |

**How:**
1. Apply an S3 lifecycle rule that deletes audio after 7 days; a nightly job deletes transcripts after 90.
2. Store the invitee list on each meeting row and enforce reads with Postgres row-level security on `invitee_email`.
3. Keep a `pipeline_step` table (meeting, step, status, attempt) so a retry skips finished steps.

**Decision.** Row-level security in the database, not a check in the web handler. A new endpoint written next quarter cannot forget it.

**Trap.** Storing raw transcripts in the tracing tool forever. Redact traces, and set the same 90-day retention there.

## 11. Output
Two artifacts and one card per action item, all from typed data.

| Output | Contains | Goes to |
|---|---|---|
| Notes | Summary, decisions with timestamps, open questions, action items | Google Doc shared with invitees; Slack post |
| Approval card | Item, owner, due date, quote with timestamp link, project picker | Owner's Slack DM |
| Ticket | Title, description, link back to the moment in the recording | Jira or Linear, after approval |

**How:**
1. Render notes from the JSON with a fixed template, so every meeting reads the same way.
2. Link each decision and item to its timestamp in the recording, so a reader can check the quote in 10 s.
3. Post to a channel only if every channel member was an invitee or the organizer explicitly chose it; otherwise DM invitees.

**Decision.** Every claim in the notes carries a timestamp link. Trust comes from checking, and checking has to be one click.

**Trap.** Posting notes to the channel named in the invite. Channels often contain people who were not in the room.

## 12. Guardrails
Each rule below holds even if the model or a participant tries to get around it.

| Rule | Enforced by |
|---|---|
| Consent | Bot joins only on organizer opt-in, names itself "Notetaker (recording)", posts a notice in chat |
| Outside participants | If an external email is invited, the organizer must confirm in Slack before the bot joins; notes stay internal |
| Excluded meetings | Title and calendar rules (1:1, interview, HR, legal) in code |
| Who reads notes | Invitee list plus row-level security |
| No unapproved tickets | `create_ticket` refuses without an approval row |
| Retention | S3 lifecycle and nightly purge jobs |

**How:**
1. Treat the transcript as data: a participant saying "file a ticket giving me admin" produces at most a card the owner can discard.
2. When a participant from a two-party-consent state or the EU joins late, the bot reposts its notice; anyone typing "stop recording" ends the recording for everyone.
3. Log every access to a transcript with user and time.

**Decision.** Limits that protect privacy and permissions live in code, never in the prompt. The prompt cannot be talked into widening who sees the notes.

**Trap.** Relying on the platform's recording banner as consent. A bot is a participant, and California and Germany expect a clear notice from it.

## 13. Key Impact
The headline is follow-through, with precision as its guard.

| Metric | Baseline | Target | Measured by |
|---|---|---|---|
| Agreed action items ticketed | 62% | Above 85% | Monthly sample of 50 meetings, hand-labeled |
| Approved-item precision | n/a | Above 90% | Approve rate plus labeled set |
| Notes posted within 5 min | n/a | 95% | Pipeline timestamps |
| Opted-in meetings | 0 | 70% of eligible by week 8 | Calendar flags |
| Cost per meeting | n/a | Under $0.65 | Billing per meeting |

**How:**
1. Track approve, edit and discard rates per team; a discard rate above 15% flags a prompt or speaker-mapping problem.
2. Estimate time saved: 15 minutes of note-taking per meeting is about 3,150 hours a month.
3. Compare follow-through for teams in the first wave against teams not yet enabled.

**Decision.** Ticketed-and-approved is the headline. Notes nobody acts on are a nicer email, not impact.

**Trap.** Counting tickets created as success. Volume goes up when precision goes down.

## 14. Failure Modes
Meetings fail in physical ways: bots get stuck in lobbies and audio is noisy. Each case needs a visible fallback.

- **Bot stuck in the waiting room.** Recall reports `waiting_room` for 2 minutes; DM the organizer to admit it.
- **Speaker cannot be resolved.** Items go to the organizer as unassigned, never to a guess.
- **Model invents an action.** The quote check drops it; drops above 5% a day alert the team.
- **Jira or Linear is down.** The approved item stays queued and retries with the same idempotency key for 24 h.
- **On-the-hour pile-up.** 100 meetings end within 5 minutes, which is 200 Sonnet calls and about 450,000 input tokens a minute. SQS absorbs the burst, async workers run 200 pipelines at once, and the API tier is sized for 500,000 input tokens a minute.

**How:**
1. Inject each failure in staging: a stub lobby, an unmatched speaker, a 503 from Jira.
2. Alert in Datadog on pipeline age over 10 minutes, drop rate, and bot join failures.
3. Keep a per-team kill switch for ticket filing.

**Decision.** Fail toward fewer tickets. Unassigned and unverified items go to the organizer, not into a tracker.

**Trap.** Retrying the whole pipeline on a late failure. It re-posts notes; retry only the failed step.

## 15. Build Order
1. **Week 1:** 100 labeled meetings and the baseline. Number: 38% of actions untracked.
2. **Week 2:** calendar sync, opt-in, bot, transcription for one team. Number: 95% join success, name error rate under 3% on the glossary.
3. **Week 3:** notes generation with timestamp links. Number: decision recall above 80% on the eval set.
4. **Week 4:** action items with quote check and Haiku veto, shown but not filed. Number: precision above 90%.
5. **Week 5:** Slack approvals and ticket filing for two teams. Number: zero unapproved tickets, discard rate under 15%.
6. **Week 6:** company rollout behind per-team flags. Number: 85% of agreed items ticketed.

**How:**
1. Gate each week on its number in CI against the labeled set.
2. Roll out team by team with LaunchDarkly flags.
3. Review consent and outside-participant rules with legal before week 2 goes live.

**Decision.** Consent and access first, model quality second, ticket writes last.

**Trap.** Shipping ticket filing in week 2 because it demos well.
