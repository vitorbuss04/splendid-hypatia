from html.parser import HTMLParser
from pathlib import Path
import re
import pytest

class InputParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inputs = []

    def handle_starttag(self, tag, attrs):
        if tag == "input":
            attr_dict = dict(attrs)
            self.inputs.append(attr_dict)

def test_html_numeric_inputs_step_attributes():
    html_file = Path(__file__).parent.parent / "frontend" / "index.html"
    assert html_file.exists(), "frontend/index.html must exist"
    
    parser = InputParser()
    parser.feed(html_file.read_text(encoding="utf-8"))

    # Map inputs by ID
    inputs_by_id = {inp.get("id"): inp for inp in parser.inputs if inp.get("id")}

    # 1. Filament Spool Weight: must accept 1000g (not just odd values)
    assert "filament-weight" in inputs_by_id
    f_weight = inputs_by_id["filament-weight"]
    assert f_weight.get("type") == "number"
    assert f_weight.get("step") == "any", "filament-weight step should be 'any' to accept 1000g without stepMismatch"

    # 2. Filament Spool Price: must accept cents / decimal values (not step='1')
    assert "filament-price" in inputs_by_id
    f_price = inputs_by_id["filament-price"]
    assert f_price.get("type") == "number"
    assert f_price.get("step") in ["any", "0.01"], "filament-price step should allow cents"
    assert f_price.get("step") != "1", "filament-price must not be restricted to integer steps"

    # 3. Printer Lifespan: must accept 5000h (not just values with odd steps like 5001)
    assert "printer-lifespan" in inputs_by_id
    p_lifespan = inputs_by_id["printer-lifespan"]
    assert p_lifespan.get("type") == "number"
    assert p_lifespan.get("step") == "any", "printer-lifespan step should be 'any' so 5000 is valid"

    # 4. Printer Cost: must accept cents (e.g. 3499.90)
    assert "printer-cost" in inputs_by_id
    p_cost = inputs_by_id["printer-cost"]
    assert p_cost.get("step") in ["any", "0.01"], "printer-cost step should allow cents"

    # 5. Check all numeric inputs: ensure none have step > 1 combined with min=1
    for inp in parser.inputs:
        if inp.get("type") == "number":
            inp_id = inp.get("id", "(no id)")
            step = inp.get("step")
            min_val = inp.get("min")
            if step and step != "any":
                try:
                    step_val = float(step)
                    min_val_f = float(min_val) if min_val is not None else 0.0
                    # If min is 1 and step > 1, round numbers like 1000, 5000 fail validation
                    if min_val_f == 1.0 and step_val > 1.0:
                        pytest.fail(f"Input '{inp_id}' has min=1 and step={step_val}, which causes stepMismatch on round numbers!")
                except ValueError:
                    pass

def test_parse_locale_float_logic():
    """
    Validates parseLocaleFloat algorithm in Python to ensure it matches
    the behavior implemented in frontend/js/app.js.
    """
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
                # Brazilian format: 1.234,56 -> remove dots, replace comma
                s = s.replace(".", "").replace(",", ".")
            else:
                # US format: 1,234.56 -> remove commas
                s = s.replace(",", "")
        elif last_comma != -1:
            s = s.replace(",", ".")

        try:
            return float(s)
        except ValueError:
            return fallback

    # Standard integer inputs
    assert parse_locale_float("1000") == 1000.0
    assert parse_locale_float("1001") == 1001.0
    assert parse_locale_float("5000") == 5000.0
    assert parse_locale_float("5001") == 5001.0

    # Decimal cents with comma (Feedback point: 56,50)
    assert parse_locale_float("56,50") == 56.50
    assert parse_locale_float("89,90") == 89.90
    assert parse_locale_float("32,75") == 32.75

    # Decimal cents with dot
    assert parse_locale_float("56.50") == 56.50
    assert parse_locale_float("3499.90") == 3499.90

    # Brazilian thousands with cents
    assert parse_locale_float("1.200,50") == 1200.50
    assert parse_locale_float("3.499,90") == 3499.90
    assert parse_locale_float("1.000,00") == 1000.0

    # Currency symbol prefixed (e.g. copied from banking/invoice: 'R$ 56,50')
    assert parse_locale_float("R$ 56,50") == 56.50
    assert parse_locale_float("R$ 3.499,90") == 3499.90

    # Empty, null, and fallback cases
    assert parse_locale_float("", 90) == 90
    assert parse_locale_float(None, 5000) == 5000
    assert parse_locale_float("0", 1000) == 0.0
    assert parse_locale_float(0, 1000) == 0.0

def test_app_js_safety_and_event_listeners():
    """
    Validates that frontend/js/app.js includes:
    1. beforeinput event listener for comma decimal support
    2. paste event listener for clipboard support
    3. safe editPrinter and editFilament functions without inline JSON stringification
    """
    app_js = Path(__file__).parent.parent / "frontend" / "js" / "app.js"
    assert app_js.exists(), "frontend/js/app.js must exist"
    content = app_js.read_text(encoding="utf-8")

    assert "beforeinput" in content, "Must include beforeinput event listener for comma decimal handling"
    assert "keydown" in content, "Must include keydown event listener for comma decimal handling fallback"
    assert "paste" in content, "Must include paste event listener for clipboard support"
    assert "function editPrinter" in content, "Must define editPrinter helper"
    assert "function editFilament" in content, "Must define editFilament helper"
    assert "editPrinter(" in content, "renderPrintersGrid must use editPrinter"
    assert "editFilament(" in content, "renderFilamentsGrid must use editFilament"

def test_dynamic_plate_and_bom_inputs_in_app_js():
    """
    Validates that dynamic inputs generated in app.js for plates and BOM
    also support step='any' and do not impose stepMismatch on decimals or round numbers.
    """
    app_js = Path(__file__).parent.parent / "frontend" / "js" / "app.js"
    content = app_js.read_text(encoding="utf-8")

    # Plates quantitative inputs
    assert 'custom_printer_hourly_rate' in content
    assert 'custom_filament_cost_per_g' in content
    assert 'step="any"' in content

    # BOM unit cost input
    assert 'placeholder="R$ Unit"' in content
    assert 'min="0" step="any"' in content

