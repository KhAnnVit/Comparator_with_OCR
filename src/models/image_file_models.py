from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image


@dataclass
class ImageFileLoadSettings:
    """
    Настройки загрузки изображения.
    """

    max_display_side: int = 1800


@dataclass
class ImageFileLoadResult:
    """
    Результат загрузки изображения.

    display_image — облегчённая версия для просмотра.
    ocr_image — полная версия для OCR.
    """

    success: bool

    file_path: Optional[Path] = None

    display_image: Optional[Image.Image] = None
    ocr_image: Optional[Image.Image] = None

    original_size: tuple[int, int] | None = None
    display_size: tuple[int, int] | None = None

    error_message: str = ""