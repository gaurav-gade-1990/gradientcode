Your ML platform serves models by alias: the serving layer loads whatever version is in **Production** for a model name. You're implementing the registry behind it: stage transitions with four-eyes approval, automatic archiving on promotion, one-call rollback, and lineage queries for incident response.

Implement `class ModelRegistry`.

**`register(model, data_version, code_version, metrics) -> int`** stores a new version in stage `"None"` and returns its number. Versions count **per model**, starting at 1. `metrics` is a dict to store as-is.

**`transition(model, version, to_stage, actor, approved_by=None) -> dict`** returns `{"ok": True}` or `{"ok": False, "error": code}`. Check in this order, and change nothing on an error:

| # | error | when |
|---|---|---|
| 1 | `"not_found"` | the model or version doesn't exist |
| 2 | `"invalid_transition"` | `(current, to_stage)` is not one of: `None→Staging`, `None→Archived`, `Staging→Production`, `Staging→Archived`, `Production→Archived`, `Archived→Staging` |
| 3 | `"approval_required"` | `to_stage == "Production"` and `approved_by` is `None` |
| 4 | `"self_approval"` | `to_stage == "Production"` and `approved_by == actor` |

On success, a move to Production first archives the model's current Production version, if there is one: it emits an event with reason `"superseded"` and records that version in the model's **rollback history**. Then it moves this version and emits an event with reason `"manual"`. Every other successful transition emits one `"manual"` event.

**`rollback(model, actor) -> dict`**: the target is the **most recently superseded** version (latest in the rollback history) whose stage is still `"Archived"`. If the model doesn't exist, return `{"ok": False, "error": "not_found"}`. If there is no target, return `{"ok": False, "error": "no_rollback_target"}`. Otherwise archive the current Production version, if any (reason `"rolled_back"`; it does **not** join the rollback history), then move the target to Production (reason `"rollback"`), and return `{"ok": True, "version": target}`. Rollback needs no approval, since it's the incident path.

**Queries**

- `production(model)`: the Production version number, or `None`
- `stage(model, version)`: the stage string, or `None` if it doesn't exist
- `lineage(model, version)`: `{"data_version", "code_version", "metrics"}`, or `None`
- `models_using_data(data_version)`: `[[model, version], ...]` for versions trained on that data that are currently in `Staging` or `Production`, sorted by model name and then version

**`events`** is a list attribute. Each successful stage change appends `{"model", "version", "from", "to", "actor", "reason"}`, where `from` and `to` are stage strings, including `"None"`.

The judge runs a script of calls and records every return value plus the final `events`.

**Constraints**

- Stages are exactly `"None"`, `"Staging"`, `"Production"` and `"Archived"`
- At most 200 calls per script
