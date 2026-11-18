from typing import List, Optional
import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session

from fastapi.security import HTTPAuthorizationCredentials
from backend.database import get_db
from backend import models, schemas
from backend.auth import get_current_user, get_user_from_token, security
from backend.engine import calculate_project_summary, calculate_plate_cost, calculate_failure_cost
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
        filaments_by_id=filaments_map,
        failure_logs=project.failure_logs,
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

    # Enrich failure logs
    failure_responses = []
    for f in project.failure_logs:
        f_res = schemas.PlateFailureLogResponse.model_validate(f)
        failure_responses.append(f_res)

    res = schemas.ProjectResponse.model_validate(project)
    res.plates = plate_responses
    res.bom_items = bom_responses
    res.failure_logs = failure_responses
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

MONTH_NAMES_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
}

@router.get("/dashboard-stats", response_model=schemas.DashboardStatsResponse)
def get_dashboard_stats(
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

    total_projects = len(projects)
    total_printers = len(printers)
    total_filaments = len(filaments)

    active_quotes = 0
    total_revenue_approved = 0.0
    pipeline_revenue = 0.0
    total_net_profit = 0.0
    total_print_hours = 0.0
    total_filament_g = 0.0
    total_scrap_cost = 0.0
    total_scrap_filament_g = 0.0
    margins_sum = 0.0
    margins_count = 0

    status_counts = {
        "draft": 0,
        "quoted": 0,
        "approved": 0,
        "in_production": 0,
        "completed": 0,
        "cancelled": 0,
    }
    status_values = {
        "draft": 0.0,
        "quoted": 0.0,
        "approved": 0.0,
        "in_production": 0.0,
        "completed": 0.0,
        "cancelled": 0.0,
    }

    material_cost = 0.0
    machine_energy_cost = 0.0
    labor_cost = 0.0
    bom_cost = 0.0
    overhead_cost = 0.0
    profit_acc = 0.0

    monthly_data = {}
    project_items = []

    for proj in projects:
        summary = calculate_project_summary(
            project=proj,
            plates=proj.plates,
            bom_items=proj.bom_items,
            printers_by_id=printers_map,
            filaments_by_id=filaments_map,
            failure_logs=proj.failure_logs,
        )

        st = proj.status or "draft"
        if st not in status_counts:
            status_counts[st] = 0
            status_values[st] = 0.0
        status_counts[st] += 1

        final_price = float(summary.get("final_price_to_client", 0.0) or 0.0)
        base_cost = float(summary.get("base_cost", 0.0) or 0.0)
        net_profit = float(summary.get("net_profit", 0.0) or 0.0)
        hours = float(summary.get("total_print_time_hours", 0.0) or 0.0)
        weight = float(summary.get("total_filament_weight_g", 0.0) or 0.0)
        scrap_c = float(summary.get("total_scrap_cost", 0.0) or 0.0)
        scrap_w = float(summary.get("total_scrap_filament_g", 0.0) or 0.0)

        total_scrap_cost += scrap_c
        total_scrap_filament_g += scrap_w

        status_values[st] = round(status_values[st] + final_price, 2)

        if st in ["draft", "quoted", "in_production"]:
            active_quotes += 1

        if st in ["approved", "in_production", "completed"]:
            total_revenue_approved += final_price
            total_net_profit += net_profit
            total_print_hours += hours
            total_filament_g += weight
        elif st in ["draft", "quoted"]:
            pipeline_revenue += final_price

        if base_cost > 0:
            eff_margin = float(summary.get("effective_profit_margin_percent", 0.0) or 0.0)
            margins_sum += eff_margin
            margins_count += 1

        material_cost += float(summary.get("total_material_cost", 0.0) or 0.0)
        machine_energy_cost += float(summary.get("total_machine_cost", 0.0) or 0.0) + float(summary.get("total_energy_cost", 0.0) or 0.0)
        labor_cost += float(summary.get("total_labor_cost", 0.0) or 0.0)
        bom_cost += float(summary.get("total_bom_cost", 0.0) or 0.0)
        overhead_cost += float(summary.get("overhead_cost", 0.0) or 0.0)
        profit_acc += max(0.0, net_profit)

        created_dt = proj.created_at or datetime.datetime.now()
        month_key = created_dt.strftime("%Y-%m")
        pt_m = MONTH_NAMES_PT.get(created_dt.month, str(created_dt.month))
        year_short = created_dt.strftime("%y")
        month_label = f"{pt_m}/{year_short}"

        if month_key not in monthly_data:
            monthly_data[month_key] = {
                "month_key": month_key,
                "month_label": month_label,
                "revenue": 0.0,
                "base_cost": 0.0,
                "net_profit": 0.0,
                "print_hours": 0.0,
                "projects_count": 0,
            }
        monthly_data[month_key]["revenue"] = round(monthly_data[month_key]["revenue"] + final_price, 2)
        monthly_data[month_key]["base_cost"] = round(monthly_data[month_key]["base_cost"] + base_cost, 2)
        monthly_data[month_key]["net_profit"] = round(monthly_data[month_key]["net_profit"] + net_profit, 2)
        monthly_data[month_key]["print_hours"] = round(monthly_data[month_key]["print_hours"] + hours, 2)
        monthly_data[month_key]["projects_count"] += 1

        project_items.append(schemas.TopProjectItem(
            id=proj.id,
            name=proj.name,
            client_name=proj.client_name,
            status=proj.status,
            final_price=round(final_price, 2),
            net_profit=round(net_profit, 2),
            print_hours=round(hours, 2),
        ))

    # Pad with recent months up to 6 months
    now = datetime.datetime.now()
    for i in range(5, -1, -1):
        y = now.year
        m = now.month - i
        while m <= 0:
            m += 12
            y -= 1
        pad_key = f"{y:04d}-{m:02d}"
        if pad_key not in monthly_data:
            pt_m = MONTH_NAMES_PT.get(m, str(m))
            year_short = str(y)[-2:]
            monthly_data[pad_key] = {
                "month_key": pad_key,
                "month_label": f"{pt_m}/{year_short}",
                "revenue": 0.0,
                "base_cost": 0.0,
                "net_profit": 0.0,
                "print_hours": 0.0,
                "projects_count": 0,
            }

    sorted_months = [monthly_data[k] for k in sorted(monthly_data.keys())]

    top_projects = sorted(project_items, key=lambda x: x.final_price, reverse=True)[:5]
    avg_margin = round(margins_sum / margins_count, 1) if margins_count > 0 else 0.0
    total_all_filament_g = total_filament_g + total_scrap_filament_g
    overall_scrap_rate = round((total_scrap_filament_g / total_all_filament_g * 100.0), 1) if total_all_filament_g > 0 else 0.0

    return schemas.DashboardStatsResponse(
        total_projects=total_projects,
        active_quotes=active_quotes,
        total_printers=total_printers,
        total_filaments=total_filaments,
        total_revenue_approved=round(total_revenue_approved, 2),
        pipeline_revenue=round(pipeline_revenue, 2),
        total_net_profit=round(total_net_profit, 2),
        total_print_hours=round(total_print_hours, 2),
        total_filament_kg=round(total_filament_g / 1000.0, 2),
        avg_profit_margin_percent=avg_margin,
        status_counts=status_counts,
        status_values=status_values,
        monthly_timeline=[schemas.MonthlyTimelineItem(**item) for item in sorted_months],
        cost_breakdown=schemas.CostBreakdownTotals(
            material_cost=round(material_cost, 2),
            machine_energy_cost=round(machine_energy_cost, 2),
            labor_cost=round(labor_cost, 2),
            bom_cost=round(bom_cost, 2),
            overhead_cost=round(overhead_cost, 2),
            net_profit=round(profit_acc, 2),
        ),
        top_projects=top_projects,
        total_scrap_cost=round(total_scrap_cost, 2),
        total_scrap_filament_g=round(total_scrap_filament_g, 2),
        scrap_rate_percent=overall_scrap_rate,
    )

@router.post("", response_model=schemas.ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    proj_in: schemas.ProjectCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # If project margins/rates are default 0 or user wants their profile defaults
    proj_data = proj_in.model_dump(exclude={"plates", "bom_items", "failure_logs"})
    project = models.Project(
        user_id=current_user.id,
        **proj_data
    )
    db.add(project)
    db.flush()

    inserted_plates = []
    if proj_in.plates:
        for p_data in proj_in.plates:
            plate_dict = p_data.model_dump(exclude={"id"})
            plate = models.Plate(
                project_id=project.id,
                **plate_dict
            )
            db.add(plate)
            inserted_plates.append(plate)
        db.flush()

    if proj_in.bom_items:
        for b_data in proj_in.bom_items:
            bom_dict = b_data.model_dump(exclude={"id"})
            bom = models.BOMItem(
                project_id=project.id,
                **bom_dict
            )
            db.add(bom)
        db.flush()

    if proj_in.failure_logs:
        printers_map = {pr.id: pr for pr in db.query(models.Printer).filter(models.Printer.user_id == current_user.id).all()}
        filaments_map = {fl.id: fl for fl in db.query(models.Filament).filter(models.Filament.user_id == current_user.id).all()}

        for f_data in proj_in.failure_logs:
            target_plate_id = f_data.plate_id
            target_plate = None
            if target_plate_id:
                target_plate = next((p for p in inserted_plates if p.id == target_plate_id), None)
            elif f_data.plate_idx is not None and 0 <= f_data.plate_idx < len(inserted_plates):
                target_plate = inserted_plates[f_data.plate_idx]
                target_plate_id = target_plate.id

            printer = printers_map.get(target_plate.printer_id) if (target_plate and target_plate.printer_id) else None
            filament = filaments_map.get(target_plate.filament_id) if (target_plate and target_plate.filament_id) else None
            cost_info = calculate_failure_cost(f_data, plate=target_plate, printer=printer, filament=filament)

            f_log = models.PlateFailureLog(
                project_id=project.id,
                plate_id=target_plate_id,
                lost_time_hours=cost_info["lost_time_hours"],
                lost_filament_weight_g=cost_info["lost_filament_weight_g"],
                reason=cost_info["reason"],
                reason_notes=cost_info["reason_notes"],
                reprinted=cost_info["reprinted"],
                charged_to_client=cost_info["charged_to_client"],
                calculated_material_cost=cost_info["calculated_material_cost"],
                calculated_machine_cost=cost_info["calculated_machine_cost"],
                calculated_cost=cost_info["calculated_cost"],
            )
            db.add(f_log)

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
    update_data = proj_update.model_dump(exclude_unset=True, exclude={"plates", "bom_items", "failure_logs"})
    for field, value in update_data.items():
        setattr(project, field, value)

    # 1. Update Plates in-place without destroying untouched plate IDs
    active_plates = []
    if proj_update.plates is not None:
        existing_plates_list = list(project.plates)
        existing_plates_by_id = {p.id: p for p in existing_plates_list}
        used_plate_ids = set()

        for idx, p_data in enumerate(proj_update.plates):
            p_dict = p_data.model_dump(exclude_unset=True)
            p_id = p_dict.pop("id", None)

            plate = None
            if p_id and p_id in existing_plates_by_id:
                plate = existing_plates_by_id[p_id]
            elif not p_id and idx < len(existing_plates_list) and existing_plates_list[idx].id not in used_plate_ids:
                plate = existing_plates_list[idx]

            if plate:
                for k, v in p_dict.items():
                    setattr(plate, k, v)
                used_plate_ids.add(plate.id)
                active_plates.append(plate)
            else:
                new_plate = models.Plate(project_id=project.id, **p_dict)
                db.add(new_plate)
                active_plates.append(new_plate)

        # Remove deleted plates
        for p in existing_plates_list:
            if p.id not in used_plate_ids:
                db.delete(p)

        db.flush()

    # 2. Update BOM Items in-place
    if proj_update.bom_items is not None:
        existing_bom_list = list(project.bom_items)
        existing_bom_by_id = {b.id: b for b in existing_bom_list}
        used_bom_ids = set()

        for idx, b_data in enumerate(proj_update.bom_items):
            b_dict = b_data.model_dump(exclude_unset=True)
            b_id = b_dict.pop("id", None)

            bom = None
            if b_id and b_id in existing_bom_by_id:
                bom = existing_bom_by_id[b_id]
            elif not b_id and idx < len(existing_bom_list) and existing_bom_list[idx].id not in used_bom_ids:
                bom = existing_bom_list[idx]

            if bom:
                for k, v in b_dict.items():
                    setattr(bom, k, v)
                used_bom_ids.add(bom.id)
            else:
                bom = models.BOMItem(project_id=project.id, **b_dict)
                db.add(bom)

        for b in existing_bom_list:
            if b.id not in used_bom_ids:
                db.delete(b)

        db.flush()

    # 3. Update Failure Logs in-place with recalculation
    if proj_update.failure_logs is not None:
        printers_map = {pr.id: pr for pr in db.query(models.Printer).filter(models.Printer.user_id == current_user.id).all()}
        filaments_map = {fl.id: fl for fl in db.query(models.Filament).filter(models.Filament.user_id == current_user.id).all()}
        existing_failures_list = list(project.failure_logs)
        existing_failures_by_id = {f.id: f for f in existing_failures_list}
        used_fail_ids = set()

        # Current plates map for lookup
        current_plates_list = active_plates if proj_update.plates is not None else list(project.plates)
        plates_map = {p.id: p for p in current_plates_list}

        for idx, f_data in enumerate(proj_update.failure_logs):
            target_plate_id = f_data.plate_id
            target_plate = None
            if target_plate_id and target_plate_id in plates_map:
                target_plate = plates_map[target_plate_id]
            elif f_data.plate_idx is not None and 0 <= f_data.plate_idx < len(current_plates_list):
                target_plate = current_plates_list[f_data.plate_idx]
                target_plate_id = target_plate.id
            elif not target_plate_id and len(current_plates_list) == 1:
                target_plate = current_plates_list[0]
                target_plate_id = target_plate.id
            else:
                target_plate_id = None

            printer = printers_map.get(target_plate.printer_id) if (target_plate and target_plate.printer_id) else None
            filament = filaments_map.get(target_plate.filament_id) if (target_plate and target_plate.filament_id) else None
            cost_info = calculate_failure_cost(f_data, plate=target_plate, printer=printer, filament=filament)

            f_log = None
            if f_data.id and f_data.id in existing_failures_by_id:
                f_log = existing_failures_by_id[f_data.id]
            elif not f_data.id and idx < len(existing_failures_list) and existing_failures_list[idx].id not in used_fail_ids:
                f_log = existing_failures_list[idx]

            if f_log:
                f_log.plate_id = target_plate_id
                f_log.lost_time_hours = cost_info["lost_time_hours"]
                f_log.lost_filament_weight_g = cost_info["lost_filament_weight_g"]
                f_log.reason = cost_info["reason"]
                f_log.reason_notes = cost_info["reason_notes"]
                f_log.reprinted = cost_info["reprinted"]
                f_log.charged_to_client = cost_info["charged_to_client"]
                f_log.calculated_material_cost = cost_info["calculated_material_cost"]
                f_log.calculated_machine_cost = cost_info["calculated_machine_cost"]
                f_log.calculated_cost = cost_info["calculated_cost"]
                used_fail_ids.add(f_log.id)
            else:
                new_f = models.PlateFailureLog(
                    project_id=project.id,
                    plate_id=target_plate_id,
                    lost_time_hours=cost_info["lost_time_hours"],
                    lost_filament_weight_g=cost_info["lost_filament_weight_g"],
                    reason=cost_info["reason"],
                    reason_notes=cost_info["reason_notes"],
                    reprinted=cost_info["reprinted"],
                    charged_to_client=cost_info["charged_to_client"],
                    calculated_material_cost=cost_info["calculated_material_cost"],
                    calculated_machine_cost=cost_info["calculated_machine_cost"],
                    calculated_cost=cost_info["calculated_cost"],
                )
                db.add(new_f)

        for f in existing_failures_list:
            if f.id not in used_fail_ids:
                db.delete(f)

    db.commit()
    db.refresh(project)
    return build_project_response(project, db)

@router.post("/{project_id}/failures", response_model=schemas.PlateFailureLogResponse)
def add_plate_failure_log(
    project_id: int,
    log_in: schemas.PlateFailureLogCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_user_project(project_id, current_user.id, db)
    plate = None
    if log_in.plate_id:
        plate = db.query(models.Plate).filter(
            models.Plate.id == log_in.plate_id,
            models.Plate.project_id == project.id
        ).first()

    printer = db.query(models.Printer).filter(models.Printer.id == plate.printer_id).first() if (plate and plate.printer_id) else None
    filament = db.query(models.Filament).filter(models.Filament.id == plate.filament_id).first() if (plate and plate.filament_id) else None

    cost_info = calculate_failure_cost(log_in, plate=plate, printer=printer, filament=filament)

    failure = models.PlateFailureLog(
        project_id=project.id,
        plate_id=log_in.plate_id,
        lost_time_hours=cost_info["lost_time_hours"],
        lost_filament_weight_g=cost_info["lost_filament_weight_g"],
        reason=cost_info["reason"],
        reason_notes=cost_info["reason_notes"],
        reprinted=cost_info["reprinted"],
        charged_to_client=cost_info["charged_to_client"],
        calculated_material_cost=cost_info["calculated_material_cost"],
        calculated_machine_cost=cost_info["calculated_machine_cost"],
        calculated_cost=cost_info["calculated_cost"],
    )
    db.add(failure)
    db.commit()
    db.refresh(failure)
    return failure

@router.delete("/{project_id}/failures/{failure_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plate_failure_log(
    project_id: int,
    failure_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = get_user_project(project_id, current_user.id, db)
    failure = db.query(models.PlateFailureLog).filter(
        models.PlateFailureLog.id == failure_id,
        models.PlateFailureLog.project_id == project.id
    ).first()
    if not failure:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro de falha não encontrado.")

    db.delete(failure)
    db.commit()
    return None

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
            slicer_filament_profile=pl.slicer_filament_profile,
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
