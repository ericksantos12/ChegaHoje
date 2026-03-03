from datetime import date
from sqlalchemy import select
from db.engine import SessionLocal
from db.models import Encomenda


class SqlAlchemyEncomendaRepository:
    def add(self, chat_id: int, item: str, data: date) -> Encomenda:
        with SessionLocal() as session:
            encomenda = Encomenda(chat_id=chat_id, item=item, data=data)
            session.add(encomenda)
            session.commit()
            session.refresh(encomenda)
            return encomenda

    def list_by_chat(self, chat_id: int) -> list[Encomenda]:
        with SessionLocal() as session:
            result = session.execute(
                select(Encomenda)
                .where(Encomenda.chat_id == chat_id)
                .order_by(Encomenda.data.asc())
            )
            return list(result.scalars().all())

    def remove_by_id(self, id: int) -> None:
        with SessionLocal() as session:
            encomenda = session.get(Encomenda, id)
            if encomenda:
                session.delete(encomenda)
                session.commit()

    def list_by_date(self, data: date) -> list[Encomenda]:
        with SessionLocal() as session:
            result = session.execute(
                select(Encomenda).where(Encomenda.data == data)
            )
            return list(result.scalars().all())
