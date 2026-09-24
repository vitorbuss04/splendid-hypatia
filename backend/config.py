import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present — override=False ensures Docker/system env vars always win
load_dotenv(override=False)

APP_ENV = os.getenv("APP_ENV", "development").lower()

BASE_DIR = Path(__file__).resolve().parent.parent

# Supabase VPS PostgreSQL — the only allowed production database
SUPABASE_DB_URL = "postgresql+psycopg://postgres.your-tenant-id:124c92be406d143842e01a4c0c09fb1c@136.248.126.192:5432/postgres"

_raw_url = os.getenv("DATABASE_URL", SUPABASE_DB_URL)

# In production, always use Supabase — reject any SQLite URL that may leak in
if APP_ENV == "production" and _raw_url.startswith("sqlite"):
    DATABASE_URL = SUPABASE_DB_URL
else:
    DATABASE_URL = _raw_url

# Normalize standard postgresql:// to postgresql+psycopg://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Schema: always 3dprintcalc in production; overridable to "" for SQLite tests
DB_SCHEMA = os.getenv("DB_SCHEMA", "3dprintcalc")
if APP_ENV == "production":
    DB_SCHEMA = "3dprintcalc"

DEFAULT_SECRET = "dev_secret_key_super_safe_67890_minimum_32_characters"
SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
