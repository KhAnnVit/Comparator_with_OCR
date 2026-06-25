import logging
import sys
from logging.handlers import RotatingFileHandler
from config import DATA_DIR  # Импортируем путь к папке data из конфига

def setup_logger():
    """ Настройка сквозного логирования с автоматической ротацией (самоочисткой) """
    logger = logging.getLogger("AppLogger")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(module)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # Путь к файлу логов внутри папки data (например, data/app.log)
    log_file_path = DATA_DIR / "app.log"

    # --- УМНЫЙ ХЕНДЛЕР С САМООЧИСТКОЙ ---
    # maxBytes=5*1024*1024 — это ровно 5 Мегабайт
    # backupCount=3 — хранить максимум 3 архивных файла (старые удаляются сами)
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Хендлер для вывода в консоль (оставляем без изменений)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

logger = setup_logger()