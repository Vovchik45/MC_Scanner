import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from datetime import datetime
import openpyxl


class NewFileWindow(tk.Toplevel):
    """Сбор SGTIN для выпуска продукции: CSV Нанесение + XLSX ВводВОборот."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.parent = parent
        self.title("Сбор нового файла выпуска продукции")
        self.geometry("800x600")

        self.input_strings = []
        self.unique_strings = set()
        self.expected_gtin = None
        self.delete_mode = False

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.create_widgets()

    def on_close(self):
        """Обработчик закрытия окна"""
        self.app.show_main_window()
        self.destroy()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Введите строку GS1:").pack(anchor=tk.W)

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

        columns = ('#', 'GTIN (01)', 'SN (21)', 'Код проверки (91)', 'Криптохвост')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=10)

        self.tree.heading('#', text='#')
        self.tree.heading('GTIN (01)', text='GTIN (01)')
        self.tree.heading('SN (21)', text='SN (21)')
        self.tree.heading('Код проверки (91)', text='Код проверки (91)')
        self.tree.heading('Криптохвост', text='Криптохвост (92/93/94)')

        self.tree.column('#', width=50)
        self.tree.column('GTIN (01)', width=150)
        self.tree.column('SN (21)', width=150)
        self.tree.column('Код проверки (91)', width=120)
        self.tree.column('Криптохвост', width=150)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def add_string(self):
        text = self.entry.get('1.0', tk.END).strip()
        if not text:
            return

        processed_text = self.app.replace_gs(text)

        if self.delete_mode:
            self.delete_string_by_content(processed_text)
            self.entry.delete('1.0', tk.END)
            return

        if processed_text in self.unique_strings:
            self.app.root.bell()
            self.app.speak("Эта строка уже была добавлена!")
            messagebox.showwarning("Дубликат", "Эта строка уже была добавлена!")
            return

        parsed_data = self.app.parse_gs1_string(processed_text)

        if not self.app.is_full_sgtin(parsed_data):
            self.app.root.bell()
            self.app.speak("Ошибка парсинга. Не удалось распарсить строку.")
            messagebox.showerror(
                "Ошибка парсинга",
                "Не удалось распарсить строку.\n"
                "Нужны GTIN (01), SN (21) и криптохвост (92 / 93 / 94).\n"
                "Ключ проверки (91) — если есть в коде."
            )
            return

        if self.expected_gtin is None:
            self.expected_gtin = parsed_data['gtin']
            self.gtin_label.config(text=f"Ожидаемый GTIN: {self.expected_gtin}")
        elif self.expected_gtin != parsed_data['gtin']:
            self.app.root.bell()
            self.app.speak("Ошибка ДжиТиИН. Строка не соответствует ожидаемому товару.")
            messagebox.showerror(
                "Ошибка GTIN",
                f"GTIN в строке ({parsed_data['gtin']}) не совпадает с ожидаемым ({self.expected_gtin})!\n"
                f"Строка не будет добавлена."
            )
            return

        self.input_strings.append(processed_text)
        self.unique_strings.add(processed_text)

        self.update_table()
        self.app.speak_count(len(self.input_strings))
        self.entry.delete('1.0', tk.END)

    def update_table(self):
        """Обновляет таблицу с данными"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, string in enumerate(self.input_strings, 1):
            parsed_data = self.app.parse_gs1_string(string)
            crypto = parsed_data['crypto_tail'] or 'Не найден'
            if parsed_data.get('crypto_ai') and parsed_data['crypto_tail']:
                crypto = f"{parsed_data['crypto_ai']}:{parsed_data['crypto_tail']}"
            self.tree.insert('', tk.END, values=(
                i,
                parsed_data['gtin'] or 'Не найден',
                parsed_data['sn'] or 'Не найден',
                parsed_data['check_code'] or '—',
                crypto
            ))

    def delete_last_string(self):
        """Удаляет последнюю добавленную строку"""
        if not self.input_strings:
            self.app.speak("Нет строк для удаления!")
            messagebox.showwarning("Пустой список", "Нет строк для удаления!")
            return

        last_string = self.input_strings.pop()
        self.unique_strings.discard(last_string)

        if not self.input_strings:
            self.expected_gtin = None
            self.gtin_label.config(text="Ожидаемый GTIN: не установлен")

        self.update_table()
        self.app.speak("Последняя строка удалена!")
        messagebox.showinfo("Успех", "Последняя строка удалена!")

    def delete_selected_string(self):
        """Удаляет выбранную строку из таблицы"""
        selected_item = self.tree.selection()
        if not selected_item:
            self.app.speak("Не выбрана строка для удаления!")
            messagebox.showwarning("Не выбрана строка", "Пожалуйста, выберите строку для удаления!")
            return

        item_index = self.tree.index(selected_item[0])

        if 0 <= item_index < len(self.input_strings):
            removed_string = self.input_strings.pop(item_index)
            self.unique_strings.discard(removed_string)

            if not self.input_strings:
                self.expected_gtin = None
                self.gtin_label.config(text="Ожидаемый GTIN: не установлен")

            self.update_table()
            self.app.speak("Выбранная строка удалена!")
            messagebox.showinfo("Успех", "Выбранная строка удалена!")

    def delete_string_by_content(self, string_to_delete):
        """Удаляет строку по содержимому (в режиме удаления)"""
        processed_to_delete = self.app.replace_gs(string_to_delete)

        for i, string in enumerate(self.input_strings):
            if string == processed_to_delete:
                self.input_strings.pop(i)
                self.unique_strings.discard(string)

                if not self.input_strings:
                    self.expected_gtin = None
                    self.gtin_label.config(text="Ожидаемый GTIN: не установлен")

                self.update_table()
                self.app.speak("Строка найдена и удалена!")
                messagebox.showinfo("Успех", "Строка найдена и удалена!")
                return

        self.app.root.bell()
        self.app.speak("Строка для удаления не найдена!")
        messagebox.showwarning("Не найдено", "Строка для удаления не найдена!")

    def toggle_delete_mode(self):
        """Переключает режим удаления"""
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
            initialdir=self.app.get_export_dir(),
        )
        if not directory:
            return

        base_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

        csv_filename = f"Нанесение_{base_filename}.csv"
        xls_filename = f"Выпуск_{base_filename}.xlsx"

        csv_path = os.path.join(directory, csv_filename)
        xls_path = os.path.join(directory, xls_filename)

        try:
            with open(csv_path, 'w', encoding='utf-8') as f:
                for string in self.input_strings:
                    f.write(string + '\n')

            workbook = openpyxl.Workbook()
            worksheet = workbook.active
            worksheet.title = "Коды маркировки"

            for string in self.input_strings:
                parsed_data = self.app.parse_gs1_string(string)
                gtin = parsed_data['gtin']
                sn = parsed_data['sn']

                if gtin and gtin != 'Не найден' and sn and sn != 'Не найден':
                    concatenated_string = f"01{gtin}21{sn}"
                    worksheet.append([concatenated_string])
                else:
                    worksheet.append([string])

            workbook.save(xls_path)

            self.app.speak(f"Файлы успешно сохранены. Всего строк: {len(self.input_strings)}")
            messagebox.showinfo(
                "Успех",
                f"Файлы успешно сохранены:\n\n"
                f"CSV (Нанесение): {csv_filename}\n"
                f"XLS (Выпуск): {xls_filename}\n\n"
                f"В папке: {directory}"
            )
            self.on_close()
        except Exception as e:
            self.app.speak("Ошибка сохранения файлов!")
            messagebox.showerror("Ошибка", f"Не удалось сохранить файлы:\n{str(e)}")
