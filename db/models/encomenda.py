from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Text, Date, Index

Base = declarative_base()

class Encomenda(Base):
    __tablename__ = 'encomendas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, index=True, nullable=False)
    item = Column(Text, nullable=False)
    data = Column(Date, index=True, nullable=False)
    dono = Column(Text, default="Sem dono")

Index('ix_encomendas_chat_id_data', Encomenda.chat_id, Encomenda.data)
