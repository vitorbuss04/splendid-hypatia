import pytest

def test_registration_starts_100_percent_clean(client):
    """
    CRITICAL REQUIREMENT:
    Accounts must start 100% empty upon registration (no pre-loaded or mock printers/filaments/projects).
    """
    resp = client.post("/api/auth/register", json={
        "email": "clean_user@example.com",
        "password": "strongpassword123",
        "full_name": "Usuario Limpo",
        "company_name": "Oficina 3D"
    })
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify printers list is 100% empty
    printers_resp = client.get("/api/printers", headers=headers)
    assert printers_resp.status_code == 200
    assert printers_resp.json() == []

    # Verify filaments list is 100% empty
    filaments_resp = client.get("/api/filaments", headers=headers)
    assert filaments_resp.status_code == 200
    assert filaments_resp.json() == []

    # Verify projects list is 100% empty
    projects_resp = client.get("/api/projects", headers=headers)
    assert projects_resp.status_code == 200
    assert projects_resp.json() == []

def test_duplicate_registration_fails(client):
    payload = {"email": "dup@example.com", "password": "pass123456"}
    resp1 = client.post("/api/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post("/api/auth/register", json=payload)
    assert resp2.status_code == 400
    assert "já está cadastrado" in resp2.json()["detail"]

def test_login_flow(client, make_user):
    user_info = make_user(email="login_test@example.com", password="mypassword123")

    # Correct login
    login_resp = client.post("/api/auth/login", json={
        "email": "login_test@example.com",
        "password": "mypassword123"
    })
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()

    # Wrong password
    bad_login = client.post("/api/auth/login", json={
        "email": "login_test@example.com",
        "password": "wrongpassword"
    })
    assert bad_login.status_code == 401

def test_printers_crud(client, make_user):
    user = make_user(email="printer_user@example.com")
    headers = user["headers"]

    # 1. Create printer
    p_data = {
        "name": "Bambu Lab P1S",
        "model": "CoreXY 256x256",
        "acquisition_cost": 4500.0,
        "lifespan_hours": 5000.0,
        "avg_power_watts": 160.0,
        "maintenance_cost_per_hour": 1.5,
        "energy_rate_kwh": 0.85,
        "notes": "Bico 0.4mm endurecido",
    }
    create_resp = client.post("/api/printers", json=p_data, headers=headers)
    assert create_resp.status_code == 201
    printer = create_resp.json()
    assert printer["name"] == "Bambu Lab P1S"
    assert printer["machine_hourly_rate"] > 0
    p_id = printer["id"]

    # 2. List printers
    list_resp = client.get("/api/printers", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 3. Get single printer
    get_resp = client.get(f"/api/printers/{p_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == p_id

    # 4. Update printer
    update_resp = client.put(f"/api/printers/{p_id}", json={"avg_power_watts": 200.0}, headers=headers)
    assert update_resp.status_code == 200
    assert update_resp.json()["avg_power_watts"] == 200.0

    # 5. Delete printer
    del_resp = client.delete(f"/api/printers/{p_id}", headers=headers)
    assert del_resp.status_code == 204

    # 6. Verify deleted
    get_del = client.get(f"/api/printers/{p_id}", headers=headers)
    assert get_del.status_code == 404

def test_filaments_crud(client, make_user):
    user = make_user(email="filament_user@example.com")
    headers = user["headers"]

    # 1. Create filament
    f_data = {
        "name": "PLA Preto Fosco",
        "brand": "Voolt3D",
        "material": "PLA",
        "color": "Preto",
        "spool_weight_g": 1000.0,
        "spool_price": 95.0,
        "density_g_cm3": 1.24,
    }
    create_resp = client.post("/api/filaments", json=f_data, headers=headers)
    assert create_resp.status_code == 201
    filament = create_resp.json()
    assert filament["cost_per_gram"] == 0.095
    f_id = filament["id"]

    # 2. List filaments
    list_resp = client.get("/api/filaments", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 3. Update filament
    update_resp = client.put(f"/api/filaments/{f_id}", json={"spool_price": 100.0}, headers=headers)
    assert update_resp.status_code == 200
    assert update_resp.json()["cost_per_gram"] == 0.10

    # 4. Delete filament
    del_resp = client.delete(f"/api/filaments/{f_id}", headers=headers)
    assert del_resp.status_code == 204

def test_project_complete_lifecycle_and_pdf(client, make_user):
    user = make_user(email="project_boss@example.com")
    headers = user["headers"]

    # Create printer & filament
    p_resp = client.post("/api/printers", json={
        "name": "Creality Ender 3 V3",
        "acquisition_cost": 2000.0,
        "lifespan_hours": 4000.0,  # 0.50/h
        "avg_power_watts": 120.0,
        "energy_rate_kwh": 0.85,   # 0.102/h
        "maintenance_cost_per_hour": 1.0,  # 1.00/h -> total machine = 1.602/h
    }, headers=headers)
    printer_id = p_resp.json()["id"]

    f_resp = client.post("/api/filaments", json={
        "name": "PETG Cinza",
        "spool_weight_g": 1000.0,
        "spool_price": 110.0,  # 0.11/g
    }, headers=headers)
    filament_id = f_resp.json()["id"]

    # Create project with 1 plate and 1 BOM item
    proj_payload = {
        "name": "Suporte Articulado para Câmera",
        "client_name": "João Engenheiro",
        "client_email": "joao@eng.com",
        "client_phone": "(11) 98765-4321",
        "status": "draft",
        "cad_hours": 1.5,
        "cad_hourly_rate": 60.0,  # CAD = 90.00
        "post_process_hours": 0.5,
        "post_process_hourly_rate": 40.0,  # Post = 20.00
        "overhead_cost": 15.0,  # Overhead = 15.00
        "profit_margin_percent": 35.0,
        "tax_rate_percent": 6.0,
        "discount_percent": 0.0,
        "shipping_cost": 25.0,
        "plates": [
            {
                "name": "Base e Braço Articulado",
                "printer_id": printer_id,
                "filament_id": filament_id,
                "print_time_hours": 6.0,
                "part_weight_g": 120.0,
                "purge_weight_g": 10.0,  # 130g
                "failure_margin_percent": 10.0,  # 143g effective * 0.11 = 15.73
                "quantity": 1,
            }
        ],
        "bom_items": [
            {
                "name": "Parafusos M4 e Porcas Travantes",
                "category": "Fixadores",
                "quantity": 4,
                "unit_cost": 2.50,  # 10.00
            }
        ]
    }

    create_proj = client.post("/api/projects", json=proj_payload, headers=headers)
    assert create_proj.status_code == 201
    proj_data = create_proj.json()
    proj_id = proj_data["id"]
    assert proj_data["name"] == "Suporte Articulado para Câmera"
    assert len(proj_data["plates"]) == 1
    assert len(proj_data["bom_items"]) == 1

    summary = proj_data["summary"]
    assert summary["base_cost"] > 0
    assert summary["suggested_price"] > summary["base_cost"]
    assert summary["final_price_to_client"] > summary["suggested_price"]  # includes shipping

    # Add second plate
    plate_resp = client.post(f"/api/projects/{proj_id}/plates", json={
        "name": "Adaptador de Rosca 1/4",
        "printer_id": printer_id,
        "filament_id": filament_id,
        "print_time_hours": 1.0,
        "part_weight_g": 20.0,
        "purge_weight_g": 0.0,
        "failure_margin_percent": 5.0,
        "quantity": 2,
    }, headers=headers)
    assert plate_resp.status_code == 201

    # Check updated project summary
    sum_resp = client.get(f"/api/projects/{proj_id}/summary", headers=headers)
    assert sum_resp.status_code == 200
    assert sum_resp.json()["total_plates_count"] == 2

    # Duplicate project
    dup_resp = client.post(f"/api/projects/{proj_id}/duplicate", headers=headers)
    assert dup_resp.status_code == 200
    dup_proj = dup_resp.json()
    assert "(Cópia)" in dup_proj["name"]
    assert len(dup_proj["plates"]) == 2

    # PDF Export: Client quote
    pdf_client = client.get(f"/api/projects/{proj_id}/pdf?type=client", headers=headers)
    assert pdf_client.status_code == 200
    assert pdf_client.headers["content-type"] == "application/pdf"
    assert len(pdf_client.content) > 1000

    # PDF Export: Production technical order
    pdf_tech = client.get(f"/api/projects/{proj_id}/pdf?type=technical", headers=headers)
    assert pdf_tech.status_code == 200
    assert pdf_tech.headers["content-type"] == "application/pdf"
    assert len(pdf_tech.content) > 1000

def test_multitenant_data_isolation(client, make_user):
    user_a = make_user(email="alice@company.com")
    user_b = make_user(email="bob@company.com")

    # User A creates a printer and project
    p_resp = client.post("/api/printers", json={"name": "Alice's Printer"}, headers=user_a["headers"])
    alice_printer_id = p_resp.json()["id"]

    proj_resp = client.post("/api/projects", json={"name": "Alice's Secret Project"}, headers=user_a["headers"])
    alice_project_id = proj_resp.json()["id"]

    # User B should NOT see Alice's items
    bob_printers = client.get("/api/printers", headers=user_b["headers"]).json()
    assert len(bob_printers) == 0

    bob_projects = client.get("/api/projects", headers=user_b["headers"]).json()
    assert len(bob_projects) == 0

    # User B attempting to access Alice's project directly must receive 404
    get_alice_proj = client.get(f"/api/projects/{alice_project_id}", headers=user_b["headers"])
    assert get_alice_proj.status_code == 404

    # User B attempting to delete Alice's printer must receive 404
    del_alice_printer = client.delete(f"/api/printers/{alice_printer_id}", headers=user_b["headers"])
    assert del_alice_printer.status_code == 404

    # User B attempting to download Alice's PDF must receive 404
    pdf_resp = client.get(f"/api/projects/{alice_project_id}/pdf", headers=user_b["headers"])
    assert pdf_resp.status_code == 404
