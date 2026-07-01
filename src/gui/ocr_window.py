import customtkinter as ctk
import tkinter as tk
from tkinter import Menu, messagebox

from PIL import Image, ImageTk

from src.utils.logger import logger


class OCRViewerFrame(ctk.CTkFrame):
    """
    Второй раздел приложения: просмотр результатов OCR.

    Что делает:
    - каждый новый OCR-результат открывает в отдельной вкладке;
    - показывает вырезанный фрагмент изображения;
    - показывает распознанный текст;
    - сохраняет ручные правки текста при переключении вкладок;
    - позволяет отправить весь текст в поле сравнения;
    - позволяет отправить выделенный фрагмент текста в поле сравнения.
    """

    PREVIEW_MAX_HEIGHT = 130
    DEFAULT_TEXT = "Здесь появится распознанный текст...\n"
    DEFAULT_IMAGE_TEXT = "Здесь появится вырезанный фрагмент"

    def __init__(self, master):
        super().__init__(master)

        self.current_image = None
        self.current_ctk_image = None
        self.current_photo_image = None
        self.current_text = ""

        self.ocr_tabs = {}
        self.active_ocr_tab_id = None
        self.next_ocr_tab_id = 1

        self._configure_grid()
        self._create_widgets()
        self._create_context_menu()
        self._bind_events()

    # =========================================================
    # ИНИЦИАЛИЗАЦИЯ
    # =========================================================

    def _configure_grid(self):
        """Настраивает сетку OCR-раздела."""

        # row=0 — вкладки OCR
        # row=1 — превью изображения
        # row=2 — текст OCR, занимает всё свободное место
        # row=3 — кнопки переноса текста
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=0)

        self.grid_columnconfigure(0, weight=1)

    # =========================================================
    # СОЗДАНИЕ ИНТЕРФЕЙСА
    # =========================================================

    def _create_widgets(self):
        """Создаёт все элементы интерфейса."""

        self._create_tabs_panel()
        self._create_image_panel()
        self._create_textbox()
        self._create_bottom_panel()

    def _create_tabs_panel(self):
        """Создаёт панель вкладок OCR-результатов."""

        self.tabs_panel = ctk.CTkScrollableFrame(
            self,
            height=44,
            orientation="horizontal"
        )
        self.tabs_panel.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=10,
            pady=(10, 0)
        )

        self._refresh_ocr_tabs_panel()

    def _create_image_panel(self):
        """Создаёт верхнюю панель с превью изображения."""

        self.image_panel = ctk.CTkFrame(self, height=150)
        self.image_panel.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=10,
            pady=(5, 5)
        )

        self.image_panel.pack_propagate(False)

        self.lbl_image = tk.Label(
            self.image_panel,
            text=self.DEFAULT_IMAGE_TEXT,
            bg="#2b2b2b",
            fg="white"
        )
        self.lbl_image.pack(expand=True, fill="both")

    def _create_textbox(self):
        """Создаёт поле с распознанным текстом."""

        self.textbox = ctk.CTkTextbox(
            self,
            wrap="word",
            font=ctk.CTkFont(size=14)
        )
        self.textbox.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=10,
            pady=(5, 5)
        )

        self._set_text(self.DEFAULT_TEXT)

    def _create_bottom_panel(self):
        """Создаёт нижнюю панель с кнопками переноса текста."""

        self.bottom_panel = ctk.CTkFrame(self)
        self.bottom_panel.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=10,
            pady=(5, 10)
        )

        self.bottom_panel.grid_columnconfigure((0, 1), weight=1)

        self.btn_send_1 = ctk.CTkButton(
            self.bottom_panel,
            text="Перенести полностью в Поле 1",
            command=lambda: self.send_full_text(1, append=False)
        )
        self.btn_send_1.grid(
            row=0,
            column=0,
            padx=5,
            pady=(10, 4),
            sticky="ew"
        )

        self.btn_send_2 = ctk.CTkButton(
            self.bottom_panel,
            text="Перенести полностью в Поле 2",
            command=lambda: self.send_full_text(2, append=False)
        )
        self.btn_send_2.grid(
            row=0,
            column=1,
            padx=5,
            pady=(10, 4),
            sticky="ew"
        )

        self.btn_append_1 = ctk.CTkButton(
            self.bottom_panel,
            text="Добавить полностью в Поле 1",
            command=lambda: self.send_full_text(1, append=True)
        )
        self.btn_append_1.grid(
            row=1,
            column=0,
            padx=5,
            pady=(4, 10),
            sticky="ew"
        )

        self.btn_append_2 = ctk.CTkButton(
            self.bottom_panel,
            text="Добавить полностью в Поле 2",
            command=lambda: self.send_full_text(2, append=True)
        )
        self.btn_append_2.grid(
            row=1,
            column=1,
            padx=5,
            pady=(4, 10),
            sticky="ew"
        )

    # =========================================================
    # КОНТЕКСТНОЕ МЕНЮ
    # =========================================================

    def _create_context_menu(self):
        """Создаёт контекстное меню для текстового поля."""

        self.context_menu = Menu(self, tearoff=0)

        self.context_menu.add_command(
            label="Перенести выделенное в Поле 1",
            command=lambda: self.send_selection(1, append=False)
        )

        self.context_menu.add_command(
            label="Перенести выделенное в Поле 2",
            command=lambda: self.send_selection(2, append=False)
        )

        self.context_menu.add_separator()

        self.context_menu.add_command(
            label="Добавить выделенное в Поле 1",
            command=lambda: self.send_selection(1, append=True)
        )

        self.context_menu.add_command(
            label="Добавить выделенное в Поле 2",
            command=lambda: self.send_selection(2, append=True)
        )

    def _bind_events(self):
        """Привязывает события OCR-раздела."""

        self.textbox.bind("<Button-3>", self.show_context_menu)

        # Сохраняем ручные правки текста, когда пользователь печатает.
        self.textbox.bind("<KeyRelease>", self._on_text_changed)

    def show_context_menu(self, event):
        """
        Показывает контекстное меню только если есть выделенный текст.
        """

        if not self._has_selected_text():
            return

        try:
            self.context_menu.post(event.x_root, event.y_root)
        except Exception:
            logger.exception("Ошибка при открытии контекстного меню OCR")

    def _has_selected_text(self) -> bool:
        """Проверяет, есть ли выделение в текстовом поле."""

        try:
            return bool(self.textbox.tag_ranges("sel"))
        except tk.TclError:
            return False

    def _on_text_changed(self, event=None):
        """
        Сохраняет изменения текста в активную OCR-вкладку.
        """

        self._save_current_ocr_tab()

    # =========================================================
    # ОБНОВЛЕНИЕ СОДЕРЖИМОГО
    # =========================================================

    def update_content(self, pil_image, text):
        """
        Создаёт новую OCR-вкладку после распознавания.

        Этот метод вызывается через AppController.
        """

        tab_id = self._create_ocr_tab(
            pil_image=pil_image,
            text=text or ""
        )

        self._switch_ocr_tab(tab_id)

        logger.info(
            "Создана новая OCR-вкладка. tab_id=%s, text_length=%s",
            tab_id,
            len(text or "")
        )

    # =========================================================
    # OCR-ВКЛАДКИ
    # =========================================================

    def _create_ocr_tab(self, pil_image, text):
        """
        Создаёт новую вкладку OCR.
        """

        tab_id = self.next_ocr_tab_id
        self.next_ocr_tab_id += 1

        title = f"OCR {tab_id}"

        self.ocr_tabs[tab_id] = {
            "title": title,
            "image": pil_image,
            "text": text or "",
            "photo_image": None,
        }

        self._refresh_ocr_tabs_panel()

        return tab_id

    def _switch_ocr_tab(self, tab_id):
        """
        Переключается на выбранную OCR-вкладку.
        """

        if tab_id not in self.ocr_tabs:
            logger.warning("OCR-вкладка не найдена: %s", tab_id)
            return

        self._save_current_ocr_tab()

        self.active_ocr_tab_id = tab_id

        tab_data = self.ocr_tabs[tab_id]

        self.current_image = tab_data["image"]
        self.current_text = tab_data["text"]

        self._show_image(self.current_image)
        self._set_text(self.current_text)

        self._refresh_ocr_tabs_panel()

        logger.info("Переключение на OCR-вкладку: %s", tab_id)

    def _save_current_ocr_tab(self):
        """
        Сохраняет текущий текст во вкладку.

        Нужно, если пользователь вручную поправил OCR-текст.
        """

        if self.active_ocr_tab_id is None:
            return

        if self.active_ocr_tab_id not in self.ocr_tabs:
            return

        self.ocr_tabs[self.active_ocr_tab_id]["text"] = self._get_full_text()
        self.current_text = self.ocr_tabs[self.active_ocr_tab_id]["text"]

    def _close_ocr_tab(self, tab_id):
        """
        Закрывает OCR-вкладку.
        """

        if tab_id not in self.ocr_tabs:
            return

        was_active = tab_id == self.active_ocr_tab_id

        del self.ocr_tabs[tab_id]

        if not self.ocr_tabs:
            self._reset_after_all_tabs_closed()
            return

        if was_active:
            new_tab_id = self._get_last_ocr_tab_id()
            self._switch_ocr_tab(new_tab_id)
        else:
            self._refresh_ocr_tabs_panel()

        logger.info("OCR-вкладка закрыта: %s", tab_id)

    def _get_last_ocr_tab_id(self):
        """
        Возвращает последнюю открытую OCR-вкладку.
        """

        if not self.ocr_tabs:
            return None

        return list(self.ocr_tabs.keys())[-1]

    def _reset_after_all_tabs_closed(self):
        """
        Сбрасывает OCR-раздел, если закрыты все вкладки.
        """

        self.active_ocr_tab_id = None

        self.current_image = None
        self.current_photo_image = None
        self.current_text = ""

        self.lbl_image.configure(
            image="",
            text=self.DEFAULT_IMAGE_TEXT
        )
        self.lbl_image.image = None

        self._set_text(self.DEFAULT_TEXT)
        self._refresh_ocr_tabs_panel()

        logger.info("Все OCR-вкладки закрыты")

    def _refresh_ocr_tabs_panel(self):
        """
        Перерисовывает панель OCR-вкладок.
        """

        for widget in self.tabs_panel.winfo_children():
            widget.destroy()

        if not self.ocr_tabs:
            label = ctk.CTkLabel(
                self.tabs_panel,
                text="OCR-вкладок пока нет"
            )
            label.pack(side="left", padx=10, pady=5)
            return

        for tab_id, tab_data in self.ocr_tabs.items():
            tab_frame = ctk.CTkFrame(self.tabs_panel)
            tab_frame.pack(side="left", padx=3, pady=4)

            title = tab_data["title"]

            if tab_id == self.active_ocr_tab_id:
                title = f"● {title}"

            btn_tab = ctk.CTkButton(
                tab_frame,
                text=title,
                width=95,
                height=26,
                command=lambda current_tab_id=tab_id: self._switch_ocr_tab(
                    current_tab_id
                )
            )
            btn_tab.pack(side="left", padx=(3, 1), pady=3)

            btn_close = ctk.CTkButton(
                tab_frame,
                text="×",
                width=26,
                height=26,
                command=lambda current_tab_id=tab_id: self._close_ocr_tab(
                    current_tab_id
                )
            )
            btn_close.pack(side="left", padx=(1, 3), pady=3)

    # =========================================================
    # ИЗОБРАЖЕНИЕ
    # =========================================================

    def _show_image(self, pil_image):
        """
        Показывает превью вырезанного изображения.

        Используем обычный tk.Label + ImageTk.PhotoImage,
        потому что CTkImage иногда даёт TclError:
        image "pyimage..." doesn't exist при частом создании/закрытии вкладок.
        """

        if pil_image is None:
            self.current_photo_image = None
            self.current_ctk_image = None

            self.lbl_image.configure(
                image="",
                text=self.DEFAULT_IMAGE_TEXT
            )
            self.lbl_image.image = None
            return

        try:
            preview_image = self._prepare_preview_image(pil_image)

            photo_image = ImageTk.PhotoImage(preview_image)

            self.current_photo_image = photo_image
            self.current_ctk_image = None

            self.lbl_image.configure(
                image=photo_image,
                text=""
            )

            # Важно сохранить ссылку, иначе Tkinter удалит изображение.
            self.lbl_image.image = photo_image

            if self.active_ocr_tab_id in self.ocr_tabs:
                self.ocr_tabs[self.active_ocr_tab_id]["photo_image"] = photo_image

        except Exception:
            logger.exception("Ошибка при отображении OCR-изображения")

            self.current_photo_image = None
            self.current_ctk_image = None

            self.lbl_image.configure(
                image="",
                text="Не удалось показать изображение"
            )
            self.lbl_image.image = None

    def _prepare_preview_image(self, pil_image):
        """
        Подготавливает изображение для превью.

        Если изображение слишком высокое — уменьшаем его
        до PREVIEW_MAX_HEIGHT, сохраняя пропорции.
        """

        preview_image = pil_image.copy()

        if preview_image.height > self.PREVIEW_MAX_HEIGHT:
            ratio = self.PREVIEW_MAX_HEIGHT / preview_image.height
            new_width = max(1, int(preview_image.width * ratio))

            preview_image = preview_image.resize(
                (new_width, self.PREVIEW_MAX_HEIGHT),
                Image.Resampling.LANCZOS
            )

        return preview_image

    # =========================================================
    # ТЕКСТ
    # =========================================================

    def _set_text(self, text):
        """Устанавливает текст в OCR-поле."""

        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text or "")

    def _get_full_text(self) -> str:
        """Возвращает весь текст из OCR-поля."""

        return self.textbox.get("1.0", "end-1c").strip()

    def _get_selected_text(self) -> str:
        """Возвращает выделенный текст из OCR-поля."""

        try:
            return self.textbox.get("sel.first", "sel.last").strip()
        except tk.TclError:
            return ""

    # =========================================================
    # ОТПРАВКА ТЕКСТА В СРАВНЕНИЕ
    # =========================================================

    def send_selection(self, field_num, append=False):
        """
        Отправляет выделенный фрагмент OCR-текста в поле сравнения.
        """

        selected_text = self._get_selected_text()

        if not selected_text:
            messagebox.showwarning(
                "Текст не выделен",
                "Сначала выделите текст для переноса."
            )
            logger.warning("Попытка отправить невыделенный OCR-текст")
            return

        self._send_text_to_compare(
            text=selected_text,
            field_num=field_num,
            append=append
        )

    def send_full_text(self, field_num, append=False):
        """
        Отправляет весь OCR-текст в поле сравнения.
        """

        full_text = self._get_full_text()

        if not full_text:
            messagebox.showwarning(
                "OCR-текст пуст",
                "Нет текста для переноса в сравнение."
            )
            logger.warning("Попытка отправить пустой OCR-текст")
            return

        self._send_text_to_compare(
            text=full_text,
            field_num=field_num,
            append=append
        )

    def _send_text_to_compare(self, text, field_num, append=False):
        """
        Отправляет текст в Compare-раздел через AppController.
        """

        if not hasattr(self.master, "controller"):
            logger.warning("AppController не найден. OCR-текст не отправлен.")
            return

        self.master.controller.send_text_to_compare(
            text=text,
            field_num=field_num,
            source="ocr",
            append=append
        )

        logger.info(
            "OCR-текст отправлен в поле сравнения %s. Длина: %s, append=%s",
            field_num,
            len(text),
            append
        )