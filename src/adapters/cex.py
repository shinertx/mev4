class CEXAdapter:
    """Placeholder CEX adapter."""

    def place_order(self, pair, side, amount):
        return {
            'pair': pair,
            'side': side,
            'amount': amount,
        }
