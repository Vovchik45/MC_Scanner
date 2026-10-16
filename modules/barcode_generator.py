import os
import configparser
from datetime import datetime
from reportlab.lib.pagesizes import mm
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing
import re

class BarcodeGenerator:
    def __init__(self, config_file='config.ini'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self):
        """Загружает конфигурацию из файла"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding='utf-8')
        else:
            # Создаем конфиг по умолчанию
            self.config['SSCC'] = {
                'last_code': '000000000000000000',
                'company_prefix': '04630010001',
                'extension_digit': '3'
            }
            self.config['PRINT'] = {
                'label_width': '80',
                'label_height': '40'
            }
            self.save_config()
    
    def save_config(self):
        """Сохраняет конфигурацию в файл"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
    
    def get_last_code(self):
        """Возвращает последний сгенерированный код"""
        return self.config.get('SSCC', 'last_code', fallback='000000000000000000')
    
    def generate_sscc(self, quantity, container_type, gs1_company_prefix=None):
        """
        Генерирует SSCC коды
        quantity: количество кодов
        container_type: 'box' или 'pallet'
        gs1_company_prefix: префикс компании GS1 (если None, берется из конфига)
        """
        if gs1_company_prefix is None:
            gs1_company_prefix = self.config.get('SSCC', 'company_prefix', fallback='04630010001')
        
        # Определяем extension digit в зависимости от типа контейнера
        if container_type == 'box':
            extension_digit = '1'  # Коробка
        elif container_type == 'pallet':
            extension_digit = '2'  # Паллета
        else:
            extension_digit = '1'  # По умолчанию коробка
        
        last_code = self.get_last_code()
        
        # Извлекаем последовательную часть из последнего кода
        # Учитываем, что последний код может быть другого типа
        if len(last_code) == 18:
            # Проверяем, совпадает ли extension digit с текущим типом
            if last_code[0] == extension_digit:
                last_serial = int(last_code[7:17])  # Пропускаем extension digit (1) + префикс (6)
            else:
                # Если тип другой, начинаем с 1
                last_serial = 0
        else:
            last_serial = 0
        
        sscc_codes = []
        
        for i in range(quantity):
            serial_number = last_serial + i + 1
            serial_str = str(serial_number).zfill(9)
            
            # Формируем SSCC: Extension Digit (1) + Company Prefix (7) + Serial Reference (9) + Check Digit (1)
            sscc_without_check = extension_digit + gs1_company_prefix + serial_str
            
            check_digit = self.calculate_sscc_check_digit(sscc_without_check)
            sscc_code = sscc_without_check + check_digit
            
            sscc_codes.append(sscc_code)
        
        # Сохраняем последний код только если сгенерировали хотя бы один
        if sscc_codes:
            self.config.set('SSCC', 'last_code', sscc_codes[-1])
            self.save_config()
        
        return sscc_codes
    
    def calculate_sscc_check_digit(self, sscc_without_check):
        """Вычисляет контрольную цифру для SSCC"""
        weights = [3, 1] * 8  # Чередующиеся веса 3 и 1
        total = 0
        
        for i, digit in enumerate(sscc_without_check):
            weight = weights[i % 2]
            total += int(digit) * weight
        
        check_digit = (10 - (total % 10)) % 10
        return str(check_digit)
    
    def generate_barcode_pdf(self, sscc_codes, output_file=None):
        """Генерирует PDF с штрихкодами в горизонтальной ориентации"""
        if output_file is None:
            output_file = f"sscc_barcodes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Размеры этикетки: 40мм ширина (горизонталь) × 20мм высота (вертикаль)
        width = 60 * mm   # Горизонталь
        height = 43 * mm  # Вертикаль
        
        c = canvas.Canvas(output_file, pagesize=(width, height))
        
        for sscc_code in sscc_codes:
            # Создаем вертикальный штрихкод
            barcode = code128.Code128(sscc_code, barHeight=12*mm, barWidth=0.6)
            
            # Рассчитываем позицию для центрирования
            barcode_width = barcode.width
            barcode_height = barcode.height
            
            # Центрируем штрихкод
            x = (width - barcode_width) / 2
            y = (height - barcode_height) / 2 - 1*mm  # Немного смещаем вниз
            
            # Рисуем штрихкод
            barcode.drawOn(c, x, y)
            
            # Добавляем текст с кодом - увеличиваем шрифт и поднимаем выше
            c.setFont("Helvetica", 8)  # Увеличиваем шрифт с 5 до 8
            text_width = c.stringWidth(sscc_code, "Helvetica", 8)
            text_x = (width - text_width) / 2
            text_y = y - 5*mm  # Поднимаем текст выше (было -4mm)
            
            c.drawString(text_x, text_y, sscc_code)
            
            # Новая страница для следующего кода
            c.showPage()
        
        c.save()
        return output_file