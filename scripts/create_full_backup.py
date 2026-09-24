import json
import psycopg
from datetime import datetime
from pathlib import Path

BACKUP_DIR = Path("data/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = BACKUP_DIR / f"full_pre_migration_backup_{timestamp}.json"

conn = psycopg.connect('postgresql://postgres.your-tenant-id:124c92be406d143842e01a4c0c09fb1c@136.248.126.192:5432/postgres')
cur = conn.cursor()

backup_data = {
    "created_at": datetime.now().isoformat(),
    "description": "Pre-migration full backup of user account and data",
    "sources": {}
}

# 1. Supabase auth.users
cur.execute("SELECT id, email, created_at FROM auth.users WHERE email = 'augustobussvitor@gmail.com'")
row = cur.fetchone()
if row:
    backup_data["sources"]["auth_user"] = {
        "id": str(row[0]),
        "email": row[1],
        "created_at": str(row[2])
    }

# 2. Supabase 3dprinting-calculator schema
for tbl in ["global_settings", "printers", "materials", "project_folders", "projects", "BatchPayment"]:
    try:
        cur.execute(f'SELECT * FROM "3dprinting-calculator".{tbl} WHERE user_id = \'ba75ba83-3019-4cb4-9a77-9ab7035692c9\'')
        cols = [desc[0] for desc in cur.description]
        rows = [dict(zip(cols, [str(v) if not isinstance(v, (int, float, bool, dict, list, type(None))) else v for v in r])) for r in cur.fetchall()]
        backup_data["sources"][f"3dprinting_calculator_{tbl}"] = rows
        print(f"Backed up 3dprinting-calculator.{tbl}: {len(rows)} rows")
    except Exception as e:
        print(f"Error backing up {tbl}: {e}")

# 3. VPS prod.db user account
# From earlier extraction of prod.db:
backup_data["sources"]["vps_prod_db_users"] = [
    {
        "id": 2,
        "email": "augustobussvitor@gmail.com",
        "password_hash": "$2b$12$S0ohpmYxEouKiPMNNr6iHujHKxaC2pgIZQi61heyhpM8g7My3v6vC",
        "full_name": "Vitor Augusto Buss",
        "company_name": "3D Studio",
        "phone": "(55) 93505-4380",
        "pix_key": "augustobussvitor@gmail.com",
        "default_energy_rate": 0.74,
        "default_failure_rate": 10.0,
        "default_profit_margin": 50.0,
        "default_tax_rate": 0.0,
        "default_cad_rate": 50.0,
        "default_post_rate": 20.0,
        "default_payment_terms": "A combinar / 50% na aprovação e 50% na entrega.",
        "default_warranty_terms": "Garantia de fabricação contra defeitos dimensionais ou delaminação de camadas conforme especificações acordadas.",
        "created_at": "2026-09-23 20:47:21.757815"
    }
]

with open(backup_file, "w", encoding="utf-8") as f:
    json.dump(backup_data, f, indent=2, ensure_ascii=False)

print(f"Saved complete backup to {backup_file}")
conn.close()
