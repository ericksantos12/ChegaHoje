from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from db.models import Encomenda
from repositories.interfaces import EncomendaRepository
from utils import get_logger

log = get_logger(__name__)


class SAEncomenda(EncomendaRepository):
    """Implementação SQLAlchemy do repositório de encomendas.

    Cada método abre uma sessão curta a partir da fábrica injetada. A fábrica
    deve ser criada com `expire_on_commit=False` (ver `db.create_session_factory`)
    para que os objetos retornados continuem utilizáveis após o fechamento da sessão.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, chat_id: int, item: str, data: date, dono: str = "Sem dono") -> Encomenda | None:
        with self._session_factory() as session:
            try:
                encomenda = Encomenda(chat_id=chat_id, item=item, data=data, dono=dono)
                session.add(encomenda)
                session.commit()
                session.refresh(encomenda)
                return encomenda
            except SQLAlchemyError as e:
                session.rollback()
                log.error("Erro ao criar encomenda para o chat %s: %s", chat_id, e)
                return None

    def remove(self, chat_id: int, encomenda_id: int) -> bool:
        with self._session_factory() as session:
            try:
                result = session.execute(
                    delete(Encomenda).where(Encomenda.id == encomenda_id, Encomenda.chat_id == chat_id)
                )
                session.commit()
                if result.rowcount == 0:
                    log.warning("Encomenda %s não encontrada no chat %s para remoção", encomenda_id, chat_id)
                    return False
                return True
            except SQLAlchemyError as e:
                session.rollback()
                log.error("Erro ao remover encomenda %s do chat %s: %s", encomenda_id, chat_id, e)
                return False

    def get_by_chat_id(self, chat_id: int) -> list[Encomenda]:
        with self._session_factory() as session:
            try:
                stmt = (
                    select(Encomenda)
                    .where(Encomenda.chat_id == chat_id)
                    .order_by(Encomenda.data.asc(), Encomenda.id.asc())
                )
                return list(session.scalars(stmt).all())
            except SQLAlchemyError as e:
                session.rollback()
                log.error("Erro ao buscar encomendas do chat %s: %s", chat_id, e)
                return []

    def get_by_date(self, data: date) -> list[Encomenda]:
        with self._session_factory() as session:
            try:
                log.debug("Buscando encomendas para a data: %s", data)
                stmt = (
                    select(Encomenda)
                    .where(Encomenda.data == data)
                    .order_by(Encomenda.chat_id.asc(), Encomenda.id.asc())
                )
                encomendas = list(session.scalars(stmt).all())
                if not encomendas:
                    log.debug("Nenhuma encomenda encontrada para a data %s", data)
                return encomendas
            except SQLAlchemyError as e:
                session.rollback()
                log.error("Erro ao buscar encomendas pela data %s: %s", data, e)
                return []

    def remove_before(self, data: date) -> int:
        with self._session_factory() as session:
            try:
                result = session.execute(delete(Encomenda).where(Encomenda.data < data))
                session.commit()
                removidas = result.rowcount or 0
                if removidas:
                    log.info("%s encomenda(s) anteriores a %s removida(s)", removidas, data)
                return removidas
            except SQLAlchemyError as e:
                session.rollback()
                log.error("Erro ao remover encomendas anteriores a %s: %s", data, e)
                return 0
