from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models, schemas
from backend.auth import get_current_user

router = APIRouter(prefix="/api/filaments", tags=["Filamentos"])

def enrich_filament_response(filament: models.Filament) -> schemas.FilamentResponse:
    cost_per_gram = (filament.spool_price / filament.spool_weight_g) if filament.spool_weight_g > 0 else 0.0
    res = schemas.FilamentResponse.model_validate(filament)
    res.cost_per_gram = round(cost_per_gram, 4)
    return res

@router.get("", response_model=List[schemas.FilamentResponse])
def list_filaments(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filaments = db.query(models.Filament).filter(models.Filament.user_id == current_user.id).order_by(models.Filament.id.desc()).all()
    return [enrich_filament_response(f) for f in filaments]

@router.post("", response_model=schemas.FilamentResponse, status_code=status.HTTP_201_CREATED)
def create_filament(
    filament_in: schemas.FilamentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filament = models.Filament(
        user_id=current_user.id,
        **filament_in.model_dump()
    )
    db.add(filament)
    db.commit()
    db.refresh(filament)
    return enrich_filament_response(filament)

@router.get("/{filament_id}", response_model=schemas.FilamentResponse)
def get_filament(
    filament_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filament = db.query(models.Filament).filter(
        models.Filament.id == filament_id,
        models.Filament.user_id == current_user.id
    ).first()
    if not filament:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filamento não encontrado.")
    return enrich_filament_response(filament)

@router.put("/{filament_id}", response_model=schemas.FilamentResponse)
def update_filament(
    filament_id: int,
    filament_update: schemas.FilamentUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filament = db.query(models.Filament).filter(
        models.Filament.id == filament_id,
        models.Filament.user_id == current_user.id
    ).first()
    if not filament:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filamento não encontrado.")

    for field, value in filament_update.model_dump(exclude_unset=True).items():
        setattr(filament, field, value)

    db.commit()
    db.refresh(filament)
    return enrich_filament_response(filament)

@router.delete("/{filament_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_filament(
    filament_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filament = db.query(models.Filament).filter(
        models.Filament.id == filament_id,
        models.Filament.user_id == current_user.id
    ).first()
    if not filament:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filamento não encontrado.")

    db.delete(filament)
    db.commit()
    return None
