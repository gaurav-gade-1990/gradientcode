### Context

An airline group with entities in the EU (Ireland), the UK, the US, Brazil and Japan takes 180,000 support calls a day in 12 languages. Calls land on a mix of an on-premises Avaya contact center and Genesys Cloud, then reach 3,500 outsourced agents at an assumed fully loaded $1.10 a minute. The touch-tone IVR resolves 12 percent of calls; during weather disruptions hold times pass 90 minutes. The group wants a voice agent that answers in the caller's language, handles rebooking, baggage and check-in questions end to end, and hands everything else to a human with full context.

### Requirements

- Answer in 12 languages (English, Spanish, Portuguese, French, German, Italian, Dutch, Japanese, Korean, Mandarin, Arabic, Hindi).
- Natural turn-taking: the caller can interrupt (barge-in) and the agent stops within a fraction of a second.
- Look up bookings in the Amadeus Altéa passenger service system, rebook within fare and waiver rules, check baggage status, and open cases in the Siebel CRM.
- Take card payments for fare differences without card data reaching the model, transcripts or recordings (PCI DSS).
- Hand off to a human queue with a summary, keeping the caller on the line.
- Tell callers they are speaking with an AI and that the call is recorded; honor opt-outs.
- Each entity's call audio and transcripts stay in its own region; QA covers every language.

### Scale and constraints

- 180,000 calls a day, average 6 minutes and 14 caller turns; average concurrency about 750 calls, and design for 4,000 concurrent during disruption.
- Turn latency: from the end of the caller's speech to the first audio of the reply, under 800 ms at p95.
- Target: 45 percent of calls fully resolved by the agent within 12 months.
- Models via in-region cloud endpoints at Anthropic list prices per million tokens: Haiku 5.5 $0.10 input and $0.50 output, Sonnet 5.5 $2 and $10 with $0.20 cache reads.
- Platform budget $400,000 a month. Team: 20 engineers, 12 months.
- Regulation: GDPR, UK GDPR, Brazil's LGPD, Japan's APPI, PCI DSS, EU AI Act transparency duties, and recording-consent laws that differ by US state.

### What a strong answer covers

- Where each of the 800 ms goes, and what you do when a tool call takes 2 seconds.
- How barge-in works without the agent's memory of the call drifting from what the caller actually heard.
- How audio from two legacy telephony platforms reaches the agent and goes back to a human queue.
- The monthly cost of speech, models and telephony, with the levers applied, against the human cost saved.
- How residency is kept when not every speech or model service exists in every region.
- How QA works in 12 languages when nobody on the platform team speaks most of them.
