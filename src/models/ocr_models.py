from dataclasses import dataclass
from typing import Optional


@dataclass
class OCRSettings:
    """
    Настройки OCR.

    В приложении используется один универсальный OCR-сценарий:
    большой блок мелкого текста с возможными спецсимволами
    и цветным текстом/фоном.

    mode оставлен только для обратной совместимости со старым кодом.
    В новой логике он не используется.
    """

    mode: str = "unified"
    languages: str = "rus+eng"
    psm: Optional[int] = None


@dataclass
class OCRResult:
    """
    Результат OCR.
    """

    success: bool
    text: str = ""
    error_message: str = ""

    mode: str = "unified"
    languages: str = "rus+eng"
    psm: int = 6

    original_size: tuple[int, int] | None = None
    processed_size: tuple[int, int] | None = None