import pandas as pd
import tkinter as tk
from tkinter import Menu, filedialog
import customtkinter as ctk
from tksheet import Sheet


class ExcelViewerFrame(ctk.CTkFrame):
    """Класс четвертого раздела: Просмотр и выделение данных из Excel"""

    def __init__(self, master):
        super().__init__(master)

        # --- Прокси для bind_all ---
        self.bind_all = self._bind_all_proxy
        self.unbind_all = self._unbind_all_proxy

        # Настраиваем сетку
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Переменные ---
        self.df = None
        self.current_cell_value = ""
        self.current_row = None
        self.current_col = None
        self.edit_window = None  # Ссылка на окно редактирования

        # --- Верхняя панель кнопок ---
        self.top_panel = ctk.CTkFrame(self, height=40)
        self.top_panel.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        self.btn_load = ctk.CTkButton(self.top_panel, text="Загрузить Excel",
                                      command=self.load_excel, width=150)
        self.btn_load.pack(side="left", padx=5, pady=5)

        self.btn_zoom_in = ctk.CTkButton(self.top_panel, text="➕",
                                         command=self.zoom_in, width=40)
        self.btn_zoom_in.pack(side="left", padx=5, pady=5)

        self.btn_zoom_out = ctk.CTkButton(self.top_panel, text="",
                                          command=self.zoom_out, width=40)
        self.btn_zoom_out.pack(side="left", padx=5, pady=5)

        self.btn_zoom_reset = ctk.CTkButton(self.top_panel, text="100%",
                                            command=self.zoom_reset, width=60)
        self.btn_zoom_reset.pack(side="left", padx=5, pady=5)

        # --- Контейнер для таблицы ---
        self.table_container = tk.Frame(self, bg="#2b2b2b")
        self.table_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.table_container.grid_rowconfigure(0, weight=1)
        self.table_container.grid_columnconfigure(0, weight=1)

        # --- Создаём Sheet ---
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

        # --- ВКЛЮЧАЕМ BINDINGS (БЕЗ edit_cell!) ---
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

        # --- Настраиваем контекстное меню для режима просмотра ---
        self._setup_context_menu()

        # --- Привязываем события ---
        self.sheet.bind("<<SheetSelect>>", self.on_cell_select)
        self.sheet.bind("<Double-Button-1>", self.on_double_click)  # Двойной клик — наше окно

    def _bind_all_proxy(self, *args, **kwargs):
        return tk.Frame.bind_all(self, *args, **kwargs)

    def _unbind_all_proxy(self, *args, **kwargs):
        return tk.Frame.unbind_all(self, *args, **kwargs)

    def _setup_context_menu(self):
        """Настраивает контекстное меню для режима просмотра"""
        MT = self.sheet.MT
        MT.empty_rc_popup_menu = True
        MT.extra_rc_func = self._on_right_click
        MT.extra_table_rc_menu_funcs = {
            "📋 Вся ячейка → Поле 1": {
                "command": lambda: self.send_full_cell(1)
            },
            "📋 Вся ячейка → Поле 2": {
                "command": lambda: self.send_full_cell(2)
            },
        }
        print("✅ Контекстное меню настроено")

    def _on_right_click(self, event_dict):
        """Callback при правом клике в режиме просмотра"""
        self.on_cell_select()
        return None

    def on_cell_select(self, event=None):
        """Срабатывает при выделении ячейки"""
        try:
            selected = self.sheet.get_selected_cells()
            if selected:
                selected_list = list(selected)
                row, col = selected_list[-1]
                value = self.sheet.get_cell_data(row, col)
                self.current_cell_value = str(value) if value is not None else ""
                self.current_row = row
                self.current_col = col
        except Exception as e:
            print(f"Ошибка on_cell_select: {e}")

    def on_double_click(self, event=None):
        """
        Двойной клик по ячейке — открывает наше окно редактирования.
        """
        self.on_cell_select()

        # Если окно уже открыто — не открываем второе
        if self.edit_window is not None and self.edit_window.winfo_exists():
            self.edit_window.focus()
            return

        # Создаём новое окно редактирования
        self.edit_window = CellEditWindow(
            self,
            cell_value=self.current_cell_value,
            row=self.current_row,
            col=self.current_col,
            on_close=self._on_edit_window_close
        )

    def _on_edit_window_close(self, new_value):
        """
        Вызывается при закрытии окна редактирования.
        Обновляет значение ячейки в таблице.
        """
        if new_value is not None and self.current_row is not None:
            # Обновляем данные в DataFrame
            self.df.iloc[self.current_row, self.current_col] = new_value
            # Обновляем ячейку в tksheet
            self.sheet.set_cell_data(self.current_row, self.current_col, new_value)
            self.current_cell_value = new_value
            print(f"✅ Ячейка обновлена: {new_value[:50]}...")

        self.edit_window = None

    def load_excel(self):
        """Загружает Excel файл"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Excel Files", "*.xlsx *.xls")]
        )

        if not file_path:
            return

        try:
            self.df = pd.read_excel(file_path)

            if self.df.empty:
                print("Файл пуст!")
                return

            data = self.df.values.tolist()

            for row in data:
                for i in range(len(row)):
                    if pd.isna(row[i]):
                        row[i] = ""
                    else:
                        row[i] = str(row[i])

            headers = [str(col) for col in self.df.columns]

            self.sheet.set_sheet_data(data)
            self.sheet.headers(headers)
            self.sheet.set_all_column_widths()

            self.after(100, self._setup_context_menu)

            print(f"✅ Загружено: {len(self.df)} строк, {len(headers)} столбцов")

        except Exception as e:
            print(f"Ошибка при загрузке Excel: {e}")
            import traceback
            traceback.print_exc()

    def zoom_in(self):
        self.sheet.zoom_in()
        self.btn_zoom_reset.configure(text="Zoom")

    def zoom_out(self):
        self.sheet.zoom_out()
        self.btn_zoom_reset.configure(text="Zoom")

    def zoom_reset(self):
        self.sheet.font(("Arial", 11, ""))
        self.sheet.header_font(("Arial", 11, "bold"))
        self.sheet.set_all_column_widths()
        self.btn_zoom_reset.configure(text="100%")

    def send_full_cell(self, field_num):
        """Отправляет всю ячейку в поле сравнения"""
        self.on_cell_select()

        if not self.current_cell_value:
            print("⚠️ Ячейка не выбрана!")
            return

        compare_frame = self.master.frames["tab3"]

        if field_num == 1:
            compare_frame.set_text_left(self.current_cell_value)
        else:
            compare_frame.set_text_right(self.current_cell_value)

        print(f"✅ Отправлена ячейка в Поле {field_num}: {self.current_cell_value[:50]}...")
        self.master.select_frame("tab3")


class CellEditWindow(ctk.CTkToplevel):
    """
    Кастомное окно редактирования ячейки на CustomTkinter.
    Показывает содержимое ячейки и позволяет выделить текст.
    """

    def __init__(self, parent, cell_value, row, col, on_close):
        super().__init__(parent)

        self.parent_frame = parent
        self.on_close_callback = on_close
        self.row = row
        self.col = col

        # Настройки окна
        self.title(f"Редактирование ячейки [{row}, {col}]")
        self.geometry("500x400")
        self.resizable(True, True)

        # Делаем окно модальным (блокирует родительское окно)
        self.transient(parent.master)
        self.grab_set()

        # --- Заголовок ---
        self.title_label = ctk.CTkLabel(
            self,
            text=f"Ячейка [{row}, {col}]",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.title_label.pack(pady=(10, 5))

        # --- Текстовое поле ---
        self.textbox = ctk.CTkTextbox(
            self,
            wrap="word",
            font=ctk.CTkFont(size=14),
            undo=True
        )
        self.textbox.pack(fill="both", expand=True, padx=10, pady=10)
        self.textbox.insert("1.0", cell_value)

        # --- Контекстное меню ---
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

        # Привязываем правый клик
        self.textbox.bind("<Button-3>", self._show_context_menu)

        # --- Кнопки ---
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

        # Обработчик закрытия окна (крестик)
        self.protocol("WM_DELETE_WINDOW", self._save_and_close)

        # Фокус на текстовое поле
        self.textbox.focus()

    def _show_context_menu(self, event):
        """Показывает контекстное меню"""
        try:
            self.context_menu.post(event.x_root, event.y_root)
        except Exception:
            pass

    def _send_selected_text(self, field_num):
        """Отправляет выделенный текст в поле сравнения"""
        try:
            selected_text = self.textbox.get("sel.first", "sel.last").strip()
            if not selected_text:
                print("⚠️ Текст не выделен!")
                return

            compare_frame = self.parent_frame.master.frames["tab3"]

            if field_num == 1:
                compare_frame.set_text_left(selected_text)
            else:
                compare_frame.set_text_right(selected_text)

            print(f"✅ Отправлен выделенный текст в Поле {field_num}: {selected_text[:50]}...")
            self.parent_frame.master.select_frame("tab3")

        except tk.TclError:
            print("⚠️ Текст не выделен!")

    def _send_full_text(self, field_num):
        """Отправляет весь текст из окна в поле сравнения"""
        full_text = self.textbox.get("1.0", "end-1c").strip()

        if not full_text:
            print("⚠️ Текст пуст!")
            return

        compare_frame = self.parent_frame.master.frames["tab3"]

        if field_num == 1:
            compare_frame.set_text_left(full_text)
        else:
            compare_frame.set_text_right(full_text)

        print(f"✅ Отправлен весь текст в Поле {field_num}: {full_text[:50]}...")
        self.parent_frame.master.select_frame("tab3")

    def _save_and_close(self):
        """Сохраняет изменения и закрывает окно"""
        new_value = self.textbox.get("1.0", "end-1c")
        self.grab_release()
        self.destroy()
        self.on_close_callback(new_value)

    def _cancel_and_close(self):
        """Закрывает окно без сохранения"""
        self.grab_release()
        self.destroy()
        self.on_close_callback(None)