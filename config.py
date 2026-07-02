import os
import sys
from pathlib import Path

# 1. Определяем базовую директорию для ВНУТРЕННИХ ресурсов (внутри .exe или проекта)
if hasattr(sys, '_MEIPASS'):
    # Путь к временной папке, куда PyInstaller распакует poppler и tesseract при запуске
    BASE_DIR = Path(sys._MEIPASS)
else:
    # Путь к корню проекта при разработке.
    # config.py лежит в корне проекта.
    BASE_DIR = Path(__file__).resolve().parent

# 2. Определяем базовую директорию для ВНЕШНИХ пользовательских данных
if hasattr(sys, '_MEIPASS'):
    # В продакшене — это папка, в которой лежит сам запущенный файл .exe
    USER_DIR = Path(sys.executable).parent
else:
    # При разработке — это корень вашего проекта
    USER_DIR = BASE_DIR

# --- ПУТИ К ДАННЫМ (будут созданы рядом с .exe или в корне проекта) ---
DATA_DIR = USER_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Автоматически создаем папки для пользователя, если их нет
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- НАСТРОЙКИ СИСТЕМНЫХ УТИЛИТ ---
# Для exe эти папки должны быть добавлены в сборку PyInstaller:
# - poppler
# - Tesseract-OCR
if hasattr(sys, '_MEIPASS'):
    POPPLER_PATH = BASE_DIR / "poppler" / "bin"
    TESSERACT_EXE = BASE_DIR / "Tesseract-OCR" / "tesseract.exe"
    TESSDATA_PREFIX = BASE_DIR / "Tesseract-OCR" / "tessdata"
else:
    # Пути к пакам на вашем ПК при разработке
    POPPLER_PATH = Path(r"C:\poppler\poppler-26.02.0\Library\bin")
    TESSERACT_EXE = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    TESSDATA_PREFIX = Path(r"C:\Program Files\Tesseract-OCR\tessdata")

# ВАЖНО: Принудительно регистрируем путь к языковым пакетам в системе.
# Преобразование в str() гарантирует отсутствие внешних кавычек, которые ломают Windows.
os.environ['TESSDATA_PREFIX'] = str(TESSDATA_PREFIX)

# Настройки для распознавания текста (OCR)
OCR_LANGUAGES = "rus+eng"  # Распознаем русский и английский одновременно