# Global Real-Time Voice Support Agent: model answer

## 1. Scenario

The user is a traveller on the phone, often stressed and mid-disruption, who wants a rebooking or an answer in their own language without waiting 90 minutes. The job is to resolve the simple half of calls end to end and hand the rest to a human with the work already done.

| What | Number | What it forces |
|---|---|---|
| Calls | 180,000 a day, 5.4M a month, 32.4M minutes | Speech cost per minute dominates the bill |
| Concurrency | 750 average, 4,000 in disruption | Speech capacity must scale 5 times in minutes |
| Turns | 14 per call, 75.6M a month | The model cost is per turn |
| Turn latency | Under 800 ms p95 | Streaming at every stage, small model by default |
| Human cost | Assumed $1.10 a minute, $35.6M a month | 45 percent resolution at 4 minutes a call saves about $10.7M a month |
| Entities | 5 regions, 12 languages | Regional speech stacks; languages launched in waves |

**How:**
1. Pull 3 months of call reasons by language: rebooking, baggage and check-in are 52 percent of calls.
2. Baselines: 12 percent IVR containment, 90-minute holds in disruption, 6-minute average handle time.
3. Define resolved: no human, no callback within 72 hours, no complaint.
4. Out of scope: outbound calling, loyalty account changes, refunds over the waiver rules.

**Decision.** Resolve three intents fully before touching the rest, because a voice agent that half-handles everything sends angry callers to humans with nothing done.

**Trap.** Measuring containment as calls that did not reach a human. Callers who hang up in frustration count as contained.

## 2. Single View

| Layer | What runs here and what it hands over | Why we need it |
|---|---|---|
| Telephony | Avaya via SIP through AudioCodes SBCs; Genesys Cloud via AudioHook. Hands over a call's audio stream and caller metadata | Two legacy platforms, one media path |
| Media server | LiveKit with SIP per region, echo cancellation, VAD, playback tracking. Hands over caller audio frames and played-word positions | Barge-in and timing live here |
| Turn detection | VAD plus a small semantic end-of-turn model. Hands over "caller finished" | The largest single latency item |
| Speech to text | Self-hosted streaming ASR on L4 GPUs per region. Hands over partial and final transcripts | Latency and residency control |
| Dialogue agent | Haiku 5.5 by default, Sonnet 5.5 for rebooking reasoning, streaming. Hands over reply text sentence by sentence and tool calls | Fast first token |
| Tools | MCP servers over Amadeus Altéa, baggage, Siebel, payments, transfer. Hand over typed results | Real actions with limits in code |
| Text to speech | Vendor neural voices in region, phrase cache. Hands over audio with word timestamps | 12 languages of natural voice |
| Payments | A PCI DSS Level 1 DTMF-masking service. Hands over a card token | Card data never touches our systems |
| Handoff | SIP REFER back to the ACD queue with a summary in Genesys participant data or Avaya UUI. Hands over a warm transfer | Humans start where the agent stopped |
| QA and records | Transcripts per region, Haiku judge on all calls, native-speaker QA on 2 percent. Hands over scores per language | Quality where nobody on the team speaks the language |

**The one idea to hold:** latency is spent in turn detection and first tokens, and the call history must record what the caller actually heard, not what the model wrote.

## 3. Data Sources

The agent reads live operational systems; nothing about a booking is indexed.

**How:**
1. **Amadeus Altéa**: booking, flight status and rebooking availability through its web services, by PNR and last name.
2. **Waiver rules**: disruption waivers published by operations, loaded as a versioned rule table, not as prompt text.
3. **Baggage**: WorldTracer status by tag number.
4. **Policies**: baggage allowance and check-in rules per carrier in 12 languages, retrieved from a small pgvector index.
5. **Siebel CRM**: customer tier and open cases, read-only except case creation.

**Decision.** Waivers are a rule table the rebooking tool enforces, because a waiver read by the model from text can be talked wider by a caller.

**Trap.** Translating policies on the fly from English. Legal wording differs by market; index the approved local text.

## 4. Processing

Audio is processed as a stream; every stage starts before the previous one ends.

**How:**
1. Language is set by the dialled number, then confirmed by language ID on the first 3 seconds; callers may switch mid-call.
2. Streaming ASR emits partials every 100 ms; the final transcript lands 50 to 80 ms after end of turn.
3. The model's reply is cut at sentence boundaries; sentence one goes to TTS while the model writes sentence two.
4. While payment is active, the media server stops sending audio to ASR and recording, by system control, not by an agent pressing pause.
5. PNRs, names and phone numbers in transcripts are replaced with tokens before storage and QA.

**Decision.** Sentence-level streaming into TTS, because waiting for the full reply adds 1 to 2 seconds per turn.

**Trap.** Running ASR on the payment segment and redacting afterwards. The card number was already processed and stored.

## 5. Agents

One dialogue agent per call with a small, fixed toolset; the model mix is the main cost lever.

| Lever, in order | Model cost a month | Saving a month |
|---|---|---|
| Start: Sonnet 5.5 on 75.6M turns, 4k input, 60 output, no caching | $650k | |
| Model mix: Haiku 5.5 for 80 percent of turns | $156k | $494k |
| Prompt caching of the 2.5k system prefix (Haiku cache reads assumed at $0.01) | $74.4k | $81.6k |
| History trimming: summarize beyond 6 turns, 1.5k to 0.9k tokens | $52.6k | $21.8k |

**How:**
1. Sonnet 5.5 is used only for rebooking option reasoning and tangled multi-leg trips, chosen by the workflow state, not the model.
2. Replies are capped at 2 sentences; voice rewards short turns.
3. Handoff triggers in code: two failed intents, the caller asks for a person, or a tool error on a write.

**Decision.** Haiku 5.5 by default, because its first token fits the budget and most turns are confirmations.

**Trap.** Using the larger model everywhere "for quality". It adds about 100 ms to every turn and, even with caching, about $235k a month.

## 6. Memory

Memory is the call, plus what the airline already knows.

**How:**
1. Call state in Redis per region: language, verified identity, PNR, intent, tools called, the transcript as played.
2. On barge-in, the assistant turn is truncated to the words the media server reports as played, using TTS word timestamps.
3. Prior contact: the last 30 days of cases from Siebel, read at call start.
4. No long-term voice memory and no voiceprints.

**Decision.** History is what the caller heard, because if the model thinks it offered three flights and the caller heard one, the next turn is nonsense.

**Trap.** Voice biometrics for identity. It is special-category biometric data under GDPR and LGPD; use PNR plus last name, with an SMS code before changes.

## 7. MCP Tool Servers

Tools are MCP servers per region; limits that protect money live in the tools.

**How:**
1. `find_booking(pnr, last_name)`, `flight_status`, `baggage_status(tag)`, `create_case`.
2. `search_rebooking(pnr, constraints)` returns at most 3 options inside the waiver table; `rebook(pnr, option_id, idempotency_key)` refuses any fare difference not covered or paid.
3. `start_secure_payment(amount)` hands the call to the DTMF service and returns a token or a failure.
4. `transfer(queue, summary)` performs the SIP REFER with the summary attached.

**Decision.** The fare and waiver limits are checked inside `rebook`, because a persuasive caller can talk a model past any limit written in a prompt.

**Trap.** A rebooking tool without an idempotency key. A dropped call and a retry book the passenger twice.

## 8. Endpoints

The voice path is media, not HTTP; latency is measured from the end of caller speech to the first reply audio.

| Stage | p50 | p95 |
|---|---|---|
| Carrier and SBC ingress | 30 ms | 50 ms |
| End-of-turn detection | 180 ms | 230 ms |
| ASR final transcript | 50 ms | 80 ms |
| Model first token, cached prefix | 180 ms | 250 ms |
| First sentence to TTS first audio | 90 ms | 120 ms |
| Egress to caller | 30 ms | 50 ms |
| **Turn latency** | **about 560 ms** | **about 780 ms** |

**How:**
1. SIP trunks terminate on SBCs per region; Genesys streams through AudioHook WebSockets; both reach LiveKit SIP in the caller's entity region.
2. A tool call over 700 ms triggers a cached filler phrase immediately, so silence never passes 1.5 s while Altéa answers in 1.5 to 3 s.
3. Barge-in: VAD on caller audio during playback, with echo cancellation; playback stops within 150 ms, and short backchannels ("mm-hm") are ignored.
4. Admission: at 4,000 concurrent calls, new calls go to the human queue with an offer of a callback.

**Decision.** Run the whole loop in the caller's region, because a round trip across an ocean costs 150 ms the budget does not have.

**Trap.** A REST call per turn to a central service. It adds network hops on every turn and crosses borders.

## 9. Caching

Text to speech is the largest bill, so caching speech matters more than caching text.

**How:**
1. Cache audio for fixed phrases (greetings, the AI and recording disclosures, fillers, confirmations) per language and voice: about 25 percent of spoken characters.
2. At an assumed $16 per million characters, 9.07B characters a month cost $145k; the phrase cache cuts that to $109k, saving $36k.
3. Prompt-cache the system prompt and tool schemas per language.
4. Cache flight status for 60 seconds per flight during disruption, when thousands ask about the same flight.

**Decision.** Pre-render disclosures, because they are said on every call and must be word-perfect in each language.

**Trap.** Caching personalized sentences. A cached "your flight to Lisbon" plays to a caller going to Tokyo.

## 10. Data Stores

Every store runs inside each of the 5 regions, so a call's audio, transcript and events never leave the region where the caller lives. Recordings are the only large store; everything else is small.

| Store, per region | Holds | Size |
|---|---|---|
| Redis | Live call state | Under 2 GB at 4,000 calls |
| Object storage | Recordings, 90 days, unless opted out | 32.4M minutes a month at about 0.24 MB a minute (Opus codec, 16 kbps, two channels): about 7.8 TB a month, 23 TB held |
| Postgres | Transcripts with tokens, QA scores, 1 year | About 5 GB a month |
| Kafka | Call events into QA and analytics | Under 100 GB a day |

**How:**
1. Monthly cost: models $52.6k, TTS $109k, QA judge $3.8k (Haiku 5.5 on 5.4M transcripts of 6k tokens), and assumed prices for ASR GPUs $12.4k (about 20 L4 on average at $0.85 an hour, autoscaled), extra media legs $65k ($0.002 a minute), and regional infra $40k: about $283k against $400k.
2. GPUs: 4,000 streams at an assumed 100 per L4 is 40, 58 at 70 percent, plus a spare per region: 63 L4 at peak, 16 at average load.

**Decision.** Self-host ASR and rent TTS, because ASR sits on the latency path and must exist in all 5 regions, while TTS vendors already cover them.

**Trap.** Keeping recordings for years "for training". Retention needs a purpose under GDPR, LGPD and APPI; 90 days covers disputes.

## 11. Output

The caller hears short spoken turns; the systems receive records.

**How:**
1. **Spoken replies**: at most 2 sentences, with one question at a time.
2. **Confirmations** read back from the tool result: flight, time and booking reference, then sent by SMS.
3. **Handoff summary**: intent, verified identity, what was tried, tool results, caller mood, attached to the transfer.
4. **Call record**: transcript as played, tool calls, disclosures given, outcome, language.

**Decision.** Confirmations come from the tool result, never the model's words, because a misheard flight number is a missed flight.

**Trap.** A handoff with no summary. The human asks everything again and the caller's patience is gone.

## 12. Guardrails

Every limit on money, identity and data is in code; the prompt only sets tone.

**How:**
1. AI and recording disclosures at call start in every market, as the EU AI Act's transparency duty and all-party consent states require; "no recording" disables storage.
2. Identity: PNR plus last name to read; an SMS code before any change.
3. Payments only through the DTMF service; the agent sees a token and the last 4 digits.
4. Each entity's audio and transcripts stay in its region; where an LLM endpoint is not in region, redacted transcripts go to the nearest region allowed by that entity's legal transfer basis, set in gateway configuration.

**Decision.** The transfer basis is a recorded legal decision per entity, enforced by the gateway, because residency must not depend on which region an engineer picked.

**Trap.** Reading card numbers aloud back to the caller "to confirm". Card data is now in the TTS vendor's logs.

## 13. Key Impact

The business metric is resolution without a callback, and its cost.

| Metric | Baseline | Target | How measured |
|---|---|---|---|
| Resolved by the agent | 12 percent IVR | 45 percent | No human, no callback in 72 h |
| Cost per resolved call | $4.40 human at 4 minutes | About $0.12 | $283k over 2.43M resolved calls |
| Turn latency p95 | None | Under 800 ms | Media server timestamps |
| CSAT, AI-resolved calls | IVR 3.1 of 5 | 4.0 | Post-call survey |
| Handoff handle time | 6 minutes | 4.5 | ACD reports |

**How:**
1. Hold out 10 percent of calls per language to IVR for 6 weeks to measure resolution and CSAT honestly.
2. Report per language; a weak language hides in a global average.

**Decision.** Count callbacks within 72 hours against resolution, because a wrong rebooking is a second call tomorrow.

**Trap.** One global CSAT number. Japanese and Brazilian callers rate differently, and averages hide a failing language.

## 14. Failure Modes

Every failure falls back to the human queue, never to silence.

**How:**
1. **Disruption surge**: ASR GPUs autoscale from a warm pool in 2 minutes; above 4,000 calls, callback offers.
2. **Altéa slow or down**: fillers, then a handoff with "systems are slow" after 8 seconds.
3. **Model endpoint outage**: LiteLLM fails over within the allowed regions; otherwise transfer.
4. **Bad ASR in one language**: per-language word error rate from QA alerts at 3 points over baseline; that language routes to humans.
5. **Barge-in false triggers on noisy lines**: per-call VAD threshold rises after two false stops.

**Decision.** Any failure in a turn longer than 8 seconds ends in a transfer with summary, because silence on a phone line reads as a dropped call.

**Trap.** Retrying the model three times on the live call. Each retry is a second of dead air.

## 15. Build Order

Twelve months, by language wave and intent.

**How:**
1. **Months 1-3**: media path on Genesys in the US, English, baggage status only. Measure: turn latency p95.
2. **Months 4-5**: rebooking with waivers, payments, handoff. Measure: resolved rate in English.
3. **Months 6-7**: Spanish and Portuguese, Brazil and EU regions, QA calibration. Measure: per-language kappa.
4. **Months 8-9**: Avaya sites, UK, French, German, Italian, Dutch. Measure: resolved rate per language.
5. **Months 10-12**: Japan, Korean, Mandarin, Arabic, Hindi; disruption load test at 4,000 calls. Measure: 45 percent resolved.

**Decision.** One intent in one language first, because latency and barge-in problems show up on the first call, not the thousandth.

**Trap.** Launching 12 languages at once. QA cannot calibrate 12 judges in a month, and one bad language damages the brand in a whole market.
