from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken

def _get_cipher():
    key = settings.FERNET_KEY
    if not key:
        return None
    return Fernet(key.encode())

class EncryptedCharField(models.CharField):
    def from_db_value(self, value, expression, connection):
        if value is None: return value
        cipher = _get_cipher()
        if not cipher: return value
        try:
            return cipher.decrypt(value.encode()).decode()
        except (InvalidToken, ValueError):
            return value

    def get_prep_value(self, value):
        if value is None: return value
        cipher = _get_cipher()
        if not cipher: return value
        try:
            return cipher.encrypt(value.encode()).decode()
        except (InvalidToken, ValueError):
            return "[encrypt error]"

class EncryptedTextField(models.TextField):
    def from_db_value(self, value, expression, connection):
        if value is None: return value
        cipher = _get_cipher()
        if not cipher: return value
        try:
            return cipher.decrypt(value.encode()).decode()
        except (InvalidToken, ValueError):
            return value

    def get_prep_value(self, value):
        if value is None: return value
        cipher = _get_cipher()
        if not cipher: return value
        try:
            return cipher.encrypt(value.encode()).decode()
        except (InvalidToken, ValueError):
            return "[encrypt error]"