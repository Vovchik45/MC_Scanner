import requests

try:
    import py_cz_api
    PY_CZ_API_AVAILABLE = True
except ImportError:
    PY_CZ_API_AVAILABLE = False
    print("Модуль py_cz_api не установлен")

class CertificateAuth:
    """Аутентификация через оттиск сертификата КриптоПро"""
    
    def __init__(self):
        self.base_url = "https://int01.gismt.crpt.tech/api/v3"
        
    def get_certificate_thumbprint(self, cert_file_path):
        """Получение оттиска сертификата из файла"""
        try:
            import hashlib
            import base64
            
            with open(cert_file_path, 'rb') as cert_file:
                cert_data = cert_file.read()
                
            sha1_hash = hashlib.sha1(cert_data).digest()
            thumbprint = base64.b64encode(sha1_hash).decode('utf-8')
            
            return thumbprint
            
        except Exception as e:
            raise Exception(f"Ошибка чтения сертификата: {e}")
    
    def auth_by_thumbprint(self, thumbprint):
        """Аутентификация по оттиску сертификата"""
        try:
            auth_url = f"{self.base_url}/auth/cert/"
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            data = {
                "thumbprint": thumbprint
            }
            
            response = requests.post(auth_url, headers=headers, json=data, verify=False)
            
            if response.status_code == 200:
                return response.json().get('token')
            else:
                raise Exception(f"Ошибка аутентификации: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise Exception(f"Ошибка при аутентификации: {e}")

class TrueApiClient:
    """Клиент для работы с True API Честного ЗНАКа через py_cz_api"""
    
    def __init__(self):
        self.api = None
        self.authenticated = False
        
    def auth_by_certificate_serial(self, cert_serial):
        """Аутентификация по серийному номеру сертификата через py_cz_api"""
        if not PY_CZ_API_AVAILABLE:
            raise Exception("Модуль py_cz_api не установлен. Установите: pip install py_cz_api")
        
        try:
            certificate = py_cz_api.Certificate(cert_serial)
            token = py_cz_api.Token.create_from_cert(certificate)
            self.api = py_cz_api.Api(token, py_cz_api.Pgs.ncp)
            
            self.authenticated = True
            return True
            
        except Exception as e:
            print(f"Ошибка аутентификации через py_cz_api: {e}")
            return False
    
    def send_aggregation_document(self, document_data):
        """Отправка документа агрегации через py_cz_api"""
        if not self.authenticated or not self.api:
            raise Exception("Не выполнена аутентификация")
        
        try:
            result = self.api.send_document(
                document=document_data,
                document_format="MANUAL",
                signature="",
                document_type="LP_INTRODUCE_GOODS"
            )
            
            return result
            
        except Exception as e:
            raise Exception(f"Ошибка при отправке документа: {e}")