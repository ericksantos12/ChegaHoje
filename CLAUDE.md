# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ChegaHoje is a Telegram bot (python-telegram-bot v22, async) that tracks expected package deliveries per chat and sends a reminder at 08:00 (America/Sao_Paulo) for packages due the next day. Data lives in PostgreSQL via SQLAlchemy 2.0, with Alembic migrations. Code identifiers, comments, and all user-facing bot messages are in Portuguese (bot replies use a casual, lowercase, slangy tone — keep it consistent).

## Commands

There is no test suite, linter, or formatter configured.

```bash
# Full stack (bot + postgres + adminer on http://localhost:5460)
docker-compose up -d --build

# Local, without Docker (needs a reachable Postgres in DATABASE_URL)
pip install -r requirements.txt
alembic upgrade head
python main.py

# New migration after changing a model
alembic revision --autogenerate -m "description"
```

The container's `entrypoint.sh` runs `alembic upgrade head` before `python main.py`, so migrations apply automatically on deploy.

## Environment

Loaded from `.env` via python-dotenv (see `.env.example`): `TELEGRAM_TOKEN` (required), `DATABASE_URL` (required — importing `db` raises `ValueError` if unset, so even importing repositories needs it), `DEVELOPER_CHAT_ID` (receives full tracebacks from `error_handler` in `main.py`), `POSTGRES_*` (compose db service), optional `TIME_ZONE` (used by the daily check job to compute "tomorrow", default America/Sao_Paulo) and `LOG_LEVEL` (default INFO). `docker-compose.yml` only forwards `TELEGRAM_TOKEN`, `DATABASE_URL`, and `DEVELOPER_CHAT_ID` to the bot container.

## Architecture

Layered: `main.py` → `usecases/` → `repositories/` → `db/`.

- **`main.py`** builds the `Application`, creates a single `SAEncomenda` repository, and registers each use case as a `CommandHandler` with the repository injected via `functools.partial(handler, repository=repository)`. It also schedules `checar_entregas` with `app.job_queue.run_daily` at 08:00 SP time (hardcoded there, separate from `TIME_ZONE`). Commands: `/start`, `/adicionar`, `/listar`, `/remover`, and the undocumented `/testar_alerta` (triggers the daily check immediately — note it alerts *all* chats with packages due tomorrow, not just the caller).
- **`usecases/`** — one async handler per file with signature `(update, context, repository)` (the job takes `(context, repository)`), exported through `usecases/__init__.py`. Handlers parse `context.args`, call the repository, and reply via `context.bot.send_message`. New commands follow this pattern: add the file, export it in `__init__.py`, register it in `main.py`.
- **`repositories/interfaces/IEncomendaRepository.py`** — `EncomendaRepository` is a `typing.Protocol`; use cases type against it. `repositories/SAEncomenda.py` is the SQLAlchemy implementation. Each method opens its own short-lived `SessionLocal()` session, catches `SQLAlchemyError`, logs, and returns a failure value (`(None, False)`, `False`, or `[]`) instead of raising — use cases check these return values to send error messages. Returned ORM objects are detached from their session.
- **`db/`** — `engine.py` creates the engine/`SessionLocal` at import time. The only model is `Encomenda` (table `encomendas`: `id`, `chat_id`, `item`, `data` (Date), `dono`). Its `declarative_base()` `Base` is defined in `db/models/encomenda.py` and imported by `migrations/env.py` as `target_metadata`; any new model must use that same `Base` (or env.py must be updated) for autogenerate to see it.
- **`utils/logger.py`** — call `logger(__name__)`; logging is configured once at module import. Modules conventionally name the result `logging`.

### Behavior worth knowing

- `/adicionar` input is `item - dd/mm/aaaa`, split on `-` (so a hyphen inside the item name breaks parsing). Dates are stored as `Date`; displayed as `dd/mm/YYYY`.
- `/remover N` uses the 1-based position from `/listar`, not the DB id. Both rely on `get_by_chat_id` ordering by `(data, id)`, so that ordering must stay in sync between the two.
- Packages are scoped per `chat_id` (a group chat shares one list); `dono` stores the adding user's first name.
