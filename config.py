"""Configuração central da aplicação, lida das variáveis de ambiente (.env)."""
import os
from dataclasses import dataclass
from datetime import time
from functools import lru_cache
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

DEFAULT_TIME_ZONE = "America/Sao_Paulo"
DEFAULT_ALERT_TIME = "08:00"


class ConfigError(ValueError):
    """Variável de ambiente ausente ou inválida."""


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    database_url: str
    developer_chat_id: int | None
    time_zone: ZoneInfo
    alert_time: time  # já com tzinfo=time_zone
    log_level: str


def _parse_alert_time(raw: str, tz: ZoneInfo) -> time:
    try:
        hour, minute = (int(part) for part in raw.split(":"))
        return time(hour=hour, minute=minute, tzinfo=tz)
    except ValueError as e:
        raise ConfigError(f"ALERT_TIME inválido: {raw!r} (use HH:MM)") from e


@lru_cache
def get_settings() -> Settings:
    load_dotenv()

    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise ConfigError("TELEGRAM_TOKEN é obrigatório.")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ConfigError("DATABASE_URL é obrigatório.")

    dev_chat_raw = os.getenv("DEVELOPER_CHAT_ID", "").strip()
    try:
        developer_chat_id = int(dev_chat_raw) if dev_chat_raw else None
    except ValueError as e:
        raise ConfigError(f"DEVELOPER_CHAT_ID inválido: {dev_chat_raw!r}") from e

    tz = ZoneInfo(os.getenv("TIME_ZONE", DEFAULT_TIME_ZONE))

    return Settings(
        telegram_token=token,
        database_url=database_url,
        developer_chat_id=developer_chat_id,
        time_zone=tz,
        alert_time=_parse_alert_time(os.getenv("ALERT_TIME", DEFAULT_ALERT_TIME), tz),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
