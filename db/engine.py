import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.makedirs("database", exist_ok=True)

engine = create_engine(
    "sqlite:///database/encomendas.db",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True, expire_on_commit=False)
