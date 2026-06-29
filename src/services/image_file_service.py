from pathlib import Path

from PIL import Image, ImageOps

from src.models.image_file_models import ImageFileLoadSettings, ImageFileLoadResult
from src.utils.logger import logger


class ImageFileService:
    """
    Сервис для загрузки обычных изображений.

    Этот класс не знает ничего про Tkinter, Canvas,
    кнопки, messagebox и GUI.

    Его задача:
    - проверить путь к изображению;
    - открыть картинку;
    - подготовить лёгкую версию для просмотра;
    - сохранить полную версию для OCR.
    """

    SUPPORTED_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".bmp",
        ".tif",
        ".tiff",
        ".jfif",
    }

    def load_image(
        self,
        image_path: str | Path,
        settings: ImageFileLoadSettings
    ) -> ImageFileLoadResult:
        """
        Загружает изображение.

        display_image используется для просмотра.
        ocr_image используется для OCR.
        """

        image_path_obj = None

        try:
            image_path_obj = Path(image_path)

            validation_error = self._validate_image_path(image_path_obj)

            if validation_error:
                return ImageFileLoadResult(
                    success=False,
                    file_path=image_path_obj,
                    error_message=validation_error
                )

            with Image.open(image_path_obj) as image:
                # Учитываем EXIF-поворот у фотографий.
                ocr_image = ImageOps.exif_transpose(image).convert("RGB")

            display_image = ocr_image.copy()
            display_image.thumbnail(
                (settings.max_display_side, settings.max_display_side),
                resample=Image.Resampling.LANCZOS
            )

            logger.info(
                "Изображение загружено. path=%s, original_size=%s, display_size=%s",
                image_path_obj,
                ocr_image.size,
                display_image.size
            )

            return ImageFileLoadResult(
                success=True,
                file_path=image_path_obj,
                display_image=display_image,
                ocr_image=ocr_image,
                original_size=ocr_image.size,
                display_size=display_image.size
            )

        except Exception as error:
            logger.exception("Ошибка при загрузке изображения")

            return ImageFileLoadResult(
                success=False,
                file_path=image_path_obj,
                error_message=str(error)
            )

    def _validate_image_path(self, image_path: Path) -> str:
        """
        Проверяет путь к изображению.
        Возвращает текст ошибки или пустую строку.
        """

        if not image_path.exists():
            return "Файл изображения не найден."

        if not image_path.is_file():
            return "Выбранный путь не является файлом."

        if image_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return "Выбранный файл не является поддерживаемым изображением."

        return ""