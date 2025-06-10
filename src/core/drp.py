class DRP:
    """Disaster Recovery Protocol snapshot/restore logic."""

    def snapshot(self, state, path):
        with open(path, 'w') as f:
            f.write(str(state.snapshot()))

    def restore(self, state, path):
        with open(path) as f:
            snapshot = eval(f.read())
        state.restore(snapshot)
