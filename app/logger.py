# app/logger.py
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import os
import time


BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "project.log"


class SafeTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    TimedRotatingFileHandler, устойчивый к WinError 32.
    Закрывает файл перед ротацией.
    """

    def doRollover(self):
        if self.stream:
            try:
                self.stream.close()
                self.stream = None
            except Exception:
                pass

        current_time = int(time.time())
        dfn = self.rotation_filename(
            self.baseFilename + "." + time.strftime(self.suffix, time.localtime(current_time))
        )

        if not os.path.exists(dfn):
            try:
                os.rename(self.baseFilename, dfn)
            except PermissionError:
                # если Windows не дал переименовать — просто пропускаем
                return

        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                try:
                    os.remove(s)
                except OSError:
                    pass

        if not self.delay:
            self.stream = self._open()


def setup_logger(name: str = "aibot") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    # --- Файл логов ---
    file_handler = SafeTimedRotatingFileHandler(
        filename=str(LOG_FILE),
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
        delay=True,
        utc=False
    )

    file_handler.suffix = "%Y-%m-%d"

    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(module)s:%(lineno)d | %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)

    # --- Консоль ---
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logger()
