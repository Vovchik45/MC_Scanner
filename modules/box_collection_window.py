import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import os
import re
import json
from datetime import datetime
import openpyxl

try:
    import py_cz_api
    PY_CZ_API_AVAILABLE = True
except ImportError:
    PY_CZ_API_AVAILABLE = False
    print("Модуль py_cz_api не установлен")

class BoxCollectionWindow(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.parent = parent
        self.enable_chz = getattr(app, 'enable_chz', False)
        if self.enable_chz:
            self.title("Сбор коробок и отправка в ЧЗ")
        else:
            self.title("Сбор коробок")
        self.geometry("900x700")
        
        self.current_strings = []
        self.unique_strings = set()
        self.all_strings = set()
        self.expected_gtin = None
        self.boxes = {}
        self.delete_mode = False
        
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
        
        # Секция авторизации ЧЗ (только при enable_chz)
        if self.enable_chz:
            auth_frame = ttk.LabelFrame(main_frame, text="Авторизация в Честном ЗНАКе")
            auth_frame.pack(fill=tk.X, pady=5)
            
            auth_content = ttk.Frame(auth_frame)
            auth_content.pack(fill=tk.X, padx=5, pady=5)
            
            if not PY_CZ_API_AVAILABLE:
                ttk.Label(auth_content, text="Модуль py_cz_api не установлен!", foreground="red").grid(row=1, column=0, columnspan=3, sticky=tk.W)
                ttk.Label(auth_content, text="Установите: pip install py_cz_api", foreground="red").grid(row=2, column=0, columnspan=3, sticky=tk.W)
            
            ttk.Label(auth_content, text="Серийный номер сертификата:").grid(row=4, column=0, sticky=tk.W, padx=(0, 5))
            self.cert_serial_entry = ttk.Entry(auth_content, width=50)
            self.cert_serial_entry.grid(row=4, column=1, sticky=tk.W, padx=(0, 10))
            
            auth_button = ttk.Button(auth_content, text="Авторизоваться",
                    command=self.authenticate)
            auth_button.grid(row=4, column=2, padx=5)
            
            self.auth_status = ttk.Label(auth_content, text="Не авторизован", foreground="red")
            self.auth_status.grid(row=4, column=3, padx=5)
            
            ttk.Button(auth_content, text="Как получить?",
                    command=self.show_help).grid(row=3, column=0, columnspan=4, pady=5)
        
        # Секция ввода строк
        ttk.Label(main_frame, text="Введите строки для текущей коробки:").pack(anchor=tk.W, pady=(10,0))
        
        self.entry = tk.Text(main_frame, height=4, width=70)
        self.entry.pack(fill=tk.X, pady=5)
        self.entry.bind('<Return>', lambda e: self.add_string())
        
        # Кнопки для работы со строками
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="Добавить строку", 
                  command=self.add_string).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(button_frame, text="Удалить последнюю строку", 
                  command=self.delete_last_string).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Удалить выбранную строку", 
                  command=self.delete_selected_string).pack(side=tk.LEFT, padx=5)
        
        # Кнопка для переключения режима удаления
        self.delete_mode_button = ttk.Button(button_frame, text="Включить режим удаления", 
                                           command=self.toggle_delete_mode)
        self.delete_mode_button.pack(side=tk.LEFT, padx=5)
        
        # Отображение ожидаемого GTIN
        self.gtin_label = ttk.Label(main_frame, text="Ожидаемый GTIN: не установлен", foreground="blue")
        self.gtin_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Индикатор режима удаления
        self.delete_mode_label = ttk.Label(main_frame, text="", foreground="red")
        self.delete_mode_label.pack(anchor=tk.W, pady=(0, 5))
        
        ttk.Label(main_frame, text="Текущие строки (парсинг GS1):").pack(anchor=tk.W, pady=(10,0))
        
        # Создаем таблицу для отображения распарсенных данных
        self.create_table(main_frame)
        
        # Кнопки для работы с коробками
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(action_frame, text="Собрать коробку", 
                  command=self.collect_box).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(action_frame, text="Завершить сборку", 
                  command=self.finish_collection).pack(side=tk.LEFT, padx=5)
        
        if self.enable_chz:
            ttk.Button(action_frame, text="Сгенерировать документ", 
                      command=self.generate_document).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(action_frame, text="Отправить в ЧЗ", 
                      command=self.send_to_crpt).pack(side=tk.LEFT, padx=5)
        
        # Отображение собранных коробок
        ttk.Label(main_frame, text="Собранные коробки:").pack(anchor=tk.W, pady=(10,0))
        
        self.boxes_frame = ttk.Frame(main_frame)
        self.boxes_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.update_boxes_display()


    def create_table(self, parent):
        # Фрейм для таблицы с прокруткой
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Создаем Treeview (таблицу)
        columns = ('#', 'GTIN (01)', 'SN (21)', 'Код проверки (91)', 'Криптохвост')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=8)
        
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

    def show_help(self):
        """Показывает справку о получении серийного номера"""
        help_text = """
Как получить серийный номер сертификата:

1. Откройте КриптоПро CSP
2. Перейдите во вкладку 'Сервис'
3. Нажмите 'Просмотреть сертификаты в контейнере'
4. Выберите ваш контейнер
5. В свойствах сертификата найдите поле 'Серийный номер'
6. Скопируйте значение без пробелов

Пример: 01EB1AA50033B12D894A535821B96C26C0
"""
        messagebox.showinfo("Справка", help_text)

    def authenticate(self):
        """Аутентификация через серийный номер сертификата"""
        print("Метод authenticate вызван!")  # Отладочный вывод
        
        # Временно упрощаем для тестирования
        try:
            print("Начинаем авторизацию...")
            
            if not PY_CZ_API_AVAILABLE:
                self.app.speak("Модуль py_cz_api не установлен")
                messagebox.showinfo("Инфо", "Модуль не установлен, но кнопка работает!")
                return
            
            cert_serial = self.cert_serial_entry.get().strip()
            print(f"Серийный номер: {cert_serial}")
            
            if not cert_serial:
                self.app.speak("Введите серийный номер")
                messagebox.showinfo("Ошибка", "Введите серийный номер")
                return
            
            # Просто тестируем что метод вызывается
            self.app.speak("Попытка авторизации")
            self.auth_status.config(text="Авторизация...", foreground="orange")
            
            # Имитируем задержку
            self.after(1000, lambda: self.finish_auth_test(cert_serial))
            
        except Exception as e:
            print(f"Ошибка в authenticate: {e}")
            self.app.speak(f"Ошибка: {str(e)}")

    def finish_auth_test(self, cert_serial):
        """Завершение тестовой авторизации"""
        print(f"Завершение авторизации для: {cert_serial}")
        self.auth_status.config(text="Авторизован (тест)", foreground="green")
        self.app.speak("Тестовая авторизация завершена")
    
    def add_string(self):
        text = self.entry.get('1.0', tk.END).strip()
        if not text:
            return
            
        processed_text = self.app.replace_gs(text)
        
        # Если включен режим удаления
        if self.delete_mode:
            self.delete_string_by_content(processed_text)
            self.entry.delete('1.0', tk.END)
            return
            
        # Обычный режим добавления
        if processed_text in self.unique_strings:
            self.app.root.bell()
            self.app.speak("Эта строка уже была добавлена в текущую коробку!")
            messagebox.showwarning("Дубликат", "Эта строка уже была добавлена в текущую коробку!")
            return
            
        # Проверяем уникальность строки среди всех коробок
        if processed_text in self.all_strings:
            self.app.root.bell()
            self.app.speak("Эта строка уже используется в другой коробке!")
            messagebox.showwarning("Дубликат", "Эта строка уже используется в другой коробке!")
            return
            
        # Парсим строку GS1
        parsed_data = self.app.parse_gs1_string(processed_text)
        
        # Проверяем, что обязательные поля найдены
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
        
        # Проверяем GTIN
        if self.expected_gtin is None:
            # Устанавливаем ожидаемый GTIN по первой строке
            self.expected_gtin = parsed_data['gtin']
            self.gtin_label.config(text=f"Ожидаемый GTIN: {self.expected_gtin}")
        elif self.expected_gtin != parsed_data['gtin']:
            # GTIN не совпадает с ожидаемым
            self.app.root.bell()
            self.app.speak("Ошибка ДжиТиИН. Строка не соответствует ожидаемому товару.")
            messagebox.showerror(
                "Ошибка GTIN", 
                f"GTIN в строке ({parsed_data['gtin']}) не совпадает с ожидаемым ({self.expected_gtin})!\n"
                f"Строка не будет добавена."
            )
            return
        
        # Добавляем в список
        self.current_strings.append(processed_text)
        self.unique_strings.add(processed_text)
        
        # Обновляем таблицу
        self.update_table()
        
        # Озвучиваем количество строк
        self.app.speak_count(len(self.current_strings))
        
        self.entry.delete('1.0', tk.END)

    def update_table(self):
        """Обновляет таблицу с данными"""
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Заполняем таблицу заново
        for i, string in enumerate(self.current_strings, 1):
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
        if not self.current_strings:
            self.app.speak("Нет строк для удаления!")
            messagebox.showwarning("Пустой список", "Нет строк для удаления!")
            return
            
        last_string = self.current_strings.pop()
        self.unique_strings.discard(last_string)
        
        # Если список пуст, сбрасываем ожидаемый GTIN
        if not self.current_strings:
            self.expected_gtin = None
            self.gtin_label.config(text="Ожидаемый GTIN: не установлен")
        
        # Обновляем таблицу
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
            
        # Получаем индекс выбранной строки
        item_index = self.tree.index(selected_item[0])
        
        if 0 <= item_index < len(self.current_strings):
            # Удаляем строку
            removed_string = self.current_strings.pop(item_index)
            self.unique_strings.discard(removed_string)
            
            # Если список пуст, сбрасываем ожидаемый GTIN
            if not self.current_strings:
                self.expected_gtin = None
                self.gtin_label.config(text="Ожидаемый GTIN: не установлен")
            
            # Обновляем таблицу
            self.update_table()
            self.app.speak("Выбранная строка удалена!")
            messagebox.showinfo("Успех", "Выбранная строка удалена!")

    def delete_string_by_content(self, string_to_delete):
        """Удаляет строку по содержимому (в режиме удаления)"""
        processed_to_delete = self.app.replace_gs(string_to_delete)
        
        # Ищем строку в списке
        for i, string in enumerate(self.current_strings):
            if string == processed_to_delete:
                # Удаляем найденную строку
                self.current_strings.pop(i)
                self.unique_strings.discard(string)
                
                # Если список пуст, сбрасываем ожидаемый GTIN
                if not self.current_strings:
                    self.expected_gtin = None
                    self.gtin_label.config(text="Ожидаемый GTIN: не установлен")
                
                # Обновляем таблицу
                self.update_table()
                self.app.speak("Строка найдена и удалена!")
                messagebox.showinfo("Успех", "Строка найдена и удалена!")
                return
        
        # Если строка не найдена
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

    def collect_box(self):
        """Собирает текущие строки в коробку с заданным кодом"""
        if not self.current_strings:
            self.app.speak("Не добавлено ни одной строки для коробки!")
            messagebox.showwarning("Пустой список", "Не добавлено ни одной строки для коробки!")
            return
            
        # Запрашиваем код коробки
        box_code = tk.simpledialog.askstring("Код коробки", "Введите код коробки:")
        if not box_code:
            return
            
        # Проверяем уникальность кода коробки
        if box_code in self.boxes:
            self.app.root.bell()
            self.app.speak(f"Код коробки {box_code} уже используется!")
            messagebox.showerror("Ошибка", f"Код коробки '{box_code}' уже используется!")
            return
            
        # Сохраняем текущие строки под этим кодом
        self.boxes[box_code] = self.current_strings.copy()
        
        # Добавляем строки в общий набор для проверки уникальности
        for string in self.current_strings:
            self.all_strings.add(string)
        
        # Очищаем текущие данные
        self.current_strings.clear()
        self.unique_strings.clear()
        self.expected_gtin = None
        self.gtin_label.config(text="Ожидаемый GTIN: не установлен")
        
        # Обновляем таблицу и отображение коробок
        self.update_table()
        self.update_boxes_display()
        
        # Озвучиваем успешное создание коробки
        self.app.speak(f"Коробка {box_code} собрана")

    def update_boxes_display(self):
        """Обновляет отображение собранных коробок"""
        # Очищаем фрейм с коробками
        for widget in self.boxes_frame.winfo_children():
            widget.destroy()
            
        if not self.boxes:
            ttk.Label(self.boxes_frame, text="Нет собранных коробок").pack(pady=10)
            return
            
        # Создаем таблицу для отображения коробок
        columns = ('Код коробки', 'Количество строк')
        boxes_tree = ttk.Treeview(self.boxes_frame, columns=columns, show='headings', height=5)
        
        # Настраиваем заголовки
        boxes_tree.heading('Код коробки', text='Код коробки')
        boxes_tree.heading('Количество строк', text='Количество строк')
        
        # Настраиваем ширину колонок
        boxes_tree.column('Код коробки', width=200)
        boxes_tree.column('Количество строк', width=150)
        
        # Заполняем таблицу
        for box_code, strings in self.boxes.items():
            boxes_tree.insert('', tk.END, values=(box_code, len(strings)))
        
        # Добавляем прокрутку
        scrollbar = ttk.Scrollbar(self.boxes_frame, orient=tk.VERTICAL, command=boxes_tree.yview)
        boxes_tree.configure(yscrollcommand=scrollbar.set)
        
        boxes_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def generate_document(self):
        """Генерация документа агрегации"""
        if not self.boxes:
            self.app.speak("Нет собранных коробок")
            messagebox.showerror("Ошибка", "Нет собранных коробок")
            return
        
        try:
            document = self.create_aggregation_document()
            
            # Сохраняем в файл
            directory = filedialog.askdirectory(
                title="Выберите папку для сохранения документа",
                initialdir=self.app.get_boxes_dir(),
            )
            if directory:
                filename = f"aggregation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                file_path = os.path.join(directory, filename)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(document, f, ensure_ascii=False, indent=2)
                
                self.generated_document = document
                self.app.speak("Документ агрегации сгенерирован")
                messagebox.showinfo("Успех", f"Документ агрегации сохранен:\n{file_path}")
                
        except Exception as e:
            self.app.speak(f"Ошибка генерации документа: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка генерации документа: {str(e)}")

    def create_aggregation_document(self):
        """Создает документ агрегации из собранных коробок"""
        products = []
        
        for box_code, codes_list in self.boxes.items():
            for code in codes_list:
                parsed_data = self.app.parse_gs1_string(code)
                
                if parsed_data['gtin'] and parsed_data['sn']:
                    product = {
                        "gtin": parsed_data['gtin'],
                        "serial_number": parsed_data['sn'],
                        "cost": "0.00",
                        "vat_rate": "20"
                    }
                    products.append(product)
        
        document = {
            "description": f"Агрегация {len(products)} товаров",
            "doc_id": f"AGG_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "doc_status": "DRAFT",
            "operation_type": "AGGREGATION",
            "products": products,
            "aggregation_details": {
                "parent_gtin": products[0]["gtin"] if products else "",
                "parent_serial": f"PARENT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "child_count": len(products)
            }
        }
        
        return document

    def send_to_crpt(self):
        """Отправка документа в Честный ЗНАК"""
        if not self.app.trueapi_client or not self.app.trueapi_client.authenticated:
            self.app.speak("Сначала выполните авторизацию")
            messagebox.showerror("Ошибка", "Сначала выполните авторизацию")
            return
        
        if not hasattr(self, 'generated_document'):
            self.app.speak("Сначала сгенерируйте документ")
            messagebox.showerror("Ошибка", "Сначала сгенерируйте документ")
            return
        
        try:
            result = self.app.trueapi_client.send_aggregation_document(self.generated_document)
            
            if result:
                self.app.speak("Документ успешно отправлен в ЧЗ")
                messagebox.showinfo("Успех", f"Документ успешно отправлен!\nID документа: {result.get('id', 'Неизвестно')}")
            else:
                self.app.speak("Ошибка при отправке документа")
                messagebox.showerror("Ошибка", "Ошибка при отправке документа")
                
        except Exception as e:
            self.app.speak(f"Ошибка при отправке документа: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка при отправке документа: {str(e)}")

    def finish_collection(self):
        """Завершает сборку и выгружает файлы"""
        if not self.boxes:
            self.app.speak("Не собрано ни одной коробки!")
            messagebox.showwarning("Пустой список", "Не собрано ни одной коробки!")
            return
            
        # Запрашиваем каталог для сохранения
        directory = filedialog.askdirectory(
            title="Выберите папку для сохранения файлов коробок",
            initialdir=self.app.get_boxes_dir(),
        )
        if not directory:
            return
            
        try:
            # Создаем файлы для каждой коробки
            for box_code, strings in self.boxes.items():
                # Создаем безопасное имя файла
                safe_box_code = self.make_filename_safe(box_code)
                filename = f"{safe_box_code}.xlsx"
                file_path = os.path.join(directory, filename)
                
                # Создаем XLS файл с конкатенацией "01"+GTIN+"21"+SN
                workbook = openpyxl.Workbook()
                worksheet = workbook.active
                worksheet.title = "Коды маркировки"
                
                # Добавляем данные в формате "01"+GTIN+"21"+SN
                for string in strings:
                    parsed_data = self.app.parse_gs1_string(string)
                    gtin = parsed_data['gtin']
                    sn = parsed_data['sn']
                    
                    # Проверяем, что GTIN и SN найдены
                    if gtin and gtin != 'Не найден' and sn and sn != 'Не найден':
                        concatenated_string = f"01{gtin}21{sn}"
                        worksheet.append([concatenated_string])
                    else:
                        # Если не удалось распарсить, сохраняем исходную строку
                        worksheet.append([string])
                
                # Сохраняем XLS файл
                workbook.save(file_path)
            
            self.app.speak(f"Создано {len(self.boxes)} файлов коробок")
            messagebox.showinfo(
                "Успех", 
                f"Создано {len(self.boxes)} файлов коробок в папке:\n{directory}"
            )
            self.on_close()  # Используем on_close вместо destroy
        except Exception as e:
            self.app.speak("Ошибка сохранения файлов коробок!")
            messagebox.showerror("Ошибка", f"Не удалось сохранить файлы:\n{str(e)}")

    def make_filename_safe(self, filename):
        """Делает имя файла безопасным, заменяя недопустимые символы"""
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        safe_name = safe_name.strip('. ')
        if len(safe_name) > 200:
            safe_name = safe_name[:200]
            return safe_name
    
    def browse_file(self, entry_widget, file_type):
        """Выбор файла через диалог"""
        filename = filedialog.askopenfilename(
            title=f"Выберите файл {file_type}",
            filetypes=[("Файлы сертификата", file_type), ("Все файлы", "*.*")]
        )
        if filename:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, filename)
