from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image


@dataclass
class PDFLoadSettings:
    """
    Настройки загрузки PDF.
    """

    dpi: int = 300
    poppler_path: Optional[Path | str] = None


@dataclass
class PDFLoadResult:
    """
    Результат загрузки PDF.
    """

    success: bool

    pdf_path: Optional[Path] = None
    first_page: Optional[Image.Image] = None
    page_count: int = 0

    error_message: str = ""