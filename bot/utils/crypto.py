import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Выгрузка ключа шифрования, и проверка на наличие
load_dotenv()
FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    raise ValueError("FERNET_KEY not set in .env")

fernet = Fernet(FERNET_KEY)

#  Все функции, связанные с шифрованием/дешифрованием.
def encrypt_text(plain_text: str) -> str:
    token = fernet.encrypt(plain_text.encode())
    return token.decode()

def decrypt_text(cipher_text: str) -> str:
    plain_bytes = fernet.decrypt(cipher_text.encode())
    return plain_bytes.decode()