# System Design catalog (ids 201–215)

Design problems follow the **Unified framework**: fifteen sections under four pillars, about five minutes of answer per pillar. Difficulty follows the ladder below.
- **Easy:** one company, a small team, no GPUs.
- **Medium:** tenants, scale, admission control, a durable workflow, and a feature store or event log.
- **Complex:** regulators, legacy systems, several legal entities, data residency.

## design-easy (Easy, 201–205)
- 0201 returns-refunds-agent: a customer-facing returns and refunds agent for a mid-size retailer. It has order lookup, policy RAG, refund limits in code, and human handoff.
- 0202 internal-knowledge-slack-bot: a Slack bot that answers questions from Confluence, Drive and Jira with ACL-aware retrieval and citations.
- 0203 lead-qualification-agent: enriches inbound leads, scores them against an ICP, writes back to the CRM, and routes them to reps.
- 0204 document-intake-pipeline: invoices and forms by email and upload, then OCR, extraction, validation and ERP posting with a review queue.
- 0205 meeting-notes-coworker: an AI coworker that joins calls, writes notes and action items, and files tickets with approval.

## design-medium (Medium, 206–211)
- 0206 multi-tenant-support-platform: a shared support-agent platform for 200 B2B tenants with per-tenant prompts, tools, quotas, isolation and evals.
- 0207 llm-gateway-cost-controls: a company-wide LLM gateway covering routing, caching, budgets, rate limits, failover, PII redaction and observability for 40 internal teams.
- 0208 mcp-tool-platform: a shared MCP tool platform with a registry, auth (OAuth on behalf of users), per-tool scopes, sandboxing, an audit trail and versioning.
- 0209 agent-eval-observability: tracing, online and offline evals, LLM-as-judge, regression gates, drift dashboards and a feedback loop for production agents.
- 0210 code-review-agent: a PR review agent at a 2,000-engineer company with repo context, policy checks, comment budgets and a measured false-positive rate.
- 0211 shared-ai-coworker-platform: a platform where teams build AI coworkers (Slack, email, tickets), with a shared memory, skills marketplace, permissions and human-in-the-loop.

## design-complex (Hard, 212–215)
- 0212 bank-kyc-agent: KYC and AML case-handling agents for a bank in 3 jurisdictions with residency, model risk management, explainability and a regulator audit.
- 0213 healthcare-prior-auth: prior-authorization agents across payer portals and legacy EHRs (HL7/FHIR), with PHI controls, clinical review gates and SLAs.
- 0214 self-hosted-llm-serving: serving open-weight models for a regulated enterprise on its own GPUs, covering capacity, multi-LoRA, batching, autoscaling, fallback to an API and cost per token.
- 0215 global-voice-agent: a real-time voice support agent in 12 languages with a sub-800 ms turn latency, telephony, barge-in, residency and QA sampling.
