from .base import AbstractStrategy


class CexDexArbStrategy(AbstractStrategy):
    """Simple placeholder CEX-DEX arbitrage strategy."""

    def run(self, state, adapters, config):
        killer = config.get('killer')
        if killer and killer.killed:
            self.abort('Kill switch engaged')
            return
        dex = adapters.get('dex')
        cex = adapters.get('cex')
        ai = adapters.get('ai')
        prediction = ai.predict({'market': 'eth'}) if ai else {}
        state.set('prediction', prediction)
        if dex and cex:
            tx = dex.swap('ETH', 'USDC', 1)
            state.set('last_tx', tx)

    def abort(self, reason):
        raise SystemExit(reason)
