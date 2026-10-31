## 1. What the problem is really asking

Under the airline story, this is a **real-time streaming pipeline with a hard latency budget**, wrapped around an agent that takes real actions with money. A caller speaks, and within 800 ms at p95 they must hear the first audio of a reply, in one of 12 languages, from a system that may also be rebooking their flight and taking a card payment. The rest is constraints: two legacy telephony platforms, five regulatory regions, PCI DSS and a $400k budget.

The core tension is **latency against capability**. A larger model reasons better about multi-leg rebookings, but it adds about 100 ms to every turn and costs far more. A tool call to Amadeus can take 1.5 to 3 seconds, far over budget. The strong design spends the 800 ms deliberately: streaming at every stage, the small model by default, sentence-by-sentence TTS, and a filler phrase when a tool is slow.

Three decisions carry the design:

- **Stream everything, in region.** Turn detection, ASR, the model and TTS are streaming stages in the caller's region, and the model's first sentence goes to TTS while it writes the second. A round trip across an ocean costs 150 ms the budget doesn't have.
- **History is what the caller heard.** On barge-in, the assistant turn is cut to the words actually played, using TTS word timestamps. Otherwise the model believes it offered three flights when the caller heard one.
- **Money limits and card data live outside the model.** Fare and waiver limits are checked inside the `rebook` tool, with an idempotency key. Card entry goes to a PCI DSS DTMF-masking service, and the media server stops ASR and recording during payment by system control.

The model answer's one idea: latency is spent in turn detection and first tokens, and the call history must record what the caller actually heard, not what the model wrote.

## 2. The numbers that drive the design

**Calls, minutes and turns a month.**

- 180,000 calls × 30 = **5.4M calls a month**.
- × 6 minutes = **32.4M minutes a month**. Speech is priced per minute or per character, so this number dominates the bill.
- × 14 turns = **75.6M turns a month**. The model is priced per turn.

**Concurrency.** 180,000 calls × 6 minutes / 1,440 minutes a day = **750 concurrent calls** on average. Disruption design point is 4,000, more than 5 times average, and speech capacity has to scale to it in minutes.

**The human cost, and what 45 percent saves.**

- Today: 32.4M minutes × an assumed $1.10 = **$35.6M a month**.
- At 45 percent resolution: 5.4M × 0.45 = 2.43M resolved calls. The model answer values each at 4 human minutes, so 2.43M × 4 × $1.10 ≈ **$10.7M a month saved**.
- A human-handled resolved call is 4 × $1.10 = **$4.40**.

**The model lever table.** Assume 4k input and 60 output tokens per turn, as the model answer does.

| Step | Per turn | Monthly cost |
|---|---|---|
| Sonnet 5.5 on every turn, no caching | 4,000 × $2/M + 60 × $10/M = $0.0086 | 75.6M × $0.0086 = **$650k** |
| Model mix: Haiku 5.5 on 80 percent of turns | Haiku: 4,000 × $0.10/M + 60 × $0.50/M = $0.00043 | **$156k** (saves $494k) |
| Prompt caching the 2.5k system prefix | Sonnet saves 2,500 × $1.80/M; Haiku saves 2,500 × $0.09/M, with Haiku's $0.01 cache read **assumed** | **$74.4k** (saves $81.6k) |
| History trimming: 1.5k → 0.9k tokens past 6 turns | 600 fewer uncached tokens per turn | **$52.6k** (saves $21.8k) |

The model mix is by far the biggest lever, and it's also the latency lever: Haiku's first token fits the budget.

**Text to speech, the biggest bill.** 9.07B characters a month at an assumed $16 per million characters = **$145k**. Caching fixed phrases (about 25 percent of spoken characters) brings it to **$109k**, saving $36k. TTS costs twice the models after the levers.

**ASR GPUs.** 4,000 streams at an assumed 100 streams per L4 = 40 GPUs; at 70 percent utilization, 58; plus a spare in each of 5 regions = **63 L4 at peak**. At 750 calls, about 16. The model answer's cost line uses about 20 L4 on average × an assumed $0.85/h × 730 h = **$12.4k a month**.

**Recordings.** Opus at 16 kbps on two channels is 32 kbps = 4 KB/s = **0.24 MB a minute**. 32.4M minutes × 0.24 MB ≈ **7.8 TB a month**, about **23 TB held** at 90 days.

**Total.** Models $52.6k + TTS $109k + QA judge $3.8k + ASR GPUs $12.4k + extra media legs $65k (32.4M minutes × an assumed $0.002) + regional infra $40k ≈ **$283k a month** against $400k. Cost per resolved call: $283k / 2.43M ≈ **$0.12**, against $4.40 for a human.

**Turn latency.** p95: ingress 50 + end-of-turn 230 + ASR final 80 + model first token 250 + TTS first audio 120 + egress 50 = **780 ms**, just under 800. p50 is about 560 ms. End-of-turn detection is the largest single item.

## 3. How to spend your time

| Minutes | What you do |
|---|---|
| 0–6 | Read the prompt. Write 32.4M minutes, 75.6M turns, 750 and 4,000 concurrent, $35.6M human cost. |
| 6–18 | **Pillar A.** Define resolved, pick three intents, draw ten layers including both telephony paths, payments and handoff. |
| 18–38 | **Pillar B.** Rule tables, streaming stages, payment pause, the model lever table, barge-in truncation, money limits in tools. |
| 38–55 | **Pillar C.** The 800 ms table, fillers and barge-in, TTS phrase cache, the GPU and storage sizing, the $283k total. |
| 55–70 | **Pillar D.** Disclosures, verification tiers, residency per entity, per-language holdout, fallbacks to humans, language waves. |
| 70–75 | Check the latency table adds up and every money limit is in a tool. |

## 4. Pillar A: Frame

### Scenario

**The question:** who's calling, what does the agent resolve, and which numbers shape the design?

The caller is a traveller, often stressed and mid-disruption, who wants a rebooking or an answer in their own language without waiting 90 minutes. The job: resolve the simple half of calls end to end, and hand the rest to a human with the work already done.

How to reason to the scope: pull 3 months of call reasons by language. Rebooking, baggage and check-in are 52 percent of calls. **Resolve those three intents fully** before touching anything else, because a voice agent that half-handles everything sends angry callers to humans with nothing done.

Define **resolved** carefully: no human, no callback within 72 hours, no complaint. Then show the volume conversion and the $10.7M saving from section 2. Baselines: 12 percent IVR containment, 90-minute holds in disruption, 6-minute handle time. Out of scope: outbound calling, loyalty account changes, refunds beyond the waiver rules.

**The trap:** measuring containment as calls that didn't reach a human. Callers who hang up in frustration count as contained.

**Rubric:** minutes, concurrency and turns (1.1), resolved excluding hang-ups and callbacks (1.2), the human cost saved (1.3), and a few high-volume intents first (1.4).

### Single View

**The question:** draw the media and control path from a call to a reply and to a human.

Ten layers: Telephony (Avaya via SIP through AudioCodes SBCs; Genesys Cloud via AudioHook) → Media server (LiveKit with SIP per region, echo cancellation, VAD, playback tracking) → Turn detection → Speech to text (self-hosted streaming ASR on L4s) → Dialogue agent (Haiku 5.5 default, Sonnet 5.5 for rebooking reasoning) → Tools (MCP over Altéa, baggage, Siebel, payments, transfer) → Text to speech (vendor voices with a phrase cache) → Payments (PCI DSS Level 1 DTMF masking) → Handoff (SIP REFER back to the ACD with a summary) → QA and records.

The reasoning that earns marks:

- **Both legacy platforms reach one media path.** You don't build two agents.
- **Turn detection, ASR, model and TTS are separate streaming stages**, so each can start before the previous one ends.
- **Payments leave the agent entirely**, which is how card data never touches your systems.
- **Warm handoff** carries the summary in Genesys participant data or Avaya UUI.

**The trap:** drawing "phone → speech-to-speech model → phone." It has nowhere to put playback tracking, payments or the handoff.

**Rubric:** one media path for both platforms (2.1), streaming stages kept separate (2.2), payments outside the agent (2.3), and warm handoff with context (2.4).

## 5. Pillar B: Build the core

### Data Sources

**The question:** what does the agent read, and which rules are data rather than prompt text?

Amadeus Altéa for booking, flight status and rebooking availability, **read live** by PNR and last name. **Disruption waivers as a versioned rule table** published by operations. WorldTracer for baggage by tag number. Baggage and check-in policies per carrier in 12 languages from a small pgvector index. Siebel for customer tier and open cases, read-only except case creation.

The reasoning for the waiver table: a waiver the model reads from text can be talked wider by a persuasive caller. A waiver the rebooking tool enforces can't.

For policies: index the **approved local-language text**, because legal wording differs by market.

**The trap:** translating policies on the fly from English.

**Rubric:** bookings read live (3.1), waivers as a versioned rule table (3.2), and approved local text rather than live translation (3.3).

### Processing

**The question:** how is audio processed so each stage starts before the last ends?

- **Language** is set by the dialled number, then confirmed by language ID on the first 3 seconds, and callers can switch mid-call.
- **Streaming ASR** emits partials every 100 ms; the final lands 50 to 80 ms after end of turn.
- **The model's reply is cut at sentence boundaries**; sentence one goes to TTS while the model writes sentence two. Waiting for the full reply would add 1 to 2 seconds per turn.
- **During payment, the media server stops sending audio to ASR and recording**, by system control, not by an agent pressing pause.
- PNRs, names and phone numbers in transcripts are replaced with tokens before storage and QA.

**The trap:** running ASR on the payment segment and redacting afterwards. The card number was already processed and stored.

**Rubric:** sentence-by-sentence TTS (4.1), language from dialled number and first seconds (4.2), and ASR and recording stopped during payment by system control (4.3).

### Agents

**The question:** which models answer which turns, and what does it cost?

One dialogue agent per call with a small, fixed toolset. **Haiku 5.5 by default**, because its first token fits the budget and most turns are confirmations. **Sonnet 5.5 only for rebooking option reasoning and tangled multi-leg trips, chosen by the workflow state**, not by the model. Replies are capped at 2 sentences.

Handoff triggers are **in code**: two failed intents, the caller asks for a person, or a tool error on a write.

Then the lever table from section 2: $650k → $52.6k. Reveal the model answer for the table.

**The trap:** using the larger model everywhere "for quality." It adds about 100 ms to every turn and, even with caching, about $235k a month more.

**Rubric:** levers in order with savings (5.1), small model by default with the larger chosen by workflow state (5.2), and handoff conditions in code (5.3).

### Memory

**The question:** what's remembered, and how does barge-in affect it?

Call state in **Redis per region**: language, verified identity, PNR, intent, tools called, and **the transcript as played**. On barge-in, the assistant turn is truncated to the words the media server reports as played, using TTS word timestamps. Prior contact comes from the last 30 days of Siebel cases, read at call start. No long-term voice memory, no voiceprints.

The reasoning: if the model's history says it offered three flights and the caller only heard the first before interrupting, "the second one" means nothing, and the next turn is nonsense.

On voice biometrics: they're **special-category biometric data under GDPR and LGPD**. Use PNR plus last name, with an SMS code before changes.

**The trap:** voice biometrics for identity.

**Rubric:** truncation to the words played (6.1), call state per region (6.2), and no voice biometrics, with the reason (6.3).

### MCP Tool Servers

**The question:** which tools exist, and where are money limits enforced?

MCP servers per region: `find_booking`, `flight_status`, `baggage_status`, `create_case`; `search_rebooking(pnr, constraints)` returning at most 3 options inside the waiver table; `rebook(pnr, option_id, idempotency_key)` which **refuses any fare difference not covered or paid**; `start_secure_payment(amount)` which hands the call to the DTMF service and **returns a token or a failure**; `transfer(queue, summary)` for the SIP REFER.

The reasoning: a persuasive caller can talk a model past any limit written in a prompt, so the limit lives in `rebook`. The idempotency key matters because phone calls drop (problem idempotent-tool-execution).

**The trap:** a rebooking tool without an idempotency key. A dropped call and a retry book the passenger twice.

**Rubric:** limits inside the rebooking tool (7.1), idempotency keys (7.2), and payment returning only a token (7.3).

## 6. Pillar C: Serve and store

### Endpoints

**The question:** where do the 800 ms go, and what happens on a slow tool call?

The voice path is media, not HTTP. Show the stage table (section 2): about 560 ms p50 and 780 ms p95.

Then the three behaviors the rubric asks for:

- **Slow tools:** a tool call over 700 ms triggers a cached filler phrase immediately, so silence never passes 1.5 s while Altéa answers in 1.5 to 3 s.
- **Barge-in:** VAD on caller audio during playback with **echo cancellation** (so the agent's own voice doesn't trigger it); playback stops within **150 ms**; short backchannels like "mm-hm" are ignored.
- **In region:** SIP trunks terminate on SBCs per region; Genesys streams through AudioHook WebSockets; both reach LiveKit SIP in the caller's entity region.

Admission: at 4,000 concurrent calls, new calls go to the human queue with a callback offer.

**The trap:** a REST call per turn to a central service. It adds hops on every turn and crosses borders.

**Rubric:** a stage budget under 800 ms (8.1), fillers on slow tools (8.2), barge-in with echo cancellation and a stop time (8.3), and the loop in the caller's region (8.4).

### Caching

**The question:** what's cached, and why does speech caching matter most?

TTS is the largest bill, so caching speech beats caching text. Cache audio for fixed phrases (greetings, the AI and recording disclosures, fillers, confirmations) per language and voice, about 25 percent of spoken characters, saving $36k a month (section 2). Prompt-cache the system prompt and tool schemas per language. Cache flight status for **60 seconds per flight** during disruption, when thousands ask about the same flight.

Pre-rendering disclosures also guarantees they're word-perfect in each language.

**The trap:** caching personalized sentences. A cached "your flight to Lisbon" plays to a caller going to Tokyo.

**Rubric:** TTS priced per character with phrase caching and the saving (9.1), no personalized audio cached (9.2), and brief flight-status caching in disruption (9.3).

### Data Stores

**The question:** what's stored where, how much, and what does the whole system cost?

Every store runs in each of the 5 regions. Redis holds live call state (under 2 GB at 4,000 calls). Object storage holds **recordings for 90 days** unless opted out: 7.8 TB a month, 23 TB held. Postgres holds tokenized transcripts and QA scores for a year. Kafka carries call events.

The cost total of about $283k, with every non-model price assumed, and the GPU sizing of 63 L4 at peak (section 2).

The decision: **self-host ASR, rent TTS.** ASR sits on the latency path and must exist in all 5 regions; TTS vendors already cover them.

The retention reason: recordings need a purpose under GDPR, LGPD and APPI, and 90 days covers disputes.

**The trap:** keeping recordings for years "for training."

**Rubric:** recording storage from minutes and bytes (10.1), ASR GPUs from peak streams with a per-GPU assumption (10.2), a total against $400k with assumed labels (10.3), and retention with a purpose (10.4).

### Output

**The question:** what does the caller hear, and what does the human receive?

Spoken replies of **at most 2 sentences**, one question at a time. **Confirmations read back from the tool result** (flight, time, booking reference), then sent by SMS. A **handoff summary** with intent, verified identity, what was tried, tool results and caller mood, attached to the transfer. A call record with the transcript as played, tool calls, disclosures given, outcome and language.

The reasoning for confirmations from the tool result: a misheard or mis-generated flight number is a missed flight.

**The trap:** a handoff with no summary. The human asks everything again.

**Rubric:** short turns (11.1), confirmations from tool results and in writing (11.2), and a structured summary on every handoff (11.3).

## 7. Pillar D: Run it safely

### Guardrails

**The question:** which legal and safety rules apply, and how are they enforced?

- **Disclosures:** AI and recording disclosures at call start in every market, for the EU AI Act's transparency duty and all-party consent states. "No recording" disables storage.
- **Verification tiers:** PNR plus last name to read; an **SMS code before any change**.
- **Payments** only through the DTMF service; the agent sees a token and the last 4 digits.
- **Residency:** each entity's audio and transcripts stay in its region. Where an LLM endpoint isn't in region, redacted transcripts go to the nearest region allowed by that entity's **legal transfer basis, set in gateway configuration**.

That last point answers "residency when not every service exists in every region": the transfer basis is a recorded legal decision per entity, enforced by the gateway, so it doesn't depend on which region an engineer picked.

**The trap:** reading card numbers aloud to confirm. Card data is then in the TTS vendor's logs.

**Rubric:** disclosure with opt-out (12.1), stronger verification before changes (12.2), residency with transfer basis in code (12.3), and card data out of agent, transcripts and TTS (12.4).

### Key Impact

**The question:** how do you prove the agent resolves calls well in every language?

Five metrics: resolved by the agent (12 → 45 percent), cost per resolved call ($4.40 human → about $0.12), turn latency p95 (under 800 ms), CSAT on AI-resolved calls (IVR 3.1 → 4.0 of 5), and handoff handle time (6 → 4.5 minutes).

The method: **hold out 10 percent of calls per language to IVR for 6 weeks**, and **report per language**. A weak language hides in a global average, and Japanese and Brazilian callers rate differently. Callbacks within 72 hours count against resolution, because a wrong rebooking is a second call tomorrow.

**The trap:** one global CSAT number.

**Rubric:** a holdout for resolution and CSAT (13.1), metrics per language (13.2), and cost per resolved call against human cost (13.3).

### Failure Modes

**The question:** what breaks on a live call, and what does the caller experience?

Every failure falls back to the human queue, never to silence:

- **Disruption surge:** ASR GPUs autoscale from a warm pool in 2 minutes; above 4,000 calls, callback offers.
- **Altéa slow or down:** fillers, then a handoff with "systems are slow" after 8 seconds.
- **Model endpoint outage:** LiteLLM fails over within allowed regions; otherwise transfer.
- **Bad ASR in one language:** per-language word error rate from QA alerts at 3 points over baseline, and that language routes to humans.
- **Barge-in false triggers on noisy lines:** the per-call VAD threshold rises after two false stops.

The rule: any failure in a turn longer than 8 seconds ends in a transfer with summary, because silence on a phone line reads as a dropped call.

**The trap:** retrying the model three times on the live call. Each retry is a second of dead air.

**Rubric:** human transfer rather than silence (14.1), surge autoscaling and callbacks (14.2), and a degraded language detected by QA and routed to humans (14.3).

### Build Order

**The question:** how do you roll out 12 languages in 12 months?

Media path on Genesys in the US, English, **baggage status only** (months 1–3, turn latency p95); rebooking, payments and handoff (4–5, English resolved rate); Spanish and Portuguese with Brazil and EU regions and **QA calibration** (6–7, per-language kappa); Avaya sites, UK, French, German, Italian, Dutch (8–9); Japan, Korean, Mandarin, Arabic, Hindi and the **4,000-call disruption load test** (10–12, 45 percent resolved).

The reasoning: latency and barge-in problems show up on the first call, not the thousandth, so one intent in one language comes first. QA (a Haiku judge on all calls plus native-speaker review of 2 percent) needs calibrating per language, which is why languages come in waves.

**The trap:** launching 12 languages at once. QA can't calibrate 12 judges in a month, and one bad language damages the brand in a whole market.

**Rubric:** one intent in one language first (15.1), language waves with QA calibration (15.2), and a disruption load test before full launch (15.3).

## 8. The decisions that separate strong answers

**Haiku by default vs the larger model everywhere.** The larger model reasons better, and weak answers use it for safety. But 100 ms on every turn breaks a budget with 20 ms to spare at p95, and it costs about $235k a month more. Strong answers use Haiku 5.5 for most turns and pick Sonnet 5.5 by workflow state for rebooking reasoning, where the extra latency hides behind a filler anyway.

**History as played vs history as generated.** Most text-agent designs append the model's full reply to the transcript. On a voice call with barge-in, that's wrong: the caller heard part of it. Truncating to played words with TTS timestamps keeps the model's picture of the call matched to the caller's.

**Limits in tools and system controls vs limits in the prompt.** The waiver rule in `rebook`, the payment pause in the media server, and the transfer basis in the gateway are all things a caller can't talk the model out of. Weak answers write "never accept card numbers" in the system prompt and run ASR on everything.

## 9. Common mistakes

- No stage-by-stage latency table, or one that doesn't add to under 800 ms.
- Waiting for the full model reply before starting TTS.
- Ignoring TTS cost; it's the biggest line after the levers.
- Appending the full generated reply after a barge-in.
- Card digits passing through ASR, recordings or TTS.
- Waiver limits in the prompt.
- Silence while a slow tool runs.
- One global quality metric across 12 languages.
- Voiceprints for identity without addressing special-category data.
- Routing calls through a central region "for simplicity."

## 10. Follow-ups an interviewer might ask

- *A caller switches from Spanish to English mid-call.* Language ID keeps running; switch ASR and TTS voices and the policy index to the new language, and keep the same call state.
- *Altéa takes 4 seconds.* A filler plays at 700 ms, and if the turn passes 8 seconds the agent hands off with "systems are slow" and a summary.
- *How do you score QA in Hindi when nobody on the team speaks it?* A Haiku judge on all calls, calibrated against native-speaker review of 2 percent, with agreement measured per language before launch (problem llm-judge-position-swap for judge bias).
- *How do you measure turn latency honestly?* Media-server timestamps from end of caller speech to first reply audio, reported as p95 per language and region (problem streaming-latency-percentiles).
- *How does the human agent pick up mid-call?* SIP REFER back to the ACD queue with intent, identity, attempts and tool results in participant data (problem agent-handoff-context).
