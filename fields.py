from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken

class EncryptedCharField(models.CharField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cipher = Fernet(settings.FERNET_KEY.encode())

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            return self.cipher.decrypt(value.encode()).decode()
        except (InvalidToken, ValueError):
            return value

    def get_prep_value(self, value):
        if value is None:
            return value
        try:
            return self.cipher.encrypt(value.encode()).decode()
        except (InvalidToken, ValueError):
            return "[encrypt error]"

class EncryptedTextField(models.TextField):
    def __init__(self, *args, **kwargs):
        self.cipher = Fernet(settings.FERNET_KEY.encode())
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            return self.cipher.decrypt(value.encode()).decode()
        except (InvalidToken, ValueError):
            return value

    def get_prep_value(self, value):
        if value is None:
            return value
        try:
            return self.cipher.encrypt(value.encode()).decode()
        except (InvalidToken, ValueError):
            return "[encrypt error]"