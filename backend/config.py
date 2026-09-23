import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

APP_ENV = os.getenv("APP_ENV", "development").lower()

BASE_DIR = Path(__file__).resolve().parent.parent

# Database configuration per environment
if APP_ENV == "production":
    DEFAULT_DB_URL = "sqlite:////app/data/prod.db"
    DEFAULT_SECRET = "CHANGE_THIS_IN_PRODUCTION_EASYPANEL_KEY_9876543210_SECURE"
elif APP_ENV == "test":
    DEFAULT_DB_URL = "sqlite:///data/test.db"
    DEFAULT_SECRET = "test_secret_key_1234567890_super_safe_length_32"
else:  # development
    DEFAULT_DB_URL = "sqlite:///data/dev.db"
    DEFAULT_SECRET = "dev_secret_key_super_safe_67890_minimum_32_characters"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Ensure SQLite directory exists if using SQLite
if DATABASE_URL.startswith("sqlite:///"):
    sqlite_path = DATABASE_URL.replace("sqlite:///", "")
    # Check if absolute or relative
    if sqlite_path and sqlite_path != ":memory:":
        db_path = Path(sqlite_path)
        if not db_path.is_absolute():
            db_path = BASE_DIR / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
