import os
import base64
import json
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

'''
@brief APIKeyHandler module - Handles encrypted API key management using AES-GCM and RSA.
@details
- Loads and decrypts API keys from environment variables.
- Supports listing services and decrypting individual keys.
@constructor
- @param None (uses environment variables).
@method
- `list_services() -> list`
    - @return (list): List of service names with stored keys.
- `decrypt_api_key(enc_data: dict) -> str`
    - @param enc_data (dict): Encrypted API key data.
    - @return (str): Decrypted API key.
- `get_all_keys() -> list`
    - @return (list): List of all decrypted API keys.
'''
class APIKeyHandler:
    """
    Xử lý API key mã hóa bằng AES-GCM + RSA (SSH key).
    Lưu tất cả key trong biến ALL_KEYS_DATA (base64 JSON).
    """

    def __init__(self):
        '''
        @brief Constructor for APIKeyHandler.
        @details Loads encrypted API keys from environment variables.
        '''
        self.private_key_path = os.getenv("PRV_KEY_PATH")
        self.all_keys_data = os.getenv("ALL_KEYS_DATA")

        if not self.private_key_path or not os.path.exists(self.private_key_path):
            raise FileNotFoundError(f"PRV_KEY_PATH không tồn tại: {self.private_key_path}")

        if not self.all_keys_data:
            raise EnvironmentError("Thiếu biến môi trường ALL_KEYS_DATA")

        # Load all keys từ env
        self.keys_dict = self._load_all_keys()

    def _load_all_keys(self):
        '''
        @brief Decodes and parses all API keys from base64 JSON.
        @return (dict): Dictionary of all keys.
        '''
        """Giải base64 và parse JSON"""
        try:
            decoded_json = base64.b64decode(self.all_keys_data).decode()
            return json.loads(decoded_json)
        except Exception as e:
            raise ValueError(f"Lỗi parse ALL_KEYS_DATA: {e}")

    def list_services(self):
        '''
        @brief Returns a list of service names with stored API keys.
        @return (list): List of service names.
        '''
        """Trả về danh sách tên service đang lưu key"""
        return list(self.keys_dict.keys())

    def decrypt_api_key(self, enc_data: dict) -> str:
        '''
        @brief Decrypts a single API key from encrypted data.
        @param enc_data (dict): Encrypted API key data.
        @return (str): Decrypted API key.
        '''
        """Giải mã 1 API key từ enc_data"""
        with open(self.private_key_path, "rb") as f:
            private_key = serialization.load_ssh_private_key(f.read(), password=None)

        # Giải mã AES key
        aes_key = private_key.decrypt(
            base64.b64decode(enc_data["enc_aes_key"]),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # Giải mã API key bằng AES-GCM
        iv = base64.b64decode(enc_data["iv"])
        tag = base64.b64decode(enc_data["tag"])
        ciphertext = base64.b64decode(enc_data["ciphertext"])

        decryptor = Cipher(algorithms.AES(aes_key), modes.GCM(iv, tag)).decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        return plaintext.decode()

    def get_all_keys(self) -> list:
        '''
        @brief Decrypts all API keys and returns them as a list.
        @return (list): List of decrypted API keys.
        '''
        """Giải mã toàn bộ key và trả về dạng list"""
        return [self.decrypt_api_key(enc_data) for enc_data in self.keys_dict.values()]
