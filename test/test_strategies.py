from src.strategies.base import AbstractStrategy


def test_base_abstract():
    strat = AbstractStrategy()
    try:
        strat.run(None, None, None)
    except NotImplementedError:
        assert True
    else:
        assert False
