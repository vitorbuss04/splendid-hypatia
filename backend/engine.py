from typing import Dict, Any, List, Optional

def calculate_printer_hourly_rate(
    acquisition_cost: float = 0.0,
    lifespan_hours: float = 5000.0,
    avg_power_watts: float = 150.0,
    energy_rate_kwh: float = 0.85,
    maintenance_cost_per_hour: float = 1.0,
) -> Dict[str, float]:
    """
    Calculates detailed printer operational rates:
    - Deprecation per hour: acquisition_cost / lifespan_hours
    - Energy cost per hour: (avg_power_watts / 1000) * energy_rate_kwh
    - Maintenance reserve per hour
    - Total machine hourly rate
    """
    acquisition_cost = max(0.0, float(acquisition_cost or 0.0))
    lifespan_hours = float(lifespan_hours or 0.0)
    avg_power_watts = max(0.0, float(avg_power_watts or 0.0))
    energy_rate_kwh = max(0.0, float(energy_rate_kwh or 0.0))
    maintenance_cost_per_hour = max(0.0, float(maintenance_cost_per_hour or 0.0))

    depreciation_per_hour = (acquisition_cost / lifespan_hours) if lifespan_hours > 0 else 0.0
    energy_cost_per_hour = (avg_power_watts / 1000.0) * energy_rate_kwh
    total_hourly_rate = depreciation_per_hour + maintenance_cost_per_hour + energy_cost_per_hour

    return {
        "depreciation_per_hour": round(depreciation_per_hour, 4),
        "energy_cost_per_hour": round(energy_cost_per_hour, 4),
        "maintenance_cost_per_hour": round(maintenance_cost_per_hour, 4),
        "machine_hourly_rate": round(total_hourly_rate, 4),
    }


def calculate_plate_cost(
    plate: Any,
    printer: Optional[Any] = None,
    filament: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Calculates detailed cost for a single plate (multiplied by its quantity).
    Accepts SQLAlchemy models, dataclasses, or dicts.
    """
    def get_attr(obj, attr, default=0.0):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    name = str(get_attr(plate, "name", "Placa"))
    print_time_hours = max(0.0, float(get_attr(plate, "print_time_hours", 0.0) or 0.0))
    part_weight_g = max(0.0, float(get_attr(plate, "part_weight_g", 0.0) or 0.0))
    purge_weight_g = max(0.0, float(get_attr(plate, "purge_weight_g", 0.0) or 0.0))
    failure_margin_percent = max(0.0, float(get_attr(plate, "failure_margin_percent", 0.0) or 0.0))
    quantity = max(1, int(get_attr(plate, "quantity", 1) or 1))

    # Calculate filament cost per gram
    cost_per_gram = 0.0
    filament_name = "Filamento padrão"
    if filament is not None:
        spool_price = max(0.0, float(get_attr(filament, "spool_price", 0.0) or 0.0))
        spool_weight_g = float(get_attr(filament, "spool_weight_g", 1000.0) or 1000.0)
        cost_per_gram = (spool_price / spool_weight_g) if spool_weight_g > 0 else 0.0
        filament_name = str(get_attr(filament, "name", "Filamento"))
    else:
        custom_g = get_attr(plate, "custom_filament_cost_per_g", None)
        if custom_g is not None:
            cost_per_gram = max(0.0, float(custom_g or 0.0))
            filament_name = "Personalizado"

    # Total filament weight per unit and failure multiplier
    unit_raw_weight = part_weight_g + purge_weight_g
    failure_factor = 1.0 + (failure_margin_percent / 100.0)
    unit_effective_weight = unit_raw_weight * failure_factor
    unit_material_cost = unit_effective_weight * cost_per_gram

    # Calculate printer hourly rate
    machine_rate_details = {
        "depreciation_per_hour": 0.0,
        "energy_cost_per_hour": 0.0,
        "maintenance_cost_per_hour": 0.0,
        "machine_hourly_rate": 0.0,
    }
    printer_name = "Impressora padrão"
    if printer is not None:
        machine_rate_details = calculate_printer_hourly_rate(
            acquisition_cost=get_attr(printer, "acquisition_cost", 0.0),
            lifespan_hours=get_attr(printer, "lifespan_hours", 5000.0),
            avg_power_watts=get_attr(printer, "avg_power_watts", 150.0),
            energy_rate_kwh=get_attr(printer, "energy_rate_kwh", 0.85),
            maintenance_cost_per_hour=get_attr(printer, "maintenance_cost_per_hour", 1.0),
        )
        printer_name = str(get_attr(printer, "name", "Impressora"))
    else:
        custom_hr = get_attr(plate, "custom_printer_hourly_rate", None)
        if custom_hr is not None:
            rate = max(0.0, float(custom_hr or 0.0))
            machine_rate_details["machine_hourly_rate"] = rate
            printer_name = "Personalizada"

    machine_hourly_rate = machine_rate_details["machine_hourly_rate"]
    unit_machine_cost = print_time_hours * machine_hourly_rate
    unit_total_cost = unit_material_cost + unit_machine_cost

    # Multiplied by quantity
    total_material_cost = unit_material_cost * quantity
    total_machine_cost = unit_machine_cost * quantity
    total_cost = unit_total_cost * quantity
    total_time_hours = print_time_hours * quantity
    total_weight_g = unit_raw_weight * quantity
    total_effective_weight_g = unit_effective_weight * quantity

    # Energy, depreciation, maintenance breakdown totals
    total_energy_cost = (print_time_hours * machine_rate_details["energy_cost_per_hour"]) * quantity
    total_depreciation_cost = (print_time_hours * machine_rate_details["depreciation_per_hour"]) * quantity
    total_maintenance_cost = (print_time_hours * machine_rate_details["maintenance_cost_per_hour"]) * quantity

    return {
        "plate_id": get_attr(plate, "id", None),
        "name": name,
        "quantity": quantity,
        "printer_name": printer_name,
        "filament_name": filament_name,
        "cost_per_gram": round(cost_per_gram, 4),
        "machine_hourly_rate": round(machine_hourly_rate, 4),
        "unit_print_time_hours": round(print_time_hours, 2),
        "part_weight_g": round(part_weight_g, 2),
        "purge_weight_g": round(purge_weight_g, 2),
        "failure_margin_percent": round(failure_margin_percent, 2),
        "unit_raw_weight_g": round(unit_raw_weight, 2),
        "unit_material_cost": round(unit_material_cost, 2),
        "unit_machine_cost": round(unit_machine_cost, 2),
        "unit_total_cost": round(unit_total_cost, 2),
        "total_time_hours": round(total_time_hours, 2),
        "total_weight_g": round(total_weight_g, 2),
        "total_effective_weight_g": round(total_effective_weight_g, 2),
        "total_material_cost": round(total_material_cost, 2),
        "total_machine_cost": round(total_machine_cost, 2),
        "total_energy_cost": round(total_energy_cost, 2),
        "total_depreciation_cost": round(total_depreciation_cost, 2),
        "total_maintenance_cost": round(total_maintenance_cost, 2),
        "total_cost": round(total_cost, 2),
    }


def calculate_project_summary(
    project: Any,
    plates: List[Any],
    bom_items: List[Any],
    printers_by_id: Optional[Dict[int, Any]] = None,
    filaments_by_id: Optional[Dict[int, Any]] = None,
) -> Dict[str, Any]:
    """
    Computes complete project financials:
    - Plate costs (materials + machine + electricity)
    - BOM items
    - CAD & post-processing labor
    - Overhead
    - Target profit margin & tax deduction
    - Discount & shipping
    - Final selling price and margins
    """
    def get_attr(obj, attr, default=0.0):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    printers_map = printers_by_id or {}
    filaments_map = filaments_by_id or {}

    # 1. Plates calculation
    plates_details = []
    total_plates_cost = 0.0
    total_material_cost = 0.0
    total_machine_cost = 0.0
    total_energy_cost = 0.0
    total_depreciation_cost = 0.0
    total_maintenance_cost = 0.0
    total_print_time_hours = 0.0
    total_filament_weight_g = 0.0
    total_effective_filament_weight_g = 0.0

    for pl in plates:
        p_id = get_attr(pl, "printer_id", None)
        f_id = get_attr(pl, "filament_id", None)
        printer = printers_map.get(p_id) if p_id else getattr(pl, "printer", None)
        filament = filaments_map.get(f_id) if f_id else getattr(pl, "filament", None)

        c = calculate_plate_cost(pl, printer=printer, filament=filament)
        plates_details.append(c)

        total_plates_cost += c["total_cost"]
        total_material_cost += c["total_material_cost"]
        total_machine_cost += c["total_machine_cost"]
        total_energy_cost += c["total_energy_cost"]
        total_depreciation_cost += c["total_depreciation_cost"]
        total_maintenance_cost += c["total_maintenance_cost"]
        total_print_time_hours += c["total_time_hours"]
        total_filament_weight_g += c["total_weight_g"]
        total_effective_filament_weight_g += c["total_effective_weight_g"]

    # 2. BOM Items calculation
    bom_details = []
    total_bom_cost = 0.0
    total_bom_items_count = 0
    for b in bom_items:
        qty = max(0, int(get_attr(b, "quantity", 1) or 0))
        unit_c = max(0.0, float(get_attr(b, "unit_cost", 0.0) or 0.0))
        subtotal = qty * unit_c
        total_bom_cost += subtotal
        total_bom_items_count += qty
        bom_details.append({
            "id": get_attr(b, "id", None),
            "name": str(get_attr(b, "name", "Item BOM")),
            "category": str(get_attr(b, "category", "Fixadores")),
            "quantity": qty,
            "unit_cost": round(unit_c, 2),
            "subtotal": round(subtotal, 2),
            "notes": str(get_attr(b, "notes", "") or ""),
        })

    # 3. Labor & Services
    cad_hours = max(0.0, float(get_attr(project, "cad_hours", 0.0) or 0.0))
    cad_hourly_rate = max(0.0, float(get_attr(project, "cad_hourly_rate", 0.0) or 0.0))
    cad_labor_cost = cad_hours * cad_hourly_rate

    post_hours = max(0.0, float(get_attr(project, "post_process_hours", 0.0) or 0.0))
    post_hourly_rate = max(0.0, float(get_attr(project, "post_process_hourly_rate", 0.0) or 0.0))
    post_labor_cost = post_hours * post_hourly_rate

    total_labor_cost = cad_labor_cost + post_labor_cost

    # 4. Overhead & Base Cost
    overhead_cost = max(0.0, float(get_attr(project, "overhead_cost", 0.0) or 0.0))
    base_cost = total_plates_cost + total_bom_cost + total_labor_cost + overhead_cost

    # 5. Pricing, Margins and Taxes
    profit_margin_percent = max(0.0, float(get_attr(project, "profit_margin_percent", 30.0) or 0.0))
    tax_rate_percent = max(0.0, min(99.0, float(get_attr(project, "tax_rate_percent", 6.0) or 0.0)))
    discount_percent = max(0.0, min(100.0, float(get_attr(project, "discount_percent", 0.0) or 0.0)))
    shipping_cost = max(0.0, float(get_attr(project, "shipping_cost", 0.0) or 0.0))

    # Mathematical formula from user requirement:
    # Final Selling Price = (Base Cost * (1 + profit_margin%)) / (1 - tax_rate%)
    tax_divisor = max(0.01, 1.0 - (tax_rate_percent / 100.0))
    if base_cost > 0:
        suggested_price = round((base_cost * (1.0 + (profit_margin_percent / 100.0))) / tax_divisor, 2)
    else:
        suggested_price = 0.0

    discount_amount = round(suggested_price * (discount_percent / 100.0), 2)
    subtotal_after_discount = round(suggested_price - discount_amount, 2)

    # Tax calculated on the charged price
    tax_amount = round(subtotal_after_discount * (tax_rate_percent / 100.0), 2)
    net_revenue = round(subtotal_after_discount - tax_amount, 2)

    # Net profit after base costs and taxes
    net_profit = round(net_revenue - base_cost, 2)
    effective_profit_margin_percent = round((net_profit / base_cost * 100.0), 2) if base_cost > 0 else 0.0

    final_price_to_client = round(subtotal_after_discount + shipping_cost, 2)

    return {
        "plates_details": plates_details,
        "bom_details": bom_details,
        "total_plates_count": len(plates_details),
        "total_bom_items_count": total_bom_items_count,
        "total_print_time_hours": round(total_print_time_hours, 2),
        "total_filament_weight_g": round(total_filament_weight_g, 2),
        "total_effective_filament_weight_g": round(total_effective_filament_weight_g, 2),
        # Costs breakdown
        "total_material_cost": round(total_material_cost, 2),
        "total_machine_cost": round(total_machine_cost, 2),
        "total_energy_cost": round(total_energy_cost, 2),
        "total_depreciation_cost": round(total_depreciation_cost, 2),
        "total_maintenance_cost": round(total_maintenance_cost, 2),
        "total_plates_cost": round(total_plates_cost, 2),
        "total_bom_cost": round(total_bom_cost, 2),
        # Labor
        "cad_hours": round(cad_hours, 2),
        "cad_hourly_rate": round(cad_hourly_rate, 2),
        "cad_labor_cost": round(cad_labor_cost, 2),
        "post_hours": round(post_hours, 2),
        "post_hourly_rate": round(post_hourly_rate, 2),
        "post_labor_cost": round(post_labor_cost, 2),
        "total_labor_cost": round(total_labor_cost, 2),
        "overhead_cost": round(overhead_cost, 2),
        # Totals and Pricing
        "base_cost": round(base_cost, 2),
        "profit_margin_percent": round(profit_margin_percent, 2),
        "tax_rate_percent": round(tax_rate_percent, 2),
        "suggested_price": round(suggested_price, 2),
        "discount_percent": round(discount_percent, 2),
        "discount_amount": round(discount_amount, 2),
        "subtotal_after_discount": round(subtotal_after_discount, 2),
        "shipping_cost": round(shipping_cost, 2),
        "final_price_to_client": round(final_price_to_client, 2),
        "tax_amount": round(tax_amount, 2),
        "net_revenue": round(net_revenue, 2),
        "net_profit": round(net_profit, 2),
        "effective_profit_margin_percent": round(effective_profit_margin_percent, 2),
    }
