import customtkinter as ctk
import tkinter as tk
from tkinter import Menu
import difflib
import re
import unicodedata
from collections import Counter

from src.utils.logger import logger


class CompareSection(ctk.CTkFrame):
    """
    Третий раздел приложения: сравнение двух текстов.

    Основная идея новой версии:
    - по умолчанию искать самый похожий блок между двумя текстами;
    - не считать лишние блоки до/после найденного участка ошибкой;
    - оставить возможность строгого сравнения всего текста;
    - оставить сравнение без учёта порядка слов;
    - оставить отдельный режим сравнения составов.
    """

    def __init__(self, master):
        super().__init__(master)

        self.active_textbox = None

        self._configure_grid()
        self._create_settings_variables()
        self._create_widgets()
        self._create_context_menu()
        self._configure_text_tags()

    # =========================================================
    # ИНИЦИАЛИЗАЦИЯ
    # =========================================================

    def _configure_grid(self):
        """
        Настраивает главную сетку раздела.
        """

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def _create_settings_variables(self):
        """
        Создаёт переменные настроек сравнения.
        """

        # OCR часто ломает переносы и пробелы, поэтому это включено.
        self.ignore_whitespace_var = tk.BooleanVar(value=True)

        # AQUA и aqua по умолчанию считаем одинаковыми.
        self.case_sensitive_var = tk.BooleanVar(value=False)

        # Пунктуацию по умолчанию не игнорируем.
        # Пользователь может включить это вручную.
        self.ignore_punctuation_var = tk.BooleanVar(value=False)

        # Если включено, слова сравниваются как набор,
        # но внутри найденного похожего блока.
        self.ignore_word_order_var = tk.BooleanVar(value=False)

        # Главное новое поведение:
        # ищем похожий блок, а лишние части текста не считаем ошибками.
        self.find_similar_block_var = tk.BooleanVar(value=True)

        # Совпадения зелёным по умолчанию не подсвечиваем,
        # чтобы экран не был перегружен.
        self.show_matches_var = tk.BooleanVar(value=False)

    # =========================================================
    # СОЗДАНИЕ ИНТЕРФЕЙСА
    # =========================================================

    def _create_widgets(self):
        """
        Создаёт все элементы интерфейса.
        """

        self._create_title()
        self._create_settings_panel()
        self._create_text_fields()
        self._create_bottom_panel()
        self._create_result_label()

    def _create_title(self):
        """
        Создаёт заголовок раздела.
        """

        self.title_label = ctk.CTkLabel(
            self,
            text="Сравнение текстов",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.title_label.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(10, 5)
        )

    def _create_settings_panel(self):
        """
        Создаёт панель настроек сравнения.
        """

        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=10,
            pady=(5, 10)
        )

        for column_index in range(3):
            self.settings_frame.grid_columnconfigure(
                column_index,
                weight=1
            )

        self.ignore_whitespace_checkbox = ctk.CTkCheckBox(
            self.settings_frame,
            text="Игнорировать пробелы и переносы",
            variable=self.ignore_whitespace_var,
            command=self.clear_highlights
        )
        self.ignore_whitespace_checkbox.grid(
            row=0,
            column=0,
            sticky="w",
            padx=12,
            pady=(10, 5)
        )

        self.case_sensitive_checkbox = ctk.CTkCheckBox(
            self.settings_frame,
            text="Учитывать регистр",
            variable=self.case_sensitive_var,
            command=self.clear_highlights
        )
        self.case_sensitive_checkbox.grid(
            row=0,
            column=1,
            sticky="w",
            padx=12,
            pady=(10, 5)
        )

        self.ignore_punctuation_checkbox = ctk.CTkCheckBox(
            self.settings_frame,
            text="Игнорировать пунктуацию",
            variable=self.ignore_punctuation_var,
            command=self.clear_highlights
        )
        self.ignore_punctuation_checkbox.grid(
            row=0,
            column=2,
            sticky="w",
            padx=12,
            pady=(10, 5)
        )

        self.find_similar_block_checkbox = ctk.CTkCheckBox(
            self.settings_frame,
            text="Искать похожий блок",
            variable=self.find_similar_block_var,
            command=self.clear_highlights
        )
        self.find_similar_block_checkbox.grid(
            row=1,
            column=0,
            sticky="w",
            padx=12,
            pady=(5, 5)
        )

        self.ignore_word_order_checkbox = ctk.CTkCheckBox(
            self.settings_frame,
            text="Не учитывать порядок слов",
            variable=self.ignore_word_order_var,
            command=self.clear_highlights
        )
        self.ignore_word_order_checkbox.grid(
            row=1,
            column=1,
            sticky="w",
            padx=12,
            pady=(5, 5)
        )

        self.show_matches_checkbox = ctk.CTkCheckBox(
            self.settings_frame,
            text="Подсвечивать совпадения",
            variable=self.show_matches_var,
            command=self.clear_highlights
        )
        self.show_matches_checkbox.grid(
            row=1,
            column=2,
            sticky="w",
            padx=12,
            pady=(5, 5)
        )

        self.btn_clear_highlights = ctk.CTkButton(
            self.settings_frame,
            text="Очистить подсветку",
            command=self.clear_highlights,
            width=160
        )
        self.btn_clear_highlights.grid(
            row=2,
            column=2,
            sticky="e",
            padx=12,
            pady=(5, 10)
        )

    def _create_text_fields(self):
        """
        Создаёт два текстовых поля.
        """

        self.texts_frame = ctk.CTkFrame(self)
        self.texts_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=10,
            pady=10
        )

        self.texts_frame.grid_rowconfigure(0, weight=1)
        self.texts_frame.grid_columnconfigure(0, weight=1)
        self.texts_frame.grid_columnconfigure(1, weight=1)

        self.left_frame = ctk.CTkFrame(self.texts_frame)
        self.left_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 5)
        )
        self.left_frame.grid_rowconfigure(1, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        self.left_label = ctk.CTkLabel(
            self.left_frame,
            text="Текст 1",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.left_label.grid(
            row=0,
            column=0,
            sticky="w",
            padx=10,
            pady=(10, 5)
        )

        self.left_textbox = tk.Text(
            self.left_frame,
            wrap="word",
            font=("Consolas", 12),
            undo=True,
            padx=10,
            pady=10
        )
        self.left_textbox.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(10, 0),
            pady=(0, 10)
        )

        self.left_scrollbar = ctk.CTkScrollbar(
            self.left_frame,
            command=self.left_textbox.yview
        )
        self.left_scrollbar.grid(
            row=1,
            column=1,
            sticky="ns",
            padx=(0, 10),
            pady=(0, 10)
        )
        self.left_textbox.configure(
            yscrollcommand=self.left_scrollbar.set
        )

        self.right_frame = ctk.CTkFrame(self.texts_frame)
        self.right_frame.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(5, 0)
        )
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.right_label = ctk.CTkLabel(
            self.right_frame,
            text="Текст 2",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.right_label.grid(
            row=0,
            column=0,
            sticky="w",
            padx=10,
            pady=(10, 5)
        )

        self.right_textbox = tk.Text(
            self.right_frame,
            wrap="word",
            font=("Consolas", 12),
            undo=True,
            padx=10,
            pady=10
        )
        self.right_textbox.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(10, 0),
            pady=(0, 10)
        )

        self.right_scrollbar = ctk.CTkScrollbar(
            self.right_frame,
            command=self.right_textbox.yview
        )
        self.right_scrollbar.grid(
            row=1,
            column=1,
            sticky="ns",
            padx=(0, 10),
            pady=(0, 10)
        )
        self.right_textbox.configure(
            yscrollcommand=self.right_scrollbar.set
        )

    def _create_bottom_panel(self):
        """
        Создаёт нижнюю панель с кнопками сравнения.
        """

        self.bottom_panel = ctk.CTkFrame(self)
        self.bottom_panel.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=10,
            pady=(0, 5)
        )

        self.bottom_panel.grid_columnconfigure(0, weight=1)
        self.bottom_panel.grid_columnconfigure(1, weight=1)
        self.bottom_panel.grid_columnconfigure(2, weight=1)

        self.btn_compare = ctk.CTkButton(
            self.bottom_panel,
            text="Сравнить",
            command=self.compare_texts,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        self.btn_compare.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(20, 8),
            pady=10
        )

        self.btn_compare_composition = ctk.CTkButton(
            self.bottom_panel,
            text="Сравнить как состав",
            command=self.compare_as_composition,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        self.btn_compare_composition.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=8,
            pady=10
        )

        self.btn_clear_fields = ctk.CTkButton(
            self.bottom_panel,
            text="Очистить поля",
            command=self.clear_fields,
            height=40
        )
        self.btn_clear_fields.grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(8, 20),
            pady=10
        )

    def _create_result_label(self):
        """
        Создаёт строку результата.
        """

        self.result_label = ctk.CTkLabel(
            self,
            text=(
                "По умолчанию: ищется похожий блок, "
                "лишние части текста не мешают совпадениям."
            ),
            anchor="w"
        )
        self.result_label.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=15,
            pady=(0, 10)
        )

    # =========================================================
    # КОНТЕКСТНОЕ МЕНЮ
    # =========================================================

    def _create_context_menu(self):
        """
        Создаёт контекстное меню для двух текстовых полей.
        """

        self.context_menu = Menu(self, tearoff=0)

        self.context_menu.add_command(
            label="Копировать",
            command=self.copy_text
        )

        self.context_menu.add_command(
            label="Вставить",
            command=self.paste_text
        )

        self.context_menu.add_separator()

        self.context_menu.add_command(
            label="Выделить всё",
            command=self.select_all
        )

        self.left_textbox.bind("<Button-3>", self.show_context_menu)
        self.right_textbox.bind("<Button-3>", self.show_context_menu)

        self.left_textbox.bind(
            "<Button-1>",
            lambda event: self.set_active_textbox(self.left_textbox)
        )
        self.right_textbox.bind(
            "<Button-1>",
            lambda event: self.set_active_textbox(self.right_textbox)
        )

        self.left_textbox.bind(
            "<FocusIn>",
            lambda event: self.set_active_textbox(self.left_textbox)
        )
        self.right_textbox.bind(
            "<FocusIn>",
            lambda event: self.set_active_textbox(self.right_textbox)
        )

        self.active_textbox = self.left_textbox

    def set_active_textbox(self, textbox):
        """
        Запоминает активное текстовое поле.
        """

        self.active_textbox = textbox

    def show_context_menu(self, event):
        """
        Показывает контекстное меню.
        """

        self.active_textbox = event.widget

        try:
            self.context_menu.post(event.x_root, event.y_root)
        except Exception:
            logger.exception("Ошибка при открытии контекстного меню сравнения")

    def copy_text(self):
        """
        Копирует выделенный текст.
        """

        if self.active_textbox is None:
            return

        try:
            selected_text = self.active_textbox.get("sel.first", "sel.last")
            self.master.clipboard_clear()
            self.master.clipboard_append(selected_text)
        except tk.TclError:
            pass

    def paste_text(self):
        """
        Вставляет текст из буфера обмена.
        """

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
        """
        Выделяет весь текст в активном поле.
        """

        if self.active_textbox is None:
            return

        self.active_textbox.focus_set()
        self.active_textbox.tag_add("sel", "1.0", "end")

    # =========================================================
    # ПОДСВЕТКА
    # =========================================================

    def _configure_text_tags(self):
        """
        Настраивает теги подсветки.
        """

        for textbox in (self.left_textbox, self.right_textbox):
            textbox.tag_configure(
                "diff",
                foreground="red",
                background="#ffcccc"
            )

            textbox.tag_configure(
                "match",
                foreground="green"
            )

            textbox.tag_configure(
                "block",
                background="#fff2b2"
            )

    def clear_highlights(self):
        """
        Удаляет подсветку.
        """

        for textbox in (self.left_textbox, self.right_textbox):
            textbox.tag_remove("diff", "1.0", "end")
            textbox.tag_remove("match", "1.0", "end")
            textbox.tag_remove("block", "1.0", "end")

        self.result_label.configure(text="Подсветка очищена.")

    def clear_fields(self):
        """
        Очищает оба поля сравнения.
        """

        self.left_textbox.delete("1.0", "end")
        self.right_textbox.delete("1.0", "end")
        self.clear_highlights()
        self.result_label.configure(text="Поля очищены.")

    def _add_text_tag(self, textbox, start_char, end_char, tag_name):
        """
        Добавляет тег к диапазону символов.
        """

        if start_char is None or end_char is None:
            return

        if start_char >= end_char:
            return

        start_index = f"1.0+{start_char}c"
        end_index = f"1.0+{end_char}c"

        textbox.tag_add(tag_name, start_index, end_index)

    def _add_tag_for_normalized_range(
            self,
            textbox,
            index_map,
            norm_start,
            norm_end,
            tag_name
    ):
        """
        Подсвечивает диапазон нормализованного текста в исходном тексте.
        """

        if norm_start >= norm_end:
            return

        if not index_map:
            return

        original_positions = index_map[norm_start:norm_end]

        if not original_positions:
            return

        range_start = original_positions[0]
        previous_position = original_positions[0]

        for position in original_positions[1:]:
            if position == previous_position + 1:
                previous_position = position
                continue

            self._add_text_tag(
                textbox,
                range_start,
                previous_position + 1,
                tag_name
            )

            range_start = position
            previous_position = position

        self._add_text_tag(
            textbox,
            range_start,
            previous_position + 1,
            tag_name
        )

    # =========================================================
    # НОРМАЛИЗАЦИЯ
    # =========================================================

    def _is_punctuation(self, char):
        """
        Проверяет, является ли символ пунктуацией.
        """

        return unicodedata.category(char).startswith("P")

    def _normalize_char_for_compare(self, char):
        """
        Нормализует один символ для сравнения.
        """

        replacements = {
            "ё": "е",
            "Ё": "Е",
            "’": "'",
            "‘": "'",
            "“": '"',
            "”": '"',
            "«": '"',
            "»": '"',
            "–": "-",
            "—": "-",
            "−": "-",
        }

        char = replacements.get(char, char)

        if not self.case_sensitive_var.get():
            char = char.lower()

        return char

    def _normalize_text_with_map(self, text):
        """
        Возвращает:
            normalized_text — строка для сравнения;
            index_map — карта индексов normalized_text -> исходный текст.
        """

        normalized_chars = []
        index_map = []

        ignore_whitespace = self.ignore_whitespace_var.get()
        ignore_punctuation = self.ignore_punctuation_var.get()

        for original_index, original_char in enumerate(text):
            if ignore_whitespace and original_char.isspace():
                continue

            if ignore_punctuation and self._is_punctuation(original_char):
                continue

            normalized_char = self._normalize_char_for_compare(original_char)

            normalized_chars.append(normalized_char)
            index_map.append(original_index)

        return "".join(normalized_chars), index_map

    def _normalize_text_range_with_map(self, text, start_char, end_char):
        """
        Нормализует только выбранный диапазон текста.
        """

        substring = text[start_char:end_char]

        normalized_text, local_index_map = self._normalize_text_with_map(
            substring
        )

        global_index_map = [
            start_char + local_index
            for local_index in local_index_map
        ]

        return normalized_text, global_index_map

    def _normalize_word_for_compare(self, word):
        """
        Нормализует слово/токен для сравнения.
        """

        if not word:
            return ""

        normalized_chars = []

        for char in word:
            if self.ignore_punctuation_var.get() and self._is_punctuation(char):
                continue

            if char.isspace():
                continue

            normalized_chars.append(
                self._normalize_char_for_compare(char)
            )

        normalized_word = "".join(normalized_chars)

        return normalized_word.strip()

    def _normalize_ingredient_for_compare(self, ingredient):
        """
        Нормализует ингредиент состава.

        Для состава нормализация специально мягче к пунктуации:
        PEG-40, PEG 40 и PEG40 часто должны восприниматься как одно.
        """

        if not ingredient:
            return ""

        ingredient = ingredient.strip()

        ingredient = self._remove_composition_prefix_from_text(ingredient)

        chars = []

        for char in ingredient:
            if char.isspace():
                continue

            if self._is_punctuation(char):
                continue

            chars.append(
                self._normalize_char_for_compare(char)
            )

        return "".join(chars)

    # =========================================================
    # ТОКЕНИЗАЦИЯ
    # =========================================================

    def _tokenize_words_with_ranges(self, text, offset=0):
        """
        Разбивает текст на токены с позициями.

        Возвращает список словарей:
            {
                "value": нормализованное значение,
                "display": исходный текст токена,
                "start": начало в исходной строке,
                "end": конец в исходной строке
            }
        """

        tokens = []

        for match in re.finditer(r"\S+", text):
            display_value = match.group(0)
            normalized_value = self._normalize_word_for_compare(display_value)

            if not normalized_value:
                continue

            tokens.append({
                "value": normalized_value,
                "display": display_value,
                "start": offset + match.start(),
                "end": offset + match.end()
            })

        return tokens

    def _tokenize_ingredients_with_ranges(self, text):
        """
        Разбивает текст состава на ингредиенты по запятым.

        Если найдено слово СОСТАВ / INGREDIENTS / INCI,
        всё до него отрезается.
        """

        composition_text, composition_offset = (
            self._extract_composition_text_with_offset(text)
        )

        ingredients = []

        parts = re.split(r"[,;]", composition_text)

        current_position = 0

        for raw_part in parts:
            part_start_in_composition = current_position
            part_end_in_composition = current_position + len(raw_part)

            current_position += len(raw_part) + 1

            raw_start = composition_offset + part_start_in_composition
            raw_end = composition_offset + part_end_in_composition

            left_spaces = len(raw_part) - len(raw_part.lstrip())
            right_spaces = len(raw_part) - len(raw_part.rstrip())

            clean_start = raw_start + left_spaces
            clean_end = raw_end - right_spaces

            clean_display = raw_part.strip()

            clean_display = self._remove_composition_prefix_from_text(
                clean_display
            )

            if not clean_display:
                continue

            normalized_value = self._normalize_ingredient_for_compare(
                clean_display
            )

            if not normalized_value:
                continue

            clean_end = clean_start + len(clean_display)

            ingredients.append({
                "value": normalized_value,
                "display": clean_display,
                "start": clean_start,
                "end": clean_end
            })

        return ingredients

    # =========================================================
    # ОБЫЧНОЕ СРАВНЕНИЕ ВСЕГО ТЕКСТА
    # =========================================================

    def _compare_with_order(self, text1, text2):
        """
        Сравнивает весь текст как последовательность символов.
        """

        normalized_1, map_1 = self._normalize_text_with_map(text1)
        normalized_2, map_2 = self._normalize_text_with_map(text2)

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
                    self._add_tag_for_normalized_range(
                        self.left_textbox,
                        map_1,
                        i1,
                        i2,
                        "match"
                    )

                    self._add_tag_for_normalized_range(
                        self.right_textbox,
                        map_2,
                        j1,
                        j2,
                        "match"
                    )

                continue

            diff_blocks_count += 1

            if tag in ("replace", "delete"):
                self._add_tag_for_normalized_range(
                    self.left_textbox,
                    map_1,
                    i1,
                    i2,
                    "diff"
                )

            if tag in ("replace", "insert"):
                self._add_tag_for_normalized_range(
                    self.right_textbox,
                    map_2,
                    j1,
                    j2,
                    "diff"
                )

        if diff_blocks_count == 0:
            self.result_label.configure(text="Различий не найдено.")
        else:
            self.result_label.configure(
                text=f"Найдено блоков различий: {diff_blocks_count}."
            )

        logger.info(
            "Сравнение всего текста завершено. diff_blocks=%s",
            diff_blocks_count
        )

    # =========================================================
    # СРАВНЕНИЕ БЕЗ УЧЁТА ПОРЯДКА СЛОВ
    # =========================================================

    def _highlight_tokens_by_status(
            self,
            textbox,
            tokens,
            common_counter,
            diff_counter
    ):
        """
        Подсвечивает токены по статусу.

        Красным — то, что есть только в одном тексте.
        Зелёным — совпадения, если включена соответствующая настройка.
        """

        common_left = Counter(common_counter)
        diff_left = Counter(diff_counter)

        for token in tokens:
            value = token["value"]

            if diff_left[value] > 0:
                self._add_text_tag(
                    textbox,
                    token["start"],
                    token["end"],
                    "diff"
                )
                diff_left[value] -= 1
                continue

            if self.show_matches_var.get() and common_left[value] > 0:
                self._add_text_tag(
                    textbox,
                    token["start"],
                    token["end"],
                    "match"
                )
                common_left[value] -= 1

    def _compare_tokens_without_word_order(self, tokens1, tokens2):
        """
        Сравнивает два списка токенов без учёта порядка.
        """

        counter1 = Counter(
            token["value"]
            for token in tokens1
        )

        counter2 = Counter(
            token["value"]
            for token in tokens2
        )

        only_left = counter1 - counter2
        only_right = counter2 - counter1
        common = counter1 & counter2

        self._highlight_tokens_by_status(
            self.left_textbox,
            tokens1,
            common,
            only_left
        )

        self._highlight_tokens_by_status(
            self.right_textbox,
            tokens2,
            common,
            only_right
        )

        diff_words_count = sum(only_left.values()) + sum(only_right.values())

        return diff_words_count

    def _compare_without_word_order(self, text1, text2):
        """
        Сравнивает весь текст как набор слов.
        """

        tokens1 = self._tokenize_words_with_ranges(text1)
        tokens2 = self._tokenize_words_with_ranges(text2)

        diff_words_count = self._compare_tokens_without_word_order(
            tokens1,
            tokens2
        )

        if diff_words_count == 0:
            self.result_label.configure(
                text="Различий не найдено. Порядок слов не учитывался."
            )
        else:
            self.result_label.configure(
                text=(
                    f"Найдено отличающихся слов: {diff_words_count}. "
                    "Порядок слов не учитывался."
                )
            )

        logger.info(
            "Сравнение без учёта порядка слов завершено. diff_words=%s",
            diff_words_count
        )

    # =========================================================
    # ПОИСК ПОХОЖЕГО БЛОКА
    # =========================================================

    def _find_best_window_against_target(self, full_tokens, target_tokens):
        """
        Ищет в длинном тексте окно, наиболее похожее на короткий текст.
        """

        if not full_tokens or not target_tokens:
            return None

        full_values = [
            token["value"]
            for token in full_tokens
        ]

        target_values = [
            token["value"]
            for token in target_tokens
        ]

        full_len = len(full_values)
        target_len = len(target_values)

        if full_len <= target_len:
            ratio = difflib.SequenceMatcher(
                None,
                target_values,
                full_values,
                autojunk=False
            ).ratio()

            return {
                "start": 0,
                "end": full_len,
                "ratio": ratio
            }

        min_window_len = max(1, int(target_len * 0.70))
        max_window_len = min(full_len, int(target_len * 1.40) + 5)

        candidate_lengths = {
            target_len,
            target_len - 10,
            target_len - 5,
            target_len + 5,
            target_len + 10,
            int(target_len * 0.80),
            int(target_len * 0.90),
            int(target_len * 1.10),
            int(target_len * 1.20),
            min_window_len,
            max_window_len,
        }

        candidate_lengths = sorted(
            length
            for length in candidate_lengths
            if 1 <= length <= full_len
        )

        best_result = None

        step = 1

        if full_len > 500:
            step = max(1, full_len // 500)

        for window_len in candidate_lengths:
            max_start = full_len - window_len

            for start in range(0, max_start + 1, step):
                end = start + window_len
                window_values = full_values[start:end]

                ratio = difflib.SequenceMatcher(
                    None,
                    target_values,
                    window_values,
                    autojunk=False
                ).ratio()

                if best_result is None or ratio > best_result["ratio"]:
                    best_result = {
                        "start": start,
                        "end": end,
                        "ratio": ratio
                    }

        return best_result

    def _find_best_similar_block_pair(self, tokens1, tokens2):
        """
        Определяет, какой текст короче,
        и ищет его лучший аналог внутри второго текста.
        """

        if not tokens1 or not tokens2:
            return None

        if len(tokens1) <= len(tokens2):
            window = self._find_best_window_against_target(
                full_tokens=tokens2,
                target_tokens=tokens1
            )

            if window is None:
                return None

            return {
                "left_slice": (0, len(tokens1)),
                "right_slice": (window["start"], window["end"]),
                "ratio": window["ratio"]
            }

        window = self._find_best_window_against_target(
            full_tokens=tokens1,
            target_tokens=tokens2
        )

        if window is None:
            return None

        return {
            "left_slice": (window["start"], window["end"]),
            "right_slice": (0, len(tokens2)),
            "ratio": window["ratio"]
        }

    def _get_token_slice_text_range(self, tokens, slice_start, slice_end):
        """
        Превращает диапазон токенов в диапазон символов исходного текста.
        """

        if not tokens:
            return 0, 0

        if slice_start >= slice_end:
            return 0, 0

        slice_start = max(0, min(slice_start, len(tokens) - 1))
        slice_end = max(slice_start + 1, min(slice_end, len(tokens)))

        text_start = tokens[slice_start]["start"]
        text_end = tokens[slice_end - 1]["end"]

        return text_start, text_end

    def _highlight_found_block_ranges(self, left_range, right_range):
        """
        Немного подсвечивает найденные похожие блоки.
        """

        left_start, left_end = left_range
        right_start, right_end = right_range

        self._add_text_tag(
            self.left_textbox,
            left_start,
            left_end,
            "block"
        )

        self._add_text_tag(
            self.right_textbox,
            right_start,
            right_end,
            "block"
        )

    def _compare_ranges_with_order(
            self,
            text1,
            text2,
            left_range,
            right_range
    ):
        """
        Сравнивает только найденные похожие диапазоны.
        """

        left_start, left_end = left_range
        right_start, right_end = right_range

        normalized_1, map_1 = self._normalize_text_range_with_map(
            text=text1,
            start_char=left_start,
            end_char=left_end
        )

        normalized_2, map_2 = self._normalize_text_range_with_map(
            text=text2,
            start_char=right_start,
            end_char=right_end
        )

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
                    self._add_tag_for_normalized_range(
                        self.left_textbox,
                        map_1,
                        i1,
                        i2,
                        "match"
                    )

                    self._add_tag_for_normalized_range(
                        self.right_textbox,
                        map_2,
                        j1,
                        j2,
                        "match"
                    )

                continue

            diff_blocks_count += 1

            if tag in ("replace", "delete"):
                self._add_tag_for_normalized_range(
                    self.left_textbox,
                    map_1,
                    i1,
                    i2,
                    "diff"
                )

            if tag in ("replace", "insert"):
                self._add_tag_for_normalized_range(
                    self.right_textbox,
                    map_2,
                    j1,
                    j2,
                    "diff"
                )

        return diff_blocks_count

    def _compare_ranges_without_word_order(
            self,
            text1,
            text2,
            left_range,
            right_range
    ):
        """
        Сравнивает найденные похожие диапазоны без учёта порядка слов.
        """

        left_start, left_end = left_range
        right_start, right_end = right_range

        left_substring = text1[left_start:left_end]
        right_substring = text2[right_start:right_end]

        tokens1 = self._tokenize_words_with_ranges(
            left_substring,
            offset=left_start
        )

        tokens2 = self._tokenize_words_with_ranges(
            right_substring,
            offset=right_start
        )

        return self._compare_tokens_without_word_order(
            tokens1,
            tokens2
        )

    def _compare_by_best_similar_block(self, text1, text2):
        """
        Ищет общий похожий блок и сравнивает только его.

        Лишний текст вне найденного блока не считается ошибкой.
        """

        tokens1 = self._tokenize_words_with_ranges(text1)
        tokens2 = self._tokenize_words_with_ranges(text2)

        if not tokens1 or not tokens2:
            self._compare_with_order(text1, text2)
            return

        block_pair = self._find_best_similar_block_pair(
            tokens1=tokens1,
            tokens2=tokens2
        )

        if block_pair is None:
            self._compare_with_order(text1, text2)
            return

        similarity_percent = int(block_pair["ratio"] * 100)

        if block_pair["ratio"] < 0.30:
            self._compare_with_order(text1, text2)
            self.result_label.configure(
                text=(
                    "Похожий блок не найден. "
                    "Выполнено обычное сравнение всего текста."
                )
            )
            return

        left_slice_start, left_slice_end = block_pair["left_slice"]
        right_slice_start, right_slice_end = block_pair["right_slice"]

        left_range = self._get_token_slice_text_range(
            tokens=tokens1,
            slice_start=left_slice_start,
            slice_end=left_slice_end
        )

        right_range = self._get_token_slice_text_range(
            tokens=tokens2,
            slice_start=right_slice_start,
            slice_end=right_slice_end
        )

        self._highlight_found_block_ranges(
            left_range=left_range,
            right_range=right_range
        )

        if self.ignore_word_order_var.get():
            diff_count = self._compare_ranges_without_word_order(
                text1=text1,
                text2=text2,
                left_range=left_range,
                right_range=right_range
            )

            diff_label = "отличающихся слов"
        else:
            diff_count = self._compare_ranges_with_order(
                text1=text1,
                text2=text2,
                left_range=left_range,
                right_range=right_range
            )

            diff_label = "блоков различий"

        ignored_left_tokens = len(tokens1) - (left_slice_end - left_slice_start)
        ignored_right_tokens = len(tokens2) - (right_slice_end - right_slice_start)

        if diff_count == 0:
            self.result_label.configure(
                text=(
                    f"Различий внутри похожего блока не найдено. "
                    f"Схожесть блока: {similarity_percent}%. "
                    f"Игнорировано лишних слов вне блока: "
                    f"слева {ignored_left_tokens}, справа {ignored_right_tokens}."
                )
            )
        else:
            self.result_label.configure(
                text=(
                    f"Найдено {diff_count} {diff_label} внутри похожего блока. "
                    f"Схожесть блока: {similarity_percent}%. "
                    f"Лишние блоки вне найденного участка не учитывались."
                )
            )

        logger.info(
            (
                "Сравнение по похожему блоку завершено. "
                "ratio=%s, left_slice=%s, right_slice=%s, "
                "ignored_left=%s, ignored_right=%s, diff_count=%s"
            ),
            round(block_pair["ratio"], 3),
            block_pair["left_slice"],
            block_pair["right_slice"],
            ignored_left_tokens,
            ignored_right_tokens,
            diff_count
        )

    # =========================================================
    # СРАВНЕНИЕ СОСТАВА
    # =========================================================

    def _extract_composition_text_with_offset(self, text):
        """
        Находит начало состава.

        Поддерживает:
        - СОСТАВ:
        - INGREDIENTS:
        - INCI:
        - COMPOSITION:
        - частые OCR-варианты вроде COCTAB:
        """

        if not text:
            return text, 0

        patterns = [
            r"\bсостав\s*[:：]",
            r"\bingredients?\s*[:：]",
            r"\binci\s*[:：]",
            r"\bcomposition\s*[:：]",

            # Частые OCR-варианты слова СОСТАВ.
            r"\bcoctab\s*[:：]",
            r"\bc0ctab\s*[:：]",
            r"\bс0став\s*[:：]",
            r"\bcостав\s*[:：]",
            r"\bсoctab\s*[:：]",
        ]

        best_match = None

        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE
            )

            if match is None:
                continue

            if best_match is None or match.start() < best_match.start():
                best_match = match

        if best_match is None:
            return text, 0

        return text[best_match.end():], best_match.end()

    def _remove_composition_prefix_from_text(self, text):
        """
        Удаляет заголовок состава из фрагмента текста.
        """

        if not text:
            return ""

        patterns = [
            r"^\s*состав\s*[:：]\s*",
            r"^\s*ingredients?\s*[:：]\s*",
            r"^\s*inci\s*[:：]\s*",
            r"^\s*composition\s*[:：]\s*",
            r"^\s*coctab\s*[:：]\s*",
            r"^\s*c0ctab\s*[:：]\s*",
            r"^\s*с0став\s*[:：]\s*",
            r"^\s*cостав\s*[:：]\s*",
            r"^\s*сoctab\s*[:：]\s*",
        ]

        cleaned = text

        for pattern in patterns:
            cleaned = re.sub(
                pattern,
                "",
                cleaned,
                flags=re.IGNORECASE
            )

        return cleaned.strip()

    def _compare_ingredient_tokens(self, ingredients1, ingredients2):
        """
        Сравнивает ингредиенты как набор значений.
        """

        counter1 = Counter(
            ingredient["value"]
            for ingredient in ingredients1
        )

        counter2 = Counter(
            ingredient["value"]
            for ingredient in ingredients2
        )

        only_left = counter1 - counter2
        only_right = counter2 - counter1
        common = counter1 & counter2

        self._highlight_tokens_by_status(
            self.left_textbox,
            ingredients1,
            common,
            only_left
        )

        self._highlight_tokens_by_status(
            self.right_textbox,
            ingredients2,
            common,
            only_right
        )

        return only_left, only_right, common

    def compare_as_composition(self):
        """
        Сравнивает тексты как составы.

        Порядок ингредиентов не учитывается.
        Лишний текст до слова СОСТАВ не учитывается.
        """

        self.clear_highlights()

        text1 = self.left_textbox.get("1.0", "end-1c")
        text2 = self.right_textbox.get("1.0", "end-1c")

        if not text1 and not text2:
            self.result_label.configure(text="Оба поля пустые.")
            return

        if not text1 or not text2:
            self.result_label.configure(
                text="Одно из полей пустое. Сравнение невозможно."
            )
            return

        try:
            ingredients1 = self._tokenize_ingredients_with_ranges(text1)
            ingredients2 = self._tokenize_ingredients_with_ranges(text2)

            if not ingredients1 or not ingredients2:
                self.result_label.configure(
                    text="Не удалось выделить ингредиенты для сравнения состава."
                )
                return

            only_left, only_right, common = self._compare_ingredient_tokens(
                ingredients1,
                ingredients2
            )

            diff_count = sum(only_left.values()) + sum(only_right.values())

            if diff_count == 0:
                self.result_label.configure(
                    text=(
                        "Различий в составе не найдено. "
                        "Порядок ингредиентов не учитывался."
                    )
                )
            else:
                self.result_label.configure(
                    text=(
                        f"Найдено отличающихся ингредиентов: {diff_count}. "
                        f"Только слева: {sum(only_left.values())}. "
                        f"Только справа: {sum(only_right.values())}."
                    )
                )

            logger.info(
                (
                    "Сравнение состава завершено. "
                    "left_only=%s, right_only=%s, common=%s"
                ),
                dict(only_left),
                dict(only_right),
                dict(common)
            )

        except Exception:
            logger.exception("Ошибка при сравнении состава")
            self.result_label.configure(
                text="Ошибка при сравнении состава. Подробности в app.log."
            )

    # =========================================================
    # ГЛАВНЫЙ МЕТОД СРАВНЕНИЯ
    # =========================================================

    def compare_texts(self):
        """
        Главный метод сравнения.

        Логика:
        1. Если включено "Искать похожий блок" —
           ищем общий участок и сравниваем только его.
        2. Если похожий блок выключен, но включено
           "Не учитывать порядок слов" — сравниваем весь текст как набор слов.
        3. Иначе сравниваем весь текст как последовательность символов.
        """

        self.clear_highlights()

        text1 = self.left_textbox.get("1.0", "end-1c")
        text2 = self.right_textbox.get("1.0", "end-1c")

        if not text1 and not text2:
            self.result_label.configure(text="Оба поля пустые.")
            return

        if not text1 or not text2:
            self.result_label.configure(
                text="Одно из полей пустое. Сравнение невозможно."
            )
            return

        try:
            if self.find_similar_block_var.get():
                self._compare_by_best_similar_block(text1, text2)

            elif self.ignore_word_order_var.get():
                self._compare_without_word_order(text1, text2)

            else:
                self._compare_with_order(text1, text2)

        except Exception:
            logger.exception("Ошибка при сравнении текстов")
            self.result_label.configure(
                text="Ошибка при сравнении текстов. Подробности в app.log."
            )

    # =========================================================
    # МЕТОДЫ ДЛЯ ПЕРЕДАЧИ ТЕКСТА ИЗ OCR/EXCEL
    # =========================================================

    def set_text_left(self, text):
        """
        Устанавливает текст в левое поле.

        Вызывается через AppController.
        """

        self.left_textbox.delete("1.0", "end")
        self.left_textbox.insert("1.0", text or "")
        self.clear_highlights()

    def set_text_right(self, text):
        """
        Устанавливает текст в правое поле.

        Вызывается через AppController.
        """

        self.right_textbox.delete("1.0", "end")
        self.right_textbox.insert("1.0", text or "")
        self.clear_highlights()


# Алиасы на случай, если в main_window.py используется другое имя класса.
CompareViewerFrame = CompareSection
CompareFrame = CompareSection