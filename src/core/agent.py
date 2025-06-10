class Agent:
    """Orchestrates strategy execution and system lifecycle."""

    def __init__(self, state, adapters, config):
        self.state = state
        self.adapters = adapters
        self.config = config
        self.killer = config.get('killer')

    def run(self, strategy):
        if self.killer and self.killer.killed:
            raise SystemExit("Kill switch engaged")
        strategy.run(self.state, self.adapters, self.config)
