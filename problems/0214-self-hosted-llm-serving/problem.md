### Context

An insurer has two legal entities: a US carrier with two data centers (Ohio and Texas) and an EU carrier in Dublin. Its legal and risk teams have ruled that claims files, health information and policyholder data may not be sent to any external model provider, so 14 AI use cases (adjuster copilot, claims summarization, document extraction, underwriting notes, internal policy chat, a code assistant) are blocked or running on a hosted API with only public data. The CIO has approved buying GPUs to serve open-weight models in the insurer's own data centers, and wants a platform that every team uses, with a cost per token that finance can compare to the hosted API.

### Requirements

- Serve a large model (Llama 3.3 70B class) for reasoning and drafting, and a small model (Llama 3.1 8B class) with 24 task-specific LoRA adapters for extraction and classification.
- One OpenAI-compatible gateway for all teams, including the legacy Guidewire ClaimCenter integration and mainframe batch jobs.
- Admission control, quotas and priorities per use case; interactive traffic first, batch overnight.
- Fallback to a hosted API only for data classified public or internal, never for restricted data; EU data is served only in the EU.
- Model and adapter changes go through model risk management, and every model artifact is scanned, signed and pinned.
- Underwriting notes in the EU feed life and health risk assessment, which is high-risk under the EU AI Act; DORA applies to the EU carrier's ICT providers.

### Scale and constraints

- 1.2 million requests a day across both entities (US 80 percent, EU 20 percent); peak is 4 times the average rate.
- Average request: 3,000 prompt tokens and 350 output tokens; 35 percent of requests need the large model.
- Interactive SLO: time to first token under 800 ms and time per output token under 50 ms, both at p95. Batch jobs finish within 8 hours.
- Hardware: 8-GPU H100 80 GB servers, assumed at $300,000 each over 3 years plus $3,000 a month for power, space and support.
- Hosted comparison at Anthropic list prices per million tokens: Sonnet 5.5 $2 input and $10 output, Haiku 5.5 $0.10 and $0.50.
- Team: 9 platform engineers, 9 months. Decision records retained 7 years.

### What a strong answer covers

- KV cache bytes per token, concurrent sequences per replica, and GPU count from peak load, with the arithmetic.
- How batching, prefix caching, quantization and multi-LoRA change the GPU count.
- How capacity is shared and protected on a fixed on-premises fleet that cannot scale out in minutes.
- When the hosted API is allowed, and how the gateway enforces it.
- Cost per million tokens self-hosted against the hosted API, and an honest answer to whether self-hosting saves money.
- How a new model version reaches production in a regulated company.
