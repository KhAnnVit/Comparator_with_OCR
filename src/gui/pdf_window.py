import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, Menu, messagebox
from pathlib import Path

from PIL import Image, ImageTk

from config import POPPLER_PATH, OCR_LANGUAGES
from src.models.ocr_models import OCRSettings
from src.models.image_crop_models import ImageCropRequest
from src.models.pdf_models import PDFLoadSettings
from src.services.ocr_service import OCRService
from src.services.image_crop_service import ImageCropService
from src.services.pdf_service import PDFService
from src.utils.logger import logger
from src.models.image_file_models import ImageFileLoadSettings
from src.services.image_file_service import ImageFileService


class PDFViewerFrame(ctk.CTkFrame):
    """
    Первый раздел приложения: просмотр PDF и изображений.

    Что умеет:
    - открывать PDF;
    - открывать обычные изображения;
    - держать несколько открытых файлов во вкладках;
    - переключаться между уже открытыми файлами без повторной загрузки;
    - запоминать масштаб, поворот, смещение и страницу для каждой вкладки;
    - показывать страницы с быстрым viewport-rendering;
    - двигать изображение;
    - масштабировать изображение;
    - поворачивать изображение;
    - выделять область;
    - отправлять выделенную область в OCR.
    """

    MIN_ZOOM = 0.05
    MAX_ZOOM = 5.0
    ZOOM_STEP = 1.05

    ZOOM_REDRAW_DELAY_MS = 16
    ZOOM_FINAL_REDRAW_DELAY_MS = 180

    FAST_ZOOM_RESAMPLE = Image.Resampling.BILINEAR
    QUALITY_RESAMPLE = Image.Resampling.LANCZOS

    DISPLAY_PDF_DPI = 150
    OCR_PDF_DPI = 300

    IMAGE_DISPLAY_MAX_SIDE = 3500

    SUPPORTED_PDF_EXTENSIONS = {".pdf"}

    SUPPORTED_IMAGE_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".bmp",
        ".tif",
        ".tiff",
        ".jfif",
    }

    OCR_LANGUAGE_OPTIONS = {
        "Русский": "rus",
        "English": "eng",
        "Қазақ": "kaz",
        "한국어": "kor",
        "Español": "spa",
        "Français": "fra",
        "العربية": "ara",
    }

    MODE_PAN = "Перемещение"
    MODE_SELECT = "Выделение"

    def __init__(self, master):
        super().__init__(master)

        self.ocr_service = OCRService()
        self.image_crop_service = ImageCropService()
        self.pdf_service = PDFService()
        self.image_file_service = ImageFileService()

        self._init_state()
        self._configure_grid()
        self._create_widgets()
        self._bind_events()

    # =========================================================
    # ИНИЦИАЛИЗАЦИЯ
    # =========================================================

    def _init_state(self):
        """
        Создаёт состояние раздела просмотра.
        """

        self.pdf_path = None
        self.current_file_path = None
        self.current_file_type = None  # "pdf" или "image"

        self.current_page_index = 0
        self.page_count = 0

        # original_image — облегчённая версия для просмотра.
        # ocr_source_image — качественная версия для OCR.
        self.original_image = None
        self.ocr_source_image = None

        self.rotated_image = None
        self.current_image = None
        self.tk_image = None

        self.displayed_image_width = 0
        self.displayed_image_height = 0

        self.viewport_x = 0
        self.viewport_y = 0
        self.viewport_source_box = None

        self.zoom_factor = 1.0
        self.angle = 0

        self.zoom_redraw_after_id = None
        self.zoom_final_redraw_after_id = None

        self.offset_x = 0
        self.offset_y = 0

        self.last_mouse_x = 0
        self.last_mouse_y = 0

        self.rect_id = None
        self.start_x = 0
        self.start_y = 0

        self.ocr_language_vars = {}

        # Вкладки открытых файлов.
        self.file_tabs = {}
        self.active_file_tab_id = None
        self.next_file_tab_id = 1

    def _configure_grid(self):
        """
        Настраивает сетку раздела.
        """

        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

    # =========================================================
    # СОЗДАНИЕ ИНТЕРФЕЙСА
    # =========================================================

    def _create_widgets(self):
        """
        Создаёт интерфейс раздела.
        """

        self._create_file_tabs_panel()
        self._create_top_panel()
        self._create_ocr_panel()
        self._create_canvas()
        self._create_status_label()
        self._create_context_menu()

    def _create_file_tabs_panel(self):
        """
        Создаёт панель вкладок открытых файлов.
        """

        self.file_tabs_panel = ctk.CTkScrollableFrame(
            self,
            height=44,
            orientation="horizontal"
        )
        self.file_tabs_panel.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=10,
            pady=(10, 0)
        )

        self._refresh_file_tabs_panel()

    def _create_top_panel(self):
        """Создаёт верхнюю панель управления с горизонтальной прокруткой."""

        self.top_panel = ctk.CTkScrollableFrame(
            self,
            height=54,
            orientation="horizontal"
        )
        self.top_panel.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=10,
            pady=5
        )

        self.btn_load = ctk.CTkButton(
            self.top_panel,
            text="Загрузить файл",
            command=self.load_file,
            width=130
        )
        self.btn_load.pack(side="left", padx=5, pady=5)

        self.btn_prev_page = ctk.CTkButton(
            self.top_panel,
            text="◀",
            command=self.go_to_previous_page,
            width=40,
            state="disabled"
        )
        self.btn_prev_page.pack(side="left", padx=(10, 3), pady=5)

        self.page_label = ctk.CTkLabel(
            self.top_panel,
            text="Стр. - / -",
            width=90
        )
        self.page_label.pack(side="left", padx=3, pady=5)

        self.btn_next_page = ctk.CTkButton(
            self.top_panel,
            text="▶",
            command=self.go_to_next_page,
            width=40,
            state="disabled"
        )
        self.btn_next_page.pack(side="left", padx=(3, 10), pady=5)

        self.btn_rotate = ctk.CTkButton(
            self.top_panel,
            text="Повернуть 90°",
            command=self.rotate_image,
            width=130
        )
        self.btn_rotate.pack(side="left", padx=5, pady=5)

        self.btn_reset = ctk.CTkButton(
            self.top_panel,
            text="Сбросить вид",
            command=self.reset_view,
            width=120
        )
        self.btn_reset.pack(side="left", padx=5, pady=5)

        self.btn_clear_selection = ctk.CTkButton(
            self.top_panel,
            text="Убрать выделение",
            command=self.clear_selection,
            width=140
        )
        self.btn_clear_selection.pack(side="left", padx=5, pady=5)

        self.mode_switch = ctk.CTkSegmentedButton(
            self.top_panel,
            values=[self.MODE_PAN, self.MODE_SELECT],
            width=220
        )
        self.mode_switch.pack(side="left", padx=20, pady=5)
        self.mode_switch.set(self.MODE_SELECT)

    def _create_ocr_panel(self):
        """
        Создаёт панель OCR-настроек с горизонтальной прокруткой.

        Это нужно, чтобы языки OCR не обрезались при уменьшении окна.
        """

        self.ocr_panel = ctk.CTkScrollableFrame(
            self,
            height=54,
            orientation="horizontal"
        )
        self.ocr_panel.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=10,
            pady=(0, 5)
        )

        self.ocr_info_label = ctk.CTkLabel(
            self.ocr_panel,
            text="OCR: мелкий текст упаковки"
        )
        self.ocr_info_label.pack(side="left", padx=(10, 20), pady=5)

        self.ocr_language_label = ctk.CTkLabel(
            self.ocr_panel,
            text="Языки:"
        )
        self.ocr_language_label.pack(side="left", padx=(5, 5), pady=5)

        default_language_codes = self._get_default_ocr_language_codes()

        for language_title, language_code in self.OCR_LANGUAGE_OPTIONS.items():
            variable = tk.BooleanVar(
                value=language_code in default_language_codes
            )

            self.ocr_language_vars[language_code] = variable

            checkbox = ctk.CTkCheckBox(
                self.ocr_panel,
                text=language_title,
                variable=variable,
                onvalue=True,
                offvalue=False,
                width=90
            )
            checkbox.pack(side="left", padx=6, pady=5)

    def _create_canvas(self):
        """
        Создаёт Canvas для отображения файла.
        """

        self.canvas = tk.Canvas(
            self,
            bg="#2b2b2b",
            highlightthickness=0
        )
        self.canvas.grid(
            row=3,
            column=0,
            sticky="nsew",
            padx=10,
            pady=10
        )

    def _create_status_label(self):
        """
        Создаёт нижнюю строку статуса.
        """

        self.status_label = ctk.CTkLabel(
            self,
            text="Загрузите PDF или изображение для начала работы.",
            anchor="w"
        )
        self.status_label.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=10,
            pady=(0, 8)
        )

    def _create_context_menu(self):
        """
        Создаёт контекстное меню для выделенной области.
        """

        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.add_command(
            label="Распознать текст",
            command=self.send_to_ocr
        )

    # =========================================================
    # СОБЫТИЯ
    # =========================================================

    def _bind_events(self):
        """
        Привязывает события Canvas.
        """

        self.canvas.bind("<MouseWheel>", self.zoom_image)

        # Linux-варианты колёсика.
        self.canvas.bind("<Button-4>", self.zoom_image)
        self.canvas.bind("<Button-5>", self.zoom_image)

        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<Button-3>", self.show_context_menu)
        self.canvas.bind("<Configure>", self.on_canvas_resize)

    # =========================================================
    # СТАТУС И СБРОСЫ
    # =========================================================

    def set_status(self, text):
        """
        Обновляет строку статуса.
        """

        self.status_label.configure(text=text)

    def clear_selection(self):
        """
        Удаляет рамку выделения.
        """

        if self.rect_id is not None:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
            self.set_status("Выделение очищено.")

    def reset_view(self):
        """
        Сбрасывает вид:
        - масштаб;
        - поворот;
        - смещение;
        - выделение.
        """

        if self.original_image is None:
            return

        self._reset_view_state(fit_to_page=True)
        self.clear_selection()
        self.update_image()

        self._save_current_file_tab()

        self.set_status("Вид сброшен.")

    def _reset_view_state(self, fit_to_page: bool = False):
        """
        Сбрасывает параметры просмотра.

        fit_to_page=True:
            страница/изображение будет вписано целиком в Canvas.

        fit_to_page=False:
            масштаб будет 100%.
        """

        self.angle = 0
        self.offset_x = 0
        self.offset_y = 0

        if fit_to_page:
            self._fit_page_to_canvas()
        else:
            self.zoom_factor = 1.0

    def _reset_selection_state(self):
        """
        Сбрасывает данные выделения без обращения к Canvas.
        """

        self.rect_id = None
        self.start_x = 0
        self.start_y = 0

    def _fit_page_to_canvas(self):
        """
        Подбирает zoom_factor так, чтобы файл помещался в Canvas.
        """

        if self.original_image is None:
            return

        self.update_idletasks()

        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())

        padding = 20

        available_width = max(1, canvas_width - padding * 2)
        available_height = max(1, canvas_height - padding * 2)

        preview_image = self.original_image.rotate(
            self.angle,
            expand=True
        )

        width_ratio = available_width / preview_image.width
        height_ratio = available_height / preview_image.height

        fit_zoom = min(width_ratio, height_ratio)

        self.zoom_factor = max(
            self.MIN_ZOOM,
            min(fit_zoom, self.MAX_ZOOM)
        )

        logger.info(
            (
                "Файл масштабирован по размеру окна. "
                "zoom=%s, canvas=%sx%s, image=%sx%s"
            ),
            round(self.zoom_factor, 3),
            canvas_width,
            canvas_height,
            preview_image.width,
            preview_image.height
        )

    # =========================================================
    # ЗАГРУЗКА ФАЙЛОВ
    # =========================================================

    def load_file(self):
        """
        Открывает единый диалог выбора файла.

        Дальше логика зависит от расширения:
        - PDF открываем через PDFService;
        - изображения открываем через ImageFileService.
        """

        file_path = filedialog.askopenfilename(
            title="Выберите PDF или изображение",
            filetypes=[
                (
                    "PDF и изображения",
                    "*.pdf *.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.jfif"
                ),
                ("PDF Files", "*.pdf"),
                (
                    "Image Files",
                    "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.jfif"
                ),
                ("All Files", "*.*"),
            ]
        )

        if not file_path:
            return

        existing_tab_id = self._find_file_tab_by_path(file_path)

        if existing_tab_id is not None:
            self._switch_file_tab(existing_tab_id)
            return

        suffix = Path(file_path).suffix.lower()

        if suffix in self.SUPPORTED_PDF_EXTENSIONS:
            self.load_pdf_page(
                file_path=file_path,
                page_index=0,
                is_new_file=True
            )
            return

        if suffix in self.SUPPORTED_IMAGE_EXTENSIONS:
            self.load_image_file(file_path)
            return

        messagebox.showerror(
            "Неподдерживаемый файл",
            (
                "Можно открыть только PDF или изображение.\n\n"
                f"Выбранный файл: {file_path}"
            )
        )

        logger.warning(
            "Пользователь выбрал неподдерживаемый файл: %s",
            file_path
        )

    def load_pdf(self):
        """
        Открывает PDF и загружает первую страницу.

        Метод оставлен для совместимости, если где-то в проекте
        ещё вызывается load_pdf().
        """

        file_path = filedialog.askopenfilename(
            title="Выберите PDF-файл",
            filetypes=[("PDF Files", "*.pdf")]
        )

        if not file_path:
            return

        existing_tab_id = self._find_file_tab_by_path(file_path)

        if existing_tab_id is not None:
            self._switch_file_tab(existing_tab_id)
            return

        self.load_pdf_page(
            file_path=file_path,
            page_index=0,
            is_new_file=True
        )

    def load_image_file(self, file_path):
        """
        Загружает обычное изображение в просмотрщик.
        """

        try:
            self.set_status("Загрузка изображения...")
            self.update_idletasks()

            result = self._load_image_with_service(file_path)

            if not result.success:
                self._handle_image_load_error(result.error_message)
                return

            self._set_loaded_image(
                file_path=result.file_path,
                display_image=result.display_image,
                ocr_image=result.ocr_image
            )

            logger.info(
                (
                    "Изображение загружено в интерфейс. "
                    "path=%s, display_size=%s, original_size=%s"
                ),
                result.file_path,
                result.display_size,
                result.original_size
            )

        except Exception:
            logger.exception("Ошибка при загрузке изображения в интерфейсе")

            messagebox.showerror(
                "Ошибка загрузки изображения",
                "Не удалось загрузить изображение. Подробности в app.log."
            )

            self.set_status("Ошибка загрузки изображения.")

    def _load_image_with_service(self, file_path):
        """
        Загружает изображение через ImageFileService.
        """

        settings = ImageFileLoadSettings(
            max_display_side=self.IMAGE_DISPLAY_MAX_SIDE
        )

        return self.image_file_service.load_image(
            image_path=file_path,
            settings=settings
        )

    def _handle_image_load_error(self, error_message):
        """
        Показывает ошибку загрузки изображения.
        """

        logger.warning("Изображение не загружено: %s", error_message)

        messagebox.showerror(
            "Ошибка загрузки изображения",
            f"Не удалось загрузить изображение.\n\n{error_message}"
        )

        self.set_status("Изображение не загружено.")

    def _set_loaded_image(self, file_path, display_image, ocr_image):
        """
        Сохраняет изображение в состояние просмотрщика
        и обновляет интерфейс.
        """

        self._save_current_file_tab()

        self.active_file_tab_id = self._create_file_tab(
            file_path=file_path,
            file_type="image"
        )

        self.current_file_path = Path(file_path)
        self.current_file_type = "image"

        self.pdf_path = None

        self.original_image = display_image
        self.ocr_source_image = ocr_image

        self.current_page_index = 0
        self.page_count = 1

        self._reset_view_state(fit_to_page=True)
        self._reset_selection_state()

        self.update_image()
        self._update_page_controls()

        self._save_current_file_tab()
        self._refresh_file_tabs_panel()

        self.set_status(f"Изображение загружено: {file_path}")

    def load_pdf_page(self, file_path=None, page_index=None, is_new_file=False):
        """
        Загружает конкретную страницу PDF.

        file_path:
            путь к PDF. Если None — используется текущий self.pdf_path.

        page_index:
            номер страницы 0-based.
        """

        if file_path is None:
            file_path = self.pdf_path

        if file_path is None:
            return

        if page_index is None:
            page_index = self.current_page_index

        try:
            self.set_status("Загрузка страницы PDF...")
            self.update_idletasks()

            display_result = self._load_pdf_page_with_service(
                file_path=file_path,
                page_index=page_index,
                dpi=self.DISPLAY_PDF_DPI
            )

            if not display_result.success:
                self._handle_pdf_load_error(display_result.error_message)
                return

            ocr_result = self._load_pdf_page_with_service(
                file_path=file_path,
                page_index=page_index,
                dpi=self.OCR_PDF_DPI
            )

            if not ocr_result.success:
                logger.warning(
                    (
                        "Не удалось загрузить OCR-версию страницы PDF. "
                        "Используется display-версия. error=%s"
                    ),
                    ocr_result.error_message
                )
                ocr_page_image = display_result.page_image
            else:
                ocr_page_image = ocr_result.page_image

            self._set_loaded_pdf_page(
                file_path=display_result.pdf_path,
                page_image=display_result.page_image,
                ocr_page_image=ocr_page_image,
                page_number=display_result.page_number,
                page_count=display_result.page_count,
                is_new_file=is_new_file
            )

            logger.info(
                (
                    "PDF-страница загружена в интерфейс. "
                    "path=%s, page=%s/%s, display_size=%sx%s, ocr_size=%sx%s"
                ),
                display_result.pdf_path,
                display_result.page_number + 1,
                display_result.page_count,
                display_result.page_image.width,
                display_result.page_image.height,
                ocr_page_image.width,
                ocr_page_image.height
            )

        except Exception:
            logger.exception("Ошибка при загрузке PDF-страницы в интерфейсе")

            messagebox.showerror(
                "Ошибка загрузки PDF",
                "Не удалось загрузить страницу PDF. Подробности в app.log."
            )

            self.set_status("Ошибка загрузки PDF.")

    def _load_pdf_page_with_service(self, file_path, page_index, dpi):
        """
        Загружает страницу PDF через PDFService в указанном DPI.
        """

        settings = PDFLoadSettings(
            dpi=dpi,
            poppler_path=POPPLER_PATH
        )

        return self.pdf_service.load_page(
            pdf_path=file_path,
            page_number=page_index,
            settings=settings
        )

    def _handle_pdf_load_error(self, error_message):
        """
        Показывает ошибку загрузки PDF.
        """

        logger.warning("PDF не загружен: %s", error_message)

        messagebox.showerror(
            "Ошибка загрузки PDF",
            f"Не удалось загрузить PDF.\n\n{error_message}"
        )

        self.set_status("PDF не загружен.")

    def _set_loaded_pdf_page(
        self,
        file_path,
        page_image,
        ocr_page_image,
        page_number,
        page_count,
        is_new_file=False
    ):
        """
        Сохраняет загруженную страницу PDF
        и обновляет интерфейс.
        """

        if is_new_file:
            self._save_current_file_tab()

            self.active_file_tab_id = self._create_file_tab(
                file_path=file_path,
                file_type="pdf"
            )

        self.current_file_path = Path(file_path)
        self.current_file_type = "pdf"

        self.pdf_path = Path(file_path)

        self.original_image = page_image
        self.ocr_source_image = ocr_page_image

        self.current_page_index = page_number
        self.page_count = page_count

        if is_new_file:
            self._save_pdf_path_to_state(file_path)

        self._save_pdf_page_to_state(page_number)

        self._reset_view_state(fit_to_page=True)
        self._reset_selection_state()

        self.update_image()
        self._update_page_controls()

        self._save_current_file_tab()
        self._refresh_file_tabs_panel()

        self.set_status(
            f"PDF загружен: страница {page_number + 1} из {page_count}"
        )

        logger.info(
            "Состояние PDF-страниц обновлено. current_page=%s, page_count=%s",
            self.current_page_index,
            self.page_count
        )

    def _save_pdf_path_to_state(self, file_path):
        """
        Сохраняет путь к PDF через AppController.
        """

        if hasattr(self.master, "controller"):
            self.master.controller.set_current_pdf(file_path)

    def _save_pdf_page_to_state(self, page_number):
        """
        Сохраняет текущую страницу PDF через AppController.
        """

        if (
            hasattr(self.master, "controller")
            and hasattr(self.master.controller, "set_current_pdf_page")
        ):
            self.master.controller.set_current_pdf_page(page_number)

    # =========================================================
    # ВКЛАДКИ ФАЙЛОВ
    # =========================================================

    def _create_file_tab(self, file_path, file_type):
        """
        Создаёт вкладку открытого файла.
        """

        tab_id = self.next_file_tab_id
        self.next_file_tab_id += 1

        path_obj = Path(file_path)

        self.file_tabs[tab_id] = {
            "title": self._get_file_tab_title(path_obj),
            "file_path": path_obj,
            "file_type": file_type,

            "pdf_path": None,
            "current_file_path": path_obj,
            "current_file_type": file_type,

            "current_page_index": 0,
            "page_count": 1,

            "original_image": None,
            "ocr_source_image": None,

            "zoom_factor": 1.0,
            "angle": 0,
            "offset_x": 0,
            "offset_y": 0,
        }

        self._refresh_file_tabs_panel()

        return tab_id

    def _get_file_tab_title(self, file_path: Path) -> str:
        """
        Возвращает короткое имя вкладки.
        """

        name = file_path.name

        if len(name) > 28:
            return name[:25] + "..."

        return name

    def _find_file_tab_by_path(self, file_path):
        """
        Ищет уже открытую вкладку по пути файла.
        """

        path_obj = Path(file_path)

        for tab_id, tab_data in self.file_tabs.items():
            if Path(tab_data["file_path"]) == path_obj:
                return tab_id

        return None

    def _save_current_file_tab(self):
        """
        Сохраняет текущее состояние просмотра в активную вкладку.
        """

        if self.active_file_tab_id is None:
            return

        if self.active_file_tab_id not in self.file_tabs:
            return

        tab_data = self.file_tabs[self.active_file_tab_id]

        tab_data.update({
            "pdf_path": self.pdf_path,
            "current_file_path": self.current_file_path,
            "current_file_type": self.current_file_type,

            "current_page_index": self.current_page_index,
            "page_count": self.page_count,

            "original_image": self.original_image,
            "ocr_source_image": self.ocr_source_image,

            "zoom_factor": self.zoom_factor,
            "angle": self.angle,
            "offset_x": self.offset_x,
            "offset_y": self.offset_y,
        })

    def _switch_file_tab(self, tab_id):
        """
        Переключается на вкладку открытого файла.
        """

        if tab_id not in self.file_tabs:
            logger.warning("Вкладка файла не найдена: %s", tab_id)
            return

        self._save_current_file_tab()

        tab_data = self.file_tabs[tab_id]

        self.active_file_tab_id = tab_id

        self.pdf_path = tab_data["pdf_path"]
        self.current_file_path = tab_data["current_file_path"]
        self.current_file_type = tab_data["current_file_type"]

        self.current_page_index = tab_data["current_page_index"]
        self.page_count = tab_data["page_count"]

        self.original_image = tab_data["original_image"]
        self.ocr_source_image = tab_data["ocr_source_image"]

        self.zoom_factor = tab_data["zoom_factor"]
        self.angle = tab_data["angle"]
        self.offset_x = tab_data["offset_x"]
        self.offset_y = tab_data["offset_y"]

        self._reset_selection_state()

        self.update_image()
        self._update_page_controls()
        self._refresh_file_tabs_panel()

        self.set_status(f"Открыта вкладка: {tab_data['title']}")

        logger.info(
            "Переключение на вкладку файла. tab_id=%s, path=%s",
            tab_id,
            tab_data["file_path"]
        )

    def _close_file_tab(self, tab_id):
        """
        Закрывает вкладку файла.
        """

        if tab_id not in self.file_tabs:
            return

        was_active = tab_id == self.active_file_tab_id

        del self.file_tabs[tab_id]

        if not self.file_tabs:
            self._reset_viewer_after_all_tabs_closed()
            return

        if was_active:
            new_tab_id = self._get_last_file_tab_id()
            self._switch_file_tab(new_tab_id)
        else:
            self._refresh_file_tabs_panel()

        logger.info("Вкладка файла закрыта: %s", tab_id)

    def _get_last_file_tab_id(self):
        """
        Возвращает последнюю открытую вкладку файла.
        """

        if not self.file_tabs:
            return None

        return list(self.file_tabs.keys())[-1]

    def _reset_viewer_after_all_tabs_closed(self):
        """
        Очищает просмотрщик, если закрыты все вкладки.
        """

        self.active_file_tab_id = None

        self.pdf_path = None
        self.current_file_path = None
        self.current_file_type = None

        self.current_page_index = 0
        self.page_count = 0

        self.original_image = None
        self.ocr_source_image = None
        self.rotated_image = None
        self.current_image = None
        self.tk_image = None

        self.displayed_image_width = 0
        self.displayed_image_height = 0

        self.viewport_x = 0
        self.viewport_y = 0
        self.viewport_source_box = None

        self.zoom_factor = 1.0
        self.angle = 0
        self.offset_x = 0
        self.offset_y = 0

        self._reset_selection_state()

        self.canvas.delete("all")
        self._update_page_controls()
        self._refresh_file_tabs_panel()

        self.set_status("Загрузите PDF или изображение для начала работы.")

    def _refresh_file_tabs_panel(self):
        """
        Перерисовывает панель вкладок файлов.
        """

        for widget in self.file_tabs_panel.winfo_children():
            widget.destroy()

        if not self.file_tabs:
            label = ctk.CTkLabel(
                self.file_tabs_panel,
                text="Нет открытых файлов"
            )
            label.pack(side="left", padx=10, pady=5)
            return

        for tab_id, tab_data in self.file_tabs.items():
            tab_frame = ctk.CTkFrame(self.file_tabs_panel)
            tab_frame.pack(side="left", padx=3, pady=4)

            title = tab_data["title"]

            if tab_id == self.active_file_tab_id:
                title = f"● {title}"

            btn_tab = ctk.CTkButton(
                tab_frame,
                text=title,
                width=160,
                height=26,
                command=lambda current_tab_id=tab_id: self._switch_file_tab(
                    current_tab_id
                )
            )
            btn_tab.pack(side="left", padx=(3, 1), pady=3)

            btn_close = ctk.CTkButton(
                tab_frame,
                text="×",
                width=26,
                height=26,
                command=lambda current_tab_id=tab_id: self._close_file_tab(
                    current_tab_id
                )
            )
            btn_close.pack(side="left", padx=(1, 3), pady=3)

    # =========================================================
    # СТРАНИЦЫ PDF
    # =========================================================

    def _update_page_controls(self):
        """
        Обновляет кнопки и подпись текущей страницы.
        """

        if self.current_file_type == "image":
            self.page_label.configure(text="Изображение")
            self.btn_prev_page.configure(state="disabled")
            self.btn_next_page.configure(state="disabled")
            return

        if self.page_count <= 0:
            self.page_label.configure(text="Стр. - / -")
            self.btn_prev_page.configure(state="disabled")
            self.btn_next_page.configure(state="disabled")
            return

        self.page_label.configure(
            text=f"Стр. {self.current_page_index + 1} / {self.page_count}"
        )

        prev_state = "normal" if self.current_page_index > 0 else "disabled"
        next_state = (
            "normal"
            if self.current_page_index < self.page_count - 1
            else "disabled"
        )

        self.btn_prev_page.configure(state=prev_state)
        self.btn_next_page.configure(state=next_state)

        logger.info(
            "Кнопки страниц обновлены. current=%s, total=%s, prev=%s, next=%s",
            self.current_page_index,
            self.page_count,
            prev_state,
            next_state
        )

    def go_to_previous_page(self):
        """
        Загружает предыдущую страницу PDF.
        """

        if self.current_file_type != "pdf":
            return

        if self.pdf_path is None:
            return

        if self.current_page_index <= 0:
            return

        self.load_pdf_page(
            file_path=self.pdf_path,
            page_index=self.current_page_index - 1,
            is_new_file=False
        )

    def go_to_next_page(self):
        """
        Загружает следующую страницу PDF.
        """

        if self.current_file_type != "pdf":
            return

        if self.pdf_path is None:
            return

        if self.current_page_index >= self.page_count - 1:
            return

        self.load_pdf_page(
            file_path=self.pdf_path,
            page_index=self.current_page_index + 1,
            is_new_file=False
        )

    # =========================================================
    # ОТРИСОВКА ИЗОБРАЖЕНИЯ
    # =========================================================

    def update_image(self, fast: bool = False):
        """
        Перерисовывает изображение на Canvas.

        Не масштабируем всю страницу целиком.
        Рисуем только видимую область.
        """

        if self.original_image is None:
            return

        self._prepare_display_image(fast=fast)
        self._draw_current_image_on_canvas()

        # После перерисовки выделение лучше сбросить,
        # потому что координаты могли стать неактуальными.
        self.rect_id = None

    def _prepare_display_image(self, fast: bool = False):
        """
        Готовит изображение для отображения на Canvas.

        Вместо resize всей страницы:
        - считаем полный размер изображения при текущем zoom;
        - определяем, какая часть изображения видна на Canvas;
        - вырезаем только эту область из original_image;
        - масштабируем только её до размера Canvas-viewport.
        """

        self.rotated_image = self.original_image.rotate(
            self.angle,
            expand=True
        )

        self.displayed_image_width = max(
            1,
            int(self.rotated_image.width * self.zoom_factor)
        )
        self.displayed_image_height = max(
            1,
            int(self.rotated_image.height * self.zoom_factor)
        )

        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())

        center_x, center_y = self._get_image_center_on_canvas()

        image_left = center_x - self.displayed_image_width / 2
        image_top = center_y - self.displayed_image_height / 2
        image_right = image_left + self.displayed_image_width
        image_bottom = image_top + self.displayed_image_height

        visible_left = max(0, image_left)
        visible_top = max(0, image_top)
        visible_right = min(canvas_width, image_right)
        visible_bottom = min(canvas_height, image_bottom)

        if visible_right <= visible_left or visible_bottom <= visible_top:
            self.current_image = None
            self.tk_image = None
            self.viewport_source_box = None
            return

        source_left = (visible_left - image_left) / self.zoom_factor
        source_top = (visible_top - image_top) / self.zoom_factor
        source_right = (visible_right - image_left) / self.zoom_factor
        source_bottom = (visible_bottom - image_top) / self.zoom_factor

        source_box = (
            max(0, int(source_left)),
            max(0, int(source_top)),
            min(self.rotated_image.width, int(source_right) + 1),
            min(self.rotated_image.height, int(source_bottom) + 1)
        )

        viewport_image = self.rotated_image.crop(source_box)

        target_width = max(1, int(visible_right - visible_left))
        target_height = max(1, int(visible_bottom - visible_top))

        resample_filter = (
            self.FAST_ZOOM_RESAMPLE
            if fast
            else self.QUALITY_RESAMPLE
        )

        self.current_image = viewport_image.resize(
            (target_width, target_height),
            resample=resample_filter
        )

        self.tk_image = ImageTk.PhotoImage(self.current_image)

        self.viewport_x = int(visible_left)
        self.viewport_y = int(visible_top)
        self.viewport_source_box = source_box

        logger.debug(
            (
                "Viewport rendered. zoom=%s, full_display=%sx%s, "
                "viewport=%sx%s, source_box=%s"
            ),
            round(self.zoom_factor, 3),
            self.displayed_image_width,
            self.displayed_image_height,
            target_width,
            target_height,
            source_box
        )

    def _draw_current_image_on_canvas(self):
        """
        Рисует текущий viewport на Canvas.
        """

        self.canvas.delete("all")

        if self.tk_image is None:
            return

        self.canvas.create_image(
            self.viewport_x,
            self.viewport_y,
            anchor="nw",
            image=self.tk_image,
            tags="image"
        )

    def _get_image_center_on_canvas(self):
        """
        Возвращает центр изображения на Canvas с учётом смещения.
        """

        canvas_w = max(1, self.canvas.winfo_width())
        canvas_h = max(1, self.canvas.winfo_height())

        center_x = canvas_w // 2 + self.offset_x
        center_y = canvas_h // 2 + self.offset_y

        return center_x, center_y

    def on_canvas_resize(self, event=None):
        """
        Перерисовывает изображение при изменении размера Canvas.
        """

        if self.original_image is not None:
            self.update_image()

    # =========================================================
    # ПОВОРОТ И МАСШТАБ
    # =========================================================

    def rotate_image(self):
        """
        Поворачивает изображение на 90 градусов против часовой стрелки.
        """

        if self.original_image is None:
            return

        self.angle = (self.angle - 90) % 360

        self.clear_selection()
        self.update_image()

        self._save_current_file_tab()

        self.set_status(f"Поворот: {self.angle}°")

    def zoom_image(self, event):
        """
        Масштабирует изображение колёсиком мыши.
        """

        if self.original_image is None:
            return "break"

        old_zoom = self.zoom_factor
        self.zoom_factor = self._calculate_new_zoom(event)

        if self.zoom_factor == old_zoom:
            return "break"

        self.clear_selection()
        self.set_status(f"Масштаб: {int(self.zoom_factor * 100)}%")

        self._save_current_file_tab()
        self._schedule_zoom_redraw()

        return "break"

    def _calculate_new_zoom(self, event):
        """
        Считает новый масштаб по событию колёсика мыши.
        """

        new_zoom = self.zoom_factor

        if hasattr(event, "delta") and event.delta:
            if event.delta > 0:
                new_zoom *= self.ZOOM_STEP
            else:
                new_zoom /= self.ZOOM_STEP

        elif hasattr(event, "num"):
            if event.num == 4:
                new_zoom *= self.ZOOM_STEP
            elif event.num == 5:
                new_zoom /= self.ZOOM_STEP

        return max(self.MIN_ZOOM, min(new_zoom, self.MAX_ZOOM))

    def _schedule_zoom_redraw(self):
        """
        Планирует перерисовку при зуме.

        Во время активного вращения колёсика делаем быстрый resize.
        Когда пользователь перестал крутить — делаем финальный качественный resize.
        """

        if self.zoom_redraw_after_id is None:
            self.zoom_redraw_after_id = self.after(
                self.ZOOM_REDRAW_DELAY_MS,
                self._run_fast_zoom_redraw
            )

        if self.zoom_final_redraw_after_id is not None:
            self.after_cancel(self.zoom_final_redraw_after_id)

        self.zoom_final_redraw_after_id = self.after(
            self.ZOOM_FINAL_REDRAW_DELAY_MS,
            self._run_quality_zoom_redraw
        )

    def _run_fast_zoom_redraw(self):
        """
        Быстрая перерисовка во время прокрутки.
        """

        self.zoom_redraw_after_id = None
        self.update_image(fast=True)

    def _run_quality_zoom_redraw(self):
        """
        Финальная качественная перерисовка после окончания прокрутки.
        """

        self.zoom_final_redraw_after_id = None
        self.update_image(fast=False)

    # =========================================================
    # МЫШЬ: ПЕРЕМЕЩЕНИЕ И ВЫДЕЛЕНИЕ
    # =========================================================

    def on_mouse_press(self, event):
        """
        Обрабатывает нажатие левой кнопки мыши.
        """

        if self.original_image is None:
            return

        current_mode = self.mode_switch.get()

        if current_mode == self.MODE_PAN:
            self._start_pan(event)

        elif current_mode == self.MODE_SELECT:
            self._start_selection(event)

    def _start_pan(self, event):
        """
        Запоминает стартовую точку перемещения.
        """

        self.last_mouse_x = event.x
        self.last_mouse_y = event.y

    def _start_selection(self, event):
        """
        Начинает выделение области.
        """

        self.clear_selection()

        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)

        self.rect_id = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x,
            self.start_y,
            outline="red",
            width=2,
            dash=(4, 4),
            tags="selection"
        )

    def on_mouse_drag(self, event):
        """
        Обрабатывает движение мыши с зажатой левой кнопкой.
        """

        if self.original_image is None:
            return

        current_mode = self.mode_switch.get()

        if current_mode == self.MODE_PAN:
            self._drag_pan(event)

        elif current_mode == self.MODE_SELECT:
            self._drag_selection(event)

    def _drag_pan(self, event):
        """
        Перемещает изображение по Canvas.
        """

        dx = event.x - self.last_mouse_x
        dy = event.y - self.last_mouse_y

        self.last_mouse_x = event.x
        self.last_mouse_y = event.y

        self.offset_x += dx
        self.offset_y += dy

        self._save_current_file_tab()

        self.update_image(fast=True)

    def _drag_selection(self, event):
        """
        Изменяет размер рамки выделения.
        """

        if self.rect_id is None:
            return

        current_x = self.canvas.canvasx(event.x)
        current_y = self.canvas.canvasy(event.y)

        self.canvas.coords(
            self.rect_id,
            self.start_x,
            self.start_y,
            current_x,
            current_y
        )

    # =========================================================
    # КОНТЕКСТНОЕ МЕНЮ
    # =========================================================

    def show_context_menu(self, event):
        """
        Показывает контекстное меню, если правый клик был внутри выделения.
        """

        if not self._is_click_inside_selection(event):
            return

        try:
            self.context_menu.post(event.x_root, event.y_root)
        except Exception:
            logger.exception("Ошибка при открытии контекстного меню PDF")

    def _is_click_inside_selection(self, event) -> bool:
        """
        Проверяет, находится ли правый клик внутри рамки выделения.
        """

        if self.rect_id is None:
            return False

        try:
            x1, y1, x2, y2 = self.canvas.coords(self.rect_id)
        except Exception:
            logger.exception("Ошибка при получении координат выделения")
            return False

        click_x = self.canvas.canvasx(event.x)
        click_y = self.canvas.canvasy(event.y)

        min_x, max_x = sorted([x1, x2])
        min_y, max_y = sorted([y1, y2])

        return (
            min_x <= click_x <= max_x
            and min_y <= click_y <= max_y
        )

    # =========================================================
    # ВЫРЕЗАНИЕ ОБЛАСТИ
    # =========================================================

    def get_cropped_image(self):
        """
        Вырезает выделенную область.

        На экране пользователь видит облегчённую display-версию.
        Для OCR вырезаем ту же область из большой OCR-версии.
        """

        if not self._can_crop():
            return None

        try:
            selection_coords = tuple(self.canvas.coords(self.rect_id))

            display_request = ImageCropRequest(
                source_image=self.rotated_image,
                selection_coords=selection_coords,
                canvas_width=max(1, self.canvas.winfo_width()),
                canvas_height=max(1, self.canvas.winfo_height()),
                displayed_image_width=self.displayed_image_width,
                displayed_image_height=self.displayed_image_height,
                offset_x=self.offset_x,
                offset_y=self.offset_y,
                zoom_factor=self.zoom_factor,
                angle=self.angle,
                restore_original_orientation=False
            )

            display_crop_result = (
                self.image_crop_service.crop_from_canvas_selection(
                    display_request
                )
            )

            if (
                not display_crop_result.success
                or display_crop_result.crop_box is None
            ):
                logger.warning(
                    "Не удалось получить crop_box области: %s",
                    display_crop_result.error_message
                )
                return None

            cropped_image = self._crop_from_ocr_source(
                display_crop_box=display_crop_result.crop_box
            )

            logger.info(
                (
                    "Область вырезана из OCR-источника. "
                    "display_crop_box=%s, image_size=%s"
                ),
                display_crop_result.crop_box,
                cropped_image.size if cropped_image else None
            )

            return cropped_image

        except Exception:
            logger.exception("Ошибка при подготовке данных для OCR-crop")
            return None

    def _crop_from_ocr_source(self, display_crop_box):
        """
        Пересчитывает crop_box с display-изображения на OCR-изображение
        и вырезает область из OCR-источника.

        Если пользователь повернул изображение на экране,
        в OCR уходит область в той же ориентации.
        """

        if self.ocr_source_image is None or self.rotated_image is None:
            return None

        ocr_rotated_image = self.ocr_source_image.rotate(
            self.angle,
            expand=True
        )

        display_width = max(1, self.rotated_image.width)
        display_height = max(1, self.rotated_image.height)

        scale_x = ocr_rotated_image.width / display_width
        scale_y = ocr_rotated_image.height / display_height

        left, top, right, bottom = display_crop_box

        ocr_crop_box = (
            int(round(left * scale_x)),
            int(round(top * scale_y)),
            int(round(right * scale_x)),
            int(round(bottom * scale_y))
        )

        cropped_image = ocr_rotated_image.crop(ocr_crop_box)

        logger.info(
            (
                "OCR crop source check. "
                "angle=%s, display_rotated_size=%s, ocr_rotated_size=%s, "
                "display_crop_box=%s, ocr_crop_box=%s, "
                "scale_x=%.3f, scale_y=%.3f, cropped_size=%s"
            ),
            self.angle,
            self.rotated_image.size,
            ocr_rotated_image.size,
            display_crop_box,
            ocr_crop_box,
            scale_x,
            scale_y,
            cropped_image.size
        )

        return cropped_image

    def _save_debug_ocr_image(self, image, prefix):
        """
        Временно сохраняет изображение, которое отправляется в OCR.

        Метод оставлен для диагностики.
        """

        try:
            debug_dir = Path("data/processed/ocr_debug")
            debug_dir.mkdir(parents=True, exist_ok=True)

            file_path = debug_dir / f"{prefix}.png"

            image.save(file_path)

            logger.info(
                "DEBUG OCR image saved: %s, size=%s",
                file_path,
                image.size
            )

        except Exception:
            logger.exception("Не удалось сохранить debug OCR image")

    def _can_crop(self) -> bool:
        """
        Проверяет, есть ли всё необходимое для вырезания области.
        """

        return (
            self.rect_id is not None
            and self.original_image is not None
            and self.ocr_source_image is not None
            and self.rotated_image is not None
            and self.displayed_image_width > 0
            and self.displayed_image_height > 0
        )

    # =========================================================
    # OCR
    # =========================================================

    def _get_default_ocr_language_codes(self) -> set[str]:
        """
        Берёт языки из config.OCR_LANGUAGES
        и превращает строку вида 'rus+eng+kaz'
        в множество {'rus', 'eng', 'kaz'}.
        """

        language_codes = {
            language_code.strip()
            for language_code in OCR_LANGUAGES.split("+")
            if language_code.strip()
        }

        available_codes = set(self.OCR_LANGUAGE_OPTIONS.values())

        selected_codes = language_codes.intersection(available_codes)

        if not selected_codes:
            return {"rus", "eng"}

        return selected_codes

    def get_selected_ocr_languages(self) -> str:
        """
        Возвращает выбранные языки OCR в формате Tesseract.

        Например:
            rus+eng+kaz
        """

        selected_codes = []

        for language_code in self.OCR_LANGUAGE_OPTIONS.values():
            variable = self.ocr_language_vars.get(language_code)

            if variable is not None and variable.get():
                selected_codes.append(language_code)

        return "+".join(selected_codes)

    def send_to_ocr(self):
        """
        Вырезает выделенную область, запускает OCR
        и отправляет результат в OCR-раздел через AppController.
        """

        cropped_image = self.get_cropped_image()

        if cropped_image is None:
            messagebox.showwarning(
                "Нет области",
                (
                    "Не удалось вырезать область. Проверьте, что выделение "
                    "находится на изображении."
                )
            )
            logger.warning(
                "OCR не запущен: не удалось вырезать выделенную область"
            )
            return

        selected_languages = self.get_selected_ocr_languages()

        if not selected_languages:
            messagebox.showwarning(
                "Языки OCR",
                "Выберите хотя бы один язык для распознавания."
            )
            logger.warning("OCR не запущен: не выбран ни один язык")
            return

        try:
            self._set_wait_cursor(True)

            result = self._recognize_cropped_image(
                cropped_image=cropped_image,
                selected_languages=selected_languages
            )

            if not result.success:
                self._handle_ocr_error(result)
                return

            self._send_ocr_result_to_controller(
                cropped_image=cropped_image,
                recognized_text=result.text,
                selected_languages=selected_languages
            )

            logger.info(
                "OCR успешно завершён. languages=%s, text_length=%s",
                selected_languages,
                len(result.text)
            )

        except Exception:
            logger.exception("Ошибка при OCR")
            messagebox.showerror(
                "Ошибка OCR",
                (
                    "Произошла ошибка во время распознавания текста. "
                    "Подробности в app.log."
                )
            )

        finally:
            self._set_wait_cursor(False)

    def _recognize_cropped_image(
        self,
        cropped_image,
        selected_languages
    ):
        """
        Запускает OCRService для выделенной области.
        """

        logger.info(
            "Запущено OCR. languages=%s, image_size=%s",
            selected_languages,
            cropped_image.size
        )

        return self.ocr_service.recognize_from_pil(
            pil_image=cropped_image,
            settings=OCRSettings(
                languages=selected_languages
            )
        )

    def _handle_ocr_error(self, result):
        """
        Обрабатывает ошибку OCR.
        """

        logger.error(
            "OCR завершился ошибкой. error=%s",
            result.error_message
        )

        messagebox.showerror(
            "Ошибка OCR",
            (
                "Не удалось распознать текст.\n\n"
                f"Ошибка: {result.error_message}"
            )
        )

    def _send_ocr_result_to_controller(
        self,
        cropped_image,
        recognized_text,
        selected_languages
    ):
        """
        Передаёт OCR-результат в AppController.
        """

        if not hasattr(self.master, "controller"):
            logger.warning(
                "AppController не найден. OCR-результат не отправлен."
            )
            messagebox.showerror(
                "Ошибка",
                (
                    "Не удалось отправить результат OCR: "
                    "контроллер приложения не найден."
                )
            )
            return

        source_type = (
            "image_selection"
            if self.current_file_type == "image"
            else "pdf_selection"
        )

        self.master.controller.show_ocr_result(
            image=cropped_image,
            text=recognized_text,
            source=f"{source_type}:ocr:{selected_languages}"
        )

    def _set_wait_cursor(self, enabled: bool):
        """
        Включает или выключает курсор ожидания на время долгой операции.
        """

        if enabled:
            self.configure(cursor="watch")
            self.canvas.configure(cursor="watch")
            self.update_idletasks()
        else:
            self.configure(cursor="")
            self.canvas.configure(cursor="")
            self.update_idletasks()