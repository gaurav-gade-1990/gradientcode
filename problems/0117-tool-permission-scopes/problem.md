Your support copilot acts **on behalf of** a signed-in user. Security review found that it could refund orders the user couldn't refund themselves, because the agent's service account had broad scopes. Write the check that runs before every tool call.

Implement `authorize_calls(user, agent, role_scopes, tools, resources, calls)` and return one decision per call, in order.

**Inputs**

- `user`: `{"id": "u_maya", "tenant": "acme", "roles": ["support"]}`
- `agent`: `{"name": "refund-copilot", "allowed_tools": [...], "scopes": [...]}`
- `role_scopes`: role name to a list of scope grants. A role that isn't listed grants nothing.
- `tools`: tool name to `{"scopes": [...], "resource_arg": optional str, "admin_scope": optional str}`
- `resources`: resource id to `{"tenant": str, "owner": str}`
- `calls`: `[{"id": "call_1", "tool": "refund_order", "arguments": {...}}, ...]`

**Grants.** A list of grants `G` grants scope `s` when any of these holds:

- `s` is in `G`
- `"*"` is in `G`
- some `g` in `G` ends with `":*"` and `s.startswith(g[:-1])`. For example, `"orders:*"` grants `"orders:read"` and `"orders:refund:create"`, but not `"orders_export:run"`, and not `"orders"` on its own.

The user's grants are the concatenation of `role_scopes[r]` over their roles, and the agent's grants are `agent["scopes"]`. A scope is **effective** only when the user's grants grant it **and** the agent's grants grant it.

**Checks.** Run these in order and stop at the first one that fails:

| # | check | reason on failure |
|---|---|---|
| 1 | `call["tool"]` is a key of `tools` | `"unknown_tool"` |
| 2 | `call["tool"]` is in `agent["allowed_tools"]` | `"agent_tool_not_allowed"` |
| 3 | every scope in the tool's `scopes` is effective | `"missing_scopes"` |
| 4 | if the tool has a `resource_arg`: `arguments[resource_arg]` exists and is a key of `resources` | `"resource_not_found"` |
| 5 | the resource's `tenant` equals `user["tenant"]` | `"cross_tenant"` |
| 6 | the resource's `owner` equals `user["id"]`, **or** the tool has an `admin_scope` and it's effective | `"not_owner"` |

Checks 4–6 apply only to tools that have a `resource_arg`. An admin scope never overrides check 5.

**Output.** Each decision is `{"id": call id, "allowed": bool, "reason": str or None, "missing": [...]}`. `reason` is `None` when the call is allowed. `missing` is the sorted list of non-effective required scopes when the reason is `"missing_scopes"`, and `[]` otherwise.

**Constraints**

- At most 50 calls. Scope strings are non-empty and contain no spaces.
- Each call is decided on its own: a denial doesn't affect the calls after it.
- Don't mutate the inputs.
