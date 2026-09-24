import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

APP_ENV = os.getenv("APP_ENV", "development").lower()

BASE_DIR = Path(__file__).resolve().parent.parent

# Supabase VPS PostgreSQL connection
SUPABASE_DB_URL = "postgresql+psycopg://postgres.your-tenant-id:124c92be406d143842e01a4c0c09fb1c@136.248.126.192:5432/postgres"

DATABASE_URL = os.getenv("DATABASE_URL", SUPABASE_DB_URL)

# Normalize standard postgresql:// to postgresql+psycopg://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Enforce schema 3dprintcalc for Supabase VPS (can be overridden by env var for tests)
DB_SCHEMA = os.getenv("DB_SCHEMA", "3dprintcalc")

DEFAULT_SECRET = "dev_secret_key_super_safe_67890_minimum_32_characters"
SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
