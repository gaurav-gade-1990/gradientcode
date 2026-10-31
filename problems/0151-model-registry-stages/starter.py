class ModelRegistry:
    def __init__(self):
        self.events = []

    def register(self, model, data_version, code_version, metrics):
        raise NotImplementedError

    def transition(self, model, version, to_stage, actor, approved_by=None):
        raise NotImplementedError

    def rollback(self, model, actor):
        raise NotImplementedError

    def production(self, model):
        raise NotImplementedError

    def stage(self, model, version):
        raise NotImplementedError

    def lineage(self, model, version):
        raise NotImplementedError

    def models_using_data(self, data_version):
        raise NotImplementedError
