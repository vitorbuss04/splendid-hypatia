from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.config import DATABASE_URL, DB_SCHEMA

execution_options = {}
connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    execution_options["schema_translate_map"] = {None: DB_SCHEMA}
    connect_args["options"] = f"-c search_path={DB_SCHEMA}"

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    execution_options=execution_options,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

metadata = MetaData(schema=DB_SCHEMA) if (DB_SCHEMA and not DATABASE_URL.startswith("sqlite")) else MetaData()
Base = declarative_base(metadata=metadata)

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

    # Safe column migrations
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names(schema=DB_SCHEMA) if DB_SCHEMA else inspector.get_table_names()
        with engine.connect() as conn:
            prefix = f'"{DB_SCHEMA}".' if DB_SCHEMA else ""
            if "users" in tables:
                user_cols = [c["name"] for c in inspector.get_columns("users", schema=DB_SCHEMA)]
                if "default_payment_terms" not in user_cols:
                    conn.execute(text(f"ALTER TABLE {prefix}users ADD COLUMN default_payment_terms VARCHAR(500)"))
                if "default_warranty_terms" not in user_cols:
                    conn.execute(text(f"ALTER TABLE {prefix}users ADD COLUMN default_warranty_terms VARCHAR(500)"))
                conn.execute(text(f"UPDATE {prefix}users SET default_payment_terms = 'A combinar / 50% na aprovação e 50% na entrega.' WHERE default_payment_terms IS NULL"))
                conn.execute(text(f"UPDATE {prefix}users SET default_warranty_terms = 'Garantia de fabricação contra defeitos dimensionais ou delaminação de camadas conforme especificações acordadas.' WHERE default_warranty_terms IS NULL"))
            if "filaments" in tables:
                fil_cols = [c["name"] for c in inspector.get_columns("filaments", schema=DB_SCHEMA)]
                if "color_hex" not in fil_cols:
                    conn.execute(text(f"ALTER TABLE {prefix}filaments ADD COLUMN color_hex VARCHAR(20) DEFAULT '#10b981'"))
            if "projects" in tables:
                proj_cols = [c["name"] for c in inspector.get_columns("projects", schema=DB_SCHEMA)]
                if "delivery_days" not in proj_cols:
                    conn.execute(text(f"ALTER TABLE {prefix}projects ADD COLUMN delivery_days INTEGER DEFAULT 3"))
                if "payment_terms" not in proj_cols:
                    conn.execute(text(f"ALTER TABLE {prefix}projects ADD COLUMN payment_terms VARCHAR(500)"))
                if "warranty_terms" not in proj_cols:
                    conn.execute(text(f"ALTER TABLE {prefix}projects ADD COLUMN warranty_terms VARCHAR(500)"))
            if "plates" in tables:
                plate_cols = [c["name"] for c in inspector.get_columns("plates", schema=DB_SCHEMA)]
                if "slicer_filament_profile" not in plate_cols:
                    conn.execute(text(f"ALTER TABLE {prefix}plates ADD COLUMN slicer_filament_profile VARCHAR(255)"))
            conn.commit()
    except Exception as e:
        pass
