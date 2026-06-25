from dataclasses import dataclass
from typing import Optional


@dataclass
class OCRSettings:
    """
    Настройки OCR.

    mode:
        "default"     — обычный режим, похожий на текущий;
        "small_text"  — мелкий текст;
        "block"       — текстовый блок;
        "composition" — состав/ингредиенты;
        "raw"         — без агрессивной предобработки.

    languages:
        языки Tesseract, например "rus+eng".

    psm:
        ручной режим сегментации страницы Tesseract.
        Если None, сервис выберет psm сам по mode.
    """

    mode: str = "default"
    languages: str = "rus+eng"
    psm: Optional[int] = None


@dataclass
class OCRResult:
    """
    Результат OCR.

    Теперь OCR не возвращает ошибку как текст.
    Вместо этого есть:
        success=True/False
        text
        error_message
    """

    success: bool
    text: str = ""
    error_message: str = ""

    mode: str = "default"
    languages: str = "rus+eng"
    psm: int = 11

    original_size: tuple[int, int] | None = None
    processed_size: tuple[int, int] | None = None