from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class ExcelWorkbookResult:
    """
    Результат открытия Excel-книги.

    Нужен, чтобы GUI получил список листов,
    но не занимался pandas-логикой.
    """

    success: bool
    file_path: Optional[Path] = None
    sheet_names: list[str] = field(default_factory=list)
    error_message: str = ""


@dataclass
class ExcelSheetResult:
    """
    Результат загрузки конкретного листа Excel.
    """

    success: bool
    file_path: Optional[Path] = None
    sheet_name: str = ""

    # Сам DataFrame оставляем, потому что окно редактирования
    # сейчас обновляет self.df.iloc[row, col].
    dataframe: Optional[Any] = None

    # Готовые данные для tksheet.
    data: list[list[str]] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)

    row_count: int = 0
    column_count: int = 0
    is_empty: bool = False

    error_message: str = ""