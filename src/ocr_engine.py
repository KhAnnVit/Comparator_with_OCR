from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from config import OCR_LANGUAGES
from src.models.ocr_models import OCRSettings
from src.services.ocr_service import OCRService
from src.utils.logger import logger


_ocr_service = OCRService()


def preprocess_image(img):
    """
    Старый метод предобработки.

    Оставлен для обратной совместимости.
    Новый код лучше писать через OCRService.
    """
    return _ocr_service.preprocess_numpy_image(
        image=img,
        mode="default"
    )


def extract_text_from_pil(pil_image, mode: str = "default"):
    """
    Старый публичный метод OCR.

    Оставлен, чтобы не сломать pdf_window.py.

    Внутри теперь используется OCRService.
    """

    result = _ocr_service.recognize_from_pil(
        pil_image=pil_image,
        settings=OCRSettings(
            mode=mode,
            languages=OCR_LANGUAGES
        )
    )

    if result.success:
        return result.text

    logger.error("OCR завершился ошибкой: %s", result.error_message)

    return f"Ошибка OCR: {result.error_message}"


def extract_text(image_path, mode: str = "default"):
    """
    Распознаёт текст из файла изображения.

    Оставлено для обратной совместимости.
    """

    clean_path = str(image_path).strip('"\'')
    image_path_obj = Path(clean_path)

    try:
        if not image_path_obj.exists():
            return f"Ошибка: файл не найден: {image_path_obj}"

        with Image.open(image_path_obj) as img:
            pil_image = img.copy()

        return extract_text_from_pil(
            pil_image=pil_image,
            mode=mode
        )

    except Exception as error:
        logger.exception("Ошибка при OCR изображения из файла")
        return f"Ошибка OCR: {error}"