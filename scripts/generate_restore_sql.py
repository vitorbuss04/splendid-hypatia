import json
from pathlib import Path

# Load backup
backup_files = sorted(Path("data/backups").glob("full_pre_migration_backup_*.json"))
latest_backup = backup_files[-1]
with open(latest_backup, "r", encoding="utf-8") as f:
    backup = json.load(f)

sources = backup["sources"]
user_info = sources["vps_prod_db_users"][0]
printers = sources.get("3dprinting_calculator_printers", [])
materials = sources.get("3dprinting_calculator_materials", [])
folders = {f["id"]: f for f in sources.get("3dprinting_calculator_project_folders", [])}
projects = sources.get("3dprinting_calculator_projects", [])

sql_statements = []

# 1. User
sql_statements.append(f"""
INSERT INTO "3dprintcalc".users (
    id, email, password_hash, full_name, company_name, phone, pix_key,
    default_energy_rate, default_failure_rate, default_profit_margin, default_tax_rate,
    default_cad_rate, default_post_rate, default_payment_terms, default_warranty_terms
) VALUES (
    1,
    '{user_info["email"]}',
    '{user_info["password_hash"]}',
    '{user_info["full_name"]}',
    '{user_info["company_name"]}',
    '{user_info["phone"]}',
    '{user_info["pix_key"]}',
    {user_info["default_energy_rate"]},
    {user_info["default_failure_rate"]},
    {user_info["default_profit_margin"]},
    {user_info["default_tax_rate"]},
    {user_info["default_cad_rate"]},
    {user_info["default_post_rate"]},
    '{user_info["default_payment_terms"]}',
    '{user_info["default_warranty_terms"]}'
)
ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    password_hash = EXCLUDED.password_hash,
    full_name = EXCLUDED.full_name,
    company_name = EXCLUDED.company_name,
    phone = EXCLUDED.phone,
    pix_key = EXCLUDED.pix_key,
    default_energy_rate = EXCLUDED.default_energy_rate,
    default_failure_rate = EXCLUDED.default_failure_rate,
    default_profit_margin = EXCLUDED.default_profit_margin,
    default_tax_rate = EXCLUDED.default_tax_rate,
    default_cad_rate = EXCLUDED.default_cad_rate,
    default_post_rate = EXCLUDED.default_post_rate,
    default_payment_terms = EXCLUDED.default_payment_terms,
    default_warranty_terms = EXCLUDED.default_warranty_terms;

SELECT setval('"3dprintcalc".users_id_seq', (SELECT GREATEST(MAX(id), 1) FROM "3dprintcalc".users));
""")

# 2. Printers
old_to_new_printer_id = {}
for idx, p in enumerate(printers, start=1):
    old_to_new_printer_id[p["id"]] = idx
    p_name = p.get("name", "Bambulab A1").replace("'", "''")
    model = "A1" if "a1" in p_name.lower() else ""
    acq_cost = float(p.get("acquisition_cost") or 2900.0)
    lifespan = float(p.get("lifespan_hours") or 15000.0)
    watts = float(p.get("power_consumption") or 67.0)
    maint = float(p.get("maintenance_cost_per_hour") or 0.1)
    kwh = float(user_info["default_energy_rate"] or 0.74)
    
    sql_statements.append(f"""
INSERT INTO "3dprintcalc".printers (
    id, user_id, name, model, acquisition_cost, lifespan_hours,
    avg_power_watts, maintenance_cost_per_hour, energy_rate_kwh, is_active
) VALUES (
    {idx}, 1, '{p_name}', '{model}', {acq_cost}, {lifespan}, {watts}, {maint}, {kwh}, true
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    model = EXCLUDED.model,
    acquisition_cost = EXCLUDED.acquisition_cost,
    lifespan_hours = EXCLUDED.lifespan_hours,
    avg_power_watts = EXCLUDED.avg_power_watts,
    maintenance_cost_per_hour = EXCLUDED.maintenance_cost_per_hour,
    energy_rate_kwh = EXCLUDED.energy_rate_kwh,
    is_active = EXCLUDED.is_active;
""")

sql_statements.append('SELECT setval(\'"3dprintcalc".printers_id_seq\', (SELECT GREATEST(MAX(id), 1) FROM "3dprintcalc".printers));')

# 3. Filaments / Materials
old_to_new_mat_id = {}
for idx, m in enumerate(materials, start=1):
    old_to_new_mat_id[m["id"]] = idx
    m_name = m.get("name", "").replace("'", "''")
    m_type = m.get("type", "PLA").replace("'", "''")
    m_color_hex = m.get("color") or "#10b981"
    brand = m.get("manufacturer") or ""
    if not brand:
        if "voolt" in m_name.lower(): brand = "Voolt 3D"
        elif "soleyin" in m_name.lower() or "soleiyn" in m_name.lower(): brand = "Soleiyn"
        elif "creality" in m_name.lower(): brand = "Creality"
        elif "bambu" in m_name.lower(): brand = "Bambu Lab"
        else: brand = "Genérica"
    brand = brand.replace("'", "''")
    
    spool_weight = float(m.get("spool_weight") or 1000.0)
    spool_price = float(m.get("spool_price") or 90.0)
    
    sql_statements.append(f"""
INSERT INTO "3dprintcalc".filaments (
    id, user_id, name, brand, material, color_hex, spool_weight_g, spool_price, is_active
) VALUES (
    {idx}, 1, '{m_name}', '{brand}', '{m_type}', '{m_color_hex}', {spool_weight}, {spool_price}, true
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    brand = EXCLUDED.brand,
    material = EXCLUDED.material,
    color_hex = EXCLUDED.color_hex,
    spool_weight_g = EXCLUDED.spool_weight_g,
    spool_price = EXCLUDED.spool_price,
    is_active = EXCLUDED.is_active;
""")

sql_statements.append('SELECT setval(\'"3dprintcalc".filaments_id_seq\', (SELECT GREATEST(MAX(id), 1) FROM "3dprintcalc".filaments));')

# 4. Projects and Plates
status_map = {
    "concluido": "completed",
    "em_producao": "in_production",
    "cancelado": "cancelled",
    "aguardando": "quoted"
}

for idx, p in enumerate(projects, start=1):
    p_name = p.get("name", f"Projeto {idx}").replace("'", "''")
    folder_id = p.get("folder_id")
    folder = folders.get(folder_id) if folder_id else None
    
    client_name = folder["name"].replace("'", "''") if folder else "Cliente Geral"
    status_raw = folder["status"] if folder else "concluido"
    status = status_map.get(status_raw, "draft")
    
    labor_h = float(p.get("labor_time_hours") or 0.0) + float(p.get("labor_time_minutes") or 0.0) / 60.0
    labor_rate = float(p.get("labor_hourly_rate") or 0.0)
    markup = float(p.get("markup") or 50.0)
    
    sql_statements.append(f"""
INSERT INTO "3dprintcalc".projects (
    id, user_id, name, client_name, status,
    post_process_hours, post_process_hourly_rate,
    profit_margin_percent, tax_rate_percent, discount_percent, shipping_cost, delivery_days
) VALUES (
    {idx}, 1, '{p_name}', '{client_name}', '{status}',
    {labor_h:.2f}, {labor_rate:.2f}, {markup:.2f}, 0.0, 0.0, 0.0, 3
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    client_name = EXCLUDED.client_name,
    status = EXCLUDED.status,
    post_process_hours = EXCLUDED.post_process_hours,
    post_process_hourly_rate = EXCLUDED.post_process_hourly_rate,
    profit_margin_percent = EXCLUDED.profit_margin_percent;
""")
    
    # Plate for this project
    pr_id = old_to_new_printer_id.get(p.get("printer_id"))
    pr_id_sql = f"{pr_id}" if pr_id else "NULL"
    
    fl_id = old_to_new_mat_id.get(p.get("material_id"))
    fl_id_sql = f"{fl_id}" if fl_id else "NULL"
    
    print_h = float(p.get("print_time_hours") or 0.0) + float(p.get("print_time_minutes") or 0.0) / 60.0
    weight = float(p.get("model_weight") or 0.0)
    fail_rate = float(p.get("failure_rate") or 10.0)
    
    sql_statements.append(f"""
INSERT INTO "3dprintcalc".plates (
    id, project_id, name, printer_id, filament_id,
    print_time_hours, part_weight_g, failure_margin_percent, quantity
) VALUES (
    {idx}, {idx}, '{p_name}', {pr_id_sql}, {fl_id_sql},
    {print_h:.2f}, {weight:.2f}, {fail_rate:.2f}, 1
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    printer_id = EXCLUDED.printer_id,
    filament_id = EXCLUDED.filament_id,
    print_time_hours = EXCLUDED.print_time_hours,
    part_weight_g = EXCLUDED.part_weight_g,
    failure_margin_percent = EXCLUDED.failure_margin_percent;
""")

sql_statements.append('SELECT setval(\'"3dprintcalc".projects_id_seq\', (SELECT GREATEST(MAX(id), 1) FROM "3dprintcalc".projects));')
sql_statements.append('SELECT setval(\'"3dprintcalc".plates_id_seq\', (SELECT GREATEST(MAX(id), 1) FROM "3dprintcalc".plates));')

with open("data/backups/restore_data.sql", "w", encoding="utf-8") as f:
    f.write("\n".join(sql_statements))

print("Generated restore_data.sql with", len(sql_statements), "statements.")
