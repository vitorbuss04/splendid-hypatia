import pytest
import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from backend import models

INDEX_HTML = Path(__file__).resolve().parent.parent / "frontend" / "index.html"

def test_reports_detailed_empty_account(client, make_user):
    user = make_user("report_empty@example.com")
    resp = client.get("/api/reports/detailed", headers=user["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert "period" in data
    assert "financial" in data
    assert "printers" in data
    assert "materials" in data
    assert "failures" in data
    assert "clients" in data
    assert "projects" in data

    assert data["financial"]["total_projects"] == 0
    assert data["financial"]["revenue_approved"] == 0.0
    assert data["financial"]["net_profit"] == 0.0
    assert data["failures"]["total_scrap_cost"] == 0.0


def test_reports_detailed_with_data_and_calculations(client, make_user, db):
    user = make_user("report_data@example.com")
    headers = user["headers"]

    # 1. Create a printer
    p_resp = client.post("/api/printers", json={
        "name": "Bambu P1S Farm",
        "model": "P1S",
        "acquisition_cost": 5000.0,
        "lifespan_hours": 5000.0,
        "avg_power_watts": 150.0,
        "maintenance_cost_per_hour": 1.5,
        "energy_rate_kwh": 0.85
    }, headers=headers)
    assert p_resp.status_code == 201
    printer_id = p_resp.json()["id"]

    # 2. Create a filament
    f_resp = client.post("/api/filaments", json={
        "name": "PLA Preto Premium",
        "brand": "3D Prime",
        "material": "PLA",
        "color": "Preto",
        "color_hex": "#000000",
        "spool_weight_g": 1000.0,
        "spool_price": 100.0,
    }, headers=headers)
    assert f_resp.status_code == 201
    filament_id = f_resp.json()["id"]

    # 3. Create Project 1 (Approved)
    proj1_resp = client.post("/api/projects", json={
        "name": "Engrenagens Industriais",
        "client_name": "Metalurgica Alfa",
        "status": "approved",
        "overhead_cost": 20.0,
        "profit_margin_percent": 40.0,
        "tax_rate_percent": 6.0,
        "cad_hours": 1.0,
        "cad_hourly_rate": 50.0,
    }, headers=headers)
    assert proj1_resp.status_code == 201
    proj1_id = proj1_resp.json()["id"]

    # Add plate to Project 1
    pl_resp = client.post(f"/api/projects/{proj1_id}/plates", json={
        "name": "Placa 1 - Engrenagem",
        "printer_id": printer_id,
        "filament_id": filament_id,
        "print_time_hours": 4.0,
        "part_weight_g": 200.0,
        "purge_weight_g": 20.0,
        "failure_margin_percent": 10.0,
        "quantity": 2
    }, headers=headers)
    assert pl_resp.status_code == 201

    # Add failure log to Project 1
    fail_resp = client.post(f"/api/projects/{proj1_id}/failures", json={
        "lost_time_hours": 1.5,
        "lost_filament_weight_g": 50.0,
        "reason": "warping",
        "reason_notes": "Descolou do canto esquerdo da mesa PEI",
        "reprinted": True,
        "charged_to_client": False
    }, headers=headers)
    assert fail_resp.status_code in [200, 201]

    # 4. Create Project 2 (Draft - Pipeline)
    proj2_resp = client.post("/api/projects", json={
        "name": "Protótipo Suporte Drone",
        "client_name": "AeroTech",
        "status": "draft",
        "profit_margin_percent": 30.0,
    }, headers=headers)
    assert proj2_resp.status_code == 201
    proj2_id = proj2_resp.json()["id"]

    client.post(f"/api/projects/{proj2_id}/plates", json={
        "name": "Placa 1 - Chassi",
        "printer_id": printer_id,
        "filament_id": filament_id,
        "print_time_hours": 2.0,
        "part_weight_g": 100.0,
        "quantity": 1
    }, headers=headers)

    # Now query /api/reports/detailed
    rep_resp = client.get("/api/reports/detailed", headers=headers)
    assert rep_resp.status_code == 200
    report = rep_resp.json()

    fin = report["financial"]
    assert fin["total_projects"] == 2
    assert fin["approved_projects_count"] == 1
    assert fin["revenue_approved"] > 0
    assert fin["pipeline_revenue"] > 0
    assert fin["material_cost"] > 0
    assert fin["machine_cost"] > 0
    assert fin["net_profit"] > 0

    # Verify Printer usage
    assert len(report["printers"]) >= 1
    p_stat = [p for p in report["printers"] if p["printer_id"] == printer_id][0]
    # 4h * 2 quantity = 8h on Project 1
    assert p_stat["print_hours"] == 8.0
    assert p_stat["plates_count"] == 2
    assert p_stat["total_cost"] > 0

    # Verify Material usage
    assert len(report["materials"]) >= 1
    m_stat = [m for m in report["materials"] if m["material"] == "PLA"][0]
    # (200 + 20) * 2 = 440g
    assert m_stat["weight_g"] == 440.0
    assert m_stat["weight_kg"] == 0.44
    assert m_stat["cost"] > 0

    # Verify Failures
    assert report["failures"]["total_failures_count"] == 1
    assert report["failures"]["total_scrap_cost"] > 0
    assert report["failures"]["total_lost_weight_g"] == 50.0
    assert report["failures"]["total_lost_hours"] == 1.5
    warping_reason = [r for r in report["failures"]["reasons"] if r["reason"] == "warping"][0]
    assert warping_reason["count"] == 1
    assert warping_reason["lost_weight_g"] == 50.0

    # Verify Clients
    assert len(report["clients"]) == 2
    client_alfa = [c for c in report["clients"] if "Alfa" in c["client_name"]][0]
    assert client_alfa["approved_revenue"] > 0
    assert client_alfa["approved_projects_count"] == 1


def test_reports_period_date_filtering(client, make_user, db):
    user = make_user("report_filter@example.com")
    headers = user["headers"]

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    two_weeks_ago = today - datetime.timedelta(days=14)

    # Project 1: Recent (today)
    p1 = client.post("/api/projects", json={"name": "Projeto Hoje", "status": "approved"}, headers=headers).json()

    # Project 2: Force past date in DB
    p2 = client.post("/api/projects", json={"name": "Projeto Antigo", "status": "approved"}, headers=headers).json()
    db_p2 = db.query(models.Project).filter(models.Project.id == p2["id"]).first()
    db_p2.created_at = datetime.datetime.combine(two_weeks_ago, datetime.time(10, 0, 0))
    db.commit()

    # Query with start_date of yesterday (should only include Projeto Hoje)
    resp = client.get(f"/api/reports/detailed?start_date={yesterday.isoformat()}&end_date={today.isoformat()}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["financial"]["total_projects"] == 1
    assert data["projects"][0]["name"] == "Projeto Hoje"

    # Query with all history
    resp_all = client.get("/api/reports/detailed", headers=headers)
    assert resp_all.status_code == 200
    assert resp_all.json()["financial"]["total_projects"] == 2


def test_reports_csv_exports(client, make_user):
    user = make_user("report_csv@example.com")
    headers = user["headers"]

    # Create one project
    client.post("/api/projects", json={"name": "Projeto Teste CSV", "client_name": "Empresa Beta", "status": "approved"}, headers=headers)

    # 1. Export projects
    resp1 = client.get("/api/reports/export/csv?report_type=projects", headers=headers)
    assert resp1.status_code == 200
    assert resp1.headers["content-type"].startswith("text/csv")
    assert "Content-Disposition" in resp1.headers
    content1 = resp1.content.decode("utf-8-sig")
    assert "Nome do Projeto" in content1
    assert "Projeto Teste CSV" in content1
    assert ";" in content1

    # 2. Export materials
    resp2 = client.get("/api/reports/export/csv?report_type=materials", headers=headers)
    assert resp2.status_code == 200
    content2 = resp2.content.decode("utf-8-sig")
    assert "Material" in content2
    assert "Peso Consumido" in content2

    # 3. Export machines
    resp3 = client.get("/api/reports/export/csv?report_type=machines", headers=headers)
    assert resp3.status_code == 200
    content3 = resp3.content.decode("utf-8-sig")
    assert "Impressora" in content3
    assert "Horas de Impressao" in content3

    # 4. Export failures
    resp4 = client.get("/api/reports/export/csv?report_type=failures", headers=headers)
    assert resp4.status_code == 200
    content4 = resp4.content.decode("utf-8-sig")
    assert "Causa da Falha" in content4


def test_dashboard_stats_accepts_date_parameters(client, make_user):
    user = make_user("dashboard_filter@example.com")
    headers = user["headers"]

    client.post("/api/projects", json={"name": "Dashboard Proj"}, headers=headers)

    resp = client.get("/api/projects/dashboard-stats?start_date=2026-01-01&end_date=2026-12-31", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_projects"] == 1


def test_frontend_report_dom_elements():
    assert INDEX_HTML.exists()
    soup = BeautifulSoup(INDEX_HTML.read_text(encoding="utf-8"), "html.parser")

    # Reports navigation button and view section
    assert soup.find(id="nav-reports") is not None, "nav-reports button must exist in sidebar"
    assert soup.find(id="view-reports") is not None, "view-reports section must exist"

    # Dashboard period filter controls
    assert soup.find(id="dashboard-period-presets") is not None
    assert soup.find(id="dashboard-start-date") is not None
    assert soup.find(id="dashboard-end-date") is not None

    # Reports view controls and cards
    assert soup.find(id="rep-period-presets") is not None
    assert soup.find(id="rep-start-date") is not None
    assert soup.find(id="rep-end-date") is not None
    assert soup.find(id="rep-date-field") is not None
    assert soup.find(id="rep-revenue-approved") is not None
    assert soup.find(id="rep-pipeline-revenue") is not None
    assert soup.find(id="rep-net-profit") is not None
    assert soup.find(id="rep-avg-ticket") is not None

    # Reports 4 charts canvases
    assert soup.find(id="chart-rep-printers") is not None
    assert soup.find(id="chart-rep-materials") is not None
    assert soup.find(id="chart-rep-failures") is not None
    assert soup.find(id="chart-rep-clients") is not None

    # Reports detailed table tabs
    assert soup.find(id="rep-tab-content-projects") is not None
    assert soup.find(id="rep-tab-content-printers") is not None
    assert soup.find(id="rep-tab-content-materials") is not None
    assert soup.find(id="rep-tab-content-failures") is not None
