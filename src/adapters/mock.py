class MockAdapter:
    """Test/mocking adapter for simulations."""

    def action(self, *args, **kwargs):
        return {
            'args': args,
            'kwargs': kwargs,
        }
