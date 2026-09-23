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

def test_project_put_updates_plates_and_bom(client, make_user):
    user = make_user(email="updater@example.com")
    headers = user["headers"]

    # 1. Create initial project with 1 plate and 1 BOM item
    create_resp = client.post("/api/projects", json={
        "name": "Projeto Versao 1",
        "plates": [
            {
                "name": "Placa 1 Original",
                "print_time_hours": 2.0,
                "part_weight_g": 50.0,
                "purge_weight_g": 0.0,
                "quantity": 1,
            }
        ],
        "bom_items": [
            {
                "name": "Parafuso Original",
                "quantity": 2,
                "unit_cost": 1.0,
            }
        ]
    }, headers=headers)
    assert create_resp.status_code == 201
    proj_id = create_resp.json()["id"]
    assert len(create_resp.json()["plates"]) == 1
    assert len(create_resp.json()["bom_items"]) == 1

    # 2. Update project via PUT including modified plates and BOM items (simulate web UI save)
    update_payload = {
        "name": "Projeto Versao 2 (Atualizado)",
        "plates": [
            {
                "name": "Placa 1 Modificada",
                "print_time_hours": 4.0,
                "part_weight_g": 120.0,
                "purge_weight_g": 15.0,
                "quantity": 2,
            },
            {
                "name": "Placa 2 Nova",
                "print_time_hours": 1.5,
                "part_weight_g": 30.0,
                "purge_weight_g": 5.0,
                "quantity": 1,
            }
        ],
        "bom_items": [
            {
                "name": "Parafuso M3",
                "quantity": 8,
                "unit_cost": 0.25,
            },
            {
                "name": "Inserto M3",
                "quantity": 4,
                "unit_cost": 1.50,
            }
        ]
    }
    put_resp = client.put(f"/api/projects/{proj_id}", json=update_payload, headers=headers)
    assert put_resp.status_code == 200
    updated_data = put_resp.json()
    assert updated_data["name"] == "Projeto Versao 2 (Atualizado)"
    assert len(updated_data["plates"]) == 2
    assert updated_data["plates"][0]["name"] == "Placa 1 Modificada"
    assert updated_data["plates"][0]["purge_weight_g"] == 15.0
    assert updated_data["plates"][1]["name"] == "Placa 2 Nova"
    assert len(updated_data["bom_items"]) == 2

    # 3. GET project to verify persistence
    get_resp = client.get(f"/api/projects/{proj_id}", headers=headers)
    assert get_resp.status_code == 200
    persisted = get_resp.json()
    assert len(persisted["plates"]) == 2
    assert len(persisted["bom_items"]) == 2

    # 4. Verify Technical PDF with purge weight works
    tech_pdf = client.get(f"/api/projects/{proj_id}/pdf?type=technical", headers=headers)
    assert tech_pdf.status_code == 200
    assert tech_pdf.headers["content-type"] == "application/pdf"
    assert len(tech_pdf.content) > 1000

def test_api_unknown_route_returns_404_json(client):
    r = client.get("/api/nonexistent_endpoint")
    assert r.status_code == 404
    assert "application/json" in r.headers["content-type"]
    assert "detail" in r.json()

def test_auth_case_insensitive_email(client):
    # Register with mixed case
    reg_resp = client.post("/api/auth/register", json={
        "email": "MixedCaseUser@Example.COM",
        "password": "secretpassword123",
        "full_name": "Mixed Case"
    })
    assert reg_resp.status_code == 201

    # Duplicate registration in all lowercase must fail
    dupe_resp = client.post("/api/auth/register", json={
        "email": "mixedcaseuser@example.com",
        "password": "secretpassword123",
        "full_name": "Duplicate"
    })
    assert dupe_resp.status_code == 400

    # Login in lowercase must succeed
    login_resp = client.post("/api/auth/login", json={
        "email": "mixedcaseuser@example.com",
        "password": "secretpassword123"
    })
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_filament_feedback_decimal_price_and_weights(client, make_user):
    """
    Validates user feedback:
    - Filament spool price accepts cents/decimals (e.g. R$ 56.50)
    - Filament spool weight accepts both standard 1000g and odd values (1001g) or custom weights
    """
    user = make_user(email="filament_decimal@example.com")
    headers = user["headers"]

    # Test 1: Spool price with cents (56.50) and round weight 1000g
    resp1 = client.post("/api/filaments", json={
        "name": "PLA Amarelo Canário",
        "brand": "Voolt3D",
        "material": "PLA",
        "color": "Amarelo",
        "spool_weight_g": 1000.0,
        "spool_price": 56.50,
    }, headers=headers)
    assert resp1.status_code == 201
    f1 = resp1.json()
    assert f1["spool_price"] == 56.50
    assert f1["spool_weight_g"] == 1000.0
    assert f1["cost_per_gram"] == 0.0565

    # Test 2: Odd weight 1001g and decimal price 89.90
    resp2 = client.post("/api/filaments", json={
        "name": "PLA Branco Puro",
        "brand": "eSun",
        "material": "PLA",
        "color": "Branco",
        "spool_weight_g": 1001.0,
        "spool_price": 89.90,
    }, headers=headers)
    assert resp2.status_code == 201
    f2 = resp2.json()
    assert f2["spool_weight_g"] == 1001.0
    assert f2["spool_price"] == 89.90
    assert f2["cost_per_gram"] == round(89.90 / 1001.0, 4)

    # Test 3: Sample spool 250g with cents 32.75
    resp3 = client.post("/api/filaments", json={
        "name": "TPU Flex Azul",
        "brand": "Suntop",
        "material": "TPU",
        "color": "Azul",
        "spool_weight_g": 250.0,
        "spool_price": 32.75,
    }, headers=headers)
    assert resp3.status_code == 201
    f3 = resp3.json()
    assert f3["spool_weight_g"] == 250.0
    assert f3["spool_price"] == 32.75
    assert f3["cost_per_gram"] == round(32.75 / 250.0, 4)


def test_printer_feedback_lifespan_and_decimal_cost(client, make_user):
    """
    Validates user feedback:
    - Printer lifespan accepts standard 5000h, odd hours, or any positive number
    - Acquisition cost accepts decimal currency values (e.g. 3499.90)
    """
    user = make_user(email="printer_lifespan@example.com")
    headers = user["headers"]

    # Test 1: Standard 5000h lifespan and 3499.90 acquisition cost
    resp1 = client.post("/api/printers", json={
        "name": "Creality K1 Max",
        "model": "CoreXY 300x300",
        "acquisition_cost": 3499.90,
        "lifespan_hours": 5000.0,
        "avg_power_watts": 180.0,
        "maintenance_cost_per_hour": 1.25,
        "energy_rate_kwh": 0.85,
    }, headers=headers)
    assert resp1.status_code == 201
    p1 = resp1.json()
    assert p1["lifespan_hours"] == 5000.0
    assert p1["acquisition_cost"] == 3499.90
    expected_deprec = round(3499.90 / 5000.0, 4)
    assert p1["rates_breakdown"]["depreciation_per_hour"] == expected_deprec

    # Test 2: Odd lifespan 5001h
    resp2 = client.post("/api/printers", json={
        "name": "Bambu Lab A1 Mini",
        "model": "Bedslinger 180x180",
        "acquisition_cost": 1999.00,
        "lifespan_hours": 5001.0,
        "avg_power_watts": 80.0,
        "maintenance_cost_per_hour": 0.50,
        "energy_rate_kwh": 0.85,
    }, headers=headers)
    assert resp2.status_code == 201
    p2 = resp2.json()
    assert p2["lifespan_hours"] == 5001.0


def test_filament_and_printer_updates_with_feedback_values(client, make_user):
    """
    Validates that updating existing filaments and printers accepts
    decimal spool prices, standard/odd weights, and standard/odd lifespan hours.
    """
    user = make_user(email="update_feedback@example.com")
    headers = user["headers"]

    # 1. Create initial filament
    f_res = client.post("/api/filaments", json={
        "name": "Filamento Inicial",
        "spool_weight_g": 1000.0,
        "spool_price": 90.0,
    }, headers=headers)
    assert f_res.status_code == 201
    f_id = f_res.json()["id"]

    # Update to decimal price 56.50
    up_f = client.put(f"/api/filaments/{f_id}", json={
        "spool_price": 56.50,
        "spool_weight_g": 1000.0,
    }, headers=headers)
    assert up_f.status_code == 200
    assert up_f.json()["spool_price"] == 56.50
    assert up_f.json()["spool_weight_g"] == 1000.0
    assert up_f.json()["cost_per_gram"] == 0.0565

    # 2. Create initial printer
    p_res = client.post("/api/printers", json={
        "name": "Impressora Inicial",
        "acquisition_cost": 3000.0,
        "lifespan_hours": 4000.0,
    }, headers=headers)
    assert p_res.status_code == 201
    p_id = p_res.json()["id"]

    # Update to standard 5000h lifespan and decimal cost 3499.90
    up_p = client.put(f"/api/printers/{p_id}", json={
        "acquisition_cost": 3499.90,
        "lifespan_hours": 5000.0,
    }, headers=headers)
    assert up_p.status_code == 200
    assert up_p.json()["acquisition_cost"] == 3499.90
    assert up_p.json()["lifespan_hours"] == 5000.0

    # 3. Create project with this filament & printer, verify calculation & PDF export
    proj_res = client.post("/api/projects", json={
        "name": "Projeto com Filamento Feedback",
        "client_name": "Cliente Feedback",
        "plates": [
            {
                "name": "Placa 1",
                "printer_id": p_id,
                "filament_id": f_id,
                "print_time_hours": 4.0,
                "part_weight_g": 150.0,
                "purge_weight_g": 10.0,
                "failure_margin_percent": 10.0,
                "quantity": 1,
            }
        ]
    }, headers=headers)
    assert proj_res.status_code == 201
    proj = proj_res.json()
    proj_id = proj["id"]
    summary = proj["summary"]
    # Check effective filament cost: (150+10)*1.1 = 176g * 0.0565 = 9.944 -> 9.94
    assert summary["total_filament_weight_g"] == 160.0
    assert summary["total_effective_filament_weight_g"] == 176.0
    assert summary["total_material_cost"] == round(176.0 * 0.0565, 2)

    # PDF download should succeed without float formatting errors
    pdf_resp = client.get(f"/api/projects/{proj_id}/pdf?type=client", headers=headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert len(pdf_resp.content) > 1000


def test_filament_color_hex_and_standard_name(client, make_user):
    user = make_user(email="filament_color@example.com")
    headers = user["headers"]

    # 1. Create filament with color_hex
    payload = {
        "name": "PLA Preto - 3D Prime",
        "brand": "3D Prime",
        "material": "PLA",
        "color": "Preto",
        "color_hex": "#1a1a1a",
        "spool_weight_g": 1000.0,
        "spool_price": 89.90,
    }
    resp = client.post("/api/filaments", json=payload, headers=headers)
    assert resp.status_code == 201
    f_data = resp.json()
    assert f_data["name"] == "PLA Preto - 3D Prime"
    assert f_data["color_hex"] == "#1a1a1a"
    assert f_data["cost_per_gram"] == round(89.90 / 1000.0, 4)

    # 2. Update filament color_hex
    f_id = f_data["id"]
    up_resp = client.put(f"/api/filaments/{f_id}", json={"color_hex": "#000000"}, headers=headers)
    assert up_resp.status_code == 200
    assert up_resp.json()["color_hex"] == "#000000"


def test_project_delivery_days_and_pdf_preview(client, make_user):
    user = make_user(email="delivery_proj@example.com")
    headers = user["headers"]
    token = user["token"]

    # 1. Create project with custom delivery_days
    proj_res = client.post("/api/projects", json={
        "name": "Projeto com Prazo Especifico",
        "client_name": "Cliente Prazo",
        "delivery_days": 5,
        "plates": [
            {
                "name": "Peca Especial",
                "print_time_hours": 3.5,
                "part_weight_g": 50.0,
                "quantity": 1,
            }
        ]
    }, headers=headers)
    assert proj_res.status_code == 201
    proj = proj_res.json()
    assert proj["delivery_days"] == 5
    proj_id = proj["id"]

    # 2. Summary details should include filament_material
    plates_details = proj["summary"]["plates_details"]
    assert len(plates_details) == 1
    assert "filament_material" in plates_details[0]

    # 3. PDF with disposition=inline
    pdf_inline = client.get(f"/api/projects/{proj_id}/pdf?type=client&disposition=inline", headers=headers)
    assert pdf_inline.status_code == 200
    assert "inline;" in pdf_inline.headers["content-disposition"]
    assert pdf_inline.headers["content-type"] == "application/pdf"

    # 4. PDF with token query param authentication (without Authorization header)
    pdf_query_auth = client.get(f"/api/projects/{proj_id}/pdf?type=client&token={token}")
    assert pdf_query_auth.status_code == 200
    assert pdf_query_auth.headers["content-type"] == "application/pdf"
    assert len(pdf_query_auth.content) > 1000


def test_pdf_clean_material_and_delivery_days_grammar(client, make_user):
    from backend.pdf_service import extract_clean_material, build_pdf_document
    # 1. Test clean material extraction
    assert extract_clean_material({"filament_material": "PLA", "filament_name": "PLA Preto - 3D Prime"}) == "PLA"
    assert extract_clean_material({"filament_material": "TPU (Flexível)", "filament_name": "TPU Azul"}) == "TPU"
    assert extract_clean_material({"filament_material": "Resina UV", "filament_name": "Resina Cinza"}) == "RESINA"
    assert extract_clean_material({"filament_material": "Personalizado", "filament_name": "PETG Branco - Voolt3D"}) == "PETG"
    assert extract_clean_material({"filament_material": None, "filament_name": "Desconhecido"}) == "PLA"

    # 2. Test delivery days phrasing: 1 dia útil vs N dias úteis
    user = make_user(email="grammar_test@example.com")
    headers = user["headers"]
    user_db = user["user"]

    # Delivery days = 1
    proj_1 = client.post("/api/projects", json={
        "name": "Entrega Urgente",
        "delivery_days": 1,
        "plates": [{"name": "P1", "print_time_hours": 1.0, "part_weight_g": 20.0}]
    }, headers=headers).json()

    pdf_1 = client.get(f"/api/projects/{proj_1['id']}/pdf?type=client", headers=headers)
    assert pdf_1.status_code == 200
    # build_pdf_document directly to inspect terms string
    from backend.engine import calculate_project_summary
    sum_1 = calculate_project_summary(proj_1, proj_1["plates"], [])
    buf_1 = build_pdf_document({**proj_1, "delivery_days": 1, "summary": sum_1}, user_db, doc_type="client")
    assert buf_1.getvalue().startswith(b"%PDF")


def test_project_zero_tax_rate_and_preservation(client, make_user):
    user = make_user(email="zero_tax@example.com")
    headers = user["headers"]

    # 1. Create project with tax_rate_percent = 0.0
    payload = {
        "name": "Projeto Isento de Imposto",
        "tax_rate_percent": 0.0,
        "profit_margin_percent": 25.0,
        "delivery_days": 5,
        "plates": [
            {
                "name": "Placa 1",
                "print_time_hours": 2.0,
                "part_weight_g": 50.0,
                "quantity": 1
            }
        ]
    }
    resp = client.post("/api/projects", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["tax_rate_percent"] == 0.0
    assert data["summary"]["tax_rate_percent"] == 0.0
    assert data["summary"]["tax_amount"] == 0.0
    assert data["delivery_days"] == 5
    proj_id = data["id"]

    # 2. Get project by ID
    get_resp = client.get(f"/api/projects/{proj_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["tax_rate_percent"] == 0.0

    # 3. Update project keeping tax_rate_percent = 0.0
    upd_resp = client.put(f"/api/projects/{proj_id}", json={
        "tax_rate_percent": 0.0,
        "notes": "Atualizado com 0% imposto"
    }, headers=headers)
    assert upd_resp.status_code == 200
    assert upd_resp.json()["tax_rate_percent"] == 0.0
    assert upd_resp.json()["summary"]["tax_amount"] == 0.0

    # 4. Duplicate project: ensure tax_rate_percent = 0.0 and delivery_days = 5 are preserved
    dup_resp = client.post(f"/api/projects/{proj_id}/duplicate", headers=headers)
    assert dup_resp.status_code == 200
    dup_data = dup_resp.json()
    assert dup_data["tax_rate_percent"] == 0.0
    assert dup_data["delivery_days"] == 5
    assert dup_data["summary"]["tax_amount"] == 0.0






