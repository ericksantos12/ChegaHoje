from datetime import date
from typing import Optional

from repositories.interfaces import EncomendaRepository
from db.models import Encomenda
from db import SessionLocal
from utils.logger import logger
from sqlalchemy.exc import SQLAlchemyError

logging = logger(__name__)

class SAEncomenda(EncomendaRepository):

    def create(self, chat_id: int, item: str, data: date, dono: str = "Sem dono") -> tuple[Encomenda, bool] | tuple[None, bool]:
        with SessionLocal() as session:
            try:
                encomenda = Encomenda(chat_id=chat_id, item=item, data=data, dono=dono)
                session.add(encomenda)
                session.commit()
                session.refresh(encomenda)
                return encomenda, True
            except SQLAlchemyError as e:
                session.rollback()
                logging.error("Erro ao criar encomenda: %s", e)
                return None, False


    def update(self, encomenda_id: int, **fields: object) -> bool:
        with SessionLocal() as session:
            try:
                encomenda = session.query(Encomenda).filter_by(id=encomenda_id).first()
                if not encomenda:
                    logging.warning("Encomenda com id %d não encontrada para atualização", encomenda_id)
                    return False
                for key, value in fields.items():
                    setattr(encomenda, key, value)
                session.commit()
                return True
            except SQLAlchemyError as e:
                session.rollback()
                logging.error("Erro ao atualizar encomenda: %s", e)
                return False

    def remove(self, encomenda_id: int) -> bool:
        with SessionLocal() as session:
            try:
                encomenda = session.query(Encomenda).filter_by(id=encomenda_id).first()
                if not encomenda:
                    logging.warning("Encomenda com id %d não encontrada para remoção", encomenda_id)
                    return False
                session.delete(encomenda)
                session.commit()
                return True
            except SQLAlchemyError as e:
                session.rollback()
                logging.error("Erro ao remover encomenda: %s", e)
                return False

    def get_by_chat_id(self, chat_id: int) -> list[Encomenda]:
        with SessionLocal() as session:
            try:
                encomendas = session.query(Encomenda).filter_by(chat_id=chat_id).all()
                return encomendas
            except SQLAlchemyError as e:
                session.rollback()
                logging.error("Erro ao buscar encomendas por chat_id: %s", e)
                return []

    def get_by_date(self, date: str) -> list[Encomenda]:
        with SessionLocal() as session:
            try:
                logging.debug("Buscando encomendas para a data: %s", date)
                encomendas = session.query(Encomenda).filter_by(data=date).order_by(Encomenda.data.asc()).all()
                if not encomendas:
                    logging.warning("Nenhuma encomenda encontrada para a data %s", date)
                    return []
                return encomendas
            except SQLAlchemyError as e:
                session.rollback()
                logging.error("Erro ao buscar encomendas por data: %s", e)
                return []


