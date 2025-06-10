from src.core.state import State
from src.core.kill import KillSwitch
from src.core.agent import Agent
from src.adapters.dex import DEXAdapter
from src.adapters.cex import CEXAdapter
from src.adapters.ai_model import AIModelAdapter
from src.strategies.cex_dex_arb import CexDexArbStrategy


def test_cex_dex_arb_strategy_runs():
    state = State()
    killer = KillSwitch()
    config = {'killer': killer}
    adapters = {
        'dex': DEXAdapter(),
        'cex': CEXAdapter(),
        'ai': AIModelAdapter()
    }
    agent = Agent(state, adapters, config)
    agent.run(CexDexArbStrategy())
    assert state.get('last_tx') is not None
