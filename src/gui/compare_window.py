import customtkinter as ctk
import tkinter as tk
from tkinter import Menu
import difflib
import string
from collections import Counter

from src.utils.logger import logger

class CompareSection(ctk.CTkFrame):
    """
    Третий раздел приложения: сравнение двух текстов.

    Главное отличие от старой версии:
    сравнение выполняется не напрямую по исходному тексту, а по нормализованной
    версии текста. Благодаря этому можно игнорировать пробелы, переносы строк,
    регистр и пунктуацию, но подсветка всё равно ставится в исходных полях.
    """

    def __init__(self, master):
        super().__init__(master)

        # row=0 — заголовок
        # row=1 — панель настроек сравнения
        # row=2 — два текстовых поля
        # row=3 — нижняя панель с кнопками
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure((0, 1), weight=1)

        # Переменная для хранения активного текстового поля.
        # Она нужна для контекстного меню: копировать/вставить/выделить всё.
        self.active_textbox = None

        self._create_variables()
        self._create_widgets()
        self._configure_tags()
        self._create_context_menu()
        self._bind_events()

        self.active_textbox = self.left_textbox

    # =========================================================
    # ПЕРЕМЕННЫЕ НАСТРОЕК СРАВНЕНИЯ
    # =========================================================

    def _create_variables(self):
        """Создаёт переменные для чекбоксов настроек сравнения."""

        # По умолчанию пробелы, табы и переносы строк НЕ учитываются.
        # Это главный режим для OCR, потому что OCR часто ошибается именно
        # в пробелах и переносах.
        self.ignore_whitespace_var = tk.BooleanVar(value=True)

        # По умолчанию регистр НЕ учитывается:
        # "Молоко" и "молоко" будут считаться одинаковыми.
        self.case_sensitive_var = tk.BooleanVar(value=False)

        # По умолчанию пунктуация учитывается.
        # Если включить чекбокс, то точки, запятые, кавычки и т.д. будут игнорироваться.
        self.ignore_punctuation_var = tk.BooleanVar(value=False)

        # По умолчанию подсвечиваем только различия.
        # Совпадения можно включить отдельно, если нужно видеть всю карту совпадений.
        self.show_matches_var = tk.BooleanVar(value=False)

    # =========================================================
    # СОЗДАНИЕ ИНТЕРФЕЙСА
    # =========================================================

    def _create_widgets(self):
        """Создаёт визуальные элементы раздела сравнения."""

        # ---------- Заголовок ----------
        self.title_label = ctk.CTkLabel(
            self,
            text="Сравнение текстов",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.title_label.grid(row=0, column=0, columnspan=2, pady=(10, 5))

        # ---------- Панель настроек ----------
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=10,
            pady=(0, 5)
        )

        self.settings_frame.grid_columnconfigure(5, weight=1)

        self.ignore_whitespace_checkbox = ctk.CTkCheckBox(
            self.settings_frame,
            text="Игнорировать пробелы и переносы",
            variable=self.ignore_whitespace_var,
            command=self.clear_highlights
        )
        self.ignore_whitespace_checkbox.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.case_sensitive_checkbox = ctk.CTkCheckBox(
            self.settings_frame,
            text="Учитывать регистр",
            variable=self.case_sensitive_var,
            command=self.clear_highlights
        )
        self.case_sensitive_checkbox.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        self.ignore_punctuation_checkbox = ctk.CTkCheckBox(
            self.settings_frame,
            text="Игнорировать пунктуацию",
            variable=self.ignore_punctuation_var,
            command=self.clear_highlights
        )
        self.ignore_punctuation_checkbox.grid(row=0, column=2, padx=10, pady=10, sticky="w")

        self.show_matches_checkbox = ctk.CTkCheckBox(
            self.settings_frame,
            text="Подсвечивать совпадения",
            variable=self.show_matches_var,
            command=self.clear_highlights
        )
        self.show_matches_checkbox.grid(row=0, column=3, padx=10, pady=10, sticky="w")

        self.btn_clear = ctk.CTkButton(
            self.settings_frame,
            text="Очистить подсветку",
            command=self.clear_highlights,
            width=150
        )
        self.btn_clear.grid(row=0, column=4, padx=10, pady=10, sticky="e")

        # ---------- Левое текстовое поле ----------
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=2, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.left_frame.grid_rowconfigure(1, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        self.left_label = ctk.CTkLabel(
            self.left_frame,
            text="Текст 1",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.left_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))

        self.left_textbox = tk.Text(
            self.left_frame,
            wrap="word",
            font=("Consolas", 12),
            undo=True,
            padx=10,
            pady=10
        )
        self.left_textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.left_scrollbar = ctk.CTkScrollbar(
            self.left_frame,
            command=self.left_textbox.yview
        )
        self.left_scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 10))
        self.left_textbox.configure(yscrollcommand=self.left_scrollbar.set)

        # ---------- Правое текстовое поле ----------
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=2, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.right_label = ctk.CTkLabel(
            self.right_frame,
            text="Текст 2",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.right_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))

        self.right_textbox = tk.Text(
            self.right_frame,
            wrap="word",
            font=("Consolas", 12),
            undo=True,
            padx=10,
            pady=10
        )
        self.right_textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.right_scrollbar = ctk.CTkScrollbar(
            self.right_frame,
            command=self.right_textbox.yview
        )
        self.right_scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 10))
        self.right_textbox.configure(yscrollcommand=self.right_scrollbar.set)

        # ---------- Нижняя панель ----------
        self.bottom_panel = ctk.CTkFrame(self)
        self.bottom_panel.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        self.bottom_panel.grid_columnconfigure(0, weight=1)

        self.btn_compare = ctk.CTkButton(
            self.bottom_panel,
            text="Сравнить",
            command=self.compare_texts,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        self.btn_compare.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 5))

        self.result_label = ctk.CTkLabel(
            self.bottom_panel,
            text="Настройки по умолчанию: пробелы и переносы игнорируются, регистр не учитывается.",
            anchor="w"
        )
        self.result_label.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))

    # =========================================================
    # НАСТРОЙКА ПОДСВЕТКИ
    # =========================================================

    def _configure_tags(self):
        """Настраивает теги подсветки для обоих текстовых полей."""

        for textbox in (self.left_textbox, self.right_textbox):
            # Совпадения подсвечиваются зелёным только если включён чекбокс.
            textbox.tag_configure("match", foreground="green")

            # Различия подсвечиваются красным.
            textbox.tag_configure("diff", foreground="red", background="#ffcccc")

    def clear_highlights(self):
        """Удаляет старую подсветку из обоих текстовых полей."""

        for textbox in (self.left_textbox, self.right_textbox):
            textbox.tag_remove("match", "1.0", "end")
            textbox.tag_remove("diff", "1.0", "end")

        self.result_label.configure(text="Подсветка очищена. Нажмите «Сравнить», чтобы применить настройки.")

    # =========================================================
    # КОНТЕКСТНОЕ МЕНЮ
    # =========================================================

    def _create_context_menu(self):
        """Создаёт контекстное меню для текстовых полей."""

        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.add_command(label="Копировать", command=self.copy_text)
        self.context_menu.add_command(label="Вставить", command=self.paste_text)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Выделить всё", command=self.select_all)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Очистить подсветку", command=self.clear_highlights)

    def _bind_events(self):
        """Привязывает события к текстовым полям."""

        for textbox in (self.left_textbox, self.right_textbox):
            textbox.bind("<Button-3>", self.show_context_menu)
            textbox.bind("<Button-1>", lambda event, tb=textbox: self.set_active_textbox(tb))
            textbox.bind("<FocusIn>", lambda event, tb=textbox: self.set_active_textbox(tb))

            # Локальные горячие клавиши. Даже если есть глобальные бинды в App,
            # эти обработчики делают CompareSection более самостоятельным.
            textbox.bind("<Control-a>", self._hotkey_select_all)
            textbox.bind("<Control-A>", self._hotkey_select_all)

    def set_active_textbox(self, textbox):
        """Запоминает, с каким текстовым полем сейчас работает пользователь."""
        self.active_textbox = textbox

    def show_context_menu(self, event):
        """Показывает контекстное меню и запоминает активное поле."""

        self.active_textbox = event.widget

        try:
            self.context_menu.post(event.x_root, event.y_root)
        except tk.TclError:
            pass

    def copy_text(self):
        """Копирует выделенный текст в буфер обмена."""

        if self.active_textbox is None:
            return

        try:
            selected_text = self.active_textbox.get("sel.first", "sel.last")
            self.master.clipboard_clear()
            self.master.clipboard_append(selected_text)
        except tk.TclError:
            pass

    def paste_text(self):
        """Вставляет текст из буфера обмена в активное поле."""

        if self.active_textbox is None:
            return

        try:
            clipboard_text = self.master.clipboard_get()

            try:
                self.active_textbox.delete("sel.first", "sel.last")
            except tk.TclError:
                pass

            self.active_textbox.insert("insert", clipboard_text)
            self.clear_highlights()

        except tk.TclError:
            pass

    def select_all(self):
        """Выделяет весь текст в активном поле."""

        if self.active_textbox is None:
            return

        self.active_textbox.focus_set()
        self.active_textbox.tag_add("sel", "1.0", "end-1c")
        self.active_textbox.mark_set("insert", "1.0")
        self.active_textbox.see("insert")

    def _hotkey_select_all(self, event):
        """Обработчик Ctrl+A для текстовых полей."""

        self.active_textbox = event.widget
        self.select_all()
        return "break"

    # =========================================================
    # НОРМАЛИЗАЦИЯ ТЕКСТА
    # =========================================================

    def _is_punctuation(self, char):
        """
        Проверяет, является ли символ пунктуацией.

        string.punctuation покрывает английские символы.
        extra_punctuation добавляет русские кавычки, длинное тире, многоточие и №.
        """

        extra_punctuation = "«»“”„…—–№"
        return char in string.punctuation or char in extra_punctuation

    def _normalize_text_with_map(self, text):
        """
        Нормализует текст для сравнения и строит карту индексов.

        Возвращает:
        - normalized_text: текст, по которому реально идёт сравнение;
        - index_map: список, где каждый символ normalized_text связан
          с индексом символа в исходном тексте.

        Пример:
            исходный текст: "А Б\nВ"
            игнорируем пробелы и переносы
            normalized_text: "абв"  # если регистр не учитывается
            index_map: [0, 2, 4]

        Эта карта нужна, чтобы после сравнения подсветить символы
        именно в исходном Text widget, а не в нормализованной строке.
        """

        normalized_chars = []
        index_map = []

        ignore_whitespace = self.ignore_whitespace_var.get()
        case_sensitive = self.case_sensitive_var.get()
        ignore_punctuation = self.ignore_punctuation_var.get()

        for original_index, char in enumerate(text):
            # Пробелы, табы, переносы строк и другие whitespace-символы.
            if ignore_whitespace and char.isspace():
                continue

            # Пунктуация: . , ! ? " и т.д.
            if ignore_punctuation and self._is_punctuation(char):
                continue

            # Если регистр не учитывается, приводим символ к нижнему регистру.
            compare_char = char if case_sensitive else char.lower()

            normalized_chars.append(compare_char)
            index_map.append(original_index)

        return "".join(normalized_chars), index_map

    # =========================================================
    # СРАВНЕНИЕ И ПОДСВЕТКА
    # =========================================================

    def compare_texts(self):
        """
        Сравнивает два текста с учётом выбранных настроек.

        Важно:
        - пробелы и переносы строк по умолчанию игнорируются;
        - подсветка ставится на исходный текст;
        - если различаются только пробелы/переносы, различий не будет.
        """

        self.clear_highlights()

        text1 = self.left_textbox.get("1.0", "end-1c")
        text2 = self.right_textbox.get("1.0", "end-1c")

        if not text1 and not text2:
            self.result_label.configure(text="Оба поля пустые.")
            return

        if not text1 or not text2:
            self.result_label.configure(text="Одно из полей пустое. Сравнение невозможно.")
            return

        normalized_1, map_1 = self._normalize_text_with_map(text1)
        normalized_2, map_2 = self._normalize_text_with_map(text2)

        if not normalized_1 and not normalized_2:
            self.result_label.configure(
                text="После применения настроек оба текста стали пустыми. Проверьте настройки сравнения."
            )
            return

        matcher = difflib.SequenceMatcher(
            None,
            normalized_1,
            normalized_2,
            autojunk=False
        )

        diff_blocks_count = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                if self.show_matches_var.get():
                    self._add_tag_by_normalized_range(self.left_textbox, map_1, i1, i2, "match")
                    self._add_tag_by_normalized_range(self.right_textbox, map_2, j1, j2, "match")

            elif tag in ("replace", "delete", "insert"):
                diff_blocks_count += 1

                if tag in ("replace", "delete"):
                    self._add_tag_by_normalized_range(self.left_textbox, map_1, i1, i2, "diff")

                if tag in ("replace", "insert"):
                    self._add_tag_by_normalized_range(self.right_textbox, map_2, j1, j2, "diff")

        if diff_blocks_count == 0:
            self.result_label.configure(text="Различий не найдено с текущими настройками сравнения.")
        else:
            self.result_label.configure(
                text=f"Найдено блоков различий: {diff_blocks_count}. "
                     f"Пробелы/переносы {'игнорируются' if self.ignore_whitespace_var.get() else 'учитываются'}, "
                     f"регистр {'учитывается' if self.case_sensitive_var.get() else 'не учитывается'}."
            )

        logger.info(
            "Сравнение завершено. diff_blocks=%s, len1=%s, len2=%s, normalized_len1=%s, normalized_len2=%s",
            diff_blocks_count,
            len(text1),
            len(text2),
            len(normalized_1),
            len(normalized_2)
        )

    def _add_tag_by_normalized_range(self, textbox, index_map, start, end, tag_name):
        """
        Добавляет тег подсветки на исходный Text widget по диапазону
        нормализованной строки.

        Почему нельзя просто подсветить от start до end:
        нормализованная строка может не содержать пробелов и переносов.
        Поэтому мы используем index_map и подсвечиваем только реальные символы,
        которые участвовали в сравнении.
        """

        if start >= end:
            return

        original_indices = index_map[start:end]

        if not original_indices:
            return

        # Группируем соседние индексы, чтобы не делать tag_add для каждого символа отдельно.
        group_start = original_indices[0]
        previous_index = original_indices[0]

        for current_index in original_indices[1:]:
            if current_index == previous_index + 1:
                previous_index = current_index
                continue

            self._add_text_tag(textbox, group_start, previous_index + 1, tag_name)
            group_start = current_index
            previous_index = current_index

        self._add_text_tag(textbox, group_start, previous_index + 1, tag_name)

    def _add_text_tag(self, textbox, start_char_index, end_char_index, tag_name):
        """Добавляет тег в tk.Text по символьным индексам исходного текста."""

        textbox.tag_add(
            tag_name,
            f"1.0+{start_char_index}c",
            f"1.0+{end_char_index}c"
        )

    # =========================================================
    # МЕТОДЫ ДЛЯ ДРУГИХ РАЗДЕЛОВ ПРИЛОЖЕНИЯ
    # =========================================================

    def set_text_left(self, text):
        """Устанавливает текст в левое поле сравнения."""

        self.left_textbox.delete("1.0", "end")
        self.left_textbox.insert("1.0", text)
        self.clear_highlights()

    def set_text_right(self, text):
        """Устанавливает текст в правое поле сравнения."""

        self.right_textbox.delete("1.0", "end")
        self.right_textbox.insert("1.0", text)
        self.clear_highlights()
