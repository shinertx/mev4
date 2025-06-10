class KillSwitch:
    """Simple kill switch for emergency shutdown."""

    def __init__(self):
        self.killed = False

    def engage(self):
        self.killed = True
