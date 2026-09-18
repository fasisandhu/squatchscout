import json
import logging
import sys
from datetime import UTC, datetime

_STD = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        payload.update(
            {k: v for k, v in record.__dict__.items() if k not in _STD and not k.startswith("_")}
        )
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel("WARNING")
    # Uvicorn installs its own plain-text handlers directly on these three loggers with
    # propagate=False (see uvicorn.config.LOGGING_CONFIG), so left alone they bypass our root
    # JSON handler entirely. Strip their handlers and let records propagate up to root instead —
    # uvicorn.access stays at INFO on purpose (request logging is a §13 deliverable), not WARNING.
    for uv in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(uv)
        uv_logger.handlers.clear()
        uv_logger.propagate = True
        uv_logger.setLevel("INFO")
