class State:
    """Atomic, auditable state container."""

    def __init__(self):
        self.data = {}
        self.history = []

    def set(self, key, value):
        self.history.append((key, self.data.get(key)))
        self.data[key] = value

    def get(self, key, default=None):
        return self.data.get(key, default)

    def snapshot(self):
        return dict(self.data)

    def restore(self, snapshot):
        self.data = dict(snapshot)
