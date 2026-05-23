import logging
from pathlib import Path


class SafeFileHandler(logging.FileHandler):
    """File handler that self-disables if disk writes fail (e.g. ENOSPC)."""

    def emit(self, record):
        try:
            super().emit(record)
        except OSError:
            self.acquire()
            try:
                self.close()
            finally:
                self.release()


def setup_runtime_logger(log_dir: Path, level: str = "INFO") -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("assistant_runtime")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = SafeFileHandler(log_dir / "runtime.log", encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    logger.addHandler(stream_handler)

    return logger
