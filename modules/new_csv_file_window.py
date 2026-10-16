import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from datetime import datetime
import openpyxl


class NewCsvFileWindow(tk.Toplevel):
    """Сбор SGTIN и SSCC в CSV (+ XLSX)."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.parent = parent
        self.title("Сбор нового файла CSV (SGTIN/SSCC)")
        self.geometry("900x600")

        self.input_strings = []
        self.unique_strings = set()
        self.expected_gtin = None
        self.delete_mode = False

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.create_widgets()

    def on_close(self):
        self.app.show_main_window()
        self.destroy()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Введите строку GS1 (SGTIN или SSCC):").pack(anchor=tk.W)

        self.entry = tk.Text(main_frame, height=4, width=70)
        self.entry.pack(fill=tk.X, pady=5)
        self.entry.bind('<Return>', lambda e: self.add_string())

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)

        ttk.Button(button_frame, text="Добавить строку",
                  command=self.add_string).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(button_frame, text="Удалить последнюю строку",
                  command=self.delete_last_string).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Удалить выбранную строку",
                  command=self.delete_selected_string).pack(side=tk.LEFT, padx=5)

        self.delete_mode_button = ttk.Button(button_frame, text="Включить режим удаления",
                                           command=self.toggle_delete_mode)
        self.delete_mode_button.pack(side=tk.LEFT, padx=5)

        self.gtin_label = ttk.Label(main_frame, text="Ожидаемый GTIN: не установлен", foreground="blue")
        self.gtin_label.pack(anchor=tk.W, pady=(5, 0))

        self.delete_mode_label = ttk.Label(main_frame, text="", foreground="red")
        self.delete_mode_label.pack(anchor=tk.W, pady=(0, 5))

        ttk.Label(main_frame, text="Добавленные строки (парсинг GS1):").pack(anchor=tk.W, pady=(10, 0))

        self.create_table(main_frame)

        ttk.Button(main_frame, text="Завершить ввод",
                  command=self.finish_input).pack(pady=10)

    def create_table(self, parent):
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        columns = ('#', 'Тип', 'GTIN (01)', 'SN (21)', 'Код проверки (91)', 'Криптохвост')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=10)

        self.tree.heading('#', text='#')
        self.tree.heading('Тип', text='Тип')
        self.tree.heading('GTIN (01)', text='GTIN (01)')
        self.tree.heading('SN (21)', text='SN (21)')
        self.tree.heading('Код проверки (91)', text='Код проверки (91)')
        self.tree.heading('Криптохвост', text='Криптохвост (92/93/94)')

        self.tree.column('#', width=40)
        self.tree.column('Тип', width=70)
        self.tree.column('GTIN (01)', width=140)
        self.tree.column('SN (21)', width=160)
        self.tree.column('Код проверки (91)', width=110)
        self.tree.column('Криптохвост', width=140)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _unique_key(self, processed_text):
        code_type, payload = self.app.classify_code(processed_text)
        if code_type == 'SSCC':
            return f"SSCC:{payload}"
        return processed_text

    def _refresh_expected_gtin(self):
        self.expected_gtin = None
        for string in self.input_strings:
            code_type, payload = self.app.classify_code(string)
            if code_type == 'SGTIN':
                self.expected_gtin = payload['gtin']
                break
        if self.expected_gtin:
            self.gtin_label.config(text=f"Ожидаемый GTIN: {self.expected_gtin}")
        else:
            self.gtin_label.config(text="Ожидаемый GTIN: не установлен")

    def add_string(self):
        text = self.entry.get('1.0', tk.END).strip()
        if not text:
            return

        processed_text = self.app.replace_gs(text)

        if self.delete_mode:
            self.delete_string_by_content(processed_text)
            self.entry.delete('1.0', tk.END)
            return

        unique_key = self._unique_key(processed_text)
        if unique_key in self.unique_strings or processed_text in self.unique_strings:
            self.app.root.bell()
            self.app.speak("Эта строка уже была добавлена!")
            messagebox.showwarning("Дубликат", "Эта строка уже была добавлена!")
            return

        code_type, payload = self.app.classify_code(processed_text)

        if code_type == 'SGTIN':
            if self.expected_gtin is None:
                self.expected_gtin = payload['gtin']
                self.gtin_label.config(text=f"Ожидаемый GTIN: {self.expected_gtin}")
            elif self.expected_gtin != payload['gtin']:
                self.app.root.bell()
                self.app.speak("Ошибка ДжиТиИН. Строка не соответствует ожидаемому товару.")
                messagebox.showerror(
                    "Ошибка GTIN",
                    f"GTIN в строке ({payload['gtin']}) не совпадает с ожидаемым ({self.expected_gtin})!\n"
                    f"Строка не будет добавлена."
                )
                return
            store_value = processed_text
        elif code_type == 'SSCC':
            store_value = processed_text
        else:
            self.app.root.bell()
            self.app.speak("Ошибка парсинга. Не удалось распарсить строку.")
            messagebox.showerror(
                "Ошибка парсинга",
                "Не удалось распознать строку.\n"
                "Ожидается полный КМ (GTIN, SN, криптохвост 92/93/94)\n"
                "или SSCC (18 цифр, опционально с префиксом 00)."
            )
            return

        self.input_strings.append(store_value)
        self.unique_strings.add(unique_key)
        self.unique_strings.add(store_value)

        self.update_table()
        self.app.speak_count(len(self.input_strings))
        self.entry.delete('1.0', tk.END)

    def update_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, string in enumerate(self.input_strings, 1):
            code_type, payload = self.app.classify_code(string)
            if code_type == 'SGTIN':
                crypto = payload['crypto_tail'] or '—'
                if payload.get('crypto_ai') and payload['crypto_tail']:
                    crypto = f"{payload['crypto_ai']}:{payload['crypto_tail']}"
                self.tree.insert('', tk.END, values=(
                    i,
                    'SGTIN',
                    payload['gtin'] or '—',
                    payload['sn'] or '—',
                    payload['check_code'] or '—',
                    crypto,
                ))
            elif code_type == 'SSCC':
                self.tree.insert('', tk.END, values=(
                    i,
                    'SSCC',
                    '—',
                    payload,
                    '—',
                    '—',
                ))
            else:
                self.tree.insert('', tk.END, values=(
                    i,
                    '?',
                    '—',
                    string,
                    '—',
                    '—',
                ))

    def _remove_at_index(self, index):
        removed = self.input_strings.pop(index)
        self.unique_strings.discard(removed)
        self.unique_strings.discard(self._unique_key(removed))
        self._refresh_expected_gtin()
        self.update_table()
        return removed

    def delete_last_string(self):
        if not self.input_strings:
            self.app.speak("Нет строк для удаления!")
            messagebox.showwarning("Пустой список", "Нет строк для удаления!")
            return

        self._remove_at_index(len(self.input_strings) - 1)
        self.app.speak("Последняя строка удалена!")
        messagebox.showinfo("Успех", "Последняя строка удалена!")

    def delete_selected_string(self):
        selected_item = self.tree.selection()
        if not selected_item:
            self.app.speak("Не выбрана строка для удаления!")
            messagebox.showwarning("Не выбрана строка", "Пожалуйста, выберите строку для удаления!")
            return

        item_index = self.tree.index(selected_item[0])
        if 0 <= item_index < len(self.input_strings):
            self._remove_at_index(item_index)
            self.app.speak("Выбранная строка удалена!")
            messagebox.showinfo("Успех", "Выбранная строка удалена!")

    def delete_string_by_content(self, string_to_delete):
        processed_to_delete = self.app.replace_gs(string_to_delete)
        key_to_delete = self._unique_key(processed_to_delete)

        for i, string in enumerate(self.input_strings):
            if string == processed_to_delete or self._unique_key(string) == key_to_delete:
                self._remove_at_index(i)
                self.app.speak("Строка найдена и удалена!")
                messagebox.showinfo("Успех", "Строка найдена и удалена!")
                return

        self.app.root.bell()
        self.app.speak("Строка для удаления не найдена!")
        messagebox.showwarning("Не найдено", "Строка для удаления не найдена!")

    def toggle_delete_mode(self):
        self.delete_mode = not self.delete_mode

        if self.delete_mode:
            self.delete_mode_button.config(text="Выключить режим удаления")
            self.delete_mode_label.config(text="РЕЖИМ УДАЛЕНИЯ АКТИВЕН - вводимые строки будут удаляться из списка")
            self.app.speak("Режим удаления активирован")
        else:
            self.delete_mode_button.config(text="Включить режим удаления")
            self.delete_mode_label.config(text="")
            self.app.speak("Режим удаления выключен")

    def finish_input(self):
        if not self.input_strings:
            self.app.speak("Не добавлено ни одной строки!")
            messagebox.showwarning("Пустой список", "Не добавлено ни одной строки!")
            return

        directory = filedialog.askdirectory(
            title="Выберите папку для сохранения файлов",
            initialdir=self.app.get_assembly_dir(),
        )
        if not directory:
            return

        base_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        csv_filename = f"Сбор_{base_filename}.csv"
        xls_filename = f"Сбор_{base_filename}.xlsx"
        csv_path = os.path.join(directory, csv_filename)
        xls_path = os.path.join(directory, xls_filename)

        try:
            with open(csv_path, 'w', encoding='utf-8') as f:
                for string in self.input_strings:
                    f.write(string + '\n')

            workbook = openpyxl.Workbook()
            worksheet = workbook.active
            worksheet.title = "Коды"

            for string in self.input_strings:
                code_type, payload = self.app.classify_code(string)
                if code_type == 'SGTIN':
                    worksheet.append([f"01{payload['gtin']}21{payload['sn']}"])
                elif code_type == 'SSCC':
                    worksheet.append([payload])
                else:
                    worksheet.append([string])

            workbook.save(xls_path)

            self.app.speak(f"Файлы успешно сохранены. Всего строк: {len(self.input_strings)}")
            messagebox.showinfo(
                "Успех",
                f"Файлы успешно сохранены:\n\n"
                f"CSV: {csv_filename}\n"
                f"XLS: {xls_filename}\n\n"
                f"В папке: {directory}"
            )
            self.on_close()
        except Exception as e:
            self.app.speak("Ошибка сохранения файлов!")
            messagebox.showerror("Ошибка", f"Не удалось сохранить файлы:\n{str(e)}")
