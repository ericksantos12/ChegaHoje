from datetime import date

from sqlalchemy import BigInteger, Date, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


class Encomenda(Base):
    __tablename__ = "encomendas"
    __table_args__ = (Index("ix_encomendas_chat_id_data", "chat_id", "data"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # BigInteger: ids de supergrupos do Telegram (-100xxxxxxxxxx) não cabem em int4
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    item: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    dono: Mapped[str | None] = mapped_column(Text, default="Sem dono")

    def __repr__(self) -> str:
        return f"Encomenda(id={self.id!r}, chat_id={self.chat_id!r}, item={self.item!r}, data={self.data!r})"
