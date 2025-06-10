import logging

logger = logging.getLogger("mev").getChild("core")
logging.basicConfig(level=logging.INFO)


def log(event, **kwargs):
    message = f"{event} | {kwargs}"
    logger.info(message)
    print(message)
