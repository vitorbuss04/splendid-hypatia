from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict
import datetime

# ----------------- Auth & User Schemas -----------------

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    company_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserPreferencesUpdate(BaseModel):
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    pix_key: Optional[str] = None
    default_energy_rate: Optional[float] = Field(None, ge=0)
    default_failure_rate: Optional[float] = Field(None, ge=0)
    default_profit_margin: Optional[float] = Field(None, ge=0)
    default_tax_rate: Optional[float] = Field(None, ge=0, le=99.0)
    default_cad_rate: Optional[float] = Field(None, ge=0)
    default_post_rate: Optional[float] = Field(None, ge=0)

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    pix_key: Optional[str] = None
    default_energy_rate: float
    default_failure_rate: float
    default_profit_margin: float
    default_tax_rate: float
    default_cad_rate: float
    default_post_rate: float
    created_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ----------------- Printer Schemas -----------------

class PrinterBase(BaseModel):
    name: str
    model: Optional[str] = None
    acquisition_cost: float = Field(0.0, ge=0)
    lifespan_hours: float = Field(5000.0, gt=0)
    avg_power_watts: float = Field(150.0, ge=0)
    maintenance_cost_per_hour: float = Field(1.0, ge=0)
    energy_rate_kwh: float = Field(0.85, ge=0)
    is_active: bool = True
    notes: Optional[str] = None

class PrinterCreate(PrinterBase):
    pass

class PrinterUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    acquisition_cost: Optional[float] = Field(None, ge=0)
    lifespan_hours: Optional[float] = Field(None, gt=0)
    avg_power_watts: Optional[float] = Field(None, ge=0)
    maintenance_cost_per_hour: Optional[float] = Field(None, ge=0)
    energy_rate_kwh: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class PrinterResponse(PrinterBase):
    id: int
    user_id: int
    created_at: Optional[datetime.datetime] = None
    machine_hourly_rate: float = 0.0
    rates_breakdown: Optional[Dict[str, float]] = None

    model_config = ConfigDict(from_attributes=True)


# ----------------- Filament Schemas -----------------

class FilamentBase(BaseModel):
    name: str
    brand: Optional[str] = None
    material: str = "PLA"
    color: Optional[str] = None
    spool_weight_g: float = Field(1000.0, gt=0)
    spool_price: float = Field(90.0, ge=0)
    density_g_cm3: float = Field(1.24, gt=0)
    is_active: bool = True
    notes: Optional[str] = None

class FilamentCreate(FilamentBase):
    pass

class FilamentUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    material: Optional[str] = None
    color: Optional[str] = None
    spool_weight_g: Optional[float] = Field(None, gt=0)
    spool_price: Optional[float] = Field(None, ge=0)
    density_g_cm3: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class FilamentResponse(FilamentBase):
    id: int
    user_id: int
    created_at: Optional[datetime.datetime] = None
    cost_per_gram: float = 0.0

    model_config = ConfigDict(from_attributes=True)


# ----------------- Plate Schemas -----------------

class PlateBase(BaseModel):
    name: str = "Placa 1"
    printer_id: Optional[int] = None
    filament_id: Optional[int] = None
    custom_printer_hourly_rate: Optional[float] = None
    custom_filament_cost_per_g: Optional[float] = None
    print_time_hours: float = Field(0.0, ge=0)
    part_weight_g: float = Field(0.0, ge=0)
    purge_weight_g: float = Field(0.0, ge=0)
    failure_margin_percent: float = Field(10.0, ge=0)
    quantity: int = Field(1, ge=1)
    notes: Optional[str] = None

class PlateCreate(PlateBase):
    pass

class PlateUpdate(BaseModel):
    name: Optional[str] = None
    printer_id: Optional[int] = None
    filament_id: Optional[int] = None
    custom_printer_hourly_rate: Optional[float] = None
    custom_filament_cost_per_g: Optional[float] = None
    print_time_hours: Optional[float] = Field(None, ge=0)
    part_weight_g: Optional[float] = Field(None, ge=0)
    purge_weight_g: Optional[float] = Field(None, ge=0)
    failure_margin_percent: Optional[float] = Field(None, ge=0)
    quantity: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None

class PlateResponse(PlateBase):
    id: int
    project_id: int
    cost_breakdown: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


# ----------------- BOM Items Schemas -----------------

class BOMItemBase(BaseModel):
    name: str
    category: str = "Fixadores"
    quantity: int = Field(1, ge=0)
    unit_cost: float = Field(0.0, ge=0)
    notes: Optional[str] = None

class BOMItemCreate(BOMItemBase):
    pass

class BOMItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[int] = Field(None, ge=0)
    unit_cost: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None

class BOMItemResponse(BOMItemBase):
    id: int
    project_id: int
    subtotal: float = 0.0

    model_config = ConfigDict(from_attributes=True)


# ----------------- Project Schemas -----------------

class ProjectBase(BaseModel):
    name: str
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    status: str = "draft"
    cad_hours: float = Field(0.0, ge=0)
    cad_hourly_rate: float = Field(0.0, ge=0)
    post_process_hours: float = Field(0.0, ge=0)
    post_process_hourly_rate: float = Field(0.0, ge=0)
    overhead_cost: float = Field(0.0, ge=0)
    profit_margin_percent: float = Field(30.0, ge=0)
    tax_rate_percent: float = Field(6.0, ge=0, le=99.0)
    discount_percent: float = Field(0.0, ge=0, le=100.0)
    shipping_cost: float = Field(0.0, ge=0)
    notes: Optional[str] = None

class ProjectCreate(ProjectBase):
    plates: Optional[List[PlateCreate]] = None
    bom_items: Optional[List[BOMItemCreate]] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    status: Optional[str] = None
    cad_hours: Optional[float] = Field(None, ge=0)
    cad_hourly_rate: Optional[float] = Field(None, ge=0)
    post_process_hours: Optional[float] = Field(None, ge=0)
    post_process_hourly_rate: Optional[float] = Field(None, ge=0)
    overhead_cost: Optional[float] = Field(None, ge=0)
    profit_margin_percent: Optional[float] = Field(None, ge=0)
    tax_rate_percent: Optional[float] = Field(None, ge=0, le=99.0)
    discount_percent: Optional[float] = Field(None, ge=0, le=100.0)
    shipping_cost: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None
    plates: Optional[List[PlateCreate]] = None
    bom_items: Optional[List[BOMItemCreate]] = None

class ProjectListItem(BaseModel):
    id: int
    name: str
    client_name: Optional[str] = None
    status: str
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    plates_count: int = 0
    total_time_hours: float = 0.0
    total_filament_weight_g: float = 0.0
    base_cost: float = 0.0
    final_price_to_client: float = 0.0

class ProjectResponse(ProjectBase):
    id: int
    user_id: int
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    plates: List[PlateResponse] = []
    bom_items: List[BOMItemResponse] = []
    summary: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
