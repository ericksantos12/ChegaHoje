"""Testes de integração do SAEncomenda contra um PostgreSQL real.

Defina TEST_DATABASE_URL (ex.: postgresql://user:pass@localhost:5432/chegahoje_test)
para rodar. O schema é criado com Base.metadata.create_all e removido ao final,
então use um banco descartável.
"""

import os
from collections.abc import Iterator
from datetime import date

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from db import create_session_factory
from db.models import Base, Encomenda
from repositories import SAEncomenda

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    pytest.skip("TEST_DATABASE_URL não definida", allow_module_level=True)

SUPERGRUPO = -1001234567890
OUTRO_CHAT = 987654321


@pytest.fixture(scope="module")
def session_factory() -> Iterator[sessionmaker[Session]]:
    factory = create_session_factory(TEST_DATABASE_URL)
    engine = factory.kw["bind"]
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    try:
        yield factory
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def repo(session_factory: sessionmaker[Session]) -> Iterator[SAEncomenda]:
    yield SAEncomenda(session_factory)
    with session_factory() as session:
        session.execute(delete(Encomenda))
        session.commit()


def _count(session_factory: sessionmaker[Session]) -> int:
    with session_factory() as session:
        return session.scalar(select(func.count()).select_from(Encomenda))


def test_create_retorna_encomenda_desanexada(repo: SAEncomenda) -> None:
    encomenda = repo.create(SUPERGRUPO, "fone", date(2026, 11, 11), "Ana")

    assert encomenda is not None
    # atributos acessíveis após o fechamento da sessão
    assert encomenda.id is not None
    assert encomenda.chat_id == SUPERGRUPO
    assert encomenda.item == "fone"
    assert encomenda.data == date(2026, 11, 11)
    assert encomenda.dono == "Ana"


def test_create_dono_padrao(repo: SAEncomenda) -> None:
    encomenda = repo.create(OUTRO_CHAT, "livro", date(2026, 11, 11))

    assert encomenda is not None
    assert encomenda.dono == "Sem dono"


def test_create_supergrupo_persiste_chat_id_bigint(repo: SAEncomenda) -> None:
    repo.create(SUPERGRUPO, "teclado", date(2026, 11, 12))

    encomendas = repo.get_by_chat_id(SUPERGRUPO)
    assert [e.chat_id for e in encomendas] == [SUPERGRUPO]


def test_create_retorna_none_em_erro(repo: SAEncomenda) -> None:
    # item é NOT NULL: o erro de banco vira None, sem exceção
    assert repo.create(OUTRO_CHAT, None, date(2026, 11, 11)) is None  # type: ignore[arg-type]


def test_get_by_chat_id_ordena_por_data_e_id(repo: SAEncomenda) -> None:
    c = repo.create(SUPERGRUPO, "c", date(2026, 12, 1))
    a = repo.create(SUPERGRUPO, "a", date(2026, 11, 20))
    b = repo.create(SUPERGRUPO, "b", date(2026, 11, 20))
    repo.create(OUTRO_CHAT, "de outro chat", date(2026, 11, 1))

    encomendas = repo.get_by_chat_id(SUPERGRUPO)

    assert [e.id for e in encomendas] == [a.id, b.id, c.id]
    assert repo.get_by_chat_id(123) == []


def test_remove_apenas_do_proprio_chat(repo: SAEncomenda, session_factory: sessionmaker[Session]) -> None:
    encomenda = repo.create(SUPERGRUPO, "mouse", date(2026, 11, 11))

    # id existente, mas de outro chat: não remove e não altera a linha
    assert repo.remove(OUTRO_CHAT, encomenda.id) is False
    restantes = repo.get_by_chat_id(SUPERGRUPO)
    assert [(e.id, e.item) for e in restantes] == [(encomenda.id, "mouse")]

    assert repo.remove(SUPERGRUPO, encomenda.id) is True
    assert repo.get_by_chat_id(SUPERGRUPO) == []
    assert _count(session_factory) == 0


def test_remove_inexistente(repo: SAEncomenda) -> None:
    assert repo.remove(SUPERGRUPO, 999_999) is False


def test_get_by_date(repo: SAEncomenda) -> None:
    alvo = date(2026, 11, 11)
    e1 = repo.create(SUPERGRUPO, "um", alvo)
    e2 = repo.create(OUTRO_CHAT, "dois", alvo)
    repo.create(SUPERGRUPO, "outra data", date(2026, 11, 12))

    encomendas = repo.get_by_date(alvo)

    assert {e.id for e in encomendas} == {e1.id, e2.id}
    assert repo.get_by_date(date(2030, 1, 1)) == []


def test_remove_before(repo: SAEncomenda, session_factory: sessionmaker[Session]) -> None:
    repo.create(SUPERGRUPO, "velha 1", date(2026, 11, 1))
    repo.create(OUTRO_CHAT, "velha 2", date(2026, 11, 9))
    hoje = repo.create(SUPERGRUPO, "hoje", date(2026, 11, 10))
    futura = repo.create(OUTRO_CHAT, "futura", date(2026, 11, 11))

    assert repo.remove_before(date(2026, 11, 10)) == 2

    restantes = repo.get_by_chat_id(SUPERGRUPO) + repo.get_by_chat_id(OUTRO_CHAT)
    assert {e.id for e in restantes} == {hoje.id, futura.id}
    assert repo.remove_before(date(2026, 11, 10)) == 0
    assert _count(session_factory) == 2


def test_banco_indisponivel_retorna_valores_de_falha() -> None:
    # porta 1 recusa a conexão: nenhum método deve lançar exceção
    repo = SAEncomenda(create_session_factory("postgresql://ninguem:x@127.0.0.1:1/nada"))

    assert repo.create(SUPERGRUPO, "x", date(2026, 11, 11)) is None
    assert repo.remove(SUPERGRUPO, 1) is False
    assert repo.get_by_chat_id(SUPERGRUPO) == []
    assert repo.get_by_date(date(2026, 11, 11)) == []
    assert repo.remove_before(date(2026, 11, 11)) == 0
