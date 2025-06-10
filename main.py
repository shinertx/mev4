from src.core.config import load_config
from src.core.state import State
from src.core.kill import KillSwitch
from src.core.agent import Agent
from src.adapters.dex import DEXAdapter
from src.adapters.cex import CEXAdapter
from src.adapters.ai_model import AIModelAdapter
from src.strategies.cex_dex_arb import CexDexArbStrategy


def main():
    config = load_config()
    killer = KillSwitch()
    config['killer'] = killer
    state = State()
    adapters = {
        'dex': DEXAdapter(),
        'cex': CEXAdapter(),
        'ai': AIModelAdapter()
    }
    agent = Agent(state, adapters, config)
    strategy = CexDexArbStrategy()
    agent.run(strategy)


if __name__ == "__main__":
    main()
