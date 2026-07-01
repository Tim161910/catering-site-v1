import os

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

load_dotenv()

FERNET_KEY = os.getenv('FERNET_KEY')