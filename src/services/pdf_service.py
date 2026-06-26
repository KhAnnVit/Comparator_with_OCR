from pathlib import Path

from pdf2image import convert_from_path

from src.models.pdf_models import PDFLoadSettings, PDFLoadResult
from src.utils.logger import logger


class PDFService:
    """
    Сервис для загрузки PDF.

    Этот класс не знает ничего про Tkinter, Canvas,
    кнопки, messagebox и GUI.

    Его задача:
    - проверить путь к PDF;
    - сконвертировать PDF в изображения;
    - вернуть первую страницу как PIL.Image.
    """

    def load_first_page(
        self,
        pdf_path: str | Path,
        settings: PDFLoadSettings
    ) -> PDFLoadResult:
        """
        Загружает PDF и возвращает первую страницу.

        Сейчас приложение работает только с первой страницей,
        поэтому наружу отдаём first_page.
        """

        try:
            pdf_path = Path(pdf_path)

            validation_error = self._validate_pdf_path(pdf_path)

            if validation_error:
                return PDFLoadResult(
                    success=False,
                    pdf_path=pdf_path,
                    error_message=validation_error
                )

            poppler_path = self._prepare_poppler_path(settings.poppler_path)

            logger.info(
                "Начата конвертация PDF. path=%s, dpi=%s, poppler_path=%s",
                pdf_path,
                settings.dpi,
                poppler_path
            )

            pages = convert_from_path(
                str(pdf_path),
                dpi=settings.dpi,
                poppler_path=poppler_path
            )

            if not pages:
                return PDFLoadResult(
                    success=False,
                    pdf_path=pdf_path,
                    error_message="Не удалось получить страницы из PDF-файла."
                )

            first_page = pages[0]

            logger.info(
                "PDF сконвертирован. path=%s, pages=%s, first_page_size=%sx%s",
                pdf_path,
                len(pages),
                first_page.width,
                first_page.height
            )

            return PDFLoadResult(
                success=True,
                pdf_path=pdf_path,
                first_page=first_page,
                page_count=len(pages)
            )

        except Exception as error:
            logger.exception("Ошибка при загрузке PDF: %s", pdf_path)

            return PDFLoadResult(
                success=False,
                pdf_path=Path(pdf_path) if pdf_path else None,
                error_message=str(error)
            )

    def _validate_pdf_path(self, pdf_path: Path) -> str:
        """
        Проверяет путь к PDF.
        Возвращает текст ошибки или пустую строку.
        """

        if not pdf_path.exists():
            return "PDF-файл не найден."

        if not pdf_path.is_file():
            return "Выбранный путь не является файлом."

        if pdf_path.suffix.lower() != ".pdf":
            return "Выбранный файл не является PDF."

        return ""

    def _prepare_poppler_path(self, poppler_path):
        """
        Подготавливает путь к Poppler для pdf2image.

        pdf2image ждёт строку или None.
        """

        if poppler_path is None:
            return None

        return str(poppler_path)