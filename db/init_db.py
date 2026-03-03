import logging
from sqlalchemy import text
from db.engine import engine
from db.models import Base


def init_db() -> None:
    """Cria as tabelas e executa migração manual de data TEXT -> DATE se necessário."""
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(encomendas)"))
        columns = {row[1]: row[2] for row in result}  # name -> type

    if not columns:
        # tabela não existe ainda, cria direto
        Base.metadata.create_all(engine)
        logging.info("banco de dados inicializado com sucesso.")
        return

    data_type = columns.get("data", "").upper()
    if data_type != "DATE":
        # migração: TEXT -> DATE usando rename + recreate
        logging.info("migrando coluna 'data' de TEXT para DATE...")
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE encomendas RENAME TO encomendas_old"))
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO encomendas (id, chat_id, item, data) "
                "SELECT id, chat_id, item, date(data) FROM encomendas_old"
            ))
            conn.execute(text("DROP TABLE encomendas_old"))
        logging.info("migração de 'data' para DATE concluída.")
    else:
        logging.info("schema já atualizado, nenhuma migração necessária.")
