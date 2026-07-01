from pathlib import Path
from typing import Any

from src.app_state import AppState
from src.utils.logger import logger


class AppController:
    """
    Центральный контроллер приложения.

    Его задача:
    - управлять переходами между разделами;
    - сохранять данные в AppState;
    - передавать данные между GUI-разделами.

    GUI-разделы не должны напрямую обращаться друг к другу.
    """

    TAB_PDF = "tab1"
    TAB_OCR = "tab2"
    TAB_COMPARE = "tab3"
    TAB_EXCEL = "tab4"

    def __init__(self, app, state: AppState):
        """
        app — главное окно приложения, объект App из main_window.py.
        state — общий объект состояния приложения.
        """
        self.app = app
        self.state = state

    # =========================================================
    # ВНУТРЕННИЕ МЕТОДЫ
    # =========================================================

    def _get_frame(self, tab_name: str):
        """
        Безопасно получает фрейм по имени вкладки.

        Возвращает:
            frame — если вкладка существует;
            None  — если вкладка не найдена.
        """

        frame = self.app.frames.get(tab_name)

        if frame is None:
            logger.warning("Frame не найден: %s", tab_name)

        return frame

    def _call_frame_method(self, tab_name: str, method_name: str, *args, **kwargs) -> bool:
        """
        Безопасно вызывает метод у нужного GUI-фрейма.

        Например:
            self._call_frame_method("tab3", "set_text_left", text)

        Возвращает:
            True  — если метод найден и вызван;
            False — если frame или метод не найдены.
        """

        frame = self._get_frame(tab_name)

        if frame is None:
            return False

        method = getattr(frame, method_name, None)

        if method is None or not callable(method):
            logger.warning(
                "Frame %s не имеет метода %s",
                tab_name,
                method_name
            )
            return False

        method(*args, **kwargs)
        return True

    # =========================================================
    # НАВИГАЦИЯ
    # =========================================================

    def go_to_tab(self, tab_name: str):
        """
        Переключает приложение на нужный раздел.

        tab_name:
            "tab1" — PDF
            "tab2" — OCR
            "tab3" — Сравнение
            "tab4" — Excel
        """

        if self._get_frame(tab_name) is None:
            logger.warning("Попытка перейти на неизвестную вкладку: %s", tab_name)
            return

        self.state.current_tab = tab_name
        self.app.select_frame(tab_name)

        logger.info("Переход на вкладку: %s", tab_name)

    # =========================================================
    # PDF
    # =========================================================

    def set_current_pdf(self, pdf_path: str | Path):
        """
        Сохраняет путь к текущему PDF-файлу.
        """

        self.state.current_pdf_path = Path(pdf_path)
        self.state.current_pdf_page = 0

        logger.info("Текущий PDF сохранён в состоянии: %s", pdf_path)

    def set_current_pdf_page(self, page_number: int):
        """
        Сохраняет номер текущей страницы PDF.

        page_number хранится в формате 0-based:
            0 — первая страница.
        """

        self.state.current_pdf_page = page_number

        logger.info(
            "Текущая страница PDF сохранена в состоянии: %s",
            page_number
        )

    # =========================================================
    # OCR
    # =========================================================

    def show_ocr_result(self, image: Any, text: str, source: str = "pdf_selection"):
        """
        Получает результат OCR и передаёт его в OCR-раздел.

        image — вырезанная картинка, обычно PIL.Image.
        text — распознанный текст.
        source — источник текста.
        """

        self.state.selected_image = image
        self.state.ocr_text = text
        self.state.ocr_source = source

        logger.info(
            "OCR-результат сохранён. Источник: %s, длина текста: %s",
            source,
            len(text)
        )

        updated = self._call_frame_method(
            self.TAB_OCR,
            "update_content",
            image,
            text
        )

        if updated:
            self.go_to_tab(self.TAB_OCR)

    # =========================================================
    # COMPARE
    # =========================================================

    def send_text_to_compare(
            self,
            text: str,
            field_num: int,
            source: str = "unknown",
            append: bool = False
    ):
        """
        Отправляет текст в одно из полей сравнения.

        field_num:
            1 — левое поле
            2 — правое поле

        append:
            False — заменить содержимое поля
            True  — добавить текст в конец поля
        """

        if field_num not in (1, 2):
            logger.warning("Некорректный номер поля сравнения: %s", field_num)
            return

        text = text or ""

        if field_num == 1:
            old_text = self.state.compare_text_1
            final_text = self._build_compare_text(
                old_text=old_text,
                new_text=text,
                append=append
            )

            self.state.compare_text_1 = final_text
            self.state.compare_text_1_source = source
            method_name = "set_text_left"

        else:
            old_text = self.state.compare_text_2
            final_text = self._build_compare_text(
                old_text=old_text,
                new_text=text,
                append=append
            )

            self.state.compare_text_2 = final_text
            self.state.compare_text_2_source = source
            method_name = "set_text_right"

        updated = self._call_frame_method(
            self.TAB_COMPARE,
            method_name,
            final_text
        )

        logger.info(
            (
                "Текст отправлен в поле сравнения %s. "
                "Источник: %s, длина добавленного текста: %s, append=%s"
            ),
            field_num,
            source,
            len(text),
            append
        )

        if updated:
            self.go_to_tab(self.TAB_COMPARE)

    def _build_compare_text(
            self,
            old_text: str,
            new_text: str,
            append: bool = False
    ) -> str:
        """
        Собирает итоговый текст для поля сравнения.

        Если append=False — заменяем поле.
        Если append=True — добавляем новый текст в конец.
        """

        old_text = old_text or ""
        new_text = new_text or ""

        if not append:
            return new_text

        if not old_text.strip():
            return new_text

        if not new_text.strip():
            return old_text

        return old_text.rstrip() + "\n\n" + new_text.strip()

    def clear_compare(self):
        """
        Очищает оба поля сравнения:
        - в состоянии;
        - в интерфейсе.
        """

        self.state.reset_compare()

        self._call_frame_method(
            self.TAB_COMPARE,
            "set_text_left",
            ""
        )

        self._call_frame_method(
            self.TAB_COMPARE,
            "set_text_right",
            ""
        )

        logger.info("Поля сравнения очищены")

    # =========================================================
    # EXCEL
    # =========================================================

    def set_current_excel(self, excel_path: str | Path):
        """
        Сохраняет путь к текущему Excel-файлу.
        """

        self.state.current_excel_path = Path(excel_path)

        logger.info("Текущий Excel сохранён в состоянии: %s", excel_path)

    def set_current_excel_sheet(self, sheet_name: str):
        """
        Сохраняет название текущего выбранного листа Excel.
        """

        self.state.current_excel_sheet = sheet_name

        logger.info(
            "Текущий лист Excel сохранён в состоянии: %s",
            sheet_name
        )

    def set_current_excel_cell(self, row: int, col: int, value: str):
        """
        Сохраняет информацию о текущей выбранной ячейке Excel.
        """

        self.state.current_excel_row = row
        self.state.current_excel_col = col
        self.state.current_excel_cell_value = value

        logger.info(
            "Выбрана Excel-ячейка: row=%s, col=%s, value_length=%s",
            row,
            col,
            len(value)
        )

    def send_excel_cell_to_compare(self, value: str, field_num: int):
        """
        Отправляет значение Excel-ячейки в поле сравнения.
        """

        self.send_text_to_compare(
            text=value,
            field_num=field_num,
            source="excel"
        )

    # =========================================================
    # STATUS
    # =========================================================

    def set_status(self, message: str):
        """
        Сохраняет статусное сообщение.
        """

        self.state.set_status(message)
        logger.info("STATUS: %s", message)