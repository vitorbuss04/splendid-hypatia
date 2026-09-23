from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.config import DATABASE_URL

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from backend import models  # Ensure all models are registered with Base
    from sqlalchemy import inspect, text
    Base.metadata.create_all(bind=engine)

    # Safe column migrations for SQLite
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        with engine.connect() as conn:
            if "users" in tables:
                user_cols = [c["name"] for c in inspector.get_columns("users")]
                if "default_payment_terms" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN default_payment_terms VARCHAR(500)"))
                if "default_warranty_terms" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN default_warranty_terms VARCHAR(500)"))
            if "filaments" in tables:
                fil_cols = [c["name"] for c in inspector.get_columns("filaments")]
                if "color_hex" not in fil_cols:
                    conn.execute(text("ALTER TABLE filaments ADD COLUMN color_hex VARCHAR(20) DEFAULT '#10b981'"))
            if "projects" in tables:
                proj_cols = [c["name"] for c in inspector.get_columns("projects")]
                if "delivery_days" not in proj_cols:
                    conn.execute(text("ALTER TABLE projects ADD COLUMN delivery_days INTEGER DEFAULT 3"))
                if "payment_terms" not in proj_cols:
                    conn.execute(text("ALTER TABLE projects ADD COLUMN payment_terms VARCHAR(500)"))
                if "warranty_terms" not in proj_cols:
                    conn.execute(text("ALTER TABLE projects ADD COLUMN warranty_terms VARCHAR(500)"))
            conn.commit()
    except Exception as e:
        pass
