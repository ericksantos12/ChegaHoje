import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from utils import logger

load_dotenv()

logging = logger(__name__)

if not os.getenv('DATABASE_URL'):
    logging.error("DATABASE_URL is not set in the environment variables.")
    raise ValueError("DATABASE_URL is required to connect to the database.")

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
