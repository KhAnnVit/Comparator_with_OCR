import sys
from src.utils.logger import logger  # Подключаем наш умный логгер
from src.gui.main_window import App  # Подключаем интерфейс


def main():
    logger.info("=== ЗАПУСК ПРИЛОЖЕНИЯ PDF & EXCEL ===")

    try:
        # Инициализируем и запускаем главное окно
        app = App()
        logger.info("Интерфейс успешно загружен. Ожидание действий пользователя.")
        app.mainloop()

    except Exception as e:
        # Если программа упадет (например, не найдет библиотеки),
        # ошибка запишется в файл app.log, а не исчезнет бесследно.
        logger.critical("Критическая ошибка во время работы интерфейса:", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("=== ПРИЛОЖЕНИЕ ЗАКРЫТО ===")


if __name__ == "__main__":
    main()