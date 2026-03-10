import logging
import os
from dotenv import load_dotenv

load_dotenv()


def logger(name=__name__) -> logging.Logger:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=getattr(logging, log_level, logging.INFO)
    )
    return logging.getLogger(name)
