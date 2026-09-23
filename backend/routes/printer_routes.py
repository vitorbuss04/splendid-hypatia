from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models, schemas
from backend.auth import get_current_user
from backend.engine import calculate_printer_hourly_rate

router = APIRouter(prefix="/api/printers", tags=["Impressoras"])

def enrich_printer_response(printer: models.Printer) -> schemas.PrinterResponse:
    rates = calculate_printer_hourly_rate(
        acquisition_cost=printer.acquisition_cost,
        lifespan_hours=printer.lifespan_hours,
        avg_power_watts=printer.avg_power_watts,
        energy_rate_kwh=printer.energy_rate_kwh,
        maintenance_cost_per_hour=printer.maintenance_cost_per_hour,
    )
    res = schemas.PrinterResponse.model_validate(printer)
    res.machine_hourly_rate = rates["machine_hourly_rate"]
    res.rates_breakdown = rates
    return res

@router.get("", response_model=List[schemas.PrinterResponse])
def list_printers(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    printers = db.query(models.Printer).filter(models.Printer.user_id == current_user.id).order_by(models.Printer.id.desc()).all()
    return [enrich_printer_response(p) for p in printers]

@router.post("", response_model=schemas.PrinterResponse, status_code=status.HTTP_201_CREATED)
def create_printer(
    printer_in: schemas.PrinterCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    printer = models.Printer(
        user_id=current_user.id,
        **printer_in.model_dump()
    )
    db.add(printer)
    db.commit()
    db.refresh(printer)
    return enrich_printer_response(printer)

@router.get("/{printer_id}", response_model=schemas.PrinterResponse)
def get_printer(
    printer_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    printer = db.query(models.Printer).filter(
        models.Printer.id == printer_id,
        models.Printer.user_id == current_user.id
    ).first()
    if not printer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Impressora não encontrada.")
    return enrich_printer_response(printer)

@router.put("/{printer_id}", response_model=schemas.PrinterResponse)
def update_printer(
    printer_id: int,
    printer_update: schemas.PrinterUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    printer = db.query(models.Printer).filter(
        models.Printer.id == printer_id,
        models.Printer.user_id == current_user.id
    ).first()
    if not printer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Impressora não encontrada.")

    for field, value in printer_update.model_dump(exclude_unset=True).items():
        setattr(printer, field, value)

    db.commit()
    db.refresh(printer)
    return enrich_printer_response(printer)

@router.delete("/{printer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_printer(
    printer_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    printer = db.query(models.Printer).filter(
        models.Printer.id == printer_id,
        models.Printer.user_id == current_user.id
    ).first()
    if not printer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Impressora não encontrada.")

    db.delete(printer)
    db.commit()
    return None
