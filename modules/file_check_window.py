import tkinter as tk
from tkinter import ttk, messagebox, filedialog

class FileCheckWindow(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.parent = parent
        self.title("Проверка файла GS1")
        self.geometry("900x600")
        
        self.loaded_strings = []
        self.correct_count = 0
        self.checked_strings = set()
        
        # Обработка закрытия окна
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.create_widgets()
    
    def on_close(self):
        """Обработчик закрытия окна"""
        self.app.show_main_window()
        self.destroy()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Статистика
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(stats_frame, text="Всего строк в файле:").grid(row=0, column=0, sticky=tk.W)
        self.total_label = ttk.Label(stats_frame, text="0")
        self.total_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 20))
        
        ttk.Label(stats_frame, text="Правильно введено:").grid(row=0, column=2, sticky=tk.W)
        self.correct_label = ttk.Label(stats_frame, text="0")
        self.correct_label.grid(row=0, column=3, sticky=tk.W, padx=5)
        
        ttk.Label(stats_frame, text="Осталось:").grid(row=0, column=4, sticky=tk.W)
        self.remaining_label = ttk.Label(stats_frame, text="0")
        self.remaining_label.grid(row=0, column=5, sticky=tk.W, padx=5)
        
        ttk.Button(main_frame, text="Выбрать файл для проверки", 
                  command=self.load_file).pack(pady=5)
        
        # Таблица с содержимым файла
        content_frame = ttk.LabelFrame(main_frame, text="Содержимое файла (парсинг GS1)")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.create_table(content_frame)
        
        # Область проверки
        check_frame = ttk.LabelFrame(main_frame, text="Проверка строки")
        check_frame.pack(fill=tk.X, pady=5)
        
        self.check_entry = tk.Text(check_frame, height=3, width=70)
        self.check_entry.pack(fill=tk.X, padx=5, pady=5)
        self.check_entry.bind('<Return>', lambda e: self.check_string())
        
        ttk.Button(check_frame, text="Проверить строку", 
                  command=self.check_string).pack(pady=5)
        
        self.result_label = ttk.Label(check_frame, text="", foreground="blue")
        self.result_label.pack(pady=5)
        pass
        

    def create_table(self, parent):
        # Фрейм для таблицы с прокруткой
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Создаем Treeview (таблицу)
        columns = ('#', 'GTIN (01)', 'SN (21)', 'Код проверки (91)', 'Криптохвост')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=12)
        
        # Настраиваем заголовки
        self.tree.heading('#', text='#')
        self.tree.heading('GTIN (01)', text='GTIN (01)')
        self.tree.heading('SN (21)', text='SN (21)')
        self.tree.heading('Код проверки (91)', text='Код проверки (91)')
        self.tree.heading('Криптохвост', text='Криптохвост (92/93/94)')
        
        # Настраиваем ширину колонок
        self.tree.column('#', width=50)
        self.tree.column('GTIN (01)', width=150)
        self.tree.column('SN (21)', width=150)
        self.tree.column('Код проверки (91)', width=120)
        self.tree.column('Криптохвост', width=150)
        
        # Добавляем прокрутку
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def load_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Текстовые файлы для честного знака", "*.csv"), ("Все файлы", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.loaded_strings = [line.strip() for line in f.readlines()]
                
                self.correct_count = 0
                self.checked_strings.clear()
                
                # Очищаем таблицу
                for item in self.tree.get_children():
                    self.tree.delete(item)
                
                # Заполняем таблицу распарсенными данными
                for i, string in enumerate(self.loaded_strings, 1):
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
                
                self.update_stats()
                self.app.speak(f"Загружено {len(self.loaded_strings)} строк")
                messagebox.showinfo("Успех", f"Загружено строк: {len(self.loaded_strings)}")
            except Exception as e:
                self.app.speak("Ошибка загрузки файла")
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл:\n{str(e)}")

    def update_stats(self):
        self.total_label.config(text=str(len(self.loaded_strings)))
        self.correct_label.config(text=str(self.correct_count))
        remaining = len(self.loaded_strings) - self.correct_count
        self.remaining_label.config(text=str(remaining))
        
        # Подсветка завершения
        if self.correct_count == len(self.loaded_strings) and self.loaded_strings:
            self.result_label.config(text="Поздравляем! Все строки введены правильно!", foreground="green")
            self.app.root.bell()
            self.app.speak("Все строки введены правильно!")

    def check_string(self):
        if not self.loaded_strings:
            self.app.speak("Сначала загрузите файл!")
            messagebox.showwarning("Ошибка", "Сначала загрузите файл!")
            return
            
        text = self.check_entry.get('1.0', tk.END).strip()
        if not text:
            return
            
        processed_text = self.app.replace_gs(text)
        
        if processed_text in self.checked_strings:
            self.result_label.config(text="Эта строка уже была проверена!", foreground="orange")
            self.app.root.bell()
            self.app.speak("Эта строка уже была проверена!")
            return
            
        if processed_text in self.loaded_strings:
            self.correct_count += 1
            self.checked_strings.add(processed_text)
            self.result_label.config(
                text=f"Верно! Строка найдена в файле. Правильных вводов: {self.correct_count}/{len(self.loaded_strings)}", 
                foreground="green"
            )
            self.app.root.bell()
            self.app.speak("Верно!")
            
            # Подсветка найденной строки в таблице
            self.highlight_found_string(processed_text)
        else:
            self.result_label.config(
                text=f"Строка не найдена в файле. Правильных вводов: {self.correct_count}/{len(self.loaded_strings)}", 
                foreground="red"
            )
            self.app.speak("Не верно!")
        
        self.update_stats()
        self.check_entry.delete('1.0', tk.END)

    def highlight_found_string(self, found_string):
        """Подсвечивает найденную строку в таблице"""
        # Снимаем предыдущее выделение
        for item in self.tree.selection():
            self.tree.selection_remove(item)
        
        # Ищем строку в загруженных данных и выделяем в таблице
        try:
            index = self.loaded_strings.index(found_string)
            items = self.tree.get_children()
            if index < len(items):
                self.tree.selection_add(items[index])
                self.tree.focus(items[index])
                self.tree.see(items[index])
        except ValueError:
            pass

