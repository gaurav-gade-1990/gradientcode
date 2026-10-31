## Approach

The registry is a per-model state machine plus two pieces of history: the event log (for audit) and the rollback history (for incidents).

```python
def transition(self, model, version, to_stage, actor, approved_by=None):
    rec = ...lookup...                                   # 1. not_found
    if (rec["stage"], to_stage) not in ALLOWED: ...      # 2. invalid_transition
    if to_stage == "Production":
        if approved_by is None: ...                      # 3. approval_required
        if approved_by == actor: ...                     # 4. self_approval
        current = self.production(model)
        if current is not None:
            self._move(model, current, "Archived", actor, "superseded")
            self._history[model].append(current)
    self._move(model, version, to_stage, actor, "manual")
```

Validate everything before mutating anything, so a refused call is a no-op. Archive before you promote, so that there is never a moment, even in the log, with two Production versions.

Rollback walks the history from newest to oldest and picks the first version that is still Archived. A version restored to Staging since then, or one now back in Production, is skipped.

## Common mistakes

- **Not archiving the old Production version.** The "one Production per alias" invariant breaks, and whichever version the serving layer finds first wins. That's often the old one.
- **Self-approval.** Four-eyes approval only works if the approver is a different person. Auditors (SOC 2, SR 11-7 for banks) check for exactly this.
- **Rolling back to the latest archived version.** The latest archived version is often a rejected candidate, or the bad build you just rolled back from. Roll back to what was actually serving before.
- **Global version numbers.** Deploy configs pin `model@version`. If numbers depend on what other teams registered, pinned configs point at the wrong model.

## Production notes

- MLflow's registry had exactly these stages (None, Staging, Production, Archived) and an `archive_existing_versions` flag on promotion. MLflow 2.9+ deprecates stages in favor of **aliases** (`@champion`, `@challenger`) and tags. The same invariants apply: one version per alias, approval to move it, and an audit trail.
- Put approvals in the deploy pipeline (a GitHub environment with required reviewers, or a ServiceNow change ticket), and have the registry verify the approval token instead of trusting an `approved_by` string.
- `models_using_data` is the query you need when a dataset turns out to contain PII or poisoned labels. Store lineage when you register (data snapshot id, git SHA, training config, eval report), not afterwards.
- Pairs with `canary-analysis`: the canary's rollback decision should call `rollback()` here, and the serving layer should watch the alias and hot-swap.
