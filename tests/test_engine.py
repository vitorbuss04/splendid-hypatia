import pytest
from backend.engine import (
    calculate_printer_hourly_rate,
    calculate_plate_cost,
    calculate_project_summary,
)

def test_printer_hourly_rate_standard():
    rates = calculate_printer_hourly_rate(
        acquisition_cost=3000.0,
        lifespan_hours=5000.0,
        avg_power_watts=150.0,
        energy_rate_kwh=0.85,
        maintenance_cost_per_hour=1.0,
    )
    # Depreciation: 3000 / 5000 = 0.60
    assert rates["depreciation_per_hour"] == 0.60
    # Energy: (150 / 1000) * 0.85 = 0.1275
    assert rates["energy_cost_per_hour"] == 0.1275
    # Maintenance: 1.0
    assert rates["maintenance_cost_per_hour"] == 1.0
    # Total: 0.60 + 0.1275 + 1.0 = 1.7275
    assert rates["machine_hourly_rate"] == 1.7275

def test_printer_hourly_rate_zero_lifespan_edge_case():
    rates = calculate_printer_hourly_rate(
        acquisition_cost=3000.0,
        lifespan_hours=0.0,
        avg_power_watts=200.0,
        energy_rate_kwh=1.0,
        maintenance_cost_per_hour=0.5,
    )
    assert rates["depreciation_per_hour"] == 0.0
    assert rates["energy_cost_per_hour"] == 0.20
    assert rates["maintenance_cost_per_hour"] == 0.50
    assert rates["machine_hourly_rate"] == 0.70

def test_printer_hourly_rate_negative_inputs():
    rates = calculate_printer_hourly_rate(
        acquisition_cost=-500.0,
        lifespan_hours=1000.0,
        avg_power_watts=-50.0,
        energy_rate_kwh=-1.0,
        maintenance_cost_per_hour=-2.0,
    )
    assert rates["depreciation_per_hour"] == 0.0
    assert rates["energy_cost_per_hour"] == 0.0
    assert rates["maintenance_cost_per_hour"] == 0.0
    assert rates["machine_hourly_rate"] == 0.0

def test_plate_cost_with_printer_and_filament():
    printer = {
        "acquisition_cost": 2000.0,
        "lifespan_hours": 2000.0,  # 1.00/h depreciation
        "avg_power_watts": 0.0,
        "energy_rate_kwh": 0.0,
        "maintenance_cost_per_hour": 1.00,  # 1.00/h maintenance -> total machine = 2.00/h
    }
    filament = {
        "spool_price": 100.0,
        "spool_weight_g": 1000.0,  # 0.10 / g
    }
    plate = {
        "name": "Peça Teste",
        "print_time_hours": 3.0,  # machine cost = 3.0 * 2.00 = 6.00
        "part_weight_g": 80.0,
        "purge_weight_g": 20.0,  # total raw = 100.0g
        "failure_margin_percent": 10.0,  # effective weight = 110.0g -> material = 11.00
        "quantity": 2,  # 2 copies
    }

    res = calculate_plate_cost(plate, printer=printer, filament=filament)
    assert res["cost_per_gram"] == 0.10
    assert res["machine_hourly_rate"] == 2.00
    assert res["part_weight_g"] == 80.0
    assert res["purge_weight_g"] == 20.0
    assert res["failure_margin_percent"] == 10.0
    assert res["unit_material_cost"] == 11.00
    assert res["unit_machine_cost"] == 6.00
    assert res["unit_total_cost"] == 17.00
    assert res["quantity"] == 2
    assert res["total_material_cost"] == 22.00
    assert res["total_machine_cost"] == 12.00
    assert res["total_cost"] == 34.00
    assert res["total_time_hours"] == 6.0
    assert res["total_weight_g"] == 200.0
    assert res["total_effective_weight_g"] == 220.0


def test_plate_cost_with_parts_per_plate():
    """Verify that parts_per_plate and total_parts_produced are correctly calculated."""
    plate = {
        "name": "Placa Lote",
        "print_time_hours": 2.0,
        "part_weight_g": 50.0,
        "purge_weight_g": 0.0,
        "failure_margin_percent": 0.0,
        "custom_printer_hourly_rate": 2.0,
        "custom_filament_cost_per_g": 0.10,
        "quantity": 7,
        "parts_per_plate": 15,
    }
    res = calculate_plate_cost(plate)
    assert res["quantity"] == 7
    assert res["parts_per_plate"] == 15
    assert res["total_parts_produced"] == 105
    assert res["total_time_hours"] == 14.0


def test_plate_cost_custom_overrides_when_no_device():
    plate = {
        "name": "Placa Avulsa",
        "custom_printer_hourly_rate": 5.0,
        "custom_filament_cost_per_g": 0.15,
        "print_time_hours": 2.0,  # machine = 10.00
        "part_weight_g": 50.0,
        "purge_weight_g": 0.0,
        "failure_margin_percent": 0.0,  # material = 50 * 0.15 = 7.50
        "quantity": 1,
    }
    res = calculate_plate_cost(plate, printer=None, filament=None)
    assert res["unit_material_cost"] == 7.50
    assert res["unit_machine_cost"] == 10.00
    assert res["total_cost"] == 17.50

def test_project_summary_complete_calculation():
    project = {
        "name": "Projeto Completo",
        "cad_hours": 2.0,
        "cad_hourly_rate": 50.0,  # CAD = 100.00
        "post_process_hours": 1.0,
        "post_process_hourly_rate": 30.0,  # Post = 30.00
        "overhead_cost": 20.0,  # Overhead = 20.00
        "profit_margin_percent": 25.0,  # 25% margin
        "tax_rate_percent": 10.0,  # 10% taxes
        "discount_percent": 5.0,  # 5% discount
        "shipping_cost": 15.0,  # R$ 15 frete
    }
    plates = [
        {
            "name": "Placa 1",
            "custom_printer_hourly_rate": 2.0,
            "custom_filament_cost_per_g": 0.10,
            "print_time_hours": 5.0,  # machine: 10.00
            "part_weight_g": 100.0,  # mat: 10.00
            "purge_weight_g": 0.0,
            "failure_margin_percent": 0.0,
            "quantity": 1,  # plate total = 20.00
        },
        {
            "name": "Placa 2",
            "custom_printer_hourly_rate": 1.0,
            "custom_filament_cost_per_g": 0.20,
            "print_time_hours": 10.0,  # machine: 10.00
            "part_weight_g": 100.0,  # mat: 20.00
            "purge_weight_g": 0.0,
            "failure_margin_percent": 0.0,
            "quantity": 1,  # plate total = 30.00
        }
    ]
    bom_items = [
        {"name": "Parafusos M3", "quantity": 10, "unit_cost": 0.50},  # 5.00
        {"name": "Insertos M3", "quantity": 5, "unit_cost": 1.00},   # 5.00
    ]

    summary = calculate_project_summary(project, plates, bom_items)

    # Plates cost: 20.00 + 30.00 = 50.00
    assert summary["total_plates_cost"] == 50.00
    assert summary["total_filament_weight_g"] == 200.0
    assert summary["total_effective_filament_weight_g"] == 200.0
    # BOM cost: 5.00 + 5.00 = 10.00
    assert summary["total_bom_cost"] == 10.00
    # Labor: 100.00 + 30.00 = 130.00
    assert summary["total_labor_cost"] == 130.00
    # Overhead: 20.00
    assert summary["overhead_cost"] == 20.00
    # Base cost: 50 + 10 + 130 + 20 = 210.00
    assert summary["base_cost"] == 210.00

    # Pricing formula: (Base * (1 + Margin)) / (1 - Tax)
    # = (210.00 * 1.25) / (1 - 0.10)
    # = 262.50 / 0.90 = 291.6666... -> 291.67
    assert summary["suggested_price"] == 291.67

    # Discount: 5% of 291.67 = 14.58
    assert summary["discount_amount"] == 14.58
    # Subtotal after discount: 291.67 - 14.58 = 277.09
    assert summary["subtotal_after_discount"] == 277.09
    # Final price to client: 277.09 + 15.00 (frete) = 292.09
    assert summary["final_price_to_client"] == 292.09

    # Tax: 10% on 277.09 = 27.71
    assert summary["tax_amount"] == 27.71
    # Net revenue: 277.09 - 27.71 = 249.38
    assert summary["net_revenue"] == 249.38
    # Net profit: 249.38 - 210.00 = 39.38
    assert summary["net_profit"] == 39.38

def test_project_summary_zero_base_cost_and_high_tax_edge_case():
    project = {
        "name": "Projeto Vazio",
        "cad_hours": 0.0,
        "cad_hourly_rate": 0.0,
        "post_process_hours": 0.0,
        "post_process_hourly_rate": 0.0,
        "overhead_cost": 0.0,
        "profit_margin_percent": 50.0,
        "tax_rate_percent": 99.9,  # Very high tax rate
        "discount_percent": 0.0,
        "shipping_cost": 0.0,
    }
    summary = calculate_project_summary(project, [], [])
    assert summary["base_cost"] == 0.0
    assert summary["suggested_price"] == 0.0
    assert summary["final_price_to_client"] == 0.0
    assert summary["net_profit"] == 0.0


def test_plate_cost_with_zero_machine_hourly_rate_and_zero_filament_cost():
    """
    Verifies that 0.0 machine hourly rate (e.g. fully depreciated machine, free solar energy)
    and 0.0 filament cost per gram (e.g. client provided material) are preserved and produce
    0.0 unit costs without defaulting to non-zero values.
    """
    printer = {
        "acquisition_cost": 0.0,
        "lifespan_hours": 5000.0,
        "avg_power_watts": 0.0,
        "energy_rate_kwh": 0.0,
        "maintenance_cost_per_hour": 0.0,
    }
    filament = {
        "spool_price": 0.0,
        "spool_weight_g": 1000.0,
    }
    plate = {
        "name": "Peça Gratuita",
        "print_time_hours": 5.0,
        "part_weight_g": 100.0,
        "purge_weight_g": 0.0,
        "failure_margin_percent": 10.0,
        "quantity": 2,
    }
    cost = calculate_plate_cost(plate, printer=printer, filament=filament)
    assert cost["machine_hourly_rate"] == 0.0
    assert cost["total_machine_cost"] == 0.0
    assert cost["cost_per_gram"] == 0.0
    assert cost["total_material_cost"] == 0.0
    assert cost["total_cost"] == 0.0


def test_calculate_failure_cost_and_project_summary_scrap():
    from backend.engine import calculate_failure_cost

    printer = {
        "acquisition_cost": 3000.0,
        "lifespan_hours": 5000.0, # 0.60
        "avg_power_watts": 150.0,
        "energy_rate_kwh": 1.0,   # 0.15
        "maintenance_cost_per_hour": 1.25, # total = 2.00 / h
    }
    filament = {
        "spool_price": 100.0,
        "spool_weight_g": 1000.0, # 0.10 / g
    }
    plate = {
        "id": 1,
        "name": "Placa 1",
        "printer_id": 1,
        "filament_id": 1,
        "print_time_hours": 4.0,
        "part_weight_g": 80.0,
        "purge_weight_g": 0.0,
        "failure_margin_percent": 0.0,
        "quantity": 1,
    }

    # Failure 1: 2 hours and 30g wasted due to warping, not charged to client
    fail_log = {
        "id": 10,
        "plate_id": 1,
        "lost_time_hours": 2.0,
        "lost_filament_weight_g": 30.0,
        "reason": "warping",
        "reprinted": True,
        "charged_to_client": False,
    }

    fail_calc = calculate_failure_cost(fail_log, plate=plate, printer=printer, filament=filament)
    # Material: 30g * 0.10 = 3.00
    # Machine: 2h * 2.00 = 4.00
    # Total: 7.00
    assert fail_calc["calculated_material_cost"] == 3.00
    assert fail_calc["calculated_machine_cost"] == 4.00
    assert fail_calc["calculated_cost"] == 7.00

    project = {
        "overhead_cost": 0.0,
        "profit_margin_percent": 30.0,
        "tax_rate_percent": 6.0,
        "discount_percent": 0.0,
        "shipping_cost": 0.0,
    }

    summary = calculate_project_summary(
        project,
        plates=[plate],
        bom_items=[],
        printers_by_id={1: printer},
        filaments_by_id={1: filament},
        failure_logs=[fail_log]
    )

    # Base cost: Plate is 80g * 0.10 (8.00) + 4h * 2.00 (8.00) = 16.00
    assert summary["base_cost"] == 16.00
    # Scrap cost: 7.00
    assert summary["total_scrap_cost"] == 7.00
    assert summary["actual_base_cost"] == 23.00 # 16.00 + 7.00
    assert summary["total_scrap_filament_g"] == 30.0
    assert summary["total_scrap_time_hours"] == 2.0
    # Check that actual net profit is reduced by the absorbed scrap
    assert summary["actual_net_profit"] == round(summary["net_revenue"] - 23.00, 2)
    assert summary["scrap_profit_loss"] == 7.00


