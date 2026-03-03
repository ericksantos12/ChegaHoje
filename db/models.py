from sqlalchemy import Column, Integer, String, Date, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Encomenda(Base):
    __tablename__ = "encomendas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, nullable=False, index=True)
    item = Column(String, nullable=False)
    data = Column(Date, nullable=False, index=True)
