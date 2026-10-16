import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from datetime import datetime

from .barcode_generator import BarcodeGenerator

class PrintBarcodeWindow(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.parent = parent
        self.title("Печать штрихкода гофроящика")
        self.geometry("500x400")
        
        self.barcode_generator = BarcodeGenerator()
        
        # Обработка закрытия окна
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.create_widgets()
        self.update_display()
    
    def on_close(self):
        """Обработчик закрытия окна"""
        self.app.show_main_window()
        self.destroy()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Информация о последнем коде
        info_frame = ttk.LabelFrame(main_frame, text="Информация о последнем коде")
        info_frame.pack(fill=tk.X, pady=5)
        
        self.last_code_label = ttk.Label(info_frame, text="Последний код: ", font=("Arial", 10, "bold"))
        self.last_code_label.pack(pady=5)
        
        # Настройки генерации
        settings_frame = ttk.LabelFrame(main_frame, text="Настройки генерации")
        settings_frame.pack(fill=tk.X, pady=5)
        
        # Количество кодов
        ttk.Label(settings_frame, text="Количество новых кодов:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.quantity_var = tk.StringVar(value="1")
        quantity_entry = ttk.Entry(settings_frame, textvariable=self.quantity_var, width=10)
        quantity_entry.grid(row=0, column=1, sticky=tk.W, pady=2, padx=(5, 0))
        
        # Тип контейнера
        ttk.Label(settings_frame, text="Тип контейнера:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.container_type = tk.StringVar(value="box")
        container_frame = ttk.Frame(settings_frame)
        container_frame.grid(row=1, column=1, sticky=tk.W, pady=2, padx=(5, 0))
        
        ttk.Radiobutton(container_frame, text="Коробка", variable=self.container_type, 
                       value="box").pack(side=tk.LEFT)
        ttk.Radiobutton(container_frame, text="Паллета", variable=self.container_type, 
                       value="pallet").pack(side=tk.LEFT, padx=(10, 0))
        
        # GS1 префикс
        ttk.Label(settings_frame, text="GS1 префикс компании:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.gs1_prefix_var = tk.StringVar(value=self.barcode_generator.config.get('SSCC', 'company_prefix', fallback='04630010001'))
        gs1_entry = ttk.Entry(settings_frame, textvariable=self.gs1_prefix_var, width=20)
        gs1_entry.grid(row=2, column=1, sticky=tk.W, pady=2, padx=(5, 0))
        
        # Кнопки действий
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Сгенерировать и показать предпросмотр", 
                  command=self.generate_and_preview).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(button_frame, text="Сохранить в PDF", 
                  command=self.save_to_pdf).pack(side=tk.LEFT, padx=5)
        
        # Область предпросмотра
        preview_frame = ttk.LabelFrame(main_frame, text="Предпросмотр кодов")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Прокручиваемый текст для предпросмотра
        self.preview_text = tk.Text(preview_frame, height=8, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=scrollbar.set)
        
        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Статус
        self.status_label = ttk.Label(main_frame, text="", foreground="blue")
        self.status_label.pack(pady=5)
    
    def update_display(self):
        """Обновляет отображение последнего кода"""
        last_code = self.barcode_generator.get_last_code()
        self.last_code_label.config(text=f"Последний код: {last_code}")
    
    def validate_input(self):
        """Проверяет корректность введенных данных"""
        try:
            quantity = int(self.quantity_var.get())
            if quantity <= 0 or quantity > 1000:
                raise ValueError("Количество должно быть от 1 до 1000")
            
            gs1_prefix = self.gs1_prefix_var.get().strip()
            if not gs1_prefix or not gs1_prefix.isdigit():
                raise ValueError("GS1 префикс должен содержать только цифры")
            
            return quantity, gs1_prefix
            
        except ValueError as e:
            messagebox.showerror("Ошибка ввода", str(e))
            return None, None
    
    def generate_and_preview(self):
        """Генерирует коды и показывает предпросмотр"""
        quantity, gs1_prefix = self.validate_input()
        if quantity is None:
            return
        
        try:
            container_type = self.container_type.get()
            sscc_codes = self.barcode_generator.generate_sscc(quantity, container_type, gs1_prefix)
            
            # Обновляем префикс в конфиге если он изменился
            if gs1_prefix != self.barcode_generator.config.get('SSCC', 'company_prefix'):
                self.barcode_generator.config.set('SSCC', 'company_prefix', gs1_prefix)
                self.barcode_generator.save_config()
            
            # Показываем коды в предпросмотре
            self.preview_text.delete(1.0, tk.END)
            for i, code in enumerate(sscc_codes, 1):
                self.preview_text.insert(tk.END, f"{i:3d}. {code}\n")
            
            self.update_display()
            self.status_label.config(text=f"Сгенерировано {len(sscc_codes)} кодов")
            self.app.speak(f"Сгенерировано {len(sscc_codes)} кодов")
            
        except Exception as e:
            messagebox.showerror("Ошибка генерации", f"Ошибка при генерации кодов: {str(e)}")
    
    def save_to_pdf(self):
        """Сохраняет сгенерированные коды в PDF"""
        if not self.preview_text.get(1.0, tk.END).strip():
            messagebox.showwarning("Предупреждение", "Сначала сгенерируйте коды")
            return
        
        # Получаем количество кодов из текстового поля
        quantity, gs1_prefix = self.validate_input()
        if quantity is None:
            return
        
        # Генерируем коды заново для сохранения
        container_type = self.container_type.get()
        sscc_codes = self.barcode_generator.generate_sscc(quantity, container_type, gs1_prefix)
        
        # Запрашиваем место сохранения
        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="Сохранить PDF с штрихкодами",
            initialdir=self.app.get_barcodes_dir(),
        )
        
        if filename:
            try:
                pdf_path = self.barcode_generator.generate_barcode_pdf(sscc_codes, filename)
                self.status_label.config(text=f"PDF сохранен: {os.path.basename(pdf_path)}")
                self.app.speak("PDF файл сохранен")
                
                # Показываем диалог успеха
                messagebox.showinfo("Успех", 
                    f"PDF файл успешно создан:\n\n"
                    f"Файл: {os.path.basename(pdf_path)}\n"
                    f"Путь: {os.path.dirname(pdf_path)}\n"
                    f"Количество кодов: {len(sscc_codes)}\n\n"
                    f"Последний код: {sscc_codes[-1]}")
                    
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при создании PDF: {str(e)}")