import os
from dotenv import load_dotenv

load_dotenv()

FERNET_KEY = os.getenv('FERNET_KEY')