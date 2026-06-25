# ocr_engine.py

import cv2
import numpy as np
import pytesseract
from config import TESSERACT_EXE, OCR_LANGUAGES


def preprocess_image(img):
    """
    Продвинутая предобработка изображения для улучшения качества OCR.
    """
    # 1. Конвертируем изображение в оттенки серого
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. Масштабирование (кубическое увеличение)
    height, width = gray.shape[:2]
    scaled = cv2.resize(gray, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)

    # 3. Бинаризация Оцу
    _, binarized = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return binarized


def extract_text_from_pil(pil_image):
    """
    Распознает текст напрямую из PIL.Image без сохранения на диск.
    Использует настройки из config.py.
    """
    try:
        # Указываем путь к исполняемому файлу Tesseract из конфига
        pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_EXE)

        # Конвертируем PIL.Image в numpy array
        img_array = np.array(pil_image)

        # Если изображение в RGBA или RGB, конвертируем в BGR для OpenCV
        if len(img_array.shape) == 3 and img_array.shape[2] >= 3:
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = img_array

        # Запускаем предобработку
        processed_img = preprocess_image(img_bgr)

        # Формируем конфиг: используем языки из конфига
        custom_config = rf'--psm 11 -l {OCR_LANGUAGES}'

        # Распознаем текст
        text = pytesseract.image_to_string(processed_img, config=custom_config)

        return text.strip()

    except Exception as e:
        return f"Критическая ошибка OCR движка: {str(e)}"


def extract_text(image_path):
    """
    Основная функция распознавания. Принимает путь к изображению.
    (Оставлена для обратной совместимости, если где-то используется)
    """
    clean_path = str(image_path).strip('"\'')

    try:
        pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_EXE)

        # Читаем файл в бинарный массив
        img_array = np.fromfile(clean_path, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img is None:
            return "Ошибка: Не удалось загрузить или открыть файл изображения."

        processed_img = preprocess_image(img)
        custom_config = rf'--psm 11 -l {OCR_LANGUAGES}'

        text = pytesseract.image_to_string(processed_img, config=custom_config)
        return text.strip()

    except Exception as e:
        return f"Критическая ошибка OCR движка: {str(e)}"