import logging
import os
from dotenv import load_dotenv

load_dotenv()


# Configure logging once at module level
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, log_level, logging.INFO),
    force=True
)


def logger(name=__name__) -> logging.Logger:
    return logging.getLogger(name)
