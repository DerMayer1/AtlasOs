import json
import logging
import sys
import time
from typing import Any

from app.config import settings


class JSONFormatter(logging.Formatter):
    """
    Structured JSON log formatter for production.
    Each line is a valid JSON object — compatible with Datadog, Logtail, Railway logs.
    """
    def format(self, record: logging.LogRecord) -> str:
        log: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)
        return json.dumps(log, ensure_ascii=False)


def configure_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    is_production = settings.log_level.lower() != "debug"

    handler = logging.StreamHandler(sys.stdout)

    if is_production:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        ))

    logging.basicConfig(level=level, handlers=[handler], force=True)

    # Silence noisy third-party loggers
    for noisy in ["httpx", "openai", "hpack", "httpcore", "uvicorn.access"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)
