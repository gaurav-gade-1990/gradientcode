# Accepts approved_by == actor, so one engineer can push a model to Production alone.
ALLOWED = {
    ("None", "Staging"), ("None", "Archived"),
    ("Staging", "Production"), ("Staging", "Archived"),
    ("Production", "Archived"), ("Archived", "Staging"),
}


class ModelRegistry:
    def __init__(self):
        self.events = []
        self._versions = {}   # model -> {version: record}
        self._history = {}    # model -> versions superseded by a promotion, oldest first

    def register(self, model, data_version, code_version, metrics):
        versions = self._versions.setdefault(model, {})
        self._history.setdefault(model, [])
        v = len(versions) + 1
        versions[v] = {"stage": "None", "data_version": data_version, "code_version": code_version, "metrics": metrics}
        return v

    def _move(self, model, version, to, actor, reason):
        rec = self._versions[model][version]
        self.events.append({"model": model, "version": version, "from": rec["stage"], "to": to, "actor": actor, "reason": reason})
        rec["stage"] = to

    def transition(self, model, version, to_stage, actor, approved_by=None):
        rec = self._versions.get(model, {}).get(version)
        if rec is None:
            return {"ok": False, "error": "not_found"}
        if (rec["stage"], to_stage) not in ALLOWED:
            return {"ok": False, "error": "invalid_transition"}
        if to_stage == "Production":
            if approved_by is None:
                return {"ok": False, "error": "approval_required"}
            current = self.production(model)
            if current is not None:
                self._move(model, current, "Archived", actor, "superseded")
                self._history[model].append(current)
        self._move(model, version, to_stage, actor, "manual")
        return {"ok": True}

    def rollback(self, model, actor):
        if model not in self._versions:
            return {"ok": False, "error": "not_found"}
        target = next((v for v in reversed(self._history[model]) if self._versions[model][v]["stage"] == "Archived"), None)
        if target is None:
            return {"ok": False, "error": "no_rollback_target"}
        current = self.production(model)
        if current is not None:
            self._move(model, current, "Archived", actor, "rolled_back")
        self._move(model, target, "Production", actor, "rollback")
        return {"ok": True, "version": target}

    def production(self, model):
        for v, rec in self._versions.get(model, {}).items():
            if rec["stage"] == "Production":
                return v
        return None

    def stage(self, model, version):
        rec = self._versions.get(model, {}).get(version)
        return rec["stage"] if rec else None

    def lineage(self, model, version):
        rec = self._versions.get(model, {}).get(version)
        if rec is None:
            return None
        return {"data_version": rec["data_version"], "code_version": rec["code_version"], "metrics": rec["metrics"]}

    def models_using_data(self, data_version):
        return sorted([m, v] for m, vs in self._versions.items() for v, rec in vs.items()
                      if rec["data_version"] == data_version and rec["stage"] in ("Staging", "Production"))
