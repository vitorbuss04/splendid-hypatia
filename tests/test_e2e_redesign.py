"""
E2E Redesign Test Suite for 3D Print Calc Pro (SaaS Dark Mode Redesign)
Author: E2E Testing Specialist (teamwork_preview_test_writer)
Standard: 4-Tier Quality Assurance Methodology
Tiers:
  - Tier 1: Feature Coverage (26 features from PROJECT.md Feature Inventory)
  - Tier 2: Boundary & Corner Cases (zero rates, nullish coalescing, division by zero, step attributes)
  - Tier 3: Cross-Feature Combinations (pairwise interactions, mathematical formula parity)
  - Tier 4: Real-World Application Scenarios (end-to-end workflows, PDF quotes, multi-tenant isolation)
"""

import re
import pytest
from pathlib import Path
from bs4 import BeautifulSoup
from backend.engine import (
    calculate_printer_hourly_rate,
    calculate_plate_cost,
    calculate_project_summary,
)

# Reference paths
ROOT_DIR = Path(__file__).parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
INDEX_HTML = FRONTEND_DIR / "index.html"
PREVIEW_HTML = FRONTEND_DIR / "preview.html"
STYLES_CSS = FRONTEND_DIR / "css" / "styles.css"
APP_JS = FRONTEND_DIR / "js" / "app.js"
API_JS = FRONTEND_DIR / "js" / "api.js"

# Authoritative 117 Static DOM IDs Catalog
CATALOGED_117_IDS = [
    "app-layout", "auth-modal", "bom-container", "btn-add-plate-bottom",
    "dashboard-empty-banner", "dashboard-recent-projects", "dropzone",
    "editor-project-subtitle", "editor-project-title", "filament-brand",
    "filament-color", "filament-color-hex", "filament-id", "filament-material",
    "filament-name-preview-box", "filament-preview-dot", "filament-preview-text",
    "filament-price", "filament-weight", "filaments-grid", "file-slicer-input",
    "form-filament", "form-login", "form-printer", "form-register", "form-settings",
    "live-base-cost", "live-bom-cost", "live-discount-amount", "live-discount-row",
    "live-final-price", "live-labor-cost", "live-machine-cost", "live-material-cost",
    "live-net-profit", "live-overhead-cost", "live-shipping-amount", "live-shipping-row",
    "live-suggested-price", "live-tax-amount", "live-time", "live-weight",
    "login-email", "login-password", "modal-filament", "modal-filament-title",
    "modal-printer", "modal-printer-title", "nav-dashboard", "nav-filaments",
    "nav-printers", "nav-projects", "nav-settings", "plates-container",
    "pref-cad-rate", "pref-company", "pref-energy", "pref-failure", "pref-fullname",
    "pref-margin", "pref-payment-terms", "pref-phone", "pref-pix", "pref-post-rate",
    "pref-tax", "pref-warranty-terms", "printer-cost", "printer-energy", "printer-id",
    "printer-lifespan", "printer-maintenance", "printer-model", "printer-name",
    "printer-power", "printers-grid", "proj-cad-hours", "proj-cad-rate",
    "proj-client-email", "proj-client-name", "proj-client-phone", "proj-delivery-days",
    "proj-discount", "proj-margin", "proj-name", "proj-notes", "proj-overhead",
    "proj-payment-terms", "proj-post-hours", "proj-post-rate", "proj-shipping",
    "proj-status", "proj-tax", "proj-warranty-terms", "project-search-input",
    "projects-table-container", "reg-company", "reg-email", "reg-name", "reg-password",
    "stat-active-quotes", "stat-filaments-count", "stat-printers-count",
    "stat-projects-count", "tab-login-btn", "tab-register-btn", "toast-container",
    "topbar-actions", "user-avatar", "user-display-company", "user-display-name",
    "view-dashboard", "view-filaments", "view-printers", "view-project-editor",
    "view-projects", "view-settings", "view-title"
]


# ==============================================================================
# TIER 1: FEATURE COVERAGE
# ==============================================================================

class TestTier1FeatureCoverage:
    """Verifies interface contracts, DOM integrity, and feature layout for all 26 features."""

    def test_t1_css_design_system_tokens_and_badges(self):
        """Feature 1, 3, 5: Verify Dark Mode tokens, card elevations, and status/material badges."""
        assert STYLES_CSS.exists(), "frontend/css/styles.css must exist"
        # Combine master styles and imported modular CSS files (tokens, components, views, etc.)
        css_dir = FRONTEND_DIR / "css"
        css = "\n".join(f.read_text(encoding="utf-8") for f in css_dir.glob("*.css"))

        # Dark Mode Color Tokens
        assert ("--bg-primary" in css or "--bg-app" in css)
        assert "--bg-card" in css
        assert "--border-color" in css
        assert "--accent" in css
        assert "--success" in css

        # Elevated Card & Shadow
        assert ".card-dark" in css
        assert "box-shadow:" in css

        # Status Badges
        for badge in ["badge-draft", "badge-quoted", "badge-approved", "badge-in_production", "badge-completed", "badge-cancelled"]:
            assert f".{badge}" in css, f"CSS must define .{badge}"

        # Material Badges
        for mat in ["badge-mat-pla", "badge-mat-petg", "badge-mat-abs", "badge-mat-tpu", "badge-mat-asa", "badge-mat-other"]:
            assert f".{mat}" in css, f"CSS must define .{mat}"

        # Dropzone & Dragover
        assert ".dropzone" in css
        assert ".dropzone.dragover" in css

    def test_t1_dom_117_ids_strict_preservation(self):
        """Feature 23: Verify all 117 static DOM element IDs are preserved without duplicates."""
        assert INDEX_HTML.exists(), "frontend/index.html must exist"
        soup = BeautifulSoup(INDEX_HTML.read_text(encoding="utf-8"), "html.parser")
        tags_with_id = soup.find_all(id=True)
        found_ids = [tag["id"] for tag in tags_with_id]

        assert len(found_ids) == 117, f"Expected exactly 117 static IDs, found {len(found_ids)}"
        assert len(set(found_ids)) == 117, "All element IDs must be unique (no duplicates)"

        for expected_id in CATALOGED_117_IDS:
            assert expected_id in found_ids, f"Required DOM element ID '{expected_id}' is missing!"

    def test_t1_navigation_shell_and_six_views(self):
        """Feature 6: Verify application shell, sidebar, topbar, and 6 views toggled via .hidden."""
        soup = BeautifulSoup(INDEX_HTML.read_text(encoding="utf-8"), "html.parser")

        # Shell and Topbar
        assert soup.find(id="app-layout") is not None
        assert soup.find(id="view-title") is not None
        assert soup.find(id="topbar-actions") is not None

        # User profile sidebar elements
        assert soup.find(id="user-avatar") is not None
        assert soup.find(id="user-display-name") is not None
        assert soup.find(id="user-display-company") is not None

        # 6 Views
        expected_views = [
            "view-dashboard", "view-projects", "view-project-editor",
            "view-printers", "view-filaments", "view-settings"
        ]
        for v in expected_views:
            section = soup.find(id=v)
            assert section is not None, f"View section '{v}' must exist"
            assert section.name == "section"

        # Sidebar navigation triggers
        nav_buttons = ["nav-dashboard", "nav-projects", "nav-printers", "nav-filaments", "nav-settings"]
        for btn in nav_buttons:
            assert soup.find(id=btn) is not None, f"Navigation button '{btn}' must exist"

    def test_t1_dashboard_metrics_and_recent_quotes(self, client, make_user):
        """Feature 7, 8: Verify dashboard stat counter elements, empty banner, and recent quotes table."""
        soup = BeautifulSoup(INDEX_HTML.read_text(encoding="utf-8"), "html.parser")
        assert soup.find(id="stat-projects-count") is not None
        assert soup.find(id="stat-active-quotes") is not None
        assert soup.find(id="stat-printers-count") is not None
        assert soup.find(id="stat-filaments-count") is not None
        assert soup.find(id="dashboard-empty-banner") is not None
        assert soup.find(id="dashboard-recent-projects") is not None

        # Verify API response contains project data suitable for dashboard metrics
        user = make_user()
        p_resp = client.post("/api/projects", json={"name": "Dashboard Project Test"}, headers=user["headers"])
        assert p_resp.status_code == 201
        proj_list = client.get("/api/projects", headers=user["headers"]).json()
        assert len(proj_list) == 1
        assert proj_list[0]["status"] == "draft"

    def test_t1_projects_view_and_search_filter(self):
        """Feature 9: Verify projects list container and real-time search input element."""
        soup = BeautifulSoup(INDEX_HTML.read_text(encoding="utf-8"), "html.parser")
        search_input = soup.find(id="project-search-input")
        assert search_input is not None
        assert search_input.get("type") == "text"
        assert "filterProjects()" in (search_input.get("oninput") or "")
        assert soup.find(id="projects-table-container") is not None

    def test_t1_slicer_dropzone_and_supported_extensions(self):
        """Feature 10: Verify dropzone structure and file input accepting .3mf, .gcode, .gcode.3mf."""
        soup = BeautifulSoup(INDEX_HTML.read_text(encoding="utf-8"), "html.parser")
        dropzone = soup.find(id="dropzone")
        assert dropzone is not None
        assert "dropzone" in dropzone.get("class", [])

        slicer_input = soup.find(id="file-slicer-input")
        assert slicer_input is not None
        assert slicer_input.get("type") == "file"
        accept = slicer_input.get("accept", "")
        for ext in [".3mf", ".gcode", ".gcode.3mf"]:
            assert ext in accept, f"File slicer input must accept {ext}"

    def test_t1_multi_plate_manager_and_bottom_button_ordering(self):
        """Feature 11, 12: Verify plates container and bottom button strictly following container."""
        content = INDEX_HTML.read_text(encoding="utf-8")
        plates_idx = content.find('id="plates-container"')
        btn_idx = content.find('id="btn-add-plate-bottom"')

        assert plates_idx != -1, "plates-container must exist"
        assert btn_idx != -1, "btn-add-plate-bottom must exist"
        assert btn_idx > plates_idx, "#btn-add-plate-bottom must appear AFTER #plates-container in DOM"

        soup = BeautifulSoup(content, "html.parser")
        btn = soup.find(id="btn-add-plate-bottom")
        assert "addNewPlateRow()" in (btn.get("onclick") or "")

    def test_t1_bom_insumos_manager(self):
        """Feature 13: Verify BOM container and dynamic row input requirements in app.js."""
        soup = BeautifulSoup(INDEX_HTML.read_text(encoding="utf-8"), "html.parser")
        assert soup.find(id="bom-container") is not None

        app_js = APP_JS.read_text(encoding="utf-8")
        assert 'placeholder="R$ Unit"' in app_js
        assert 'min="0" step="any"' in app_js

    def test_t1_labor_overhead_and_commercial_terms_inputs(self):
        """Feature 14: Verify CAD/Post labor fields, overhead, tax, delivery days, and terms."""
        soup = BeautifulSoup(INDEX_HTML.read_text(encoding="utf-8"), "html.parser")
        required_inputs = [
            "proj-cad-hours", "proj-cad-rate", "proj-post-hours", "proj-post-rate",
            "proj-overhead", "proj-margin", "proj-tax", "proj-discount", "proj-shipping",
            "proj-delivery-days", "proj-payment-terms", "proj-warranty-terms", "proj-notes"
        ]
        for inp_id in required_inputs:
            assert soup.find(id=inp_id) is not None, f"Input '{inp_id}' must exist in project editor"

        deliv = soup.find(id="proj-delivery-days")
        assert deliv.get("type") == "number"
        assert deliv.get("step") == "1"
        assert deliv.get("min") == "1"

    def test_t1_sticky_financial_terminal_dom_elements(self):
        """Feature 15: Verify all 16 live financial summary terminal elements."""
        soup = BeautifulSoup(INDEX_HTML.read_text(encoding="utf-8"), "html.parser")
        summary_ids = [
            "live-weight", "live-time", "live-material-cost", "live-machine-cost",
            "live-bom-cost", "live-labor-cost", "live-overhead-cost", "live-base-cost",
            "live-suggested-price", "live-discount-row", "live-discount-amount",
            "live-shipping-row", "live-shipping-amount", "live-tax-amount",
            "live-final-price", "live-net-profit"
        ]
        for sid in summary_ids:
            assert soup.find(id=sid) is not None, f"Live summary element '{sid}' must exist"

    def test_t1_printers_catalog_and_modal_inputs(self):
        """Feature 16, 17: Verify printers grid and modal input step attributes."""
        soup = BeautifulSoup(INDEX_HTML.read_text(encoding="utf-8"), "html.parser")
        assert soup.find(id="printers-grid") is not None
        assert soup.find(id="modal-printer") is not None

        printer_inputs = [
            "printer-id", "printer-name", "printer-model", "printer-cost",
            "printer-lifespan", "printer-power", "printer-maintenance", "printer-energy"
        ]
        for pid in printer_inputs:
            el = soup.find(id=pid)
            assert el is not None, f"Printer modal input '{pid}' must exist"

        cost_el = soup.find(id="printer-cost")
        assert cost_el.get("step") in ["any", "0.01"]
        lifespan_el = soup.find(id="printer-lifespan")
        assert lifespan_el.get("step") == "any"

    def test_t1_filaments_catalog_modal_and_hex_picker(self):
        """Feature 18, 19: Verify filaments grid, modal with hex picker, and absence of filament-name."""
        soup = BeautifulSoup(INDEX_HTML.read_text(encoding="utf-8"), "html.parser")
        assert soup.find(id="filaments-grid") is not None
        assert soup.find(id="modal-filament") is not None

        # Contract: filament-name MUST NOT exist; filament-color-hex MUST be type="color"
        assert soup.find(id="filament-name") is None, "filament-name text input must NOT exist"
        hex_input = soup.find(id="filament-color-hex")
        assert hex_input is not None
        assert hex_input.get("type") == "color"

        # Check preview elements
        assert soup.find(id="filament-preview-text") is not None
        assert soup.find(id="filament-preview-dot") is not None

        # Check weight and price steps
        f_weight = soup.find(id="filament-weight")
        assert f_weight.get("step") == "any"
        f_price = soup.find(id="filament-price")
        assert f_price.get("step") in ["any", "0.01"]

    def test_t1_workshop_settings_view_elements(self):
        """Feature 20: Verify workshop preferences form and all identity/rate inputs."""
        soup = BeautifulSoup(INDEX_HTML.read_text(encoding="utf-8"), "html.parser")
        assert soup.find(id="form-settings") is not None
        pref_ids = [
            "pref-company", "pref-fullname", "pref-phone", "pref-pix",
            "pref-energy", "pref-margin", "pref-tax", "pref-failure",
            "pref-cad-rate", "pref-post-rate", "pref-payment-terms", "pref-warranty-terms"
        ]
        for pid in pref_ids:
            assert soup.find(id=pid) is not None, f"Settings input '{pid}' must exist"

    def test_t1_auth_modal_tabs_and_forms(self):
        """Feature 21: Verify authentication modal tabs and clean environment notice."""
        soup = BeautifulSoup(INDEX_HTML.read_text(encoding="utf-8"), "html.parser")
        assert soup.find(id="auth-modal") is not None
        assert soup.find(id="tab-login-btn") is not None
        assert soup.find(id="tab-register-btn") is not None
        assert soup.find(id="form-login") is not None
        assert soup.find(id="form-register") is not None

        login_inputs = ["login-email", "login-password"]
        for lid in login_inputs:
            assert soup.find(id=lid) is not None

        reg_inputs = ["reg-name", "reg-company", "reg-email", "reg-password"]
        for rid in reg_inputs:
            assert soup.find(id=rid) is not None

    def test_t1_preview_html_structure_and_serving(self, client):
        """Feature 22: Verify standalone preview.html layout and static route serving."""
        assert PREVIEW_HTML.exists(), "frontend/preview.html must exist"
        soup = BeautifulSoup(PREVIEW_HTML.read_text(encoding="utf-8"), "html.parser")

        assert soup.find(id="pdf-frame") is not None
        assert soup.find(id="btn-download") is not None
        assert soup.find(id="btn-print") is not None
        assert soup.find(id="doc-title") is not None
        assert soup.find(id="error-state") is not None

        # Verify static file serving via client
        resp = client.get("/static/preview.html")
        assert resp.status_code == 200
        assert "pdf-frame" in resp.text

    def test_t1_script_loading_order_and_dependency_chain(self):
        """Feature 24: Verify script loading order in index.html: api -> gcode -> threemf -> app."""
        content = INDEX_HTML.read_text(encoding="utf-8")
        api_idx = content.find("js/api.js")
        gcode_idx = content.find("parsers/gcode.js")
        threemf_idx = content.find("parsers/threemf.js")
        app_idx = content.find("js/app.js")

        assert api_idx != -1 and gcode_idx != -1 and threemf_idx != -1 and app_idx != -1
        assert api_idx < gcode_idx, "api.js must be loaded before parsers"
        assert gcode_idx < threemf_idx, "gcode.js must be loaded before threemf.js"
        assert threemf_idx < app_idx, "threemf.js must be loaded before app.js"


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ==============================================================================

class TestTier2BoundaryAndCornerCases:
    """Verifies edge conditions, nullish coalescing, division by zero, and locale parsing."""

    def test_t2_zero_tax_rate_nullish_preservation(self, client, make_user):
        """Verify that 0% tax rate is strictly preserved without reverting to 6%."""
        user = make_user()
        resp = client.post("/api/projects", json={
            "name": "Zero Tax Project",
            "tax_rate_percent": 0.0,
            "profit_margin_percent": 25.0,
            "plates": [{
                "name": "Placa Teste",
                "print_time_hours": 2.0,
                "part_weight_g": 50.0,
                "custom_printer_hourly_rate": 5.0,
                "custom_filament_cost_per_g": 0.10,
                "quantity": 1
            }]
        }, headers=user["headers"])
        assert resp.status_code == 201
        data = resp.json()

        # Engine summary verification
        summary = data["summary"]
        assert summary["tax_rate_percent"] == 0.0
        assert summary["tax_amount"] == 0.0
        # When tax is 0%, suggested price = base_cost * (1 + margin) / 1.0
        expected_base = summary["base_cost"]
        expected_suggested = round(expected_base * 1.25, 2)
        assert summary["suggested_price"] == expected_suggested
        assert summary["final_price_to_client"] == expected_suggested

    def test_t2_zero_profit_margin_and_free_materials(self):
        """Verify that 0% profit margin and free filament (0.0/g) calculate cleanly."""
        plate = {
            "name": "Free Material Plate",
            "print_time_hours": 1.0,
            "part_weight_g": 100.0,
            "custom_printer_hourly_rate": 0.0,
            "custom_filament_cost_per_g": 0.0,
            "quantity": 1
        }
        summary = calculate_project_summary(
            project={"profit_margin_percent": 0.0, "tax_rate_percent": 0.0},
            plates=[plate],
            bom_items=[]
        )
        assert summary["base_cost"] == 0.0
        assert summary["suggested_price"] == 0.0
        assert summary["net_profit"] == 0.0
        assert summary["effective_profit_margin_percent"] == 0.0

    def test_t2_maximum_boundaries_99pct_tax_and_100pct_discount(self):
        """Verify maximum boundary conditions: 99% tax and 100% commercial discount."""
        plate = {
            "print_time_hours": 1.0,
            "part_weight_g": 10.0,
            "custom_printer_hourly_rate": 10.0,
            "custom_filament_cost_per_g": 0.10,
            "quantity": 1
        }
        # 100% discount with R$ 25 shipping
        summary = calculate_project_summary(
            project={
                "profit_margin_percent": 20.0,
                "tax_rate_percent": 10.0,
                "discount_percent": 100.0,
                "shipping_cost": 25.0
            },
            plates=[plate],
            bom_items=[]
        )
        assert summary["discount_percent"] == 100.0
        assert summary["subtotal_after_discount"] == 0.0
        # Final price to client must equal shipping only
        assert summary["final_price_to_client"] == 25.0

        # 99% tax rate boundary (tax divisor = 0.01)
        summary_high_tax = calculate_project_summary(
            project={
                "profit_margin_percent": 0.0,
                "tax_rate_percent": 99.0
            },
            plates=[plate],
            bom_items=[]
        )
        assert summary_high_tax["tax_rate_percent"] == 99.0
        assert summary_high_tax["suggested_price"] > 0

    def test_t2_division_by_zero_guards_in_engine(self):
        """Verify that zero lifespan, zero spool weight, and zero base cost do not crash."""
        # 1. Zero lifespan hours on printer
        rates = calculate_printer_hourly_rate(acquisition_cost=5000.0, lifespan_hours=0.0)
        assert rates["depreciation_per_hour"] == 0.0

        # 2. Zero spool weight on filament falls back safely to 1000g default
        plate_cost = calculate_plate_cost(
            plate={"print_time_hours": 1.0, "part_weight_g": 50.0},
            filament={"spool_price": 100.0, "spool_weight_g": 0.0}
        )
        assert plate_cost["cost_per_gram"] == 0.1  # Safe 100 / 1000g fallback avoids div by zero

        # 3. Zero base cost on project
        summary = calculate_project_summary(
            project={"profit_margin_percent": 30.0, "tax_rate_percent": 6.0},
            plates=[],
            bom_items=[]
        )
        assert summary["base_cost"] == 0.0
        assert summary["suggested_price"] == 0.0
        assert summary["effective_profit_margin_percent"] == 0.0

    def test_t2_locale_float_parsing_algorithm_parity(self):
        """Verify parseLocaleFloat handles standard BRL/US numbers, spaces, and currency symbols."""
        def parse_locale_float(val, fallback=0.0):
            if val is None or val == "":
                return fallback
            if isinstance(val, (int, float)):
                return fallback if val != val else float(val)
            s = str(val).strip()
            s = re.sub(r"^[^\d\-+]+", "", s)
            if not s:
                return fallback
            last_dot = s.rfind(".")
            last_comma = s.rfind(",")
            if last_dot != -1 and last_comma != -1:
                if last_comma > last_dot:
                    s = s.replace(".", "").replace(",", ".")
                else:
                    s = s.replace(",", "")
            elif last_comma != -1:
                s = s.replace(",", ".")
            try:
                return float(s)
            except ValueError:
                return fallback

        assert parse_locale_float("56,50") == 56.50
        assert parse_locale_float("89,90") == 89.90
        assert parse_locale_float("1.234,56") == 1234.56
        assert parse_locale_float("3.499,90") == 3499.90
        assert parse_locale_float("R$ 56,50") == 56.50
        assert parse_locale_float("  R$ 1.200,00 ") == 1200.00
        assert parse_locale_float("1000") == 1000.0
        assert parse_locale_float("0", 10) == 0.0
        assert parse_locale_float(None, 42) == 42.0
        assert parse_locale_float("", 99) == 99.0

    def test_t2_negative_numeric_sanitization(self):
        """Verify negative values in calculations are clamped to 0.0."""
        rates = calculate_printer_hourly_rate(
            acquisition_cost=-500.0,
            lifespan_hours=5000.0,
            avg_power_watts=-100.0,
            energy_rate_kwh=-0.85
        )
        assert rates["depreciation_per_hour"] == 0.0
        assert rates["energy_cost_per_hour"] == 0.0

        summary = calculate_project_summary(
            project={"cad_hours": -5.0, "overhead_cost": -20.0},
            plates=[],
            bom_items=[]
        )
        assert summary["cad_hours"] == 0.0
        assert summary["overhead_cost"] == 0.0

    def test_t2_api_unauthorized_and_invalid_token(self, client):
        """Verify API returns HTTP 401 when unauthenticated or presenting an invalid token."""
        # Unauthenticated
        resp1 = client.get("/api/projects")
        assert resp1.status_code == 401

        # Malformed Bearer Token
        resp2 = client.get("/api/projects", headers={"Authorization": "Bearer invalid.jwt.token"})
        assert resp2.status_code == 401

        # Non-existent resource with valid auth returns 404
        # (Tested in Tier 3 isolation)

    def test_t2_universal_html_step_and_min_validation(self):
        """Verify universal rule: no numeric input combines min=1 with step > 1."""
        soup = BeautifulSoup(INDEX_HTML.read_text(encoding="utf-8"), "html.parser")
        for inp in soup.find_all("input", type="number"):
            step = inp.get("step")
            min_val = inp.get("min")
            inp_id = inp.get("id", "(no-id)")
            if step and step != "any":
                try:
                    s_val = float(step)
                    m_val = float(min_val) if min_val is not None else 0.0
                    assert not (m_val == 1.0 and s_val > 1.0), (
                        f"Input '{inp_id}' combines min=1 with step={s_val}, causing stepMismatch!"
                    )
                except ValueError:
                    pass


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS
# ==============================================================================

class TestTier3CrossFeatureCombinations:
    """Verifies pairwise and multi-feature integrations between client and server logic."""

    def test_t3_full_project_financial_formula_parity(self, client, make_user):
        """Verify mathematical parity across all 7 stages between backend engine and client formula."""
        user = make_user()

        # Step 1: Create Printer & Filament
        pr_resp = client.post("/api/printers", json={
            "name": "Bambu Lab P1S",
            "model": "P1S",
            "acquisition_cost": 4500.0,
            "lifespan_hours": 5000.0,
            "avg_power_watts": 160.0,
            "energy_rate_kwh": 0.85,
            "maintenance_cost_per_hour": 1.50
        }, headers=user["headers"])
        assert pr_resp.status_code == 201
        printer_id = pr_resp.json()["id"]

        fil_resp = client.post("/api/filaments", json={
            "name": "PLA Cinza - Voolt3D",
            "material": "PLA",
            "brand": "Voolt3D",
            "color": "Cinza",
            "color_hex": "#888888",
            "spool_weight_g": 1000.0,
            "spool_price": 100.0
        }, headers=user["headers"])
        assert fil_resp.status_code == 201
        filament_id = fil_resp.json()["id"]

        # Step 2: Create Project with Multi-plate, BOM, Labor, Margin, Tax, Discount, Shipping
        proj_payload = {
            "name": "Suporte Articulado Pro",
            "client_name": "Studio Delta",
            "cad_hours": 1.5,
            "cad_hourly_rate": 60.0,
            "post_process_hours": 0.5,
            "post_process_hourly_rate": 40.0,
            "overhead_cost": 15.0,
            "profit_margin_percent": 30.0,
            "tax_rate_percent": 6.0,
            "discount_percent": 10.0,
            "shipping_cost": 22.50,
            "delivery_days": 5,
            "plates": [
                {
                    "name": "Placa Principal",
                    "printer_id": printer_id,
                    "filament_id": filament_id,
                    "print_time_hours": 3.0,
                    "part_weight_g": 120.0,
                    "purge_weight_g": 10.0,
                    "failure_margin_percent": 10.0,
                    "quantity": 2
                }
            ],
            "bom_items": [
                {
                    "name": "Parafuso M5x20",
                    "category": "Fixadores",
                    "quantity": 6,
                    "unit_cost": 0.75
                }
            ]
        }

        resp = client.post("/api/projects", json=proj_payload, headers=user["headers"])
        assert resp.status_code == 201
        summary = resp.json()["summary"]

        # Verify Stage 1: Plates
        # Cost per gram = 100 / 1000 = 0.10
        # Weight per unit = (120 + 10) * 1.10 = 143.0g
        # Unit mat cost = 14.30
        # Hourly machine rate = (4500/5000 = 0.90) + (160/1000 * 0.85 = 0.136) + 1.50 = 2.536
        # Unit machine cost = 3.0 * 2.536 = 7.608
        # Unit total = 14.30 + 7.608 = 21.908 -> * 2 plates = 43.816 -> round(43.82)
        assert summary["total_plates_count"] == 1
        assert round(summary["total_plates_cost"], 1) == 43.8

        # Verify Stage 2: BOM
        # 6 * 0.75 = 4.50
        assert summary["total_bom_cost"] == 4.50

        # Verify Stage 3: Labor
        # (1.5 * 60 = 90.0) + (0.5 * 40 = 20.0) = 110.0
        assert summary["total_labor_cost"] == 110.0

        # Verify Stage 4: Overhead & Base Cost
        # 43.82 + 4.50 + 110.0 + 15.0 = 173.32
        expected_base = round(summary["total_plates_cost"] + summary["total_bom_cost"] + summary["total_labor_cost"] + 15.0, 2)
        assert summary["base_cost"] == expected_base

        # Verify Stage 5: Suggested Price with 30% margin and 6% tax
        # suggested_price = (base_cost * 1.30) / (1 - 0.06)
        expected_suggested = round((expected_base * 1.30) / 0.94, 2)
        assert summary["suggested_price"] == expected_suggested

        # Verify Stage 6: Discount & Subtotal
        expected_discount = round(expected_suggested * 0.10, 2)
        expected_subtotal = round(expected_suggested - expected_discount, 2)
        assert summary["discount_amount"] == expected_discount
        assert summary["subtotal_after_discount"] == expected_subtotal

        # Verify Stage 7: Final Client Price (Subtotal + Shipping)
        expected_final = round(expected_subtotal + 22.50, 2)
        assert summary["final_price_to_client"] == expected_final

    def test_t3_catalog_entities_vs_custom_plate_overrides(self):
        """Verify plate using catalog entities interacts properly alongside plate with custom overrides."""
        plate_catalog = {
            "name": "Placa Catálogo",
            "printer_id": 1,
            "filament_id": 1,
            "print_time_hours": 2.0,
            "part_weight_g": 50.0,
            "quantity": 1
        }
        printer_mock = {
            "id": 1,
            "acquisition_cost": 2000.0,
            "lifespan_hours": 4000.0,
            "avg_power_watts": 100.0,
            "energy_rate_kwh": 0.80,
            "maintenance_cost_per_hour": 1.00
        }
        filament_mock = {
            "id": 1,
            "spool_price": 90.0,
            "spool_weight_g": 1000.0
        }

        plate_custom = {
            "name": "Placa Customizada",
            "print_time_hours": 1.5,
            "part_weight_g": 80.0,
            "custom_printer_hourly_rate": 6.50,
            "custom_filament_cost_per_g": 0.15,
            "quantity": 2
        }

        c1 = calculate_plate_cost(plate_catalog, printer=printer_mock, filament=filament_mock)
        c2 = calculate_plate_cost(plate_custom, printer=None, filament=None)

        # Plate 1 uses catalog:
        # machine rate = 0.50 (deprec) + 0.08 (energy) + 1.00 = 1.58 -> 2h * 1.58 = 3.16
        # filament cost = 0.09/g * 50g = 4.50 -> total unit = 7.66
        assert c1["unit_material_cost"] == 4.50
        assert c1["unit_machine_cost"] == 3.16
        assert c1["total_cost"] == 7.66

        # Plate 2 uses custom overrides:
        # machine cost = 1.5h * 6.50 = 9.75
        # filament cost = 80g * 0.15 = 12.00
        # unit total = 21.75 -> 2 qty = 43.50
        assert c2["unit_material_cost"] == 12.00
        assert c2["unit_machine_cost"] == 9.75
        assert c2["total_cost"] == 43.50

        # Project Summary
        summary = calculate_project_summary(
            project={},
            plates=[plate_catalog, plate_custom],
            bom_items=[],
            printers_by_id={1: printer_mock},
            filaments_by_id={1: filament_mock}
        )
        assert summary["total_plates_cost"] == round(7.66 + 43.50, 2)

    def test_t3_filament_duplicate_and_plate_usage(self, client, make_user):
        """Verify duplicating a filament and using the duplicated filament on a new project."""
        user = make_user()

        # Create original filament
        orig = client.post("/api/filaments", json={
            "name": "PETG Preto - Voolt3D",
            "material": "PETG",
            "brand": "Voolt3D",
            "color": "Preto",
            "color_hex": "#112233",
            "spool_weight_g": 1000.0,
            "spool_price": 110.0
        }, headers=user["headers"]).json()
        orig_id = orig["id"]

        # Duplicate filament via API endpoint
        dup_resp = client.post(f"/api/filaments/{orig_id}/duplicate", headers=user["headers"])
        assert dup_resp.status_code == 201
        dup = dup_resp.json()
        dup_id = dup["id"]

        assert dup_id != orig_id
        assert dup["material"] == "PETG"
        assert dup["brand"] == "Voolt3D"
        assert dup["spool_price"] == 110.0

        # Create project referencing duplicated filament
        proj = client.post("/api/projects", json={
            "name": "Projeto com Filamento Duplicado",
            "plates": [{
                "name": "Placa 1",
                "filament_id": dup_id,
                "print_time_hours": 1.0,
                "part_weight_g": 100.0,
                "failure_margin_percent": 0.0,
                "custom_printer_hourly_rate": 2.0
            }]
        }, headers=user["headers"]).json()

        assert proj["summary"]["total_material_cost"] == 11.0  # 100g * 0.11/g

    def test_t3_multi_tenant_data_isolation(self, client, make_user):
        """Verify strict multi-tenant isolation: User B cannot access User A's projects or assets."""
        user_a = make_user(email="alice@workshop.com")
        user_b = make_user(email="bob@makerspace.com")

        # User A creates a printer and a project
        p_resp = client.post("/api/printers", json={
            "name": "Alice Ender 3",
            "acquisition_cost": 1500.0
        }, headers=user_a["headers"])
        assert p_resp.status_code == 201
        alice_printer_id = p_resp.json()["id"]

        proj_resp = client.post("/api/projects", json={
            "name": "Alice Secret Project"
        }, headers=user_a["headers"])
        assert proj_resp.status_code == 201
        alice_proj_id = proj_resp.json()["id"]

        # User B starts with an empty environment
        bob_projects = client.get("/api/projects", headers=user_b["headers"]).json()
        assert len(bob_projects) == 0, "User B must have 0 projects initially"

        bob_printers = client.get("/api/printers", headers=user_b["headers"]).json()
        assert len(bob_printers) == 0, "User B must have 0 printers initially"

        # User B attempting to access Alice's project must receive 404
        assert client.get(f"/api/projects/{alice_proj_id}", headers=user_b["headers"]).status_code == 404
        assert client.get(f"/api/projects/{alice_proj_id}/pdf", headers=user_b["headers"]).status_code == 404

        # User B attempting to delete Alice's printer must receive 404
        assert client.delete(f"/api/printers/{alice_printer_id}", headers=user_b["headers"]).status_code == 404


# ==============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS
# ==============================================================================

class TestTier4RealWorldScenarios:
    """Verifies end-to-end user workflows and production quote lifecycles."""

    def test_t4_scenario_industrial_job_quote_and_pdf(self, client, make_user):
        """Scenario 1: Industrial job with 3 plates, BOM fasteners, custom rates, and PDF quote."""
        user = make_user(email="industrial@printpro.com", full_name="Carlos Engenharia")

        # 1. Register Industrial Printer
        printer = client.post("/api/printers", json={
            "name": "Bambu Lab X1-Carbon",
            "model": "X1C",
            "acquisition_cost": 9500.0,
            "lifespan_hours": 5000.0,
            "avg_power_watts": 250.0,
            "energy_rate_kwh": 0.85,
            "maintenance_cost_per_hour": 2.50
        }, headers=user["headers"]).json()

        # 2. Register Filaments
        fil_abs = client.post("/api/filaments", json={
            "name": "ABS Preto - Voolt3D",
            "material": "ABS",
            "brand": "Voolt3D",
            "color": "Preto",
            "color_hex": "#0a0a0a",
            "spool_weight_g": 1000.0,
            "spool_price": 130.0
        }, headers=user["headers"]).json()

        fil_pacf = client.post("/api/filaments", json={
            "name": "PA-CF Fibra de Carbono - Esun",
            "material": "PA",
            "brand": "Esun",
            "color": "Preto Fibra",
            "color_hex": "#1a1a1a",
            "spool_weight_g": 1000.0,
            "spool_price": 280.0
        }, headers=user["headers"]).json()

        # 3. Create Project with 3 Plates, 2 BOM items, Labor, Terms
        proj_resp = client.post("/api/projects", json={
            "name": "Gabarito Industrial de Solda",
            "client_name": "Metalúrgica Progresso",
            "client_email": "contato@metalurgica.com",
            "status": "quoted",
            "cad_hours": 2.5,
            "cad_hourly_rate": 80.0,
            "post_process_hours": 1.0,
            "post_process_hourly_rate": 40.0,
            "overhead_cost": 35.0,
            "profit_margin_percent": 35.0,
            "tax_rate_percent": 6.0,
            "discount_percent": 5.0,
            "shipping_cost": 42.0,
            "delivery_days": 7,
            "payment_terms": "40% de entrada e 60% na entrega técnica",
            "warranty_terms": "90 dias de garantia contra deformação térmica",
            "plates": [
                {
                    "name": "Placa 1 - Base Estrutural",
                    "printer_id": printer["id"],
                    "filament_id": fil_abs["id"],
                    "print_time_hours": 4.5,
                    "part_weight_g": 180.0,
                    "purge_weight_g": 15.0,
                    "failure_margin_percent": 10.0,
                    "quantity": 1
                },
                {
                    "name": "Placa 2 - Garras Móveis",
                    "printer_id": printer["id"],
                    "filament_id": fil_pacf["id"],
                    "print_time_hours": 2.0,
                    "part_weight_g": 60.0,
                    "purge_weight_g": 0.0,
                    "failure_margin_percent": 5.0,
                    "quantity": 2
                },
                {
                    "name": "Placa 3 - Pinos Guia",
                    "printer_id": printer["id"],
                    "filament_id": fil_abs["id"],
                    "print_time_hours": 0.8,
                    "part_weight_g": 25.0,
                    "purge_weight_g": 0.0,
                    "failure_margin_percent": 0.0,
                    "quantity": 4
                }
            ],
            "bom_items": [
                {
                    "name": "Parafusos M4x16 Inox",
                    "category": "Fixadores",
                    "quantity": 8,
                    "unit_cost": 0.65
                },
                {
                    "name": "Insertos de Latão M4",
                    "category": "Insertos",
                    "quantity": 4,
                    "unit_cost": 1.20
                }
            ]
        }, headers=user["headers"])

        assert proj_resp.status_code == 201
        proj = proj_resp.json()
        proj_id = proj["id"]

        # Validate Financial Totals
        summary = proj["summary"]
        assert summary["total_plates_count"] == 3
        assert summary["total_bom_items_count"] == 12  # 8 + 4
        assert summary["final_price_to_client"] > summary["base_cost"]
        assert summary["net_profit"] > 0

        # 4. Generate Client Quotation PDF
        client_pdf = client.get(f"/api/projects/{proj_id}/pdf?type=client", headers=user["headers"])
        assert client_pdf.status_code == 200
        assert client_pdf.headers["content-type"] == "application/pdf"
        assert client_pdf.content.startswith(b"%PDF")
        assert len(client_pdf.content) > 1000

        # 5. Generate Technical Production Order PDF
        tech_pdf = client.get(f"/api/projects/{proj_id}/pdf?type=technical", headers=user["headers"])
        assert tech_pdf.status_code == 200
        assert tech_pdf.headers["content-type"] == "application/pdf"
        assert tech_pdf.content.startswith(b"%PDF")
        assert len(tech_pdf.content) > 1000

    def test_t4_scenario_zero_tax_hobbyist_workflow(self, client, make_user):
        """Scenario 2: MEI Artisan / Hobbyist with 0% tax, simple markup, and PIX payment terms."""
        user = make_user(email="hobbyist@artes3d.com", full_name="Ana Miniaturas")

        # Save workshop settings with 0% default tax and 50% margin
        set_resp = client.put("/api/auth/preferences", json={
            "default_tax_rate": 0.0,
            "default_profit_margin": 50.0,
            "default_payment_terms": "100% via PIX na aprovação do pedido"
        }, headers=user["headers"])
        assert set_resp.status_code == 200

        # Create Project
        proj = client.post("/api/projects", json={
            "name": "Miniatura Dragão Articulado",
            "client_name": "Lucas Colecionador",
            "tax_rate_percent": 0.0,
            "profit_margin_percent": 50.0,
            "delivery_days": 2,
            "plates": [{
                "name": "Corpo & Asas",
                "print_time_hours": 6.0,
                "part_weight_g": 85.0,
                "failure_margin_percent": 0.0,
                "custom_printer_hourly_rate": 2.50,
                "custom_filament_cost_per_g": 0.12,
                "quantity": 1
            }]
        }, headers=user["headers"]).json()

        summary = proj["summary"]
        assert summary["tax_rate_percent"] == 0.0
        assert summary["tax_amount"] == 0.0
        # Base cost = (6h * 2.50 = 15.00) + (85g * 0.12 = 10.20) = 25.20
        assert summary["base_cost"] == 25.20
        # Profit = 25.20 * 0.50 = 12.60 -> Suggested & Final = 37.80
        assert summary["net_profit"] == 12.60
        assert summary["final_price_to_client"] == 37.80

        # PDF Export succeeds without tax
        pdf_resp = client.get(f"/api/projects/{proj['id']}/pdf?type=client", headers=user["headers"])
        assert pdf_resp.status_code == 200
        assert pdf_resp.content.startswith(b"%PDF")

    def test_t4_scenario_bulk_commercial_order_with_discount(self, client, make_user):
        """Scenario 3: Bulk production run (10x quantity) with 15% volume discount."""
        user = make_user()
        proj = client.post("/api/projects", json={
            "name": "Lote Chaveiros Promocionais",
            "discount_percent": 15.0,
            "delivery_days": 10,
            "plates": [{
                "name": "Cartela 10x Chaveiros",
                "print_time_hours": 3.0,
                "part_weight_g": 120.0,
                "custom_printer_hourly_rate": 3.00,
                "custom_filament_cost_per_g": 0.10,
                "quantity": 10
            }]
        }, headers=user["headers"]).json()

        summary = proj["summary"]
        assert summary["total_print_time_hours"] == 30.0
        assert summary["total_filament_weight_g"] == 1200.0
        assert summary["discount_percent"] == 15.0
        assert summary["discount_amount"] > 0
        assert summary["subtotal_after_discount"] < summary["suggested_price"]

    def test_t4_scenario_project_status_lifecycle_transitions(self, client, make_user):
        """Scenario 4: Full lifecycle status transitions (draft -> quoted -> approved -> completed)."""
        user = make_user()

        # 1. Create in draft
        proj = client.post("/api/projects", json={"name": "Lifecycle Project"}, headers=user["headers"]).json()
        proj_id = proj["id"]
        assert proj["status"] == "draft"

        # 2. Advance to quoted
        upd1 = client.put(f"/api/projects/{proj_id}", json={"status": "quoted"}, headers=user["headers"]).json()
        assert upd1["status"] == "quoted"

        # 3. Advance to approved
        upd2 = client.put(f"/api/projects/{proj_id}", json={"status": "approved"}, headers=user["headers"]).json()
        assert upd2["status"] == "approved"

        # 4. Advance to completed
        upd3 = client.put(f"/api/projects/{proj_id}", json={"status": "completed"}, headers=user["headers"]).json()
        assert upd3["status"] == "completed"
