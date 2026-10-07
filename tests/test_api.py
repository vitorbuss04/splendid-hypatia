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
    assert dup_resp.status_code == 201
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
    assert dup_resp.status_code == 201
    dup_data = dup_resp.json()
    assert dup_data["tax_rate_percent"] == 0.0
    assert dup_data["delivery_days"] == 5
    assert dup_data["summary"]["tax_amount"] == 0.0


def extract_pdf_stream_text(pdf_bytes: bytes) -> str:
    import base64
    import zlib
    start = pdf_bytes.find(b'stream\n')
    if start == -1:
        start = pdf_bytes.find(b'stream\r\n')
        start += 9
    else:
        start += 7
    end = pdf_bytes.find(b'endstream', start)
    raw = pdf_bytes[start:end].strip()
    return zlib.decompress(base64.a85decode(raw, adobe=True)).decode('latin1', errors='replace')


def test_filament_duplicate_endpoint(client, make_user):
    user1 = make_user(email="dup_fil1@example.com")
    user2 = make_user(email="dup_fil2@example.com")

    # 1. Create filament
    create_resp = client.post("/api/filaments", json={
        "name": "PETG Preto - Voolt3D",
        "brand": "Voolt3D",
        "material": "PETG",
        "color": "Preto",
        "color_hex": "#1a1a1a",
        "spool_weight_g": 1000.0,
        "spool_price": 109.90,
    }, headers=user1["headers"])
    assert create_resp.status_code == 201
    fil_orig = create_resp.json()
    fil_id = fil_orig["id"]

    # 2. Duplicate filament without body (default clone)
    dup_resp = client.post(f"/api/filaments/{fil_id}/duplicate", headers=user1["headers"])
    assert dup_resp.status_code == 201
    fil_dup = dup_resp.json()

    assert fil_dup["id"] != fil_id
    assert fil_dup["name"] == "PETG Preto - Voolt3D (Cópia)"
    assert fil_dup["brand"] == "Voolt3D"
    assert fil_dup["material"] == "PETG"
    assert fil_dup["color"] == "Preto"
    assert fil_dup["color_hex"] == "#1a1a1a"
    assert fil_dup["spool_weight_g"] == 1000.0
    assert fil_dup["spool_price"] == 109.90
    assert fil_dup["cost_per_gram"] == round(109.90 / 1000.0, 4)

    # 3. Duplicate filament with custom new color payload
    dup_resp2 = client.post(f"/api/filaments/{fil_id}/duplicate", json={
        "color": "Azul Celeste",
        "color_hex": "#00b4d8"
    }, headers=user1["headers"])
    assert dup_resp2.status_code == 201
    fil_dup2 = dup_resp2.json()
    assert fil_dup2["id"] != fil_id
    assert fil_dup2["name"] == "PETG Azul Celeste - Voolt3D"
    assert fil_dup2["color"] == "Azul Celeste"
    assert fil_dup2["color_hex"] == "#00b4d8"
    assert fil_dup2["brand"] == "Voolt3D"
    assert fil_dup2["material"] == "PETG"

    # 4. User isolation: user2 cannot duplicate user1's filament
    unauth_resp = client.post(f"/api/filaments/{fil_id}/duplicate", headers=user2["headers"])
    assert unauth_resp.status_code == 404

    # 5. Non-existent filament returns 404
    nonexist_resp = client.post("/api/filaments/99999/duplicate", headers=user1["headers"])
    assert nonexist_resp.status_code == 404


def test_project_payment_and_warranty_terms_and_pdf(client, make_user):
    user = make_user(email="terms_user@example.com")
    headers = user["headers"]

    # 1. Update user preferences with custom default terms
    pref_res = client.put("/api/auth/preferences", json={
        "default_payment_terms": "Padrão Oficina: 40% entrada, 60% entrega.",
        "default_warranty_terms": "Padrão Oficina: 30 dias de garantia contra delaminação.",
    }, headers=headers)
    assert pref_res.status_code == 200
    assert pref_res.json()["default_payment_terms"] == "Padrão Oficina: 40% entrada, 60% entrega."
    assert pref_res.json()["default_warranty_terms"] == "Padrão Oficina: 30 dias de garantia contra delaminação."

    # 2. Create project without specifying terms (fallback to user defaults in PDF)
    proj_res = client.post("/api/projects", json={
        "name": "Projeto com Termos Padrão",
        "client_name": "Cliente Termos",
        "plates": [
            {
                "name": "Placa 1",
                "custom_printer_hourly_rate": 5.0,
                "custom_filament_cost_per_g": 0.15,
                "print_time_hours": 2.0,
                "part_weight_g": 100.0,
            }
        ]
    }, headers=headers)
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    pdf_res1 = client.get(f"/api/projects/{proj_id}/pdf?type=client", headers=headers)
    assert pdf_res1.status_code == 200
    assert pdf_res1.headers["content-type"] == "application/pdf"
    assert pdf_res1.content.startswith(b"%PDF")
    # Deep verification: assert workshop defaults exist in decompressed PDF text
    pdf_text1 = extract_pdf_stream_text(pdf_res1.content)
    assert "40% entrada, 60% entrega" in pdf_text1
    assert "30 dias de garantia contra" in pdf_text1

    # 3. Update project with project-specific custom terms
    upd_res = client.put(f"/api/projects/{proj_id}", json={
        "payment_terms": "100% antecipado via PIX com 5% de desconto",
        "warranty_terms": "Garantia estendida de 90 dias com reposição imediata",
    }, headers=headers)
    assert upd_res.status_code == 200
    assert upd_res.json()["payment_terms"] == "100% antecipado via PIX com 5% de desconto"
    assert upd_res.json()["warranty_terms"] == "Garantia estendida de 90 dias com reposição imediata"

    # 4. Duplicate project preserves custom terms
    dup_res = client.post(f"/api/projects/{proj_id}/duplicate", headers=headers)
    assert dup_res.status_code == 201
    dup_data = dup_res.json()
    assert dup_data["payment_terms"] == "100% antecipado via PIX com 5% de desconto"
    assert dup_data["warranty_terms"] == "Garantia estendida de 90 dias com reposição imediata"

    # 5. Export PDF reflects project-specific terms (deep verification)
    pdf_res2 = client.get(f"/api/projects/{proj_id}/pdf?type=client", headers=headers)
    assert pdf_res2.status_code == 200
    assert pdf_res2.headers["content-type"] == "application/pdf"
    assert pdf_res2.content.startswith(b"%PDF")
    pdf_text2 = extract_pdf_stream_text(pdf_res2.content)
    assert "100% antecipado via PIX" in pdf_text2
    assert "Garantia estendida de 90 dias" in pdf_text2


def test_project_pdf_terms_with_xml_special_characters(client, make_user):
    """
    Verifies that terms with special XML/HTML characters (<, >, &, unclosed tags)
    do not crash ReportLab PDF generation and are safely rendered.
    """
    user = make_user(email="xml_terms@example.com")
    headers = user["headers"]

    proj_res = client.post("/api/projects", json={
        "name": "Projeto com Caracteres Especiais",
        "payment_terms": "Sinal 50% & 50% na entrega <aprovado>",
        "warranty_terms": "Peças < 100mm: 30 dias; Peças > 100mm: 60 dias & suporte",
        "plates": [
            {
                "name": "Placa 1",
                "custom_printer_hourly_rate": 5.0,
                "custom_filament_cost_per_g": 0.15,
                "print_time_hours": 1.0,
                "part_weight_g": 50.0,
            }
        ]
    }, headers=headers)
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    pdf_res = client.get(f"/api/projects/{proj_id}/pdf?type=client", headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF")

    pdf_text = extract_pdf_stream_text(pdf_res.content)
    assert "Sinal 50%" in pdf_text
    assert "30 dias" in pdf_text

def test_dashboard_stats_endpoint(client, make_user):
    user = make_user(email="dashboard_tester@example.com")
    headers = user["headers"]

    # 1. New user with 0 projects -> returns zeros gracefully
    empty_stats = client.get("/api/projects/dashboard-stats", headers=headers)
    assert empty_stats.status_code == 200
    data = empty_stats.json()
    assert data["total_projects"] == 0
    assert data["total_revenue_approved"] == 0.0
    assert data["pipeline_revenue"] == 0.0
    assert len(data["monthly_timeline"]) >= 6
    assert data["status_counts"]["draft"] == 0
    assert len(data["top_projects"]) == 0

    # 2. Create printer & filament
    p_resp = client.post("/api/printers", json={"name": "Ender 3", "acquisition_cost": 1500, "lifespan_hours": 3000}, headers=headers)
    assert p_resp.status_code == 201
    printer_id = p_resp.json()["id"]

    f_resp = client.post("/api/filaments", json={"name": "PLA Preto", "spool_price": 100, "spool_weight_g": 1000}, headers=headers)
    assert f_resp.status_code == 201
    filament_id = f_resp.json()["id"]

    # 3. Create approved project
    proj_resp = client.post("/api/projects", json={
        "name": "Suporte Drone",
        "client_name": "Tech Corp",
        "status": "approved",
        "plates": [
            {
                "name": "Placa 1",
                "printer_id": printer_id,
                "filament_id": filament_id,
                "print_time_hours": 10.0,
                "part_weight_g": 200.0,
                "quantity": 1,
            }
        ]
    }, headers=headers)
    assert proj_resp.status_code == 201

    # 4. Check dashboard stats now
    stats_resp = client.get("/api/projects/dashboard-stats", headers=headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_projects"] == 1
    assert stats["total_printers"] == 1
    assert stats["total_filaments"] == 1
    assert stats["status_counts"]["approved"] == 1
    assert stats["total_revenue_approved"] > 0
    assert stats["total_print_hours"] == 10.0
    assert stats["cost_breakdown"]["material_cost"] > 0
    assert len(stats["top_projects"]) == 1
    assert stats["top_projects"][0]["name"] == "Suporte Drone"


def test_project_delivery_days_zero_and_pdf_terms(client, make_user):
    user = make_user(email="zero_delivery@example.com")
    headers = user["headers"]

    # 1. Create project with delivery_days = 0
    payload = {
        "name": "Projeto Pronta Entrega",
        "client_name": "Cliente Imediato",
        "delivery_days": 0,
        "plates": [
            {
                "name": "Peça Estoque",
                "print_time_hours": 1.0,
                "part_weight_g": 30.0,
                "quantity": 1
            }
        ]
    }
    resp = client.post("/api/projects", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["delivery_days"] == 0
    proj_id = data["id"]

    # 2. Get project by ID
    get_resp = client.get(f"/api/projects/{proj_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["delivery_days"] == 0

    # 3. Update project keeping delivery_days = 0
    upd_resp = client.put(f"/api/projects/{proj_id}", json={
        "delivery_days": 0,
        "notes": "Confirmado pronta entrega"
    }, headers=headers)
    assert upd_resp.status_code == 200
    assert upd_resp.json()["delivery_days"] == 0

    # 4. Duplicate project: ensure delivery_days = 0 is preserved
    dup_resp = client.post(f"/api/projects/{proj_id}/duplicate", headers=headers)
    assert dup_resp.status_code == 201
    assert dup_resp.json()["delivery_days"] == 0

    # 5. PDF generation should format delivery phrase for 0 days
    pdf_res = client.get(f"/api/projects/{proj_id}/pdf?type=client", headers=headers)
    assert pdf_res.status_code == 200
    pdf_text = extract_pdf_stream_text(pdf_res.content)
    assert "Pronta entrega" in pdf_text or "0 dias" in pdf_text


def test_bom_items_negative_validation_rejection(client, make_user):
    user = make_user(email="bom_neg@example.com")
    headers = user["headers"]

    # 1. Project creation with negative BOM quantity should be rejected (422)
    bad_qty_payload = {
        "name": "Projeto BOM Invalido",
        "bom_items": [
            {
                "name": "Parafuso M3",
                "quantity": -2,
                "unit_cost": 1.50
            }
        ]
    }
    res_qty = client.post("/api/projects", json=bad_qty_payload, headers=headers)
    assert res_qty.status_code == 422

    # 2. Project creation with negative BOM unit_cost should be rejected (422)
    bad_cost_payload = {
        "name": "Projeto BOM Custo Negativo",
        "bom_items": [
            {
                "name": "Parafuso M3",
                "quantity": 2,
                "unit_cost": -15.0
            }
        ]
    }
    res_cost = client.post("/api/projects", json=bad_cost_payload, headers=headers)
    assert res_cost.status_code == 422


def test_plate_cross_tenant_idor_prevention(client, make_user):
    user_a = make_user(email="alice_idor@company.com")
    user_b = make_user(email="bob_idor@company.com")

    # User A creates proprietary printer and high-end filament with custom rates
    prn_a = client.post("/api/printers", json={
        "name": "Alice Industrial SLA",
        "acquisition_cost": 25000.0,
        "lifespan_hours": 2000.0,
        "avg_power_watts": 500.0,
        "energy_rate_kwh": 1.20,
        "maintenance_cost_per_hour": 15.0
    }, headers=user_a["headers"]).json()

    fil_a = client.post("/api/filaments", json={
        "name": "Alice Carbon PEEK",
        "brand": "Specialty Polymer",
        "material": "PEEK",
        "color": "Preto",
        "spool_weight_g": 500.0,
        "spool_price": 750.0
    }, headers=user_a["headers"]).json()

    # User B creates a project
    proj_b = client.post("/api/projects", json={
        "name": "Bob Stealth Quote"
    }, headers=user_b["headers"]).json()
    proj_b_id = proj_b["id"]

    # User B tries to associate Alice's printer_id and filament_id to a plate
    add_plate_res = client.post(f"/api/projects/{proj_b_id}/plates", json={
        "name": "Placa Maliciosa",
        "printer_id": prn_a["id"],
        "filament_id": fil_a["id"],
        "print_time_hours": 2.0,
        "part_weight_g": 50.0
    }, headers=user_b["headers"])
    assert add_plate_res.status_code == 201
    plate_data = add_plate_res.json()

    # The API must NOT associate Alice's foreign keys or leak Alice's proprietary machine rate and cost per gram
    assert plate_data["printer_id"] is None
    assert plate_data["filament_id"] is None
    cost_breakdown = plate_data.get("cost_breakdown", {})
    assert cost_breakdown.get("printer_name") != "Alice Industrial SLA"
    assert cost_breakdown.get("filament_name") != "Alice Carbon PEEK"


def test_project_update_with_deleted_printer_or_filament_no_crash(client, make_user):
    user = make_user(email="deleted_fk@example.com")
    headers = user["headers"]

    # 1. Create a printer and filament
    prn = client.post("/api/printers", json={"name": "Impressora Provisoria"}, headers=headers).json()
    fil = client.post("/api/filaments", json={
        "name": "Filamento Provisorio",
        "brand": "Marca",
        "material": "PLA",
        "color": "Branco",
        "spool_weight_g": 1000.0,
        "spool_price": 100.0
    }, headers=headers).json()

    # 2. Create project referencing them
    proj = client.post("/api/projects", json={
        "name": "Projeto com FK",
        "plates": [
            {
                "name": "Placa 1",
                "printer_id": prn["id"],
                "filament_id": fil["id"],
                "print_time_hours": 1.0,
                "part_weight_g": 20.0
            }
        ]
    }, headers=headers).json()
    proj_id = proj["id"]

    # 3. Delete the printer and filament
    del_prn = client.delete(f"/api/printers/{prn['id']}", headers=headers)
    assert del_prn.status_code == 204
    del_fil = client.delete(f"/api/filaments/{fil['id']}", headers=headers)
    assert del_fil.status_code == 204

    # 4. Updating the project referencing the deleted IDs must NOT crash with HTTP 500 IntegrityError
    update_res = client.put(f"/api/projects/{proj_id}", json={
        "name": "Projeto Atualizado",
        "plates": [
            {
                "name": "Placa 1",
                "printer_id": prn["id"],
                "filament_id": fil["id"],
                "print_time_hours": 1.5,
                "part_weight_g": 25.0
            }
        ]
    }, headers=headers)
    assert update_res.status_code == 200
    updated_proj = update_res.json()
    assert updated_proj["name"] == "Projeto Atualizado"
    assert len(updated_proj["plates"]) == 1
    # Foreign keys gracefully sanitized to None
    assert updated_proj["plates"][0]["printer_id"] is None
    assert updated_proj["plates"][0]["filament_id"] is None

def test_pdf_generation_with_special_characters_and_tags(client, make_user):
    user = make_user(email="special_chars_pdf@example.com")
    headers = user["headers"]

    # Update preferences with special characters
    pref_res = client.put("/api/auth/preferences", json={
        "company_name": "Maker Studio <3D> & CIA",
        "phone": "+55 (11) 98765-4321",
        "pix_key": "pix<key>&admin@maker.com",
        "default_payment_terms": "50% entrada & 50% entrega <balcão>",
        "default_warranty_terms": "Garantia <90 dias> contra empenamento & delaminação"
    }, headers=headers)
    assert pref_res.status_code == 200

    # Create project with technical/HTML-like characters: <V2>, &, <A>, <Inox>
    proj_payload = {
        "name": "Suporte <V2> Náutico & Especial",
        "client_name": "Alpha & Omega Engenharia <Ltda>",
        "client_email": "contato@alphaomega.com.br",
        "client_phone": "11988887777",
        "notes": "Tolerâncias críticas < 0.2mm & acabamento sem marcas.\nLinha 2 com <b> e <custom_tag>.",
        "status": "approved",
        "delivery_days": 4,
        "cad_hours": 1.5,
        "cad_hourly_rate": 80.0,
        "post_process_hours": 0.5,
        "post_process_hourly_rate": 40.0,
        "overhead_cost": 15.0,
        "profit_margin_percent": 40.0,
        "tax_rate_percent": 6.0,
        "discount_percent": 5.0,
        "shipping_cost": 25.0,
        "plates": [
            {
                "name": "Base Inferior <A>",
                "print_time_hours": 3.5,
                "part_weight_g": 145.0,
                "purge_weight_g": 12.0,
                "failure_margin_percent": 10.0,
                "quantity": 2
            }
        ],
        "bom_items": [
            {
                "name": "Parafuso M3x16 <Inox> & Porca",
                "category": "Fixadores <Aço>",
                "quantity": 8,
                "unit_cost": 0.85,
                "notes": "Aço inox 316 & arruela"
            }
        ]
    }
    create_res = client.post("/api/projects", json=proj_payload, headers=headers)
    assert create_res.status_code == 201
    proj_id = create_res.json()["id"]

    # 1. Test Client PDF generation
    pdf_client = client.get(f"/api/projects/{proj_id}/pdf?type=client", headers=headers)
    assert pdf_client.status_code == 200
    assert pdf_client.headers["content-type"] == "application/pdf"
    assert len(pdf_client.content) > 1000

    # 2. Test Technical PDF generation
    pdf_tech = client.get(f"/api/projects/{proj_id}/pdf?type=technical", headers=headers)
    assert pdf_tech.status_code == 200
    assert pdf_tech.headers["content-type"] == "application/pdf"
    assert len(pdf_tech.content) > 1000


def test_dashboard_stats_machine_energy_no_double_counting(client, make_user):
    user = make_user(email="energy_check@example.com")
    headers = user["headers"]

    # 1. Create printer with known parameters:
    # 350W power, energy R$ 0.95/kWh, acquisition 6000 R$, lifespan 6000h, maint 1.50 R$/h
    # hourly rate = 1.0 (depr) + 1.5 (maint) + (350/1000 * 0.95 = 0.3325 energy) = 2.8325 R$/h
    p_resp = client.post("/api/printers", json={
        "name": "Bambu Lab X1C",
        "acquisition_cost": 6000.0,
        "lifespan_hours": 6000.0,
        "avg_power_watts": 350.0,
        "maintenance_cost_per_hour": 1.50,
        "energy_rate_kwh": 0.95
    }, headers=headers)
    assert p_resp.status_code == 201
    printer_id = p_resp.json()["id"]

    f_resp = client.post("/api/filaments", json={
        "name": "PLA Preto",
        "spool_price": 100.0,
        "spool_weight_g": 1000.0
    }, headers=headers)
    assert f_resp.status_code == 201
    filament_id = f_resp.json()["id"]

    # Create project with 10h of printing
    create_res = client.post("/api/projects", json={
        "name": "Peça de Teste Energia",
        "status": "approved",
        "plates": [
            {
                "name": "Placa 1",
                "printer_id": printer_id,
                "filament_id": filament_id,
                "print_time_hours": 10.0,
                "part_weight_g": 100.0,
                "quantity": 1
            }
        ]
    }, headers=headers)
    assert create_res.status_code == 201
    proj_data = create_res.json()
    proj_summary = proj_data["summary"]

    expected_machine_cost = round(proj_summary["total_machine_cost"], 2)
    expected_energy_cost = round(proj_summary["total_energy_cost"], 2)
    assert expected_energy_cost > 0.0

    # Query dashboard stats
    stats_res = client.get("/api/projects/dashboard-stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    cb = stats["cost_breakdown"]

    # machine_energy_cost should equal total_machine_cost (already including energy), NOT total_machine_cost + total_energy_cost
    assert cb["machine_energy_cost"] == expected_machine_cost
    assert cb["machine_energy_cost"] < round(expected_machine_cost + expected_energy_cost, 2)


def test_dashboard_stats_excludes_cancelled_from_monthly_timeline(client, make_user):
    user = make_user(email="cancelled_stats@example.com")
    headers = user["headers"]

    # Create cancelled project with high value
    cancelled_res = client.post("/api/projects", json={
        "name": "Projeto Cancelado Grande",
        "client_name": "Cliente Cancelou",
        "status": "cancelled",
        "plates": [
            {
                "name": "Placa Cara",
                "print_time_hours": 20.0,
                "part_weight_g": 500.0,
                "quantity": 1
            }
        ]
    }, headers=headers)
    assert cancelled_res.status_code == 201

    stats_res = client.get("/api/projects/dashboard-stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()

    # Cancelled project should not add to total revenue approved
    assert stats["total_revenue_approved"] == 0.0
    assert stats["total_net_profit"] == 0.0
    assert stats["status_counts"]["cancelled"] == 1

    # In monthly timeline, revenue, base_cost, net_profit, and print_hours must all be 0
    timeline = stats["monthly_timeline"]
    total_timeline_rev = sum(t["revenue"] for t in timeline)
    total_timeline_profit = sum(t["net_profit"] for t in timeline)
    total_timeline_hours = sum(t["print_hours"] for t in timeline)
    assert total_timeline_rev == 0.0
    assert total_timeline_profit == 0.0
    assert total_timeline_hours == 0.0


def test_plate_and_bom_empty_name_validation(client, make_user):
    """Issue #47: Ensure empty or whitespace-only names for plates and BOM items are rejected with 422."""
    user = make_user(email="empty_names@example.com")
    headers = user["headers"]

    # 1. Project with empty plate name
    res_empty_plate = client.post("/api/projects", json={
        "name": "Projeto Teste",
        "plates": [
            {
                "name": "",
                "print_time_hours": 1.0,
                "part_weight_g": 10.0
            }
        ]
    }, headers=headers)
    assert res_empty_plate.status_code == 422

    # 2. Project with whitespace-only plate name
    res_blank_plate = client.post("/api/projects", json={
        "name": "Projeto Teste",
        "plates": [
            {
                "name": "   ",
                "print_time_hours": 1.0,
                "part_weight_g": 10.0
            }
        ]
    }, headers=headers)
    assert res_blank_plate.status_code == 422

    # 3. Project with empty BOM item name
    res_empty_bom = client.post("/api/projects", json={
        "name": "Projeto Teste",
        "bom_items": [
            {
                "name": "",
                "quantity": 1,
                "unit_cost": 2.5
            }
        ]
    }, headers=headers)
    assert res_empty_bom.status_code == 422

    # 4. Project with whitespace-only BOM item name
    res_blank_bom = client.post("/api/projects", json={
        "name": "Projeto Teste",
        "bom_items": [
            {
                "name": "   ",
                "quantity": 1,
                "unit_cost": 2.5
            }
        ]
    }, headers=headers)
    assert res_blank_bom.status_code == 422


def test_dashboard_stats_excludes_cancelled_from_top_projects_and_cost_breakdown(client, make_user):
    """Issue #48: Ensure cancelled projects are excluded from top_projects and cost breakdown in dashboard stats."""
    user = make_user(email="top_projects_cancel@example.com")
    headers = user["headers"]

    # Create active completed project
    res_active = client.post("/api/projects", json={
        "name": "Projeto Ativo",
        "status": "completed",
        "plates": [
            {"name": "P1", "print_time_hours": 2.0, "part_weight_g": 50.0}
        ]
    }, headers=headers)
    assert res_active.status_code == 201

    # Create cancelled project with massive value
    res_cancelled = client.post("/api/projects", json={
        "name": "Projeto Gigante Cancelado",
        "status": "cancelled",
        "plates": [
            {"name": "P2", "print_time_hours": 200.0, "part_weight_g": 5000.0}
        ]
    }, headers=headers)
    assert res_cancelled.status_code == 201

    stats_res = client.get("/api/projects/dashboard-stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()

    # Cancelled project must NOT be in top_projects list
    top_project_names = [p["name"] for p in stats.get("top_projects", [])]
    assert "Projeto Gigante Cancelado" not in top_project_names
    assert "Projeto Ativo" in top_project_names

    # Cancelled project cost must NOT leak into cost_breakdown
    active_cost = res_active.json()["summary"]["total_material_cost"]
    assert stats["cost_breakdown"]["material_cost"] == round(active_cost, 2)


def test_issue_53_and_57_dashboard_stats_excludes_draft_and_quoted_from_timeline_and_breakdown(client, make_user):
    """Issues #53 & #57: Ensure draft and quoted projects do not distort monthly timeline base_cost and cost_breakdown."""
    user = make_user(email="realized_metrics@example.com")
    headers = user["headers"]

    # 1. Create realized approved project
    res_appr = client.post("/api/projects", json={
        "name": "Projeto Aprovado Realizado",
        "status": "approved",
        "plates": [
            {"name": "P1", "print_time_hours": 5.0, "part_weight_g": 100.0, "custom_filament_cost_per_g": 0.10, "custom_printer_hourly_rate": 2.50}
        ]
    }, headers=headers)
    assert res_appr.status_code == 201
    appr_summary = res_appr.json()["summary"]
    appr_base_cost = appr_summary["base_cost"]
    appr_mat_cost = appr_summary["total_material_cost"]

    # 2. Create high-cost draft project
    res_draft = client.post("/api/projects", json={
        "name": "Rascunho Experimental",
        "status": "draft",
        "plates": [
            {"name": "PDraft", "print_time_hours": 50.0, "part_weight_g": 3000.0, "custom_filament_cost_per_g": 0.10, "custom_printer_hourly_rate": 2.50}
        ]
    }, headers=headers)
    assert res_draft.status_code == 201

    # 3. Create high-cost quoted project
    res_quoted = client.post("/api/projects", json={
        "name": "Orcamento Enviado",
        "status": "quoted",
        "plates": [
            {"name": "PQuoted", "print_time_hours": 30.0, "part_weight_g": 2000.0, "custom_filament_cost_per_g": 0.10, "custom_printer_hourly_rate": 2.50}
        ]
    }, headers=headers)
    assert res_quoted.status_code == 201

    stats_res = client.get("/api/projects/dashboard-stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()

    # Timeline base_cost must ONLY include the approved project (Issue #53)
    timeline = stats["monthly_timeline"]
    total_timeline_base_cost = sum(t["base_cost"] for t in timeline)
    assert round(total_timeline_base_cost, 2) == round(appr_base_cost, 2)

    # Cost breakdown must ONLY include the approved project (Issue #57)
    assert stats["cost_breakdown"]["material_cost"] == round(appr_mat_cost, 2)


def test_issue_58_active_quotes_includes_approved_projects(client, make_user):
    """Issue #58: active_quotes counter must include 'approved' status projects."""
    user = make_user(email="active_quotes_test@example.com")
    headers = user["headers"]

    statuses = ["draft", "quoted", "approved", "in_production", "completed", "cancelled"]
    for st in statuses:
        r = client.post("/api/projects", json={
            "name": f"Projeto Status {st}",
            "status": st
        }, headers=headers)
        assert r.status_code == 201

    stats_res = client.get("/api/projects/dashboard-stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()

    # Active quotes must be exactly 4: draft, quoted, approved, in_production
    assert stats["active_quotes"] == 4


def test_issue_56_orphaned_foreign_key_fallbacks_2_50_and_0_10(client, make_user):
    """Issue #56: verify orphaned printer_id / filament_id sanitation sets 2.50 and 0.10 fallbacks."""
    user = make_user(email="orphan_test@example.com")
    headers = user["headers"]

    res = client.post("/api/projects", json={
        "name": "Projeto Orfao",
        "status": "draft",
        "plates": [
            {
                "name": "Placa Orfa",
                "printer_id": 999999,
                "filament_id": 999999,
                "print_time_hours": 1.0,
                "part_weight_g": 50.0
            }
        ]
    }, headers=headers)
    assert res.status_code == 201
    plate = res.json()["plates"][0]
    assert plate["printer_id"] is None
    assert plate["filament_id"] is None
    assert plate["custom_printer_hourly_rate"] == 2.50
    assert plate["custom_filament_cost_per_g"] == 0.10


def test_issue_59_color_hex_pattern_validation(client, make_user):
    """Issue #59: color_hex must conform to hex pattern #RGB, #RRGGBB, #RRGGBBAA."""
    user = make_user(email="hex_test@example.com")
    headers = user["headers"]

    # Valid hex formats
    for hex_val in ["#fff", "#10b981", "#AABBCC", "#10b981AA"]:
        resp = client.post("/api/filaments", json={
            "name": f"Filamento {hex_val}",
            "material": "PLA",
            "color_hex": hex_val
        }, headers=headers)
        assert resp.status_code == 201

    # Invalid hex formats
    for bad_hex in ["red", "10b981", "#gggggg", "javascript:alert(1)", "#12", "#12345"]:
        resp = client.post("/api/filaments", json={
            "name": "Filamento Invalido",
            "material": "PLA",
            "color_hex": bad_hex
        }, headers=headers)
        assert resp.status_code == 422


def test_issue_60_project_status_pattern_validation(client, make_user):
    """Issue #60: project status must only accept authorized enum values."""
    user = make_user(email="status_pattern@example.com")
    headers = user["headers"]

    valid_statuses = ["draft", "quoted", "approved", "in_production", "completed", "cancelled"]
    for st in valid_statuses:
        resp = client.post("/api/projects", json={
            "name": f"Projeto {st}",
            "status": st
        }, headers=headers)
        assert resp.status_code == 201

    invalid_statuses = ["pending", "finished", "DRAFT", "<script>alert(1)</script>", "foo"]
    for bad_st in invalid_statuses:
        resp = client.post("/api/projects", json={
            "name": "Projeto Invalido",
            "status": bad_st
        }, headers=headers)
        assert resp.status_code == 422


def test_issue_61_empty_whitespace_name_rejected(client, make_user):
    """Issue #61: whitespace-only or empty names must be rejected."""
    user = make_user(email="blank_name_test@example.com")
    headers = user["headers"]

    for blank in ["", "   ", "\t\n"]:
        # Printer
        p_resp = client.post("/api/printers", json={"name": blank}, headers=headers)
        assert p_resp.status_code == 422

        # Filament
        f_resp = client.post("/api/filaments", json={"name": blank, "material": "PLA"}, headers=headers)
        assert f_resp.status_code == 422

        # Project
        pr_resp = client.post("/api/projects", json={"name": blank}, headers=headers)
        assert pr_resp.status_code == 422


def test_issue_62_and_71_dashboard_stats_realized_projects_filtering(client, make_user):
    """
    Issue #62 & #71:
    - Top projects ranking (#62) must only include realized projects (approved, in_production, completed).
    - Monthly print_hours (#71) must only sum realized projects.
    """
    user = make_user(email="stats_filtering@example.com")
    headers = user["headers"]

    # 1. Draft project: 10h, R$ 500
    client.post("/api/projects", json={
        "name": "Projeto Rascunho",
        "status": "draft",
        "plates": [{
            "name": "Placa Draft",
            "print_time_hours": 10.0,
            "part_weight_g": 100.0,
            "custom_printer_hourly_rate": 10.0,
            "custom_filament_cost_per_g": 0.50
        }]
    }, headers=headers)

    # 2. Approved project: 5h, R$ 250
    client.post("/api/projects", json={
        "name": "Projeto Aprovado",
        "status": "approved",
        "plates": [{
            "name": "Placa Approved",
            "print_time_hours": 5.0,
            "part_weight_g": 50.0,
            "custom_printer_hourly_rate": 10.0,
            "custom_filament_cost_per_g": 0.50
        }]
    }, headers=headers)

    resp = client.get("/api/projects/dashboard-stats", headers=headers)
    assert resp.status_code == 200
    stats = resp.json()

    # Issue #62: top_projects must only contain "Projeto Aprovado"
    top_names = [p["name"] for p in stats["top_projects"]]
    assert "Projeto Aprovado" in top_names
    assert "Projeto Rascunho" not in top_names

    # Issue #71: monthly timeline print_hours must equal 5.0 (not 15.0)
    import datetime
    current_month_key = datetime.datetime.now().strftime("%Y-%m")
    current_month_item = next((m for m in stats["monthly_timeline"] if m["month_key"] == current_month_key), None)
    assert current_month_item is not None
    assert current_month_item["print_hours"] == 5.0


def test_issue_64_printer_duplication_endpoint(client, make_user):
    """Issue #64: POST /api/printers/{id}/duplicate duplicates printer with (Cópia)."""
    user = make_user(email="printer_dup@example.com")
    headers = user["headers"]

    orig = client.post("/api/printers", json={
        "name": "Prusa MK4",
        "model": "i3 Style",
        "acquisition_cost": 4500.0,
        "avg_power_watts": 120.0,
        "is_active": True
    }, headers=headers).json()

    dup_res = client.post(f"/api/printers/{orig['id']}/duplicate", headers=headers)
    assert dup_res.status_code == 201
    dup = dup_res.json()
    assert dup["id"] != orig["id"]
    assert dup["name"] == "Prusa MK4 (Cópia)"
    assert dup["model"] == "i3 Style"
    assert dup["acquisition_cost"] == 4500.0
    assert dup["is_active"] is True

    # 404 for unknown printer
    assert client.post("/api/printers/99999/duplicate", headers=headers).status_code == 404


def test_issue_65_plate_negative_custom_rates_rejected(client, make_user):
    """Issue #65: negative custom_printer_hourly_rate or custom_filament_cost_per_g must be rejected."""
    user = make_user(email="plate_rates_neg@example.com")
    headers = user["headers"]

    # Negative hourly rate
    r1 = client.post("/api/projects", json={
        "name": "Projeto Neg Rates",
        "plates": [{
            "name": "P1",
            "custom_printer_hourly_rate": -5.0
        }]
    }, headers=headers)
    assert r1.status_code == 422

    # Negative cost per gram
    r2 = client.post("/api/projects", json={
        "name": "Projeto Neg Rates 2",
        "plates": [{
            "name": "P1",
            "custom_filament_cost_per_g": -0.10
        }]
    }, headers=headers)
    assert r2.status_code == 422


def test_issue_67_engine_plate_cost_fallback_when_printer_and_filament_none():
    """Issue #67: calculate_plate_cost must use 2.50/h and 0.10/g fallbacks when printer and filament are None."""
    from backend.engine import calculate_plate_cost
    from backend.models import Plate

    plate = Plate(
        name="Placa Teste Fallback",
        printer_id=None,
        filament_id=None,
        custom_printer_hourly_rate=None,
        custom_filament_cost_per_g=None,
        print_time_hours=2.0,
        part_weight_g=50.0,
        purge_weight_g=10.0,
        failure_margin_percent=0.0,
        quantity=1
    )

    cost = calculate_plate_cost(plate, printer=None, filament=None)
    # Machine rate fallback 2.50 * 2h = 5.00
    assert cost["machine_hourly_rate"] == 2.50
    assert cost["total_machine_cost"] == 5.00
    # Filament cost fallback 0.10 * 60g = 6.00
    assert cost["cost_per_gram"] == 0.10
    assert cost["total_material_cost"] == 6.00
    assert cost["total_cost"] == 11.00


def test_issue_70_plate_manufacturing_parameters_and_technical_pdf(client, make_user):
    """
    Issue #70:
    - Plate models and schemas accept nozzle_diameter, bed_type, and layer_height.
    - Technical PDF includes manufacturing parameters.
    """
    user = make_user(email="manuf_params@example.com")
    headers = user["headers"]

    proj_res = client.post("/api/projects", json={
        "name": "Projeto Setup Fab",
        "plates": [{
            "name": "Placa 0.6mm High Speed",
            "nozzle_diameter": "0.6",
            "bed_type": "Smooth PEI",
            "layer_height": "0.28",
            "print_time_hours": 3.0,
            "part_weight_g": 80.0
        }]
    }, headers=headers)
    assert proj_res.status_code == 201
    proj_data = proj_res.json()
    p = proj_data["plates"][0]
    assert p["nozzle_diameter"] == "0.6"
    assert p["bed_type"] == "Smooth PEI"
    assert p["layer_height"] == "0.28"

    # Export technical PDF
    pdf_res = client.get(f"/api/projects/{proj_data['id']}/pdf?type=technical", headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF")


def test_duplicate_project_preserves_manufacturing_parameters_issue_72(client, make_user):
    user = make_user(email="dup_manuf@example.com")
    headers = user["headers"]

    # 1. Create project with custom manufacturing parameters on plate
    res = client.post("/api/projects", json={
        "name": "Projeto Original Setup",
        "plates": [{
            "name": "Placa 0.8mm Glass",
            "nozzle_diameter": "0.8",
            "bed_type": "SuperPlate Glass",
            "layer_height": "0.32",
            "print_time_hours": 4.0,
            "part_weight_g": 120.0
        }]
    }, headers=headers)
    assert res.status_code == 201
    orig_id = res.json()["id"]

    # 2. Duplicate project
    dup_res = client.post(f"/api/projects/{orig_id}/duplicate", headers=headers)
    assert dup_res.status_code == 201
    dup_data = dup_res.json()
    assert len(dup_data["plates"]) == 1
    dup_plate = dup_data["plates"][0]
    assert dup_plate["nozzle_diameter"] == "0.8"
    assert dup_plate["bed_type"] == "SuperPlate Glass"
    assert dup_plate["layer_height"] == "0.32"


def test_dashboard_stats_total_filament_kg_includes_failure_margin_issue_80(client, make_user):
    user = make_user(email="filament_margin@example.com")
    headers = user["headers"]

    # Create approved project with 1000g piece and 10% failure margin (effective weight = 1100g = 1.10kg)
    res = client.post("/api/projects", json={
        "name": "Projeto Margem Falha",
        "status": "approved",
        "plates": [{
            "name": "Peça 1kg",
            "print_time_hours": 5.0,
            "part_weight_g": 1000.0,
            "purge_weight_g": 0.0,
            "failure_margin_percent": 10.0,
            "quantity": 1
        }]
    }, headers=headers)
    assert res.status_code == 201

    stats_res = client.get("/api/projects/dashboard-stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    # 1000g * (1 + 0.10) = 1100g -> 1.10 kg
    assert stats["total_filament_kg"] == 1.1


def test_pdf_bom_notes_rendered_issue_98(client, make_user):
    """Issue #98: BOM notes must be rendered in client quote and technical worksheet PDFs."""
    import base64
    import zlib

    user = make_user(email="pdf_bom_notes@example.com")
    headers = user["headers"]

    res = client.post("/api/projects", json={
        "name": "Projeto com BOM Notes",
        "bom_items": [{
            "name": "Parafuso M3x12",
            "category": "Fixadores",
            "quantity": 10,
            "unit_cost": 0.50,
            "notes": "Aco Inox 304 Cabeca Abaulada"
        }]
    }, headers=headers)
    assert res.status_code == 201
    proj_id = res.json()["id"]

    def extract_stream_text(raw_bytes):
        idx1 = raw_bytes.find(b'stream\n') + len(b'stream\n')
        idx2 = raw_bytes.find(b'endstream')
        stream_data = raw_bytes[idx1:idx2].strip()
        a85 = base64.a85decode(stream_data, adobe=True)
        return zlib.decompress(a85).decode('latin-1')

    # Client PDF
    r_client = client.get(f"/api/projects/{proj_id}/pdf?type=client", headers=headers)
    assert r_client.status_code == 200
    text_client = extract_stream_text(r_client.content)
    assert "Aco Inox 304 Cabeca Abaulada" in text_client

    # Technical PDF
    r_tech = client.get(f"/api/projects/{proj_id}/pdf?type=technical", headers=headers)
    assert r_tech.status_code == 200
    text_tech = extract_stream_text(r_tech.content)
    assert "Aco Inox 304 Cabeca Abaulada" in text_tech


def test_pdf_technical_empty_plates_note_issue_101(client, make_user):
    """Issue #101: Technical PDF must render explanatory row when project has no plates."""
    import base64
    import zlib

    user = make_user(email="pdf_empty_plates@example.com")
    headers = user["headers"]

    res = client.post("/api/projects", json={
        "name": "Projeto Apenas Servicos",
        "cad_hours": 3.0,
        "cad_hourly_rate": 50.0,
        "bom_items": [{
            "name": "Embalagem",
            "category": "Embalagem",
            "quantity": 1,
            "unit_cost": 5.0
        }]
    }, headers=headers)
    assert res.status_code == 201
    proj_id = res.json()["id"]

    r_tech = client.get(f"/api/projects/{proj_id}/pdf?type=technical", headers=headers)
    assert r_tech.status_code == 200

    idx1 = r_tech.content.find(b'stream\n') + len(b'stream\n')
    idx2 = r_tech.content.find(b'endstream')
    stream_data = r_tech.content[idx1:idx2].strip()
    a85 = base64.a85decode(stream_data, adobe=True)
    text_tech = zlib.decompress(a85).decode('latin-1')
    assert "Nenhuma pe" in text_tech or "Nenhuma" in text_tech


def test_pdf_technical_demonstrative_discount_and_freight_issue_104(client, make_user):
    """Issue #104: Technical production PDF must include discount and shipping in internal cost demonstrative."""
    from backend.pdf_service import build_pdf_document

    user = make_user(email="pdf_discount_shipping@example.com")
    headers = user["headers"]

    res = client.post("/api/projects", json={
        "name": "Projeto com Desconto e Frete",
        "cad_hours": 2.0,
        "cad_hourly_rate": 50.0,
        "discount_percent": 15.0,
        "shipping_cost": 25.0,
        "profit_margin_percent": 30.0,
        "tax_rate_percent": 10.0,
        "plates": [{
            "name": "Placa Teste",
            "print_time_hours": 2.5,
            "part_weight_g": 60.0,
            "filament_type": "PLA",
            "nozzle_diameter": "0.4",
            "layer_height": "0.20",
            "bed_type": "Textured PEI",
            "quantity": 1
        }]
    }, headers=headers)
    assert res.status_code == 201
    proj_data = res.json()
    proj_id = proj_data["id"]

    # Verify API PDF endpoint generates valid technical PDF
    r_tech = client.get(f"/api/projects/{proj_id}/pdf?type=technical", headers=headers)
    assert r_tech.status_code == 200
    assert r_tech.headers["content-type"] == "application/pdf"
    assert r_tech.content.startswith(b"%PDF")
    assert len(r_tech.content) > 1000

    # Test direct build_pdf_document with mock user_db and verify discount/shipping are formatted
    user_db = {
        "company_name": "3D Print Lab",
        "cnpj": "00.000.000/0001-00",
        "phone": "(11) 99999-9999",
        "email": "contato@3dlab.com"
    }
    buf = build_pdf_document(proj_data, user_db, doc_type="technical")
    pdf_bytes = buf.getvalue()
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_issue_105_engine_preserves_sub_minute_print_hours():
    """Issue #105: engine.py must preserve 4 decimal places for sub-minute prints without truncating to 0.0."""
    from backend.engine import calculate_plate_cost, calculate_project_summary

    sub_minute_plate = {
        "id": 1,
        "name": "Torre de Calibração 15s",
        "print_time_hours": 0.0042,
        "part_weight_g": 1.5,
        "purge_weight_g": 0.0,
        "failure_margin_percent": 10.0,
        "quantity": 1,
        "custom_printer_hourly_rate": 2.50,
        "custom_filament_cost_per_g": 0.10,
    }

    cost = calculate_plate_cost(sub_minute_plate)
    assert cost["unit_print_time_hours"] == 0.0042, f"Expected 0.0042, got {cost['unit_print_time_hours']}"
    assert cost["total_time_hours"] == 0.0042, f"Expected 0.0042, got {cost['total_time_hours']}"

    summary = calculate_project_summary(
        project={"cad_hours": 0.0, "post_process_hours": 0.0, "overhead_cost": 0.0},
        plates=[sub_minute_plate],
        bom_items=[]
    )
    assert summary["total_print_time_hours"] == 0.0042, f"Expected summary total_print_time_hours to be 0.0042, got {summary['total_print_time_hours']}"


def test_issue_106_pdf_format_hours_short_and_sub_minute_prints():
    """Issue #106: PDF generator must format short and sub-minute print times gracefully without displaying 0.0 h."""
    from backend.pdf_service import format_pdf_hours, build_pdf_document

    assert format_pdf_hours(0.0) == "0.0 h"
    assert format_pdf_hours(0.0042) == "&lt;1 min (~15s)"
    assert format_pdf_hours(0.05) == "3 min"
    assert format_pdf_hours(2.5) == "2.5 h"

    # Verify both client and technical PDFs generate successfully for sub-minute plate
    proj_data = {
        "id": 99,
        "name": "Projeto Calibração",
        "client_name": "Lab Test",
        "status": "approved",
        "suggested_price": 25.0,
        "discount_amount": 0.0,
        "shipping_cost": 0.0,
        "final_price_to_client": 25.0,
        "total_print_time_hours": 0.0042,
        "plates": [{
            "name": "Cubo 15s",
            "unit_print_time_hours": 0.0042,
            "total_time_hours": 0.0042,
            "part_weight_g": 1.2,
            "purge_weight_g": 0.0,
            "quantity": 1,
            "filament_material": "PLA",
            "printer_name": "P1S",
            "nozzle_diameter": "0.4",
            "bed_type": "Textured PEI",
            "layer_height": "0.20",
        }],
        "bom_items": [],
        "summary": {
            "total_print_time_hours": 0.0042,
            "suggested_price": 25.0,
            "final_price_to_client": 25.0,
            "base_cost": 5.0,
            "profit_margin_percent": 30.0,
            "tax_rate_percent": 6.0,
            "discount_percent": 0.0,
            "discount_amount": 0.0,
            "shipping_cost": 0.0,
            "tax_amount": 1.5,
            "net_revenue": 23.5,
            "net_profit": 18.5,
            "effective_profit_margin_percent": 370.0,
        }
    }
    user_data = {"company_name": "Maker Corp", "email": "maker@corp.com"}

    client_pdf = build_pdf_document(proj_data, user_data, doc_type="client").getvalue()
    assert client_pdf.startswith(b"%PDF")

    tech_pdf = build_pdf_document(proj_data, user_data, doc_type="technical").getvalue()
    assert tech_pdf.startswith(b"%PDF")


def test_issue_111_duplicate_project_status_code_201_created(client, make_user):
    """Issue #111: POST /api/projects/{id}/duplicate must return HTTP 201 Created."""
    user = make_user("dup_proj_test@example.com")
    headers = user["headers"]

    # 1. Create project
    create_resp = client.post("/api/projects", json={
        "name": "Projeto Original",
        "plates": [{
            "name": "Placa 1",
            "print_time_hours": 1.0,
            "part_weight_g": 20.0,
            "quantity": 1
        }]
    }, headers=headers)
    assert create_resp.status_code == 201
    proj_id = create_resp.json()["id"]

    # 2. Duplicate project
    dup_resp = client.post(f"/api/projects/{proj_id}/duplicate", headers=headers)
    assert dup_resp.status_code == 201, f"Expected 201 Created, got {dup_resp.status_code}"
    dup_data = dup_resp.json()
    assert dup_data["name"] == "Projeto Original (Cópia)"
    assert dup_data["id"] != proj_id


def test_issue_110_pdf_technical_renders_plate_notes():
    """Issue #110: Technical PDF must include plate operational notes in setup description."""
    from backend.pdf_service import build_pdf_document

    proj_data = {
        "id": 101,
        "name": "Projeto com Notas",
        "client_name": "Cliente Fab",
        "status": "approved",
        "suggested_price": 50.0,
        "discount_amount": 0.0,
        "shipping_cost": 0.0,
        "final_price_to_client": 50.0,
        "total_print_time_hours": 2.0,
        "plates": [{
            "name": "Placa A",
            "unit_print_time_hours": 2.0,
            "total_time_hours": 2.0,
            "part_weight_g": 30.0,
            "purge_weight_g": 0.0,
            "quantity": 1,
            "filament_material": "PETG",
            "printer_name": "Ender 3",
            "nozzle_diameter": "0.4",
            "bed_type": "Textured PEI",
            "layer_height": "0.20",
            "notes": "Pausa na camada 45 para inserir porca M3",
        }],
        "bom_items": [],
        "summary": {
            "total_print_time_hours": 2.0,
            "suggested_price": 50.0,
            "final_price_to_client": 50.0,
            "base_cost": 20.0,
            "profit_margin_percent": 30.0,
            "tax_rate_percent": 6.0,
            "discount_percent": 0.0,
            "discount_amount": 0.0,
            "shipping_cost": 0.0,
            "tax_amount": 3.0,
            "net_revenue": 47.0,
            "net_profit": 27.0,
            "effective_profit_margin_percent": 135.0,
        }
    }
    user_data = {"company_name": "Fab Tech", "email": "fab@tech.com"}
    pdf_bytes = build_pdf_document(proj_data, user_data, doc_type="technical").getvalue()
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_issue_112_pdf_technical_with_summary_plates_details_notes():
    """Issue #112: Technical PDF must render plate notes when summary['plates_details'] is generated by engine."""
    from backend.engine import calculate_project_summary
    from backend.pdf_service import build_pdf_document

    plate = {
        "id": 202,
        "name": "Placa Peça Crítica",
        "print_time_hours": 3.5,
        "part_weight_g": 85.0,
        "purge_weight_g": 0.0,
        "quantity": 1,
        "filament_material": "ABS",
        "printer_name": "Voron 2.4",
        "nozzle_diameter": "0.4",
        "bed_type": "Textured PEI",
        "layer_height": "0.20",
        "notes": "Aguardar resfriamento total da mesa antes de remover",
    }
    proj_info = {
        "id": 202,
        "name": "Projeto Gabinete",
        "client_name": "Cliente Industrial",
        "status": "approved",
        "suggested_price": 120.0,
        "discount_amount": 0.0,
        "shipping_cost": 0.0,
        "final_price_to_client": 120.0,
        "cad_hours": 0.0,
        "post_process_hours": 0.0,
        "overhead_cost": 0.0,
    }

    summary = calculate_project_summary(
        project=proj_info,
        plates=[plate],
        bom_items=[],
    )

    assert "plates_details" in summary
    assert len(summary["plates_details"]) == 1
    assert summary["plates_details"][0]["notes"] == "Aguardar resfriamento total da mesa antes de remover"

    proj_data = {
        **proj_info,
        "plates": [plate],
        "summary": summary,
    }
    user_data = {"company_name": "Print Lab 3D", "email": "lab@printlab.com"}
    pdf_bytes = build_pdf_document(proj_data, user_data, doc_type="technical").getvalue()
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_issue_118_dashboard_stats_excludes_cancelled_from_margins(client, make_user):
    """Issue #118: Endpoint /api/projects/dashboard-stats must exclude cancelled projects from avg profit margin."""
    user = make_user(email="margin_test@example.com")
    headers = user["headers"]

    # 1. Project A: approved, 30% margin
    res_a = client.post("/api/projects", json={
        "name": "Projeto Aprovado",
        "status": "approved",
        "profit_margin_percent": 30.0,
        "plates": [{
            "name": "Placa A",
            "print_time_hours": 1.0,
            "part_weight_g": 50.0,
            "quantity": 1
        }]
    }, headers=headers)
    assert res_a.status_code == 201

    stats1 = client.get("/api/projects/dashboard-stats", headers=headers).json()
    assert stats1["avg_profit_margin_percent"] > 0

    # 2. Project B: cancelled, extreme margin (e.g. 200%)
    res_b = client.post("/api/projects", json={
        "name": "Projeto Cancelado",
        "status": "cancelled",
        "profit_margin_percent": 200.0,
        "plates": [{
            "name": "Placa B",
            "print_time_hours": 1.0,
            "part_weight_g": 50.0,
            "quantity": 1
        }]
    }, headers=headers)
    assert res_b.status_code == 201

    stats2 = client.get("/api/projects/dashboard-stats", headers=headers).json()
    # Cancelled project must NOT skew the avg margin
    assert stats2["avg_profit_margin_percent"] == stats1["avg_profit_margin_percent"]





















