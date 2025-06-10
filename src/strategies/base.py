class AbstractStrategy:
    """Base strategy interface."""

    def run(self, state, adapters, config):
        raise NotImplementedError

    def simulate(self, state, adapters, config):
        raise NotImplementedError

    def mutate(self, params):
        raise NotImplementedError

    def snapshot(self, path):
        raise NotImplementedError

    def restore(self, path):
        raise NotImplementedError

    def abort(self, reason):
        raise NotImplementedError
