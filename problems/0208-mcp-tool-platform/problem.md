### Context

A 9,000-person software company has 140 internal agents owned by 70 teams. Each team wired its own tools: 48 MCP servers exposing about 410 tools over Jira, GitHub, Salesforce, Snowflake, Google Workspace, ServiceNow and a dozen internal services. Most of them call downstream systems with a shared service account, so an agent can read any Salesforce account no matter who asked. Last quarter a community MCP server shipped a new tool description that told agents to post repository contents to an external URL, and nobody could say which agents had loaded it. The CISO wants one shared tool platform before anyone ships agent 141.

### Requirements

- A registry of approved MCP servers and tools, with owners, versions, data classes and required scopes.
- Agents call tools on behalf of the signed-in user: OAuth per user to each downstream SaaS, never a shared account.
- Per-tool scopes: a call is allowed only if both the user and the agent hold the scope, and the resource is one the user can reach.
- Sandboxing for third-party servers and code-execution tools, with no ambient credentials and an egress allowlist.
- An audit trail answering "what did any agent do, for whom, with which tool version" for 400 days.
- Versioning: teams pin tool versions, upgrades roll out safely, and a bad server can be killed in minutes.
- Human approval for high-risk write tools (deleting repos, sending external email, changing CRM opportunity stages).

### Scale and constraints

- 5,000 weekly active users; 1.2 million agent model turns and 2.4 million tool calls a day, peak 90 tool calls per second.
- Platform overhead budget: p95 under 40 ms per tool call, excluding the downstream system's own latency.
- Downstream quotas are real: the Salesforce org allows 1 million API calls per 24 hours shared with the rest of the company; GitHub allows 5,000 requests per hour per user token.
- 30 downstream systems support OAuth; 6 legacy internal services accept only mTLS service identity.
- Agents load on average 60 tools today at about 180 tokens each, on Sonnet 5.5 ($2 input, $10 output, $0.20 cache reads per million tokens).
- Team: 8 platform engineers, 6 months. Infra budget $45,000 a month. SOC 2 Type II; audit logs immutable.

### What a strong answer covers

- How a user's identity reaches a downstream system without the agent ever holding a long-lived secret.
- Where the authorization decision is made, and why it cannot live in the tool description or the prompt.
- What exactly gets approved when a server is approved, and what happens when its description changes.
- How the platform protects shared downstream quotas from one noisy team.
- What happens to in-flight calls when the audit pipeline or the identity provider is down.
- How many tokens tool definitions cost per month, and how to cut that.
