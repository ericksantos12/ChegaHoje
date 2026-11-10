# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ChegaHoje is a Telegram bot (python-telegram-bot v22, async) that tracks expected package deliveries per chat and sends a daily reminder (default 08:00 America/Sao_Paulo) for packages due the next day. Data lives in PostgreSQL via SQLAlchemy 2.0, with Alembic migrations. Code identifiers, comments, and all user-facing bot messages are in Portuguese (bot replies use a casual, lowercase, slangy tone — keep it consistent).

## Commands

```bash
pip install -r requirements-dev.txt     # runtime deps + pytest + ruff

ruff check .                            # lint (config in pyproject.toml; CI runs this)
ruff format .

pytest                                  # all tests; repository tests skip without TEST_DATABASE_URL
TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/test_db pytest   # include Postgres integration tests
pytest tests/test_services.py::test_parse_simples                       # single test

# Full stack (bot + postgres + adminer on http://localhost:5460)
docker-compose up -d --build

# Local, without Docker (needs a reachable Postgres in DATABASE_URL)
alembic upgrade head
python main.py

# New migration after changing a model; `alembic check` must report no diff
alembic revision --autogenerate -m "description"
alembic check
```

CI (`.github/workflows/ci.yml`) runs `ruff check .` and `pytest` against a `postgres:16-alpine` service. The container's `entrypoint.sh` runs `alembic upgrade head` before `python main.py`, so migrations apply automatically on deploy. The repository tests create/drop the schema with `Base.metadata.create_all`, so point `TEST_DATABASE_URL` at a throwaway database.

## Configuration

All runtime config goes through `config.get_settings()` (cached `Settings` dataclass, raises `ConfigError` on missing/invalid values; `main.py` exits 1 on it). Don't call `os.getenv` elsewhere — the exceptions are `migrations/env.py` (reads `DATABASE_URL` directly so Alembic doesn't need the bot token) and `utils/logger.py` (`LOG_LEVEL` at import). Variables: `TELEGRAM_TOKEN`, `DATABASE_URL` (required), `DEVELOPER_CHAT_ID` (gets error tracebacks and is the only chat allowed to run `/testar_alerta`), `TIME_ZONE`, `ALERT_TIME` (`HH:MM`), `LOG_LEVEL`. See `.env.example`.

## Architecture

`main.py` → `handlers/` → `services/` (pure) + `repositories/` → `db/`.

- **`main.py`** loads settings, builds `SAEncomenda(create_session_factory(settings.database_url))`, and registers handlers/jobs with dependencies injected via `functools.partial(handler, repository=..., settings=...)` (keyword-only params). Jobs: `checar_entregas` at `settings.alert_time`, `limpar_encomendas_antigas` (deletes packages dated before today) at 03:00 in `settings.time_zone`.
- **`services/`** — business logic with no Telegram or DB imports: `/adicionar` parsing and validation, list-index selection, date helpers (take `now`/`tz` as args), and all bot message texts (`services/mensagens.py`). Invalid user input raises `EntradaInvalida`, whose `.mensagem` is the reply text. Put new logic here so it's unit-testable.
- **`handlers/`** — thin async adapters: `comandos.py` (commands), `jobs.py` (scheduled jobs), `erros.py` (global error handler; HTML-escapes and truncates to Telegram's 4096-char limit). Handlers import the repository only as a type (`EncomendaRepository` under `TYPE_CHECKING`), so their tests don't need a database. New command: logic in `services/`, handler in `handlers/comandos.py`, export in `handlers/__init__.py`, register in `main.py`.
- **`repositories/`** — `interfaces/IEncomendaRepository.py` is a `typing.Protocol` (the contract); `SAEncomenda` implements it. Each method opens its own session from the injected factory, catches `SQLAlchemyError`, logs, and returns a failure value (`None`, `False`, `[]`, `0`) instead of raising — handlers check these. Returned ORM objects are detached (factory uses `expire_on_commit=False`). `remove(chat_id, id)` only deletes rows belonging to that chat.
- **`db/`** — no work at import time; `create_session_factory(url)` builds engine + sessionmaker. Models use 2.0-style `Mapped`/`mapped_column` on `Base` from `db/models/base.py`, which `migrations/env.py` uses as `target_metadata` — new models must inherit it. `chat_id` is `BigInteger` (supergroup ids like `-100…` overflow int4).
- **`utils/logger.py`** — `get_logger(__name__)`; name the module variable `log` and use `%s` formatting. `main.py` silences `httpx` INFO logs because they include the bot token in URLs.

### Tests

`tests/test_services.py` (pure functions), `tests/test_handlers.py` (handlers with an in-memory fake repository and `AsyncMock` bot, coroutines run via `asyncio.run` — no pytest-asyncio), `tests/test_repository.py` (real Postgres). There is no `conftest.py`; fixtures live in each test file.

### Behavior worth knowing

- `/adicionar item - dd/mm/aaaa` splits on the **last** `-` (items may contain hyphens) and rejects dates before today.
- `/remover N` uses the 1-based position from `/listar`, not the DB id; both rely on `get_by_chat_id` ordering by `(data, id)`.
- Packages are scoped per `chat_id` (a group shares one list); `dono` stores the adding user's first name.
- `/testar_alerta` (undocumented) runs the daily check immediately and alerts *all* chats, which is why it's restricted to `DEVELOPER_CHAT_ID`.
