import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from config import settings

FERNET_KEY = settings.FERNET_KEY
fernet = Fernet(FERNET_KEY)

#  Все функции, связанные с шифрованием/дешифрованием.
def encrypt_text(plain_text: str) -> str:
    token = fernet.encrypt(plain_text.encode())
    return token.decode()

def decrypt_text(cipher_text: str) -> str:
    plain_bytes = fernet.decrypt(cipher_text.encode())
    return plain_bytes.decode()