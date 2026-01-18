import logging
from logging.handlers import TimedRotatingFileHandler
import os

# Папка для хранения логов
LOG_DIR = os.path.join(os.path.dirname(__file__), "../logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "project.log")


def setup_logger(name: str = "aibot") -> logging.Logger:
    """
    Настраивает централизованный логгер для проекта.

    Логи пишутся и в файл, и в консоль.
    Файлы логов меняются каждый день, сохраняются последние 7 дней.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)  # Можно менять на DEBUG для разработки

    if not logger.handlers:
        # --- Файл логов с ротацией по дням ---
        file_handler = TimedRotatingFileHandler(
            filename=LOG_FILE,
            when="midnight",  # ротация каждый день
            interval=1,
            backupCount=7,  # хранить последние 7 файлов
            encoding="utf-8"
        )
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(module)s:%(lineno)d | %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.INFO)

        # --- Лог в консоль ---
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)

        # Добавляем обработчики
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


# Глобальный логгер для проекта
logger = setup_logger()
