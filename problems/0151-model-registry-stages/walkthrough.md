## 1. What the problem is really asking

The serving layer loads whatever version sits in **Production** for a model name. So the registry is the thing that decides what customers see, and it needs the same guarantees as a deploy system: only allowed moves, a second person on every promotion, exactly one Production version per model, a one-call rollback for incidents, and an audit trail.

Under the story, this is **a per-object state machine plus a small history stack**:

- each version has a stage, and only six `(from, to)` moves are legal;
- promoting to Production has a side effect: it first archives the current Production version and pushes it onto the model's **rollback history**;
- rollback pops back to the most recent entry in that history that's still `Archived`.

The judge runs a script of calls through a driver, records every return value, and compares the final `events` list. Events are where most mistakes show up: the order of the two events on a promotion, an event emitted on a failed call, or the wrong `reason` string.

## 2. Understand the inputs before writing anything

| call | what it does | returns |
|---|---|---|
| `register(model, data_version, code_version, metrics)` | new version in stage `"None"` | the version number, counted per model |
| `transition(model, version, to_stage, actor, approved_by=None)` | one stage move after four checks | `{"ok": True}` or `{"ok": False, "error": code}` |
| `rollback(model, actor)` | restore the last superseded version | `{"ok": True, "version": v}` or an error |
| `production(model)`, `stage(...)`, `lineage(...)` | read-only lookups | a value or `None` |
| `models_using_data(data_version)` | live versions trained on that data | `[[model, version], ...]` sorted |
| `events` | an attribute, a list of every successful stage change | `{model, version, from, to, actor, reason}` |

Three details are easy to miss:

- **Version numbers are per model.** `churn` v1, v2 and `fraud` v1 are independent. A global counter makes `fraud`'s first version `2`, and every pinned deploy config breaks.
- **Errors are checked in a fixed order, and an error changes nothing.** No event, no stage change, no history push.
- **`"None"` is a stage string, not Python's `None`.** A freshly registered version has `stage == "None"`, and events show `"from": "None"`.

## 3. Trace Example 1 and Example 3 by hand

Example 1 registers two `churn` versions, then promotes each in turn:

| call | result | events appended | Production | history |
|---|---|---|---|---|
| register churn (ds-2026-09) | 1 | | | [] |
| register churn (ds-2026-10) | 2 | | | [] |
| v1 → Staging, maya | ok | v1 None→Staging (manual) | | [] |
| v1 → Production, maya, approved by li | ok | v1 Staging→Production (manual) | 1 | [] |
| v2 → Staging, maya | ok | v2 None→Staging (manual) | 1 | [] |
| v2 → Production, maya, approved by li | ok | **v1 Production→Archived (superseded)**, then v2 Staging→Production (manual) | 2 | [1] |

The last call emits two events, in that order: archive the old one first, then promote. That keeps "exactly one Production version" true after every event, which matters if anything reads the event stream.

Example 3 continues with `rollback("churn", "oncall")`:

1. The history is `[1]`, and v1's stage is `Archived`, so the target is v1.
2. Archive the current Production version, v2, with reason `"rolled_back"`. It does **not** go onto the history.
3. Move v1 Archived→Production with reason `"rollback"`.

It returns `{"ok": True, "version": 1}`, with no approval needed: rollback is the incident path, and you don't want on-call waiting for a second reviewer at 3 a.m. Then `lineage("churn", 1)` returns `{"data_version": "ds-2026-09", "code_version": "a1f3", "metrics": {"auc": 0.81}}`, which is what the incident channel needs to know about the restored model.

**Example 2 is the error ladder.** On a fresh `fraud` v1: None→Production is not an allowed move (`invalid_transition`). After moving it to Staging, a promotion with no approver gives `approval_required`, and `approved_by="sam"` with `actor="sam"` gives `self_approval`. Version 7 gives `not_found`. Only the move to Staging emits an event.

## 4. Key idea: roll back to what was serving, not to what was archived last

The tempting rollback is "the most recently archived version". In "rollback skips rejected candidate" that's wrong:

| step | what happens | history |
|---|---|---|
| v1 promoted, then v2 promoted | v1 superseded | [1] |
| v3 → Staging → Archived | a rejected candidate; it's now the latest archived version | [1] |
| rollback | target v1 (from history, still Archived); v2 rolled_back | [1] |
| rollback again | v1 is in Production now, not Archived | `no_rollback_target` |
| v4 promoted | v1 superseded again | [1, 1] |
| rollback | target v1 again; v4 rolled_back | [1, 1] |

"Latest archived" would restore v3, a model that never passed review. The history records only versions that were *actually serving* and got replaced by a promotion, which is exactly the set you'd want to go back to. It also leaves out two other kinds of archive:

- **Manual archives.** In "manual archive and invalid moves", v1 is archived by hand from Production. That's a deliberate retirement, not a supersede, so the first rollback returns `no_rollback_target`.
- **Rolled-back versions.** The bad build you rolled back from must never become a rollback target.

The "still Archived" filter matters too: a superseded version later moved back to Staging (like v2 at the end of the ranker script) is no longer a candidate.

## 5. Plan before you code

```
state: versions[model][v] = {stage, data_version, code_version, metrics}
       history[model] = versions superseded by a promotion, oldest first
       events = []

_move(model, v, to, actor, reason): append event (from = current stage), then set stage

transition:
    not_found -> invalid_transition -> approval_required -> self_approval
    if to Production and a Production version exists:
        _move(current, Archived, superseded); history.append(current)
    _move(this, to_stage, manual)

rollback:
    not_found; target = last history entry still Archived, else no_rollback_target
    _move(current Production, Archived, rolled_back) if any
    _move(target, Production, rollback)
```

| reason | when |
|---|---|
| `manual` | every successful `transition` move of the requested version |
| `superseded` | the old Production version archived by a promotion |
| `rolled_back` | the Production version archived by a rollback |
| `rollback` | the target restored by a rollback |

## 6. Build it one piece at a time

**Step 1: storage and per-model versions.** `len(versions) + 1` works because versions are never deleted:

```python
def register(self, model, data_version, code_version, metrics):
    versions = self._versions.setdefault(model, {})
    self._history.setdefault(model, [])
    v = len(versions) + 1
    versions[v] = {"stage": "None", "data_version": data_version, "code_version": code_version, "metrics": metrics}
    return v
```

**Step 2: one helper for every stage change.** Read `from` before overwriting the stage, so the event shows where the version came from:

```python
def _move(self, model, version, to, actor, reason):
    rec = self._versions[model][version]
    self.events.append({"model": model, "version": version, "from": rec["stage"], "to": to, "actor": actor, "reason": reason})
    rec["stage"] = to
```

Every event comes from this one function, so a failed call can't emit one by accident.

**Step 3: the checks, in order, then the side effect.** All four checks run before anything changes, so an error leaves no trace. `.get(model, {}).get(version)` handles an unknown model and an unknown version in one expression.

**Step 4: rollback.** `reversed(history)` walks newest first, and `next(..., None)` returns the first match or `None`:

```python
target = next((v for v in reversed(self._history[model]) if self._versions[model][v]["stage"] == "Archived"), None)
```

## 7. Full solution

```python
ALLOWED = {  # the only legal (from, to) stage moves
    ("None", "Staging"), ("None", "Archived"),  # a new version gets tested or rejected
    ("Staging", "Production"), ("Staging", "Archived"),  # a tested version ships or is rejected
    ("Production", "Archived"), ("Archived", "Staging"),  # retire a live one; bring an old one back for testing
}


class ModelRegistry:  # stage transitions, approvals, rollback and lineage for many models
    def __init__(self):  # one registry per driver run
        self.events = []  # audit trail of every successful stage change
        self._versions = {}   # model -> {version: record}
        self._history = {}    # model -> versions superseded by a promotion, oldest first

    def register(self, model, data_version, code_version, metrics):  # add a new version in stage "None"
        versions = self._versions.setdefault(model, {})  # first registration creates the model
        self._history.setdefault(model, [])  # empty rollback history for a new model
        v = len(versions) + 1  # versions count per model and are never deleted
        # store lineage with the version, at registration time
        versions[v] = {"stage": "None", "data_version": data_version, "code_version": code_version, "metrics": metrics}
        return v  # the caller pins model@v

    def _move(self, model, version, to, actor, reason):  # the only place a stage changes
        rec = self._versions[model][version]  # the version being moved
        # log the move with its old stage before changing it
        self.events.append({"model": model, "version": version, "from": rec["stage"], "to": to, "actor": actor, "reason": reason})
        rec["stage"] = to  # apply the move

    def transition(self, model, version, to_stage, actor, approved_by=None):  # a requested stage change
        rec = self._versions.get(model, {}).get(version)  # None if the model or the version is unknown
        if rec is None:  # check 1
            return {"ok": False, "error": "not_found"}  # nothing to move
        if (rec["stage"], to_stage) not in ALLOWED:  # check 2
            return {"ok": False, "error": "invalid_transition"}  # e.g. None -> Production skips Staging
        if to_stage == "Production":  # promotions need four eyes
            if approved_by is None:  # check 3
                return {"ok": False, "error": "approval_required"}  # nobody signed off
            if approved_by == actor:  # check 4
                return {"ok": False, "error": "self_approval"}  # signing off your own change doesn't count
            current = self.production(model)  # whatever is serving now
            if current is not None:  # keep exactly one Production version
                self._move(model, current, "Archived", actor, "superseded")  # retire the old one first
                self._history[model].append(current)  # it was really serving, so it's a rollback target
        self._move(model, version, to_stage, actor, "manual")  # the requested move itself
        return {"ok": True}  # success

    def rollback(self, model, actor):  # incident path: restore the previous serving version
        if model not in self._versions:  # unknown model
            return {"ok": False, "error": "not_found"}  # nothing to roll back
        # newest superseded version that is still Archived (not since restored or re-staged)
        target = next((v for v in reversed(self._history[model]) if self._versions[model][v]["stage"] == "Archived"), None)
        if target is None:  # nothing that was serving before is available
            return {"ok": False, "error": "no_rollback_target"}  # refuse rather than guess
        current = self.production(model)  # the bad build, if one is live
        if current is not None:  # take it out of service
            self._move(model, current, "Archived", actor, "rolled_back")  # not added to history: never roll back to it
        self._move(model, target, "Production", actor, "rollback")  # restore; no approval on the incident path
        return {"ok": True, "version": target}  # tell on-call what is serving now

    def production(self, model):  # the version the serving layer loads
        for v, rec in self._versions.get(model, {}).items():  # at most one can match
            if rec["stage"] == "Production":  # found the live version
                return v  # its number
        return None  # nothing live, or unknown model

    def stage(self, model, version):  # current stage of one version
        rec = self._versions.get(model, {}).get(version)  # None if unknown
        return rec["stage"] if rec else None  # stage string, or None for a missing version

    def lineage(self, model, version):  # what a version was built from
        rec = self._versions.get(model, {}).get(version)  # None if unknown
        if rec is None:  # nothing registered under that id
            return None  # no lineage to report
        return {"data_version": rec["data_version"], "code_version": rec["code_version"], "metrics": rec["metrics"]}  # for incidents

    def models_using_data(self, data_version):  # live versions affected by a bad dataset
        # versions trained on this data that are in Staging or Production, sorted by model then version
        return sorted([m, v] for m, vs in self._versions.items() for v, rec in vs.items()
                      if rec["data_version"] == data_version and rec["stage"] in ("Staging", "Production"))
```

## 8. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | production 2, v1 Archived; two events on the last promotion | superseded-then-manual ordering |
| Example 2 | `invalid_transition`, `approval_required`, `self_approval`, `not_found`; one event | the error ladder, and that errors change nothing |
| Example 3 | rollback to v1; events `rolled_back` then `rollback` | rollback order and no approval |
| rollback skips rejected candidate | v1, then `no_rollback_target`, then v1 again | history instead of "latest archived" |
| independent models and lineage | `churn` and `fraud` both start at v1; `ds-x` gives `[["churn", 1], ["fraud", 1]]` | per-model counters, sorted lineage queries, `None` for unknowns |
| manual archive and invalid moves | first rollback `no_rollback_target`; Archived→Production and Production→Staging invalid; `ghost` not found | manual archives aren't history; the allowed-move table |
| four eyes on promotion | two `self_approval`s, one `approval_required`; final rollback `no_rollback_target` | approval rules; nothing superseded yet |

## 9. Complexity

Every call is O(V) for `V` versions of one model at worst: `production()` scans the model's versions, and rollback scans the history. `models_using_data` scans every version of every model and sorts the matches, O(total versions · log). With at most 200 calls that's instant. You could cache the Production version per model to make `production()` O(1), at the cost of one more piece of state to keep in sync.

In a real registry the cost is in the guarantees, not the loops. Two promotions racing each other could both see the same "current" Production version. A real backend wraps the archive-then-promote pair in a transaction, or a compare-and-set on the alias, so the one-Production invariant holds under concurrency.

## 10. If you got Wrong Answer

- **Example 1's `stage(churn, 1)` is `Production`, and Example 3's rollback says `no_rollback_target`.** You promote without archiving the old version, so two versions are live, and `production()` returns whichever it finds first (v1).
- **Example 2 accepts `approved_by == actor`.** You're missing the self-approval check. "four eyes on promotion" fails too.
- **"rollback skips rejected candidate" restores v3.** You roll back to the latest archived version, which is the rejected candidate. In "manual archive and invalid moves" the same bug restores the manually retired v1.
- **"independent models and lineage" returns `not_found` for `fraud` v1.** Your version counter is global, so `fraud`'s first version became 2.
- **An event appears for a failed call.** Run every check before calling `_move`.
- **The two promotion events are in the wrong order.** Archive the old version first, then move the new one.

## 11. Follow-ups an interviewer might ask

- *MLflow deprecated stages. What replaced them?* Aliases like `@champion` and `@challenger`, plus tags. The invariants are the same: one version per alias, approval to move it, an audit trail of every move.
- *How should approval really work?* Not as a trusted string. Put it in the deploy pipeline (a GitHub environment with required reviewers, or a change ticket) and have the registry verify a signed approval token.
- *A training dataset turns out to contain PII. What do you do?* `models_using_data` lists every live version trained on it. That only works if you stored lineage at registration: data snapshot id, git SHA, config and eval report.
- *Who calls `rollback()`?* The canary controller (problem 147, canary-analysis), when it decides to roll back. The serving layer watches the alias and hot-swaps, so the rollback takes effect in seconds.
- *What else should the event stream feed?* An audit log (SOC 2 and SR 11-7 for banks both ask who promoted what and who approved it), plus the lineage behind each training set (problem 143, point-in-time-feature-join, keeps the `sources` for exactly this).
