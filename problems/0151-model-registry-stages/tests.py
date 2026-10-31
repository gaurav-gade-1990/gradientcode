def reg(model, data, code, auc):
    return ["register", {"model": model, "data_version": data, "code_version": code, "metrics": {"auc": auc}}]


def tr(model, version, to, actor, approved_by=None):
    kw = {"model": model, "version": version, "to_stage": to, "actor": actor}
    if approved_by is not None:
        kw["approved_by"] = approved_by
    return ["transition", kw]


def rb(model, actor):
    return ["rollback", {"model": model, "actor": actor}]


def q(method, **kw):
    return [method, kw]


def cases():
    ex1 = [
        reg("churn", "ds-2026-09", "a1f3", 0.81),
        reg("churn", "ds-2026-10", "b7c2", 0.84),
        tr("churn", 1, "Staging", "maya"),
        tr("churn", 1, "Production", "maya", "li"),
        tr("churn", 2, "Staging", "maya"),
        tr("churn", 2, "Production", "maya", "li"),
        q("production", model="churn"),
        q("stage", model="churn", version=1),
    ]
    ex2 = [
        reg("fraud", "ds-a", "c1", 0.9),
        tr("fraud", 1, "Production", "sam", "li"),
        tr("fraud", 1, "Staging", "sam"),
        tr("fraud", 1, "Production", "sam"),
        tr("fraud", 1, "Production", "sam", "sam"),
        tr("fraud", 7, "Staging", "sam"),
        q("production", model="fraud"),
    ]
    ex3 = ex1 + [rb("churn", "oncall"), q("production", model="churn"), q("lineage", model="churn", version=1)]

    tricky = [
        reg("ranker", "ds-1", "r1", 0.70),            # v1
        reg("ranker", "ds-2", "r2", 0.72),            # v2
        reg("ranker", "ds-2", "r3", 0.69),            # v3 (rejected)
        reg("ranker", "ds-3", "r4", 0.74),            # v4
        tr("ranker", 1, "Staging", "a"), tr("ranker", 1, "Production", "a", "b"),
        tr("ranker", 2, "Staging", "a"), tr("ranker", 2, "Production", "a", "b"),   # v1 superseded
        tr("ranker", 3, "Staging", "a"), tr("ranker", 3, "Archived", "a"),           # v3 rejected: latest archived
        rb("ranker", "oncall"),                                                      # -> v1, v2 rolled_back
        q("production", model="ranker"),
        rb("ranker", "oncall"),                                                      # history [1]: v1 is in Production -> none
        tr("ranker", 4, "Staging", "a"), tr("ranker", 4, "Production", "a", "c"),   # v1 superseded again
        rb("ranker", "oncall"),                                                      # -> v1 again
        tr("ranker", 2, "Staging", "a"),                                             # restore v2 to Staging
        q("models_using_data", data_version="ds-2"),
        q("stage", model="ranker", version=4),
    ]
    multi = [
        reg("churn", "ds-x", "c1", 0.8), reg("fraud", "ds-x", "f1", 0.9), reg("fraud", "ds-y", "f2", 0.91), reg("churn", "ds-y", "c2", 0.82),
        tr("fraud", 1, "Staging", "a"), tr("fraud", 2, "Staging", "a"), tr("churn", 2, "Staging", "a"), tr("churn", 1, "Staging", "a"),
        tr("fraud", 2, "Production", "a", "b"), tr("churn", 1, "Production", "a", "b"),
        q("models_using_data", data_version="ds-x"), q("models_using_data", data_version="ds-y"), q("models_using_data", data_version="ds-z"),
        q("lineage", model="fraud", version=2), q("lineage", model="fraud", version=3), q("stage", model="search", version=1),
        q("production", model="search"),
    ]
    archive_prod = [
        reg("asr", "d1", "w1", 0.1), reg("asr", "d2", "w2", 0.09),
        tr("asr", 1, "Staging", "u"), tr("asr", 1, "Production", "u", "v"),
        tr("asr", 1, "Archived", "u"),                       # manual archive: not rollback history
        rb("asr", "oncall"),
        tr("asr", 1, "Production", "u", "v"),                 # Archived -> Production is invalid
        tr("asr", 1, "Staging", "u"), tr("asr", 2, "Staging", "u"),
        tr("asr", 1, "Production", "u", "v"), tr("asr", 2, "Production", "w", "v"),
        tr("asr", 2, "Staging", "u"),                         # Production -> Staging is invalid
        rb("asr", "oncall"), rb("ghost", "oncall"),
        q("production", model="asr"),
    ]
    return [
        {"name": "Example 1", "hidden": False, "args": {"ops": ex1},
         "explanation": "Promoting v2 first archives v1 (reason superseded), then moves v2 to Production. That's two events for one call, in that order."},
        {"name": "Example 2", "hidden": False, "args": {"ops": ex2},
         "explanation": "None to Production skips Staging (invalid_transition). Then a promotion with no approver, then a self-approval, are both refused. Version 7 doesn't exist. Only the move to Staging emits an event."},
        {"name": "Example 3", "hidden": False, "args": {"ops": ex3},
         "explanation": "Rollback archives v2 (reason rolled_back) and restores v1, the most recently superseded version, with no approval needed. Lineage tells the incident channel which data and code v1 was built from."},
        {"name": "rollback skips rejected candidate", "args": {"ops": tricky}},
        {"name": "independent models and lineage", "args": {"ops": multi}},
        {"name": "manual archive and invalid moves", "args": {"ops": archive_prod}},
        {"name": "four eyes on promotion", "args": {"ops": [
            reg("pricing", "ds-q3", "p9", 0.77), reg("pricing", "ds-q3", "p10", 0.79),
            tr("pricing", 1, "Staging", "dev"), tr("pricing", 1, "Production", "dev", "dev"),
            tr("pricing", 1, "Production", "dev"), q("production", model="pricing"),
            tr("pricing", 1, "Production", "dev", "lead"), tr("pricing", 2, "Staging", "lead"),
            tr("pricing", 2, "Production", "lead", "lead"), q("production", model="pricing"),
            rb("pricing", "oncall")]}},
    ]
