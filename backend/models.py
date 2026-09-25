import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from backend.database import Base, DB_SCHEMA

def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": DB_SCHEMA} if DB_SCHEMA else {}

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    company_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    pix_key = Column(String(255), nullable=True)

    # User defaults for quick quotes
    default_energy_rate = Column(Float, default=0.85)  # R$/kWh
    default_failure_rate = Column(Float, default=10.0)  # %
    default_profit_margin = Column(Float, default=30.0)  # %
    default_tax_rate = Column(Float, default=6.0)  # %
    default_cad_rate = Column(Float, default=50.0)  # R$/h
    default_post_rate = Column(Float, default=30.0)  # R$/h
    default_payment_terms = Column(String(500), nullable=True, default="A combinar / 50% na aprovação e 50% na entrega.")
    default_warranty_terms = Column(String(500), nullable=True, default="Garantia de fabricação contra defeitos dimensionais ou delaminação de camadas conforme especificações acordadas.")

    created_at = Column(DateTime, default=get_utc_now)

    # Relationships
    printers = relationship("Printer", back_populates="user", cascade="all, delete-orphan")
    filaments = relationship("Filament", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")


class Printer(Base):
    __tablename__ = "printers"
    __table_args__ = {"schema": DB_SCHEMA} if DB_SCHEMA else {}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.users.id" if DB_SCHEMA else "users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    model = Column(String(255), nullable=True)
    acquisition_cost = Column(Float, default=0.0)  # R$
    lifespan_hours = Column(Float, default=5000.0)  # Total operational hours
    avg_power_watts = Column(Float, default=150.0)  # Watts
    maintenance_cost_per_hour = Column(Float, default=1.0)  # R$/h reserve
    energy_rate_kwh = Column(Float, default=0.85)  # R$/kWh
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    user = relationship("User", back_populates="printers")
    plates = relationship("Plate", back_populates="printer")


class Filament(Base):
    __tablename__ = "filaments"
    __table_args__ = {"schema": DB_SCHEMA} if DB_SCHEMA else {}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.users.id" if DB_SCHEMA else "users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    brand = Column(String(255), nullable=True)
    material = Column(String(100), default="PLA")  # PLA, PETG, ABS, TPU, ASA, Resin, etc.
    color = Column(String(100), nullable=True)
    color_hex = Column(String(20), default="#10b981", nullable=True)
    spool_weight_g = Column(Float, default=1000.0)  # grams
    spool_price = Column(Float, default=90.0)  # R$
    density_g_cm3 = Column(Float, default=1.24)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    user = relationship("User", back_populates="filaments")
    plates = relationship("Plate", back_populates="filament")


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = {"schema": DB_SCHEMA} if DB_SCHEMA else {}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.users.id" if DB_SCHEMA else "users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    client_name = Column(String(255), nullable=True)
    client_email = Column(String(255), nullable=True)
    client_phone = Column(String(50), nullable=True)
    status = Column(String(50), default="draft")  # draft, quoted, approved, in_production, completed, cancelled

    # Service & labor costs
    cad_hours = Column(Float, default=0.0)
    cad_hourly_rate = Column(Float, default=0.0)
    post_process_hours = Column(Float, default=0.0)
    post_process_hourly_rate = Column(Float, default=0.0)

    # Overhead, margin, tax and commercial adjustments
    overhead_cost = Column(Float, default=0.0)  # Fixed or indirect cost (packaging, operational)
    profit_margin_percent = Column(Float, default=30.0)  # %
    tax_rate_percent = Column(Float, default=6.0)  # %
    discount_percent = Column(Float, default=0.0)  # %
    shipping_cost = Column(Float, default=0.0)  # R$
    delivery_days = Column(Integer, default=3, nullable=True)  # Prazo de entrega em dias úteis
    payment_terms = Column(String(500), nullable=True)
    warranty_terms = Column(String(500), nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    user = relationship("User", back_populates="projects")
    plates = relationship("Plate", back_populates="project", cascade="all, delete-orphan")
    bom_items = relationship("BOMItem", back_populates="project", cascade="all, delete-orphan")


class Plate(Base):
    __tablename__ = "plates"
    __table_args__ = {"schema": DB_SCHEMA} if DB_SCHEMA else {}

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.projects.id" if DB_SCHEMA else "projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # e.g. "Placa 1 - Estrutura"
    printer_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.printers.id" if DB_SCHEMA else "printers.id", ondelete="SET NULL"), nullable=True)
    filament_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.filaments.id" if DB_SCHEMA else "filaments.id", ondelete="SET NULL"), nullable=True)

    # Custom override values if user has no saved printer or filament
    custom_printer_hourly_rate = Column(Float, nullable=True)
    custom_filament_cost_per_g = Column(Float, nullable=True)

    print_time_hours = Column(Float, default=0.0)
    part_weight_g = Column(Float, default=0.0)
    purge_weight_g = Column(Float, default=0.0)
    failure_margin_percent = Column(Float, default=10.0)
    quantity = Column(Integer, default=1)  # Number of times this plate is printed
    slicer_filament_profile = Column(String(255), nullable=True)  # Profile name from slicer G-code / 3MF
    notes = Column(Text, nullable=True)

    project = relationship("Project", back_populates="plates")
    printer = relationship("Printer", back_populates="plates")
    filament = relationship("Filament", back_populates="plates")


class BOMItem(Base):
    __tablename__ = "bom_items"
    __table_args__ = {"schema": DB_SCHEMA} if DB_SCHEMA else {}

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.projects.id" if DB_SCHEMA else "projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # e.g. "Parafuso M3x12", "Rolamento 608zz"
    category = Column(String(100), default="Fixadores")  # Fixadores, Eletrônica, Embalagem, Ferragens, Outros
    quantity = Column(Integer, default=1)
    unit_cost = Column(Float, default=0.0)  # R$ per unit
    notes = Column(Text, nullable=True)

    project = relationship("Project", back_populates="bom_items")
