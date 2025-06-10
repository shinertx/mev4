class TransactionBuilder:
    """Builds and tracks transactions with nonce management."""

    def __init__(self, nonce=0):
        self.nonce = nonce

    def build(self, to, data):
        tx = {"nonce": self.nonce, "to": to, "data": data}
        self.nonce += 1
        return tx
