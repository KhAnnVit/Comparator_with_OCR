from pathlib import Path

import pandas as pd

from src.models.excel_models import ExcelWorkbookResult, ExcelSheetResult
from src.utils.logger import logger


class ExcelService:
    """
    Сервис для работы с Excel-файлами.

    Этот класс не знает ничего про Tkinter, tksheet,
    кнопки, messagebox и GUI.

    Его задача:
    - проверить Excel-файл;
    - получить список листов;
    - загрузить выбранный лист;
    - подготовить данные для отображения.
    """

    SUPPORTED_EXTENSIONS = {".xlsx", ".xls"}

    def load_workbook_info(self, excel_path: str | Path) -> ExcelWorkbookResult:
        """
        Открывает Excel-книгу и возвращает список листов.
        """

        try:
            excel_path = Path(excel_path)

            validation_error = self._validate_excel_path(excel_path)

            if validation_error:
                return ExcelWorkbookResult(
                    success=False,
                    file_path=excel_path,
                    error_message=validation_error
                )

            excel_file = pd.ExcelFile(excel_path)
            sheet_names = excel_file.sheet_names
            excel_file.close()

            if not sheet_names:
                return ExcelWorkbookResult(
                    success=False,
                    file_path=excel_path,
                    error_message="В Excel-файле не найдено листов."
                )

            logger.info(
                "Excel-книга открыта. path=%s, sheets=%s",
                excel_path,
                sheet_names
            )

            return ExcelWorkbookResult(
                success=True,
                file_path=excel_path,
                sheet_names=sheet_names
            )

        except Exception as error:
            logger.exception("Ошибка при открытии Excel-книги")

            return ExcelWorkbookResult(
                success=False,
                file_path=Path(excel_path) if excel_path else None,
                error_message=str(error)
            )

    def load_sheet(self, excel_path: str | Path, sheet_name: str) -> ExcelSheetResult:
        """
        Загружает конкретный лист Excel.
        """

        try:
            excel_path = Path(excel_path)

            validation_error = self._validate_excel_path(excel_path)

            if validation_error:
                return ExcelSheetResult(
                    success=False,
                    file_path=excel_path,
                    sheet_name=sheet_name,
                    error_message=validation_error
                )

            if not sheet_name:
                return ExcelSheetResult(
                    success=False,
                    file_path=excel_path,
                    sheet_name=sheet_name,
                    error_message="Не выбран лист Excel."
                )

            df = pd.read_excel(
                excel_path,
                sheet_name=sheet_name
            )

            data = self.dataframe_to_sheet_data(df)
            headers = [str(column) for column in df.columns]

            logger.info(
                "Excel-лист загружен. path=%s, sheet=%s, rows=%s, columns=%s",
                excel_path,
                sheet_name,
                len(df),
                len(df.columns)
            )

            return ExcelSheetResult(
                success=True,
                file_path=excel_path,
                sheet_name=sheet_name,
                dataframe=df,
                data=data,
                headers=headers,
                row_count=len(df),
                column_count=len(df.columns),
                is_empty=df.empty
            )

        except Exception as error:
            logger.exception(
                "Ошибка при загрузке Excel-листа. path=%s, sheet=%s",
                excel_path,
                sheet_name
            )

            return ExcelSheetResult(
                success=False,
                file_path=Path(excel_path) if excel_path else None,
                sheet_name=sheet_name,
                error_message=str(error)
            )

    def dataframe_to_sheet_data(self, df) -> list[list[str]]:
        """
        Преобразует DataFrame в данные для tksheet.

        NaN заменяем на пустые строки.
        Остальные значения приводим к str.
        """

        if df is None or df.empty:
            return []

        data = df.values.tolist()

        for row in data:
            for index, value in enumerate(row):
                if pd.isna(value):
                    row[index] = ""
                else:
                    row[index] = str(value)

        return data

    def _validate_excel_path(self, excel_path: Path) -> str:
        """
        Проверяет путь к Excel-файлу.
        Возвращает текст ошибки или пустую строку.
        """

        if not excel_path.exists():
            return "Excel-файл не найден."

        if not excel_path.is_file():
            return "Выбранный путь не является файлом."

        if excel_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return "Выбранный файл не является Excel-файлом."

        return ""