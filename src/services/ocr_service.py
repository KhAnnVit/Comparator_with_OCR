import cv2
import numpy as np
import pytesseract
from PIL import Image

from config import TESSERACT_EXE, OCR_LANGUAGES
from src.models.ocr_models import OCRSettings, OCRResult
from src.utils.logger import logger


class OCRService:
    """
    Сервис распознавания текста.

    Этот класс не зависит от CustomTkinter.
    Он отвечает только за:
    - подготовку изображения;
    - выбор режима OCR;
    - запуск Tesseract;
    - возврат нормального OCRResult.
    """

    MODE_CONFIGS = {
        # Почти как текущий режим:
        # хорошо подходит для разрозненных кусочков текста.
        "default": {
            "psm": 11,
            "preprocess": "otsu_2x"
        },

        # Для мелкого текста на упаковках.
        "small_text": {
            "psm": 6,
            "preprocess": "adaptive_3x"
        },

        # Для цельного прямоугольного блока текста.
        "block": {
            "psm": 6,
            "preprocess": "otsu_2x"
        },

        # Для составов/ингредиентов.
        # Обычно состав идёт как несколько строк или один плотный блок.
        "composition": {
            "psm": 6,
            "preprocess": "adaptive_3x"
        },

        # Без агрессивной предобработки.
        # Иногда Tesseract сам лучше справляется с исходным изображением.
        "raw": {
            "psm": 11,
            "preprocess": "raw"
        },
    }

    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_EXE)

    # =========================================================
    # ПУБЛИЧНЫЙ МЕТОД
    # =========================================================

    def recognize_from_pil(
        self,
        pil_image: Image.Image,
        settings: OCRSettings | None = None
    ) -> OCRResult:
        """
        Распознаёт текст из PIL.Image и возвращает OCRResult.
        """

        if settings is None:
            settings = OCRSettings(
                mode="default",
                languages=OCR_LANGUAGES
            )

        mode = settings.mode

        if mode not in self.MODE_CONFIGS:
            logger.warning("Неизвестный OCR-режим '%s'. Используется default.", mode)
            mode = "default"

        mode_config = self.MODE_CONFIGS[mode]

        psm = settings.psm if settings.psm is not None else mode_config["psm"]
        languages = settings.languages or OCR_LANGUAGES

        try:
            if pil_image is None:
                return OCRResult(
                    success=False,
                    error_message="Изображение не передано в OCR.",
                    mode=mode,
                    languages=languages,
                    psm=psm
                )

            original_size = pil_image.size

            # Приводим изображение к RGB.
            pil_rgb = pil_image.convert("RGB")
            img_rgb = np.array(pil_rgb)

            processed_img = self._preprocess_rgb_image(
                img_rgb=img_rgb,
                preprocess_mode=mode_config["preprocess"]
            )

            processed_size = (
                processed_img.shape[1],
                processed_img.shape[0]
            )

            logger.info(
                "OCR запущен. mode=%s, psm=%s, languages=%s, original_size=%s, processed_size=%s",
                mode,
                psm,
                languages,
                original_size,
                processed_size
            )

            text = pytesseract.image_to_string(
                processed_img,
                lang=languages,
                config=f"--psm {psm}"
            )

            text = text.strip()

            logger.info(
                "OCR завершён. mode=%s, длина текста=%s",
                mode,
                len(text)
            )

            return OCRResult(
                success=True,
                text=text,
                mode=mode,
                languages=languages,
                psm=psm,
                original_size=original_size,
                processed_size=processed_size
            )

        except Exception as error:
            logger.exception("Ошибка OCR")

            return OCRResult(
                success=False,
                text="",
                error_message=str(error),
                mode=mode,
                languages=languages,
                psm=psm,
                original_size=getattr(pil_image, "size", None)
            )

    # =========================================================
    # ПРЕДОБРАБОТКА
    # =========================================================

    def _preprocess_rgb_image(
        self,
        img_rgb: np.ndarray,
        preprocess_mode: str
    ) -> np.ndarray:
        """
        Выбирает способ предобработки изображения.
        """

        if preprocess_mode == "raw":
            return img_rgb

        if preprocess_mode == "otsu_2x":
            return self._preprocess_otsu_2x(img_rgb)

        if preprocess_mode == "adaptive_3x":
            return self._preprocess_adaptive_3x(img_rgb)

        logger.warning(
            "Неизвестный режим предобработки '%s'. Используется otsu_2x.",
            preprocess_mode
        )
        return self._preprocess_otsu_2x(img_rgb)

    def _preprocess_otsu_2x(self, img_rgb: np.ndarray) -> np.ndarray:
        """
        Предобработка, похожая на старую:
        - grayscale;
        - увеличение x2;
        - бинаризация Оцу.
        """

        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

        height, width = gray.shape[:2]

        scaled = cv2.resize(
            gray,
            (width * 2, height * 2),
            interpolation=cv2.INTER_CUBIC
        )

        _, binarized = cv2.threshold(
            scaled,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        return binarized

    def _preprocess_adaptive_3x(self, img_rgb: np.ndarray) -> np.ndarray:
        """
        Режим для мелкого текста и упаковок:
        - grayscale;
        - увеличение x3;
        - лёгкое размытие;
        - адаптивная бинаризация.

        Часто лучше работает, когда фон неравномерный.
        """

        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

        height, width = gray.shape[:2]

        scaled = cv2.resize(
            gray,
            (width * 3, height * 3),
            interpolation=cv2.INTER_CUBIC
        )

        blurred = cv2.GaussianBlur(scaled, (3, 3), 0)

        processed = cv2.adaptiveThreshold(
            blurred,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11
        )

        return processed

    # =========================================================
    # СОВМЕСТИМОСТЬ СО СТАРЫМ preprocess_image
    # =========================================================

    def preprocess_numpy_image(
        self,
        image: np.ndarray,
        mode: str = "default"
    ) -> np.ndarray:
        """
        Метод для совместимости со старым preprocess_image(img).

        Старый код передавал изображение OpenCV-формата BGR.
        """

        if image is None:
            raise ValueError("Изображение не передано.")

        if len(image.shape) == 2:
            img_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            img_rgb = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2RGB)

        if mode not in self.MODE_CONFIGS:
            mode = "default"

        preprocess_mode = self.MODE_CONFIGS[mode]["preprocess"]

        return self._preprocess_rgb_image(
            img_rgb=img_rgb,
            preprocess_mode=preprocess_mode
        )