import logging
import os

from dotenv import load_dotenv

load_dotenv()

log_level = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, log_level, logging.INFO),
    force=True,
)


def get_logger(name: str = __name__) -> logging.Logger:
    return logging.getLogger(name)


# Alias temporário para compatibilidade: use get_logger.
logger = get_logger
