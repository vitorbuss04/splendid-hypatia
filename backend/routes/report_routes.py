from typing import Optional, List, Dict, Any
import datetime
import io
import csv
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models, schemas
from backend.auth import get_current_user
from backend.engine import calculate_project_summary, calculate_plate_cost

router = APIRouter(prefix="/api/reports", tags=["Relatórios & BI"])

FAILURE_REASON_LABELS = {
    "warping": "Descolamento da Mesa (Warping)",
    "nozzle_clog": "Entupimento de Bico",
    "filament_runout": "Fim de Filamento",
    "layer_shift": "Perda de Passos (Layer Shift)",
    "spaghetti": "Spaghetti / Suporte Solto",
    "power_loss": "Queda de Energia",
    "slicing_error": "Erro de Fatiamento",
    "other": "Outros Motivos",
}

STATUS_LABELS_PT = {
    "draft": "Rascunho",
    "quoted": "Orçado / Proposta",
    "approved": "Aprovado",
    "in_production": "Em Produção",
    "completed": "Concluído",
    "cancelled": "Cancelado",
}

def parse_iso_datetime(dt_str: Optional[str], is_end_of_day: bool = False) -> Optional[datetime.datetime]:
    if not dt_str:
        return None
    try:
        clean = dt_str.strip()
        if len(clean) == 10:
            dt = datetime.datetime.fromisoformat(clean)
            if is_end_of_day:
                dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            else:
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            return dt
        return datetime.datetime.fromisoformat(clean)
    except Exception:
        return None

def filter_user_projects(
    user_id: int,
    db: Session,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    date_field: str = "created_at"
) -> List[models.Project]:
    query = db.query(models.Project).filter(models.Project.user_id == user_id)
    projects = query.order_by(models.Project.id.desc()).all()

    start_dt = parse_iso_datetime(start_date, is_end_of_day=False)
    end_dt = parse_iso_datetime(end_date, is_end_of_day=True)

    if not start_dt and not end_dt:
        return projects

    filtered = []
    for p in projects:
        val = getattr(p, date_field, None) or p.created_at or datetime.datetime.now()
        # Handle naive vs tz-aware comparisons safely
        if val.tzinfo is not None and start_dt and start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=val.tzinfo)
        if val.tzinfo is not None and end_dt and end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=val.tzinfo)
        if val.tzinfo is None and start_dt and start_dt.tzinfo is not None:
            val = val.replace(tzinfo=start_dt.tzinfo)

        if start_dt and val < start_dt:
            continue
        if end_dt and val > end_dt:
            continue
        filtered.append(p)

    return filtered


@router.get("/detailed", response_model=schemas.ReportDetailedResponse)
def get_detailed_report(
    start_date: Optional[str] = Query(None, description="Data inicial YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Data final YYYY-MM-DD"),
    preset: Optional[str] = Query(None, description="Identificador do preset rápido"),
    date_field: Optional[str] = Query("created_at", description="created_at ou updated_at"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    projects = filter_user_projects(
        user_id=current_user.id,
        db=db,
        start_date=start_date,
        end_date=end_date,
        date_field=date_field or "created_at"
    )

    printers = db.query(models.Printer).filter(models.Printer.user_id == current_user.id).all()
    filaments = db.query(models.Filament).filter(models.Filament.user_id == current_user.id).all()
    printers_map = {p.id: p for p in printers}
    filaments_map = {f.id: f for f in filaments}

    # Financial aggregators
    approved_count = 0
    revenue_approved = 0.0
    pipeline_revenue = 0.0
    material_cost = 0.0
    machine_cost = 0.0
    energy_cost = 0.0
    labor_cost = 0.0
    bom_cost = 0.0
    overhead_cost = 0.0
    total_tax = 0.0
    total_discount = 0.0
    total_shipping = 0.0
    net_profit_acc = 0.0
    margins_sum = 0.0
    margins_count = 0

    # Machines aggregation
    printers_usage: Dict[Any, Dict[str, Any]] = {}
    for p in printers:
        printers_usage[p.id] = {
            "printer_id": p.id,
            "name": p.name,
            "model": p.model,
            "print_hours": 0.0,
            "plates_count": 0,
            "energy_cost": 0.0,
            "depreciation_cost": 0.0,
            "maintenance_cost": 0.0,
            "total_cost": 0.0,
        }
    # Fallback for custom or unassigned printer
    printers_usage[None] = {
        "printer_id": None,
        "name": "Outra / Não Especificada",
        "model": "Genérica",
        "print_hours": 0.0,
        "plates_count": 0,
        "energy_cost": 0.0,
        "depreciation_cost": 0.0,
        "maintenance_cost": 0.0,
        "total_cost": 0.0,
    }

    # Materials aggregation
    materials_usage: Dict[str, Dict[str, Any]] = {}

    # Failures aggregation
    reasons_stats: Dict[str, Dict[str, Any]] = {}
    for r_key, r_label in FAILURE_REASON_LABELS.items():
        reasons_stats[r_key] = {
            "reason": r_key,
            "reason_label": r_label,
            "count": 0,
            "lost_weight_g": 0.0,
            "lost_time_hours": 0.0,
            "total_cost": 0.0,
        }

    total_scrap_cost = 0.0
    total_lost_weight_g = 0.0
    total_lost_hours = 0.0
    total_failures_count = 0

    # Clients aggregation
    clients_stats: Dict[str, Dict[str, Any]] = {}

    # Project items for list view
    project_list_items = []

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
        final_price = float(summary.get("final_price_to_client", 0.0) or 0.0)
        base_cost = float(summary.get("base_cost", 0.0) or 0.0)
        net_profit = float(summary.get("net_profit", 0.0) or 0.0)
        hours = float(summary.get("total_print_time_hours", 0.0) or 0.0)
        weight = float(summary.get("total_filament_weight_g", 0.0) or 0.0)

        is_approved = st in ["approved", "in_production", "completed"]

        if is_approved:
            approved_count += 1
            revenue_approved += final_price
            net_profit_acc += net_profit
            if base_cost > 0:
                margins_sum += float(summary.get("effective_profit_margin_percent", 0.0) or 0.0)
                margins_count += 1
        elif st in ["draft", "quoted"]:
            pipeline_revenue += final_price

        # Accumulate costs across approved projects (or all projects if pipeline considered)
        # For realistic DRE of production, we accumulate for approved, but we track material cost for work
        if is_approved:
            material_cost += float(summary.get("total_material_cost", 0.0) or 0.0)
            machine_cost += float(summary.get("total_machine_cost", 0.0) or 0.0)
            energy_cost += float(summary.get("total_energy_cost", 0.0) or 0.0)
            labor_cost += float(summary.get("total_labor_cost", 0.0) or 0.0)
            bom_cost += float(summary.get("total_bom_cost", 0.0) or 0.0)
            overhead_cost += float(summary.get("overhead_cost", 0.0) or 0.0)
            total_tax += float(summary.get("tax_amount", 0.0) or 0.0)
            total_discount += float(summary.get("discount_amount", 0.0) or 0.0)
            total_shipping += float(proj.shipping_cost or 0.0)

        # Machine utilization (from approved projects or all in production)
        if is_approved:
            for plate in proj.plates:
                pr = printers_map.get(plate.printer_id)
                fl = filaments_map.get(plate.filament_id)
                cb = calculate_plate_cost(plate, printer=pr, filament=fl)
                p_id = pr.id if pr else None
                if p_id not in printers_usage:
                    p_id = None
                
                printers_usage[p_id]["print_hours"] += cb["total_time_hours"]
                printers_usage[p_id]["plates_count"] += plate.quantity
                printers_usage[p_id]["energy_cost"] += cb["total_energy_cost"]
                printers_usage[p_id]["depreciation_cost"] += cb["total_depreciation_cost"]
                printers_usage[p_id]["maintenance_cost"] += cb["total_maintenance_cost"]
                printers_usage[p_id]["total_cost"] += (cb["total_energy_cost"] + cb["total_depreciation_cost"] + cb["total_maintenance_cost"])

                # Material usage
                mat_key = fl.material if fl else "Outros"
                fil_name = fl.name if fl else (plate.slicer_filament_profile or "Personalizado")
                fil_id = fl.id if fl else None
                unique_mat_key = f"{mat_key}_{fil_name}"

                if unique_mat_key not in materials_usage:
                    materials_usage[unique_mat_key] = {
                        "material": mat_key,
                        "filament_id": fil_id,
                        "filament_name": fil_name,
                        "brand": fl.brand if fl else "Genérico",
                        "color": fl.color if fl else "Padrão",
                        "color_hex": fl.color_hex if fl and fl.color_hex else "#10b981",
                        "weight_g": 0.0,
                        "weight_kg": 0.0,
                        "spools_consumed": 0.0,
                        "cost": 0.0,
                        "percentage": 0.0,
                    }
                materials_usage[unique_mat_key]["weight_g"] += cb["total_weight_g"]
                materials_usage[unique_mat_key]["cost"] += cb["total_material_cost"]

        # Failure logs (from all projects in period)
        for flog in proj.failure_logs:
            r_key = flog.reason if flog.reason in reasons_stats else "other"
            reasons_stats[r_key]["count"] += 1
            reasons_stats[r_key]["lost_weight_g"] += float(flog.lost_filament_weight_g or 0.0)
            reasons_stats[r_key]["lost_time_hours"] += float(flog.lost_time_hours or 0.0)
            reasons_stats[r_key]["total_cost"] += float(flog.calculated_cost or 0.0)

            total_scrap_cost += float(flog.calculated_cost or 0.0)
            total_lost_weight_g += float(flog.lost_filament_weight_g or 0.0)
            total_lost_hours += float(flog.lost_time_hours or 0.0)
            total_failures_count += 1

        # Clients aggregation
        c_name = (proj.client_name or "").strip() or "Consumidor Final"
        c_key = c_name.lower()
        if c_key not in clients_stats:
            clients_stats[c_key] = {
                "client_name": c_name,
                "client_email": proj.client_email,
                "client_phone": proj.client_phone,
                "projects_count": 0,
                "approved_projects_count": 0,
                "approved_revenue": 0.0,
                "total_revenue": 0.0,
                "net_profit": 0.0,
                "total_hours": 0.0,
            }
        clients_stats[c_key]["projects_count"] += 1
        clients_stats[c_key]["total_revenue"] += final_price
        if is_approved:
            clients_stats[c_key]["approved_projects_count"] += 1
            clients_stats[c_key]["approved_revenue"] += final_price
            clients_stats[c_key]["net_profit"] += net_profit
            clients_stats[c_key]["total_hours"] += hours

        project_list_items.append(schemas.ProjectListItem(
            id=proj.id,
            name=proj.name,
            client_name=proj.client_name,
            status=proj.status,
            created_at=proj.created_at,
            updated_at=proj.updated_at,
            plates_count=len(proj.plates),
            total_print_time_hours=round(hours, 2),
            total_filament_weight_g=round(weight, 1),
            final_price=round(final_price, 2),
            net_profit=round(net_profit, 2)
        ))

    # Format printer usage items
    total_machine_hours = sum(u["print_hours"] for u in printers_usage.values())
    printer_items = []
    for u in printers_usage.values():
        if u["print_hours"] > 0 or u["printer_id"] is not None:
            util_pct = (u["print_hours"] / total_machine_hours * 100) if total_machine_hours > 0 else 0.0
            printer_items.append(schemas.ReportPrinterUsageItem(
                printer_id=u["printer_id"],
                name=u["name"],
                model=u["model"],
                print_hours=round(u["print_hours"], 2),
                plates_count=u["plates_count"],
                energy_cost=round(u["energy_cost"], 2),
                depreciation_cost=round(u["depreciation_cost"], 2),
                maintenance_cost=round(u["maintenance_cost"], 2),
                total_cost=round(u["total_cost"], 2),
                utilization_percent=round(util_pct, 1),
            ))
    # Sort printers by hours descending
    printer_items.sort(key=lambda x: x.print_hours, reverse=True)

    # Format material usage items
    total_material_weight = sum(m["weight_g"] for m in materials_usage.values())
    material_items = []
    for m in materials_usage.values():
        pct = (m["weight_g"] / total_material_weight * 100) if total_material_weight > 0 else 0.0
        material_items.append(schemas.ReportMaterialUsageItem(
            material=m["material"],
            filament_id=m["filament_id"],
            filament_name=m["filament_name"],
            brand=m["brand"],
            color=m["color"],
            color_hex=m["color_hex"],
            weight_g=round(m["weight_g"], 1),
            weight_kg=round(m["weight_g"] / 1000.0, 3),
            spools_consumed=round(m["weight_g"] / 1000.0, 2),
            cost=round(m["cost"], 2),
            percentage=round(pct, 1),
        ))
    material_items.sort(key=lambda x: x.weight_g, reverse=True)

    # Format failure items
    failure_items = []
    for r in reasons_stats.values():
        pct = (r["total_cost"] / total_scrap_cost * 100) if total_scrap_cost > 0 else 0.0
        failure_items.append(schemas.ReportFailureItem(
            reason=r["reason"],
            reason_label=r["reason_label"],
            count=r["count"],
            lost_weight_g=round(r["lost_weight_g"], 1),
            lost_time_hours=round(r["lost_time_hours"], 2),
            total_cost=round(r["total_cost"], 2),
            percentage=round(pct, 1),
        ))
    failure_items.sort(key=lambda x: x.total_cost, reverse=True)

    scrap_rate = (total_scrap_cost / (revenue_approved + total_scrap_cost) * 100) if (revenue_approved + total_scrap_cost) > 0 else 0.0

    # Format client items
    client_items = [
        schemas.ReportClientItem(
            client_name=c["client_name"],
            client_email=c["client_email"],
            client_phone=c["client_phone"],
            projects_count=c["projects_count"],
            approved_projects_count=c["approved_projects_count"],
            approved_revenue=round(c["approved_revenue"], 2),
            total_revenue=round(c["total_revenue"], 2),
            net_profit=round(c["net_profit"], 2),
            total_hours=round(c["total_hours"], 2),
        )
        for c in clients_stats.values()
    ]
    client_items.sort(key=lambda x: x.approved_revenue, reverse=True)

    # Financial summary
    total_base_cost = material_cost + machine_cost + energy_cost + labor_cost + bom_cost + overhead_cost
    avg_ticket = (revenue_approved / approved_count) if approved_count > 0 else 0.0
    avg_margin = (margins_sum / margins_count) if margins_count > 0 else 0.0

    financial_summary = schemas.ReportFinancialSummary(
        total_projects=len(projects),
        approved_projects_count=approved_count,
        revenue_approved=round(revenue_approved, 2),
        pipeline_revenue=round(pipeline_revenue, 2),
        total_revenue=round(revenue_approved + pipeline_revenue, 2),
        material_cost=round(material_cost, 2),
        machine_cost=round(machine_cost, 2),
        energy_cost=round(energy_cost, 2),
        labor_cost=round(labor_cost, 2),
        bom_cost=round(bom_cost, 2),
        overhead_cost=round(overhead_cost, 2),
        total_base_cost=round(total_base_cost, 2),
        net_profit=round(net_profit_acc, 2),
        avg_profit_margin_percent=round(avg_margin, 1),
        total_tax=round(total_tax, 2),
        total_discount=round(total_discount, 2),
        total_shipping=round(total_shipping, 2),
        avg_ticket=round(avg_ticket, 2),
    )

    return schemas.ReportDetailedResponse(
        period=schemas.ReportPeriodInfo(
            start_date=start_date,
            end_date=end_date,
            preset=preset,
            date_field=date_field or "created_at"
        ),
        financial=financial_summary,
        printers=printer_items,
        materials=material_items,
        failures=schemas.ReportFailureSummary(
            total_scrap_cost=round(total_scrap_cost, 2),
            total_lost_weight_g=round(total_lost_weight_g, 1),
            total_lost_hours=round(total_lost_hours, 2),
            total_failures_count=total_failures_count,
            scrap_rate_percent=round(scrap_rate, 1),
            reasons=failure_items
        ),
        clients=client_items,
        projects=project_list_items
    )


@router.get("/export/csv")
def export_report_csv(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    report_type: Optional[str] = Query("projects", description="projects, materials, machines, failures"),
    date_field: Optional[str] = Query("created_at"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    projects = filter_user_projects(
        user_id=current_user.id,
        db=db,
        start_date=start_date,
        end_date=end_date,
        date_field=date_field or "created_at"
    )

    printers = db.query(models.Printer).filter(models.Printer.user_id == current_user.id).all()
    filaments = db.query(models.Filament).filter(models.Filament.user_id == current_user.id).all()
    printers_map = {p.id: p for p in printers}
    filaments_map = {f.id: f for f in filaments}

    output = io.StringIO()
    # Write UTF-8 BOM so Excel opens it with correct accentuation
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    rtype = (report_type or "projects").lower()

    if rtype == "materials":
        writer.writerow(["Material", "Filamento", "Marca", "Cor", "Peso Consumido (g)", "Peso Consumido (kg)", "Carreteis (1kg)", "Custo Total (R$)"])
        materials_usage: Dict[str, Dict[str, Any]] = {}
        for proj in projects:
            if proj.status in ["approved", "in_production", "completed"]:
                for plate in proj.plates:
                    pr = printers_map.get(plate.printer_id)
                    fl = filaments_map.get(plate.filament_id)
                    cb = calculate_plate_cost(plate, printer=pr, filament=fl)
                    mat = fl.material if fl else "Outros"
                    fname = fl.name if fl else (plate.slicer_filament_profile or "Personalizado")
                    k = f"{mat}_{fname}"
                    if k not in materials_usage:
                        materials_usage[k] = {
                            "material": mat, "name": fname,
                            "brand": fl.brand if fl else "Generico",
                            "color": fl.color if fl else "Padrao",
                            "weight_g": 0.0, "cost": 0.0
                        }
                    materials_usage[k]["weight_g"] += cb["total_weight_g"]
                    materials_usage[k]["cost"] += cb["total_material_cost"]

        for m in sorted(materials_usage.values(), key=lambda x: x["weight_g"], reverse=True):
            writer.writerow([
                m["material"], m["name"], m["brand"], m["color"],
                f"{m['weight_g']:.1f}".replace(".", ","),
                f"{m['weight_g']/1000.0:.3f}".replace(".", ","),
                f"{m['weight_g']/1000.0:.2f}".replace(".", ","),
                f"{m['cost']:.2f}".replace(".", ",")
            ])

    elif rtype == "machines":
        writer.writerow(["Impressora", "Modelo", "Horas de Impressao (h)", "Bandejas Impressas", "Custo Energia (R$)", "Custo Depreciacao (R$)", "Custo Manutencao (R$)", "Custo Operacional Total (R$)"])
        p_usage: Dict[Any, Dict[str, Any]] = {}
        for p in printers:
            p_usage[p.id] = {"name": p.name, "model": p.model or "-", "hours": 0.0, "plates": 0, "energy": 0.0, "depr": 0.0, "maint": 0.0}
        for proj in projects:
            if proj.status in ["approved", "in_production", "completed"]:
                for plate in proj.plates:
                    pr = printers_map.get(plate.printer_id)
                    fl = filaments_map.get(plate.filament_id)
                    cb = calculate_plate_cost(plate, printer=pr, filament=fl)
                    pid = pr.id if pr else None
                    if pid in p_usage:
                        p_usage[pid]["hours"] += cb["total_time_hours"]
                        p_usage[pid]["plates"] += plate.quantity
                        p_usage[pid]["energy"] += cb["total_energy_cost"]
                        p_usage[pid]["depr"] += cb["total_depreciation_cost"]
                        p_usage[pid]["maint"] += cb["total_maintenance_cost"]

        for p in sorted(p_usage.values(), key=lambda x: x["hours"], reverse=True):
            tot = p["energy"] + p["depr"] + p["maint"]
            writer.writerow([
                p["name"], p["model"],
                f"{p['hours']:.2f}".replace(".", ","),
                p["plates"],
                f"{p['energy']:.2f}".replace(".", ","),
                f"{p['depr']:.2f}".replace(".", ","),
                f"{p['maint']:.2f}".replace(".", ","),
                f"{tot:.2f}".replace(".", ",")
            ])

    elif rtype == "failures":
        writer.writerow(["Projeto", "Placa", "Causa da Falha", "Horas Perdidas (h)", "Filamento Perdido (g)", "Prejuizo Total (R$)", "Cobrado do Cliente", "Data Registro"])
        for proj in projects:
            for flog in proj.failure_logs:
                plate_name = flog.plate.name if flog.plate else "Placa Removida"
                r_label = FAILURE_REASON_LABELS.get(flog.reason, flog.reason or "Outros")
                charged = "Sim" if flog.charged_to_client else "Nao (Absorvido)"
                dt_str = flog.created_at.strftime("%d/%m/%Y %H:%M") if flog.created_at else "-"
                writer.writerow([
                    proj.name, plate_name, r_label,
                    f"{flog.lost_time_hours or 0.0:.2f}".replace(".", ","),
                    f"{flog.lost_filament_weight_g or 0.0:.1f}".replace(".", ","),
                    f"{flog.calculated_cost or 0.0:.2f}".replace(".", ","),
                    charged, dt_str
                ])

    else:
        # Default: Projects list with full financial indicators
        writer.writerow([
            "ID", "Nome do Projeto", "Cliente", "Status", "Data Criacao", "Data Atualizacao",
            "Bandejas", "Horas Totais (h)", "Filamento (g)", "Custo Base (R$)",
            "Margem Efetiva (%)", "Lucro Liquido (R$)", "Imposto (R$)", "Desconto (R$)", "Preco Final (R$)"
        ])
        for proj in projects:
            summary = calculate_project_summary(
                project=proj,
                plates=proj.plates,
                bom_items=proj.bom_items,
                printers_by_id=printers_map,
                filaments_by_id=filaments_map,
                failure_logs=proj.failure_logs,
            )
            created_str = proj.created_at.strftime("%d/%m/%Y") if proj.created_at else "-"
            updated_str = proj.updated_at.strftime("%d/%m/%Y") if proj.updated_at else "-"
            st_label = STATUS_LABELS_PT.get(proj.status, proj.status or "Rascunho")
            
            final_p = float(summary.get("final_price_to_client", 0.0) or 0.0)
            base_c = float(summary.get("base_cost", 0.0) or 0.0)
            net_p = float(summary.get("net_profit", 0.0) or 0.0)
            eff_m = float(summary.get("effective_profit_margin_percent", 0.0) or 0.0)
            hours = float(summary.get("total_print_time_hours", 0.0) or 0.0)
            weight = float(summary.get("total_filament_weight_g", 0.0) or 0.0)
            tax = float(summary.get("tax_amount", 0.0) or 0.0)
            disc = float(summary.get("discount_amount", 0.0) or 0.0)

            writer.writerow([
                proj.id, proj.name, proj.client_name or "-", st_label, created_str, updated_str,
                len(proj.plates),
                f"{hours:.2f}".replace(".", ","),
                f"{weight:.1f}".replace(".", ","),
                f"{base_c:.2f}".replace(".", ","),
                f"{eff_m:.1f}".replace(".", ","),
                f"{net_p:.2f}".replace(".", ","),
                f"{tax:.2f}".replace(".", ","),
                f"{disc:.2f}".replace(".", ","),
                f"{final_p:.2f}".replace(".", ",")
            ])

    csv_data = output.getvalue()
    today_str = datetime.date.today().strftime("%Y%m%d")
    filename = f"relatorio_3dprintcalc_{rtype}_{today_str}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )
