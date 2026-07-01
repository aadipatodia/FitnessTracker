import logging
from pathlib import Path

LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger("fitai")


def _build_formatter() -> logging.Formatter:
    return logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)


def configure_logger(name: str, log_filename: str) -> logging.Logger:
    """Attach file + console handlers to a named logger (idempotent)."""
    log = logging.getLogger(name)
    if log.handlers:
        return log

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    formatter = _build_formatter()

    file_handler = logging.FileHandler(log_dir / log_filename)
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    log.addHandler(console_handler)

    log.setLevel(logging.INFO)
    log.propagate = False
    return log


def setup_app_logging() -> None:
    configure_logger("fitai", "app.log")
    logging.getLogger("uvicorn.access").disabled = True


def get_logger(name: str = "fitai") -> logging.Logger:
    return logging.getLogger(name)
