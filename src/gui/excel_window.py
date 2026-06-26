import tkinter as tk
from tkinter import Menu, filedialog, messagebox

import customtkinter as ctk
from tksheet import Sheet

from src.services.excel_service import ExcelService
from src.utils.logger import logger


class ExcelViewerFrame(ctk.CTkFrame):
    """
    Четвёртый раздел приложения: просмотр Excel-таблиц.

    Что умеет:
    - загружать Excel-файл;
    - выбирать лист книги;
    - отображать таблицу через tksheet;
    - выбирать ячейку;
    - отправлять значение ячейки в поля сравнения;
    - открывать ячейку в отдельном окне для просмотра/редактирования.
    """

    DEFAULT_SHEET_TEXT = "Лист не выбран"

    def __init__(self, master):
        super().__init__(master)

        self.excel_service = ExcelService()

        # Прокси нужны для совместимости с tksheet.
        self.bind_all = self._bind_all_proxy
        self.unbind_all = self._unbind_all_proxy

        self._init_state()
        self._configure_grid()
        self._create_widgets()
        self._bind_events()

    # =========================================================
    # ИНИЦИАЛИЗАЦИЯ
    # =========================================================

    def _init_state(self):
        """Создаёт переменные состояния Excel-раздела."""

        self.df = None

        self.current_excel_path = None

        self.sheet_names = []
        self.current_sheet_name = ""
        self.sheet_var = tk.StringVar(value=self.DEFAULT_SHEET_TEXT)

        self.current_cell_value = ""
        self.current_row = None
        self.current_col = None

        self.edit_window = None

    def _configure_grid(self):
        """Настраивает сетку основного фрейма."""

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def _bind_all_proxy(self, *args, **kwargs):
        """Прокси для bind_all, который использует tksheet."""
        return tk.Frame.bind_all(self, *args, **kwargs)

    def _unbind_all_proxy(self, *args, **kwargs):
        """Прокси для unbind_all, который использует tksheet."""
        return tk.Frame.unbind_all(self, *args, **kwargs)

    # =========================================================
    # СОЗДАНИЕ ИНТЕРФЕЙСА
    # =========================================================

    def _create_widgets(self):
        """Создаёт весь интерфейс Excel-раздела."""

        self._create_top_panel()
        self._create_table_container()
        self._create_sheet()
        self._setup_context_menu()

    def _create_top_panel(self):
        """Создаёт верхнюю панель управления."""

        self.top_panel = ctk.CTkFrame(self, height=40)
        self.top_panel.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        self.btn_load = ctk.CTkButton(
            self.top_panel,
            text="Загрузить Excel",
            command=self.load_excel,
            width=150
        )
        self.btn_load.pack(side="left", padx=5, pady=5)

        self.sheet_label = ctk.CTkLabel(
            self.top_panel,
            text="Лист:"
        )
        self.sheet_label.pack(side="left", padx=(15, 5), pady=5)

        self.sheet_menu = ctk.CTkOptionMenu(
            self.top_panel,
            values=[self.DEFAULT_SHEET_TEXT],
            variable=self.sheet_var,
            command=self.load_selected_sheet,
            width=180,
            state="disabled"
        )
        self.sheet_menu.pack(side="left", padx=5, pady=5)

        self.btn_zoom_in = ctk.CTkButton(
            self.top_panel,
            text="➕",
            command=self.zoom_in,
            width=40
        )
        self.btn_zoom_in.pack(side="left", padx=5, pady=5)

        self.btn_zoom_out = ctk.CTkButton(
            self.top_panel,
            text="➖",
            command=self.zoom_out,
            width=40
        )
        self.btn_zoom_out.pack(side="left", padx=5, pady=5)

        self.btn_zoom_reset = ctk.CTkButton(
            self.top_panel,
            text="100%",
            command=self.zoom_reset,
            width=60
        )
        self.btn_zoom_reset.pack(side="left", padx=5, pady=5)

    def _create_table_container(self):
        """Создаёт контейнер для таблицы."""

        self.table_container = tk.Frame(self, bg="#2b2b2b")
        self.table_container.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=10,
            pady=10
        )
        self.table_container.grid_rowconfigure(0, weight=1)
        self.table_container.grid_columnconfigure(0, weight=1)

    def _create_sheet(self):
        """Создаёт tksheet-таблицу."""

        self.sheet = Sheet(
            self.table_container,
            data=[[""]],
            headers=[""],
            show_index=True,
            show_header=True,
            empty_vertical=0,
            empty_horizontal=0,
            align="w",
            font=("Arial", 11, ""),
            header_font=("Arial", 11, "bold"),
            table_bg="#2b2b2b",
            table_fg="#ffffff",
            table_grid_fg="#444444",
            table_selected_cells_bg="#1a5276",
            table_selected_cells_fg="#ffffff",
            header_bg="#333333",
            header_fg="#ffffff",
            header_selected_cells_bg="#1a5276",
            header_selected_cells_fg="#ffffff",
            index_bg="#333333",
            index_fg="#ffffff",
            index_selected_cells_bg="#1a5276",
            index_selected_cells_fg="#ffffff",
        )
        self.sheet.grid(row=0, column=0, sticky="nsew")

        self.sheet.enable_bindings(
            "single_select",
            "toggle_select",
            "column_select",
            "row_select",
            "drag_select",
            "ctrl_a_select_all",
            "copy",
            "arrowkeys",
            "mousewheel",
            "rc_popup_menu",
            menu=True
        )

    def _bind_events(self):
        """Привязывает события таблицы."""

        self.sheet.bind("<<SheetSelect>>", self.on_cell_select)
        self.sheet.bind("<Double-Button-1>", self.on_double_click)

    # =========================================================
    # КОНТЕКСТНОЕ МЕНЮ ТАБЛИЦЫ
    # =========================================================

    def _setup_context_menu(self):
        """Настраивает контекстное меню для tksheet."""

        try:
            mt = self.sheet.MT
            mt.empty_rc_popup_menu = True
            mt.extra_rc_func = self._on_right_click
            mt.extra_table_rc_menu_funcs = {
                "📋 Вся ячейка → Поле 1": {
                    "command": lambda: self.send_full_cell(1)
                },
                "📋 Вся ячейка → Поле 2": {
                    "command": lambda: self.send_full_cell(2)
                },
            }

            logger.debug("Контекстное меню Excel-таблицы настроено")

        except Exception:
            logger.exception("Ошибка при настройке контекстного меню Excel")

    def _on_right_click(self, event_dict):
        """
        Срабатывает при правом клике по таблице.

        Перед открытием контекстного меню обновляем информацию
        о текущей выбранной ячейке.
        """

        self.on_cell_select()
        return None

    # =========================================================
    # ЗАГРУЗКА EXCEL
    # =========================================================

    def load_excel(self):
        """
        Загружает Excel-файл.

        GUI отвечает только за:
        - выбор файла;
        - показ ошибок;
        - обновление выпадающего списка листов.

        Работа с pandas находится в ExcelService.
        """

        file_path = filedialog.askopenfilename(
            filetypes=[("Excel Files", "*.xlsx *.xls")]
        )

        if not file_path:
            return

        result = self.excel_service.load_workbook_info(file_path)

        if not result.success:
            self._handle_excel_load_error(result.error_message)
            return

        self.current_excel_path = result.file_path
        self.sheet_names = result.sheet_names

        self._save_excel_path_to_state(result.file_path)
        self._enable_sheet_selector()

        first_sheet = self.sheet_names[0]
        self.sheet_var.set(first_sheet)
        self.load_selected_sheet(first_sheet)

        logger.info(
            "Excel-файл загружен в интерфейс: %s. Листы: %s",
            result.file_path,
            result.sheet_names
        )

    def _handle_excel_load_error(self, error_message):
        """
        Показывает ошибку загрузки Excel-файла.
        """

        logger.warning("Excel-файл не загружен: %s", error_message)

        messagebox.showerror(
            "Ошибка Excel",
            f"Не удалось загрузить Excel-файл.\n\n{error_message}"
        )

    def _save_excel_path_to_state(self, file_path):
        """Сохраняет путь к Excel-файлу через AppController."""

        if hasattr(self.master, "controller"):
            self.master.controller.set_current_excel(file_path)

    def _enable_sheet_selector(self):
        """Активирует выпадающий список листов."""

        self.sheet_menu.configure(
            values=self.sheet_names,
            state="normal"
        )

    def load_selected_sheet(self, sheet_name=None):
        """
        Загружает выбранный лист Excel в таблицу.

        Вызывается:
        - автоматически после загрузки файла;
        - при выборе другого листа в выпадающем списке.
        """

        if sheet_name is None:
            sheet_name = self.sheet_var.get()

        if not self.current_excel_path:
            return

        if not sheet_name or sheet_name == self.DEFAULT_SHEET_TEXT:
            return

        result = self.excel_service.load_sheet(
            excel_path=self.current_excel_path,
            sheet_name=sheet_name
        )

        if not result.success:
            self._handle_sheet_load_error(
                sheet_name=sheet_name,
                error_message=result.error_message
            )
            return

        self.current_sheet_name = result.sheet_name
        self.df = result.dataframe

        self._save_sheet_name_to_state(result.sheet_name)
        self._display_sheet_data(
            data=result.data,
            headers=result.headers,
            is_empty=result.is_empty
        )

        logger.info(
            "Excel-лист загружен в интерфейс: %s. Строк: %s, столбцов: %s",
            result.sheet_name,
            result.row_count,
            result.column_count
        )

    def _handle_sheet_load_error(self, sheet_name, error_message):
        """
        Показывает ошибку загрузки листа Excel.
        """

        logger.warning(
            "Excel-лист не загружен. sheet=%s, error=%s",
            sheet_name,
            error_message
        )

        messagebox.showerror(
            "Ошибка листа",
            (
                f"Не удалось загрузить лист: {sheet_name}\n\n"
                f"{error_message}"
            )
        )

    def _save_sheet_name_to_state(self, sheet_name):
        """Сохраняет текущий лист через AppController."""

        if (
                hasattr(self.master, "controller")
                and hasattr(self.master.controller, "set_current_excel_sheet")
        ):
            self.master.controller.set_current_excel_sheet(sheet_name)

    # =========================================================
    # ОТОБРАЖЕНИЕ ДАННЫХ
    # =========================================================

    def _display_sheet_data(self, data, headers, is_empty=False):
        """
        Отображает данные листа в tksheet.

        Данные уже подготовлены ExcelService.
        GUI только показывает их.
        """

        self._reset_current_cell()

        if is_empty:
            self._show_empty_table(header="Пустой лист")
            messagebox.showinfo(
                "Пустой лист",
                f"Лист '{self.current_sheet_name}' пустой."
            )
            return

        if not data:
            self._show_empty_table(header="")
            return

        self.sheet.set_sheet_data(data)
        self.sheet.headers(headers)
        self.sheet.set_all_column_widths()

        self.after(100, self._setup_context_menu)

    def _show_empty_table(self, header):
        """Показывает пустую таблицу."""

        self.sheet.set_sheet_data([[""]])
        self.sheet.headers([header])
        self.sheet.set_all_column_widths()
        self.after(100, self._setup_context_menu)

    def _reset_current_cell(self):
        """Сбрасывает информацию о выбранной ячейке."""

        self.current_cell_value = ""
        self.current_row = None
        self.current_col = None

    # =========================================================
    # ВЫБОР И РЕДАКТИРОВАНИЕ ЯЧЕЙКИ
    # =========================================================

    def on_cell_select(self, event=None):
        """Срабатывает при выделении ячейки."""

        try:
            selected = self.sheet.get_selected_cells()

            if not selected:
                return

            selected_list = list(selected)
            row, col = selected_list[-1]

            value = self.sheet.get_cell_data(row, col)

            self.current_cell_value = str(value) if value is not None else ""
            self.current_row = row
            self.current_col = col

            self._save_current_cell_to_state()

        except Exception:
            logger.exception("Ошибка при выборе Excel-ячейки")

    def _save_current_cell_to_state(self):
        """Сохраняет выбранную ячейку через AppController."""

        if not hasattr(self.master, "controller"):
            return

        if self.current_row is None or self.current_col is None:
            return

        self.master.controller.set_current_excel_cell(
            row=self.current_row,
            col=self.current_col,
            value=self.current_cell_value
        )

    def on_double_click(self, event=None):
        """
        Двойной клик по ячейке открывает окно редактирования.
        """

        self.on_cell_select()

        if self.current_row is None or self.current_col is None:
            messagebox.showwarning(
                "Ячейка не выбрана",
                "Сначала выберите ячейку."
            )
            return

        if self.edit_window is not None and self.edit_window.winfo_exists():
            self.edit_window.focus()
            return

        self.edit_window = CellEditWindow(
            parent=self,
            cell_value=self.current_cell_value,
            row=self.current_row,
            col=self.current_col,
            on_close=self._on_edit_window_close
        )

    def _on_edit_window_close(self, new_value):
        """
        Вызывается при закрытии окна редактирования.

        Если пользователь сохранил изменения,
        обновляем DataFrame, tksheet и AppState.
        """

        if (
            new_value is not None
            and self.df is not None
            and self.current_row is not None
            and self.current_col is not None
        ):
            self.df.iloc[self.current_row, self.current_col] = new_value
            self.sheet.set_cell_data(self.current_row, self.current_col, new_value)

            self.current_cell_value = new_value
            self._save_current_cell_to_state()

            logger.info(
                "Excel-ячейка обновлена. row=%s, col=%s, value_length=%s",
                self.current_row,
                self.current_col,
                len(new_value)
            )

        self.edit_window = None

    # =========================================================
    # ОТПРАВКА В СРАВНЕНИЕ
    # =========================================================

    def send_full_cell(self, field_num):
        """
        Отправляет всю выбранную ячейку в поле сравнения.
        """

        self.on_cell_select()

        if not self.current_cell_value:
            messagebox.showwarning(
                "Ячейка не выбрана",
                "Выберите ячейку с текстом."
            )
            logger.warning("Попытка отправить пустую Excel-ячейку в сравнение")
            return

        self._send_text_to_compare(
            text=self.current_cell_value,
            field_num=field_num
        )

    def _send_text_to_compare(self, text, field_num):
        """
        Отправляет текст в поле сравнения через AppController.
        """

        if not hasattr(self.master, "controller"):
            logger.warning("AppController не найден. Текст из Excel не отправлен.")
            return

        self.master.controller.send_text_to_compare(
            text=text,
            field_num=field_num,
            source="excel"
        )

        logger.info(
            "Текст из Excel отправлен в поле сравнения %s. Длина: %s",
            field_num,
            len(text)
        )

    # =========================================================
    # МАСШТАБ
    # =========================================================

    def zoom_in(self):
        """Увеличивает масштаб таблицы."""

        self.sheet.zoom_in()
        self.btn_zoom_reset.configure(text="Zoom")

    def zoom_out(self):
        """Уменьшает масштаб таблицы."""

        self.sheet.zoom_out()
        self.btn_zoom_reset.configure(text="Zoom")

    def zoom_reset(self):
        """Сбрасывает масштаб таблицы."""

        self.sheet.font(("Arial", 11, ""))
        self.sheet.header_font(("Arial", 11, "bold"))
        self.sheet.set_all_column_widths()
        self.btn_zoom_reset.configure(text="100%")


class CellEditWindow(ctk.CTkToplevel):
    """
    Окно просмотра/редактирования Excel-ячейки.

    Позволяет:
    - просмотреть полный текст ячейки;
    - отредактировать текст;
    - отправить весь текст или выделенный фрагмент в сравнение.
    """

    def __init__(self, parent, cell_value, row, col, on_close):
        super().__init__(parent)

        self.parent_frame = parent
        self.on_close_callback = on_close
        self.row = row
        self.col = col

        self._configure_window()
        self._create_widgets(cell_value)
        self._create_context_menu()
        self._bind_events()

    # =========================================================
    # СОЗДАНИЕ ОКНА
    # =========================================================

    def _configure_window(self):
        """Настраивает окно."""

        self.title(f"Редактирование ячейки [{self.row}, {self.col}]")
        self.geometry("500x400")
        self.resizable(True, True)

        self.transient(self.parent_frame.master)
        self.grab_set()

    def _create_widgets(self, cell_value):
        """Создаёт элементы окна."""

        self.title_label = ctk.CTkLabel(
            self,
            text=f"Ячейка [{self.row}, {self.col}]",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.title_label.pack(pady=(10, 5))

        self.textbox = ctk.CTkTextbox(
            self,
            wrap="word",
            font=ctk.CTkFont(size=14),
            undo=True
        )
        self.textbox.pack(fill="both", expand=True, padx=10, pady=10)
        self.textbox.insert("1.0", cell_value)

        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.btn_save = ctk.CTkButton(
            self.button_frame,
            text="💾 Сохранить и закрыть",
            command=self._save_and_close,
            width=150
        )
        self.btn_save.pack(side="left", padx=5, pady=5)

        self.btn_cancel = ctk.CTkButton(
            self.button_frame,
            text="❌ Отмена",
            command=self._cancel_and_close,
            width=150
        )
        self.btn_cancel.pack(side="right", padx=5, pady=5)

        self.textbox.focus()

    def _create_context_menu(self):
        """Создаёт контекстное меню текстового поля."""

        self.context_menu = Menu(self, tearoff=0)

        self.context_menu.add_command(
            label="➕ Выделенный текст → Поле 1",
            command=lambda: self._send_selected_text(1)
        )
        self.context_menu.add_command(
            label="➕ Выделенный текст → Поле 2",
            command=lambda: self._send_selected_text(2)
        )

        self.context_menu.add_separator()

        self.context_menu.add_command(
            label="📋 Вся ячейка → Поле 1",
            command=lambda: self._send_full_text(1)
        )
        self.context_menu.add_command(
            label="📋 Вся ячейка → Поле 2",
            command=lambda: self._send_full_text(2)
        )

    def _bind_events(self):
        """Привязывает события окна."""

        self.textbox.bind("<Button-3>", self._show_context_menu)
        self.protocol("WM_DELETE_WINDOW", self._save_and_close)

    # =========================================================
    # КОНТЕКСТНОЕ МЕНЮ
    # =========================================================

    def _show_context_menu(self, event):
        """Показывает контекстное меню."""

        try:
            self.context_menu.post(event.x_root, event.y_root)
        except Exception:
            logger.exception("Ошибка при открытии контекстного меню ячейки")

    # =========================================================
    # ОТПРАВКА ТЕКСТА В СРАВНЕНИЕ
    # =========================================================

    def _send_selected_text(self, field_num):
        """Отправляет выделенный текст в поле сравнения."""

        try:
            selected_text = self.textbox.get("sel.first", "sel.last").strip()
        except tk.TclError:
            selected_text = ""

        if not selected_text:
            messagebox.showwarning(
                "Текст не выделен",
                "Сначала выделите текст."
            )
            logger.warning("Попытка отправить невыделенный текст из Excel-ячейки")
            return

        self.parent_frame._send_text_to_compare(
            text=selected_text,
            field_num=field_num
        )

    def _send_full_text(self, field_num):
        """Отправляет весь текст ячейки в поле сравнения."""

        full_text = self.textbox.get("1.0", "end-1c").strip()

        if not full_text:
            messagebox.showwarning(
                "Текст пуст",
                "В ячейке нет текста для отправки."
            )
            logger.warning("Попытка отправить пустой текст из окна Excel-ячейки")
            return

        self.parent_frame._send_text_to_compare(
            text=full_text,
            field_num=field_num
        )

    # =========================================================
    # СОХРАНЕНИЕ / ЗАКРЫТИЕ
    # =========================================================

    def _save_and_close(self):
        """Сохраняет изменения и закрывает окно."""

        new_value = self.textbox.get("1.0", "end-1c")

        self.grab_release()
        self.destroy()
        self.on_close_callback(new_value)

    def _cancel_and_close(self):
        """Закрывает окно без сохранения."""

        self.grab_release()
        self.destroy()
        self.on_close_callback(None)