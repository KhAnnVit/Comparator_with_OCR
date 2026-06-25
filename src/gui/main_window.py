import customtkinter as ctk
import tkinter as tk
from src.gui.pdf_window import PDFViewerFrame
from src.gui.ocr_window import OCRViewerFrame
from src.gui.compare_window import CompareSection
from src.gui.excel_window import ExcelViewerFrame
# Базовые настройки интерфейса
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    """Главный класс приложения"""

    def __init__(self):
        super().__init__()
        self.title("PDF & Excel Data Reconciliator")
        self.geometry("1200x750")  # Увеличили размер окна

        # Настройка сетки (Слева - меню, Справа - контент)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- Боковая панель навигации ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)  # Изменили на 5

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Меню",
                                       font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_tab1 = ctk.CTkButton(self.sidebar_frame, text="1. Просмотр PDF",
                                      command=lambda: self.select_frame("tab1"))
        self.btn_tab1.grid(row=1, column=0, padx=20, pady=10)

        self.btn_tab2 = ctk.CTkButton(self.sidebar_frame, text="2. Распознавание",
                                      command=lambda: self.select_frame("tab2"))
        self.btn_tab2.grid(row=2, column=0, padx=20, pady=10)

        self.btn_tab3 = ctk.CTkButton(self.sidebar_frame, text="3. Сравнение",
                                      command=lambda: self.select_frame("tab3"))
        self.btn_tab3.grid(row=3, column=0, padx=20, pady=10)

        # --- НОВАЯ КНОПКА ДЛЯ EXCEL ---
        self.btn_tab4 = ctk.CTkButton(self.sidebar_frame, text="4. Просмотр Excel",
                                      command=lambda: self.select_frame("tab4"))
        self.btn_tab4.grid(row=4, column=0, padx=20, pady=10)

        # --- Фреймы (Разделы) ---
        self.frames = {}

        self.frames["tab1"] = PDFViewerFrame(self)
        self.frames["tab2"] = OCRViewerFrame(self)
        self.frames["tab3"] = CompareSection(self)
        self.frames["tab4"] = ExcelViewerFrame(self)  # Новый раздел

        # --- ГЛОБАЛЬНЫЕ ГОРЯЧИЕ КЛАВИШИ ---
        self.bind_all("<<Copy>>", self._global_copy)
        self.bind_all("<<Paste>>", self._global_paste)
        self.bind_all("<<SelectAll>>", self._global_select_all)

        # Открываем первый раздел по умолчанию
        self.select_frame("tab1")

    def select_frame(self, name):
        # Скрываем все фреймы
        for frame in self.frames.values():
            frame.grid_forget()
        # Показываем нужный
        self.frames[name].grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

    def _global_copy(self, event):
        """Глобальный обработчик копирования"""
        widget = self.focus_get()
        if not widget:
            return

        if isinstance(widget, (tk.Text, ctk.CTkTextbox)):
            try:
                selected_text = widget.get("sel.first", "sel.last")
                self.clipboard_clear()
                self.clipboard_append(selected_text)
            except tk.TclError:
                pass

    def _global_paste(self, event):
        """Глобальный обработчик вставки"""
        widget = self.focus_get()
        if not widget:
            return

        if isinstance(widget, (tk.Text, ctk.CTkTextbox)):
            try:
                clipboard_text = self.clipboard_get()
                try:
                    widget.delete("sel.first", "sel.last")
                except tk.TclError:
                    pass
                widget.insert("insert", clipboard_text)
            except tk.TclError:
                pass

    def _global_select_all(self, event):
        """Глобальный обработчик выделения всего"""
        widget = self.focus_get()
        if not widget:
            return

        if isinstance(widget, (tk.Text, ctk.CTkTextbox)):
            widget.tag_add("sel", "1.0", "end")