import re

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

    Логика под реальные задачи приложения:

    - пользователь выделяет большой блок мелкого текста;
    - текст может быть цветным;
    - фон может быть цветным;
    - исходник для OCR уже качественный;
    - спецсимволы важны: °, №, %, точки, запятые, ●, скобки;
    - предобработка должна не портить оригинал.
    """

    DEFAULT_PSM = 6

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
        Распознаёт текст из PIL.Image.

        pil_image должен быть crop из качественного оригинала,
        а не из облегчённой картинки для просмотра.
        """

        if settings is None:
            settings = OCRSettings(
                languages=OCR_LANGUAGES
            )

        languages = settings.languages or OCR_LANGUAGES
        psm = settings.psm if settings.psm is not None else self.DEFAULT_PSM

        try:
            if pil_image is None:
                return OCRResult(
                    success=False,
                    error_message="Изображение не передано в OCR.",
                    mode="unified",
                    languages=languages,
                    psm=psm
                )

            original_size = pil_image.size

            pil_rgb = pil_image.convert("RGB")
            img_rgb = np.array(pil_rgb)

            processed_img = self._preprocess_packaging_text(img_rgb)

            processed_size = (
                processed_img.shape[1],
                processed_img.shape[0]
            )

            tesseract_config = self._build_tesseract_config(psm=psm)

            logger.info(
                (
                    "OCR запущен. mode=unified, psm=%s, languages=%s, "
                    "original_size=%s, processed_size=%s, config=%s"
                ),
                psm,
                languages,
                original_size,
                processed_size,
                tesseract_config
            )

            text = pytesseract.image_to_string(
                processed_img,
                lang=languages,
                config=tesseract_config
            )

            text = self._postprocess_text(text)

            logger.info(
                "OCR завершён. mode=unified, длина текста=%s",
                len(text)
            )

            return OCRResult(
                success=True,
                text=text,
                mode="unified",
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
                mode="unified",
                languages=languages,
                psm=psm,
                original_size=getattr(pil_image, "size", None)
            )

    # =========================================================
    # НАСТРОЙКИ TESSERACT
    # =========================================================

    def _build_tesseract_config(self, psm: int) -> str:
        """
        Настройки Tesseract для большого блока мелкого текста.

        --psm 6:
            считаем, что выделенная область содержит один блок текста.

        --oem 1:
            используем LSTM OCR engine.

        --dpi 300:
            явно говорим Tesseract, что изображение достаточно качественное.
        """

        return (
            f"--oem 1 "
            f"--psm {psm} "
            f"--dpi 300 "
            f"-c user_defined_dpi=300 "
            f"-c preserve_interword_spaces=1"
        )

    # =========================================================
    # ПРЕДОБРАБОТКА
    # =========================================================

    def _preprocess_packaging_text(self, img_rgb: np.ndarray) -> np.ndarray:
        """
        Минимальная предобработка.

        Важно:
        - не переводим в ч/б;
        - не выбираем отдельный цветовой канал;
        - не делаем бинаризацию;
        - не удаляем фон;
        - не портим мелкие детали.

        Только:
        - при необходимости увеличиваем crop;
        - добавляем белую рамку вокруг текста.
        """

        if img_rgb is None:
            raise ValueError("Изображение не передано в предобработку.")

        if len(img_rgb.shape) == 2:
            img_rgb = cv2.cvtColor(img_rgb, cv2.COLOR_GRAY2RGB)

        img_rgb = img_rgb.astype(np.uint8)

        resized = self._resize_rgb_for_ocr(img_rgb)
        prepared = self._add_white_border_rgb(resized)

        logger.info(
            "OCR preprocessing done. input_size=%s, output_size=%s",
            img_rgb.shape[:2][::-1],
            prepared.shape[:2][::-1]
        )

        return prepared

    def _resize_rgb_for_ocr(self, img_rgb: np.ndarray) -> np.ndarray:
        """
        Увеличивает изображение для OCR.

        Исходник не уменьшаем никогда.
        Для мелких цифр и спецсимволов лучше дать Tesseract
        более крупное изображение.
        """

        height, width = img_rgb.shape[:2]

        if width < 1800 or height < 350:
            scale = 4
        elif height < 1000:
            scale = 3
        else:
            scale = 2

        logger.info(
            "OCR RGB resize. original=%sx%s, scale=%s",
            width,
            height,
            scale
        )

        return cv2.resize(
            img_rgb,
            (width * scale, height * scale),
            interpolation=cv2.INTER_LANCZOS4
        )

    def _add_white_border_rgb(self, img_rgb: np.ndarray) -> np.ndarray:
        """
        Добавляет белую рамку вокруг crop.

        Это помогает, если пользователь выделил область слишком близко к тексту.
        """

        return cv2.copyMakeBorder(
            img_rgb,
            40,
            40,
            40,
            40,
            cv2.BORDER_CONSTANT,
            value=(255, 255, 255)
        )

    # =========================================================
    # ПОСТОБРАБОТКА ТЕКСТА
    # =========================================================

    def _postprocess_text(self, text: str) -> str:
        """
        Аккуратная постобработка OCR-результата.

        Не переписываем смысл.
        Только нормализуем технические символы.
        """

        if not text:
            return ""

        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        text = self._normalize_special_symbols(text)
        text = self._normalize_digit_confusions_in_numeric_context(text)
        text = self._normalize_numeric_separators(text)
        text = self._normalize_temperature_text(text)
        text = self._normalize_number_sign(text)
        text = self._cleanup_spaces(text)

        return text.strip()

    def _normalize_special_symbols(self, text: str) -> str:
        """
        Нормализует похожие спецсимволы.
        """

        replacements = {
            "˚": "°",
            "º": "°",
            "℃": "°C",
            "℉": "°F",

            "−": "-",
            "–": "-",
            "—": "-",

            # Буллеты и похожие маркеры.
            "•": "●",
            "·": "●",
            "∙": "●",
            "○": "●",
            "▪": "●",
            "■": "●",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

    def _normalize_digit_confusions_in_numeric_context(self, text: str) -> str:
        """
        Исправляет похожие на цифры буквы только рядом с цифрами
        или числовыми разделителями.

        Это нужно для дат, процентов, телефонов, температур,
        веса, объёма и диапазонов.

        Не исправляем такие символы во всех словах подряд,
        чтобы не портить обычный текст.
        """

        replacements = {
            "O": "0",
            "o": "0",
            "О": "0",
            "о": "0",

            "I": "1",
            "l": "1",
            "|": "1",

            "З": "3",
            "з": "3",

            "S": "5",
            "s": "5",

            "Б": "6",
            "б": "6",
        }

        numeric_context_chars = set(
            "0123456789"
            ".,:;/%+-"
            "()[]{}"
        )

        chars = list(text)

        for index, char in enumerate(chars):
            if char not in replacements:
                continue

            left_char = self._get_nearest_non_space_char(
                chars=chars,
                start_index=index,
                direction=-1
            )

            right_char = self._get_nearest_non_space_char(
                chars=chars,
                start_index=index,
                direction=1
            )

            left_is_numeric_context = (
                    left_char is not None
                    and (
                            left_char.isdigit()
                            or left_char in numeric_context_chars
                    )
            )

            right_is_numeric_context = (
                    right_char is not None
                    and (
                            right_char.isdigit()
                            or right_char in numeric_context_chars
                    )
            )

            if left_is_numeric_context or right_is_numeric_context:
                chars[index] = replacements[char]

        fixed_text = "".join(chars)

        # Частный, но важный случай:
        # Tesseract часто распознаёт "3 кг" как "З кг".
        fixed_text = re.sub(
            r"\b[Зз]\s*(?=(кг|г|мг|л|мл|шт|%)\b)",
            "3 ",
            fixed_text,
            flags=re.IGNORECASE
        )

        return fixed_text

    def _get_nearest_non_space_char(
            self,
            chars: list[str],
            start_index: int,
            direction: int
    ) -> str | None:
        """
        Ищет ближайший непробельный символ слева или справа.
        """

        index = start_index + direction

        while 0 <= index < len(chars):
            if not chars[index].isspace():
                return chars[index]

            index += direction

        return None

    def _normalize_numeric_separators(self, text: str) -> str:
        """
        Убирает лишние пробелы вокруг точек и запятых между цифрами.

        Например:
            24 . 06 . 2026 -> 24.06.2026
            1 , 5 -> 1,5
        """

        return re.sub(
            r"(\d)\s*([.,])\s*(\d)",
            r"\1\2\3",
            text
        )

    def _normalize_temperature_text(self, text: str) -> str:
        """
        Исправляет частую потерю знака градуса.

        Например:
            30 C
            30 С
            30 oC
            30 0C

        превращаем в:
            30°C
        """

        return re.sub(
            r"(\d+(?:[.,]\d+)?)\s*(?:°|o|O|о|О|0)?\s*([cCсС])\b",
            r"\1°C",
            text
        )

    def _normalize_number_sign(self, text: str) -> str:
        """
        Нормализует знак номера.
        """

        text = re.sub(
            r"\bN\s*[°º]\s*",
            "№ ",
            text
        )

        text = re.sub(
            r"№\s*",
            "№ ",
            text
        )

        return text

    def _cleanup_spaces(self, text: str) -> str:
        """
        Чистит лишние пробелы, не ломая переносы строк.
        """

        lines = []

        for line in text.split("\n"):
            line = re.sub(r"[ \t]{2,}", " ", line)
            lines.append(line.rstrip())

        text = "\n".join(lines)

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        return text

    # =========================================================
    # СОВМЕСТИМОСТЬ СО СТАРЫМ preprocess_image
    # =========================================================

    def preprocess_numpy_image(
        self,
        image: np.ndarray,
        mode: str = "unified"
    ) -> np.ndarray:
        """
        Метод для совместимости со старым preprocess_image(img).

        mode больше не используется.
        """

        if image is None:
            raise ValueError("Изображение не передано.")

        if len(image.shape) == 2:
            img_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            img_rgb = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2RGB)

        return self._preprocess_packaging_text(img_rgb)