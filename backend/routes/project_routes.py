from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session

from fastapi.security import HTTPAuthorizationCredentials
from backend.database import get_db
from backend import models, schemas
from backend.auth import get_current_user, get_user_from_token, security
from backend.engine import calculate_project_summary, calculate_plate_cost
from backend.pdf_service import build_pdf_document

router = APIRouter(prefix="/api/projects", tags=["Projetos & Orçamentos"])

def get_user_project(project_id: int, user_id: int, db: Session) -> models.Project:
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == user_id
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")
    return project

def build_project_response(project: models.Project, db: Session) -> schemas.ProjectResponse:
    # Build maps of user printers and filaments for fast engine calculation
    printers = db.query(models.Printer).filter(models.Printer.user_id == project.user_id).all()
    filaments = db.query(models.Filament).filter(models.Filament.user_id == project.user_id).all()
    printers_map = {p.id: p for p in printers}
    filaments_map = {f.id: f for f in filaments}

    summary = calculate_project_summary(
        project=project,
        plates=project.plates,
        bom_items=project.bom_items,
        printers_by_id=printers_map,
        filaments_by_id=filaments_map
    )

    # Enrich plates with cost breakdown
    plate_responses = []
    for p in project.plates:
        pr = printers_map.get(p.printer_id)
        fl = filaments_map.get(p.filament_id)
        c_breakdown = calculate_plate_cost(p, printer=pr, filament=fl)
        p_res = schemas.PlateResponse.model_validate(p)
        p_res.cost_breakdown = c_breakdown
        plate_responses.append(p_res)

    # Enrich BOM items
    bom_responses = []
    for b in project.bom_items:
        b_res = schemas.BOMItemResponse.model_validate(b)
        b_res.subtotal = round(b.quantity * b.unit_cost, 2)
        bom_responses.append(b_res)

    res = schemas.ProjectResponse.model_validate(project)
    res.plates = plate_responses
    res.bom_items = bom_responses
    res.summary = summary
    return res

@router.get("", response_model=List[schemas.ProjectListItem])
def list_projects(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    projects = db.query(models.Project).filter(
        models.Project.user_id == current_user.id
    ).order_by(models.Project.id.desc()).all()

    printers = db.query(models.Printer).filter(models.Printer.user_id == current_user.id).all()
    filaments = db.query(models.Filament).filter(models.Filament.user_id == current_user.id).all()
    printers_map = {p.id: p for p in printers}
    filaments_map = {f.id: f for f in filaments}

    results = []
    for proj in projects:
        summary = calculate_project_summary(
            project=proj,
            plates=proj.plates,
            bom_items=proj.bom_items,
            printers_by_id=printers_map,
            filaments_by_id=filaments_map
        )
        results.append(schemas.ProjectListItem(
            id=proj.id,
            name=proj.name,
            client_name=proj.client_name,
            status=proj.status,
            created_at=proj.created_at,
            updated_at=proj.updated_at,
            plates_count=len(proj.plates),
            total_time_hours=summary["total_print_time_hours"],
            total_filament_weight_g=summary["total_filament_weight_g"],
            base_cost=summary["base_cost"],
            final_price_to_client=summary["final_price_to_client"],
        ))
    return results

@router.post("", response_model=schemas.ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    proj_in: schemas.ProjectCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # If project margins/rates are default 0 or user wants their profile defaults
    proj_data = proj_in.model_dump(exclude={"plates", "bom_items"})
    project = models.Project(
        user_id=current_user.id,
        **proj_data
    )
    db.add(project)
    db.flush()

    if proj_in.plates:
        for p_data in proj_in.plates:
            plate = models.Plate(
                project_id=project.id,
                **p_data.model_dump()
            )
            db.add(plate)

    if proj_in.bom_items:
        for b_data in proj_in.bom_items:
            bom = models.BOMItem(
                project_id=project.id,
                **b_data.model_dump()
            )
            db.add(bom)

    db.commit()
    db.refresh(project)
    return build_project_response(project, db)

@router.get("/{project_id}", response_model=schemas.ProjectResponse)
def get_project(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_user_project(project_id, current_user.id, db)
    return build_project_response(project, db)

@router.put("/{project_id}", response_model=schemas.ProjectResponse)
def update_project(
    project_id: int,
    proj_update: schemas.ProjectUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_user_project(project_id, current_user.id, db)
    update_data = proj_update.model_dump(exclude_unset=True, exclude={"plates", "bom_items"})
    for field, value in update_data.items():
        setattr(project, field, value)

    if proj_update.plates is not None:
        project.plates.clear()
        for p_data in proj_update.plates:
            plate = models.Plate(
                project_id=project.id,
                **p_data.model_dump()
            )
            db.add(plate)

    if proj_update.bom_items is not None:
        project.bom_items.clear()
        for b_data in proj_update.bom_items:
            bom = models.BOMItem(
                project_id=project.id,
                **b_data.model_dump()
            )
            db.add(bom)

    db.commit()
    db.refresh(project)
    return build_project_response(project, db)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_user_project(project_id, current_user.id, db)
    db.delete(project)
    db.commit()
    return None

@router.post("/{project_id}/duplicate", response_model=schemas.ProjectResponse)
def duplicate_project(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    orig = get_user_project(project_id, current_user.id, db)
    cloned = models.Project(
        user_id=current_user.id,
        name=f"{orig.name} (Cópia)",
        client_name=orig.client_name,
        client_email=orig.client_email,
        client_phone=orig.client_phone,
        status="draft",
        cad_hours=orig.cad_hours,
        cad_hourly_rate=orig.cad_hourly_rate,
        post_process_hours=orig.post_process_hours,
        post_process_hourly_rate=orig.post_process_hourly_rate,
        overhead_cost=orig.overhead_cost,
        profit_margin_percent=orig.profit_margin_percent,
        tax_rate_percent=orig.tax_rate_percent,
        discount_percent=orig.discount_percent,
        shipping_cost=orig.shipping_cost,
        delivery_days=orig.delivery_days,
        payment_terms=orig.payment_terms,
        warranty_terms=orig.warranty_terms,
        notes=orig.notes,
    )
    db.add(cloned)
    db.flush()

    for pl in orig.plates:
        c_plate = models.Plate(
            project_id=cloned.id,
            name=pl.name,
            printer_id=pl.printer_id,
            filament_id=pl.filament_id,
            custom_printer_hourly_rate=pl.custom_printer_hourly_rate,
            custom_filament_cost_per_g=pl.custom_filament_cost_per_g,
            print_time_hours=pl.print_time_hours,
            part_weight_g=pl.part_weight_g,
            purge_weight_g=pl.purge_weight_g,
            failure_margin_percent=pl.failure_margin_percent,
            quantity=pl.quantity,
            notes=pl.notes,
        )
        db.add(c_plate)

    for bm in orig.bom_items:
        c_bom = models.BOMItem(
            project_id=cloned.id,
            name=bm.name,
            category=bm.category,
            quantity=bm.quantity,
            unit_cost=bm.unit_cost,
            notes=bm.notes,
        )
        db.add(c_bom)

    db.commit()
    db.refresh(cloned)
    return build_project_response(cloned, db)

# ----------------- Plates Endpoints -----------------

@router.post("/{project_id}/plates", response_model=schemas.PlateResponse, status_code=status.HTTP_201_CREATED)
def add_plate(
    project_id: int,
    plate_in: schemas.PlateCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_user_project(project_id, current_user.id, db)
    plate = models.Plate(
        project_id=project.id,
        **plate_in.model_dump()
    )
    db.add(plate)
    db.commit()
    db.refresh(plate)

    printer = db.query(models.Printer).filter(models.Printer.id == plate.printer_id).first() if plate.printer_id else None
    filament = db.query(models.Filament).filter(models.Filament.id == plate.filament_id).first() if plate.filament_id else None
    c_breakdown = calculate_plate_cost(plate, printer=printer, filament=filament)

    res = schemas.PlateResponse.model_validate(plate)
    res.cost_breakdown = c_breakdown
    return res

@router.put("/{project_id}/plates/{plate_id}", response_model=schemas.PlateResponse)
def update_plate(
    project_id: int,
    plate_id: int,
    plate_update: schemas.PlateUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_user_project(project_id, current_user.id, db)
    plate = db.query(models.Plate).filter(
        models.Plate.id == plate_id,
        models.Plate.project_id == project.id
    ).first()
    if not plate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Placa não encontrada.")

    for field, value in plate_update.model_dump(exclude_unset=True).items():
        setattr(plate, field, value)

    db.commit()
    db.refresh(plate)

    printer = db.query(models.Printer).filter(models.Printer.id == plate.printer_id).first() if plate.printer_id else None
    filament = db.query(models.Filament).filter(models.Filament.id == plate.filament_id).first() if plate.filament_id else None
    c_breakdown = calculate_plate_cost(plate, printer=printer, filament=filament)

    res = schemas.PlateResponse.model_validate(plate)
    res.cost_breakdown = c_breakdown
    return res

@router.delete("/{project_id}/plates/{plate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plate(
    project_id: int,
    plate_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_user_project(project_id, current_user.id, db)
    plate = db.query(models.Plate).filter(
        models.Plate.id == plate_id,
        models.Plate.project_id == project.id
    ).first()
    if not plate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Placa não encontrada.")

    db.delete(plate)
    db.commit()
    return None

# ----------------- BOM Endpoints -----------------

@router.post("/{project_id}/bom", response_model=schemas.BOMItemResponse, status_code=status.HTTP_201_CREATED)
def add_bom_item(
    project_id: int,
    bom_in: schemas.BOMItemCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_user_project(project_id, current_user.id, db)
    bom = models.BOMItem(
        project_id=project.id,
        **bom_in.model_dump()
    )
    db.add(bom)
    db.commit()
    db.refresh(bom)

    res = schemas.BOMItemResponse.model_validate(bom)
    res.subtotal = round(bom.quantity * bom.unit_cost, 2)
    return res

@router.put("/{project_id}/bom/{bom_id}", response_model=schemas.BOMItemResponse)
def update_bom_item(
    project_id: int,
    bom_id: int,
    bom_update: schemas.BOMItemUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_user_project(project_id, current_user.id, db)
    bom = db.query(models.BOMItem).filter(
        models.BOMItem.id == bom_id,
        models.BOMItem.project_id == project.id
    ).first()
    if not bom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item BOM não encontrado.")

    for field, value in bom_update.model_dump(exclude_unset=True).items():
        setattr(bom, field, value)

    db.commit()
    db.refresh(bom)

    res = schemas.BOMItemResponse.model_validate(bom)
    res.subtotal = round(bom.quantity * bom.unit_cost, 2)
    return res

@router.delete("/{project_id}/bom/{bom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bom_item(
    project_id: int,
    bom_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_user_project(project_id, current_user.id, db)
    bom = db.query(models.BOMItem).filter(
        models.BOMItem.id == bom_id,
        models.BOMItem.project_id == project.id
    ).first()
    if not bom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item BOM não encontrado.")

    db.delete(bom)
    db.commit()
    return None

# ----------------- Summary & PDF Endpoints -----------------

@router.get("/{project_id}/summary")
def get_summary(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_user_project(project_id, current_user.id, db)
    printers = db.query(models.Printer).filter(models.Printer.user_id == current_user.id).all()
    filaments = db.query(models.Filament).filter(models.Filament.user_id == current_user.id).all()
    printers_map = {p.id: p for p in printers}
    filaments_map = {f.id: f for f in filaments}

    return calculate_project_summary(
        project=project,
        plates=project.plates,
        bom_items=project.bom_items,
        printers_by_id=printers_map,
        filaments_by_id=filaments_map
    )

@router.get("/{project_id}/pdf")
def export_pdf(
    project_id: int,
    type: str = Query("client", pattern="^(client|technical)$"),
    disposition: str = Query("inline", pattern="^(inline|attachment)$"),
    token: Optional[str] = Query(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    import unicodedata
    current_user = None
    if credentials and credentials.credentials:
        current_user = get_user_from_token(credentials.credentials, db)
    if not current_user and token:
        current_user = get_user_from_token(token, db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas ou token expirado",
            headers={"WWW-Authenticate": "Bearer"}
        )

    project = get_user_project(project_id, current_user.id, db)
    proj_resp = build_project_response(project, db)
    
    user_dict = {
        "full_name": current_user.full_name,
        "company_name": current_user.company_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "pix_key": current_user.pix_key,
        "default_payment_terms": current_user.default_payment_terms,
        "default_warranty_terms": current_user.default_warranty_terms,
    }
    
    pdf_buffer = build_pdf_document(
        project_data=proj_resp.model_dump(),
        user_data=user_dict,
        doc_type=type
    )

    filename_suffix = "orcamento" if type == "client" else "ficha_producao"
    ascii_name = unicodedata.normalize('NFKD', project.name).encode('ASCII', 'ignore').decode('ASCII')
    safe_name = "".join(c for c in ascii_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
    filename = f"{filename_suffix}_{safe_name or 'projeto'}_{project.id}.pdf"

    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"{disposition}; filename=\"{filename}\""
        }
    )
