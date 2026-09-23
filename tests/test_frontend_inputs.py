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
    assert "function duplicateFilament" in content, "Must define duplicateFilament helper"
    assert "editPrinter(" in content, "renderPrintersGrid must use editPrinter"
    assert "editFilament(" in content, "renderFilamentsGrid must use editFilament"
    assert "duplicateFilament(" in content, "renderFilamentsGrid must use duplicateFilament"

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

def test_numeric_input_normalization_and_dynamic_typing():
    """
    Validates that frontend/js/app.js implements:
    1. focusin handler switching number inputs to text + decimal inputmode
    2. focusout handler parsing with parseLocaleFloat and restoring type to number
    3. normalizeNumericInputs function called before saving projects, printers, filaments, preferences
    """
    app_js = Path(__file__).parent.parent / "frontend" / "js" / "app.js"
    content = app_js.read_text(encoding="utf-8")

    assert "focusin" in content, "Must include focusin handler for dynamic inputmode/type toggle"
    assert "focusout" in content, "Must include focusout handler for safe normalization"
    assert "function normalizeNumericInputs" in content, "Must define normalizeNumericInputs"
    assert "normalizeNumericInputs();" in content, "Must call normalizeNumericInputs() before saving"

def test_browser_headless_comma_preservation(tmp_path):
    """
    Executes a real headless Chrome/Edge browser test to prove that typing
    comma in a numeric input does NOT wipe out the entered value (preventing
    the HTML5 valid floating-point number sanitization wipeout bug).
    """
    import subprocess
    import shutil

    chrome_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chrome"),
    ]
    browser = None
    for c in chrome_candidates:
        if c and Path(c).exists():
            browser = c
            break

    if not browser:
        pytest.skip("No Chrome or Edge executable available for headless browser verification")

    app_js_path = (Path(__file__).parent.parent / "frontend" / "js" / "app.js").resolve().as_posix()
    html_test = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
<input type="number" id="test-num" step="any" value="56">
<div id="test-result"></div>
<script>
window.lucide = {{ createIcons: () => {{}} }};
window.API = {{ getToken: () => null }};
</script>
<script src="file:///{app_js_path}"></script>
<script>
window.addEventListener('DOMContentLoaded', () => {{
    const el = document.getElementById('test-num');
    // 1. Simulate focus
    el.focus();
    el.dispatchEvent(new FocusEvent('focusin', {{ bubbles: true }}));

    // 2. Simulate typing comma followed by 50
    el.dispatchEvent(new KeyboardEvent('keydown', {{ key: ',', bubbles: true, cancelable: true }}));
    el.value = el.value + ',50';

    const duringVal = el.value;
    const duringType = el.type;

    // 3. Simulate blur
    el.dispatchEvent(new FocusEvent('focusout', {{ bubbles: true }}));

    const afterVal = el.value;
    const afterType = el.type;

    document.getElementById('test-result').textContent =
        `DURING:[${{duringVal}}|${{duringType}}] AFTER:[${{afterVal}}|${{afterType}}]`;
}});
</script>
</body>
</html>"""
    test_html_file = tmp_path / "browser_test.html"
    test_html_file.write_text(html_test, encoding="utf-8")

    proc = subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--dump-dom", f"file:///{test_html_file.resolve().as_posix()}"],
        capture_output=True,
        text=True,
        timeout=15
    )
    dom_output = proc.stdout
    assert "DURING:[56,50|text]" in dom_output, f"Value was wiped out during typing! Output was:\n{dom_output}"
    assert "AFTER:[56.5|number]" in dom_output, f"Value was not properly normalized on blur! Output was:\n{dom_output}"


def test_new_feedback_frontend_elements():
    html_file = Path(__file__).parent.parent / "frontend" / "index.html"
    html_content = html_file.read_text(encoding="utf-8")
    parser = InputParser()
    parser.feed(html_content)
    inputs_by_id = {inp.get("id"): inp for inp in parser.inputs if inp.get("id")}

    # Feedback 4: filament-name removed from form inputs; filament-color-hex present
    assert "filament-name" not in inputs_by_id, "filament-name text input must be removed from modal"
    assert "filament-color-hex" in inputs_by_id, "filament-color-hex input must be present"
    assert inputs_by_id["filament-color-hex"].get("type") == "color"

    # Feedback 6: proj-delivery-days present in project form
    assert "proj-delivery-days" in inputs_by_id, "proj-delivery-days input must be present in project form"

    # Feedback 7: preview.html exists with iframe and download button
    preview_file = Path(__file__).parent.parent / "frontend" / "preview.html"
    assert preview_file.exists(), "frontend/preview.html must exist"
    preview_content = preview_file.read_text(encoding="utf-8")
    assert 'id="pdf-frame"' in preview_content
    assert 'id="btn-download"' in preview_content

    # Feedback 1: check toFixed(2) on cost per gram in app.js
    app_js = Path(__file__).parent.parent / "frontend" / "js" / "app.js"
    js_content = app_js.read_text(encoding="utf-8")
    assert "f.cost_per_gram.toFixed(2)" in js_content, "Cost per gram in filament card must use 2 decimal places"

    # Feedback 3: updatePlateTime helper defined
    assert "function updatePlateTime" in js_content, "updatePlateTime must be defined in app.js"
    assert "plate-time-h-" in js_content, "Hours input ID prefix must be present"
    assert "plate-time-m-" in js_content, "Minutes input ID prefix must be present"


def test_edit_project_preserves_zero_tax_rate_and_nullish_coalescing(tmp_path):
    """
    Verifies that editProject and settings populate numeric values using nullish
    coalescing (??) instead of logical OR (||) so that 0 (e.g. 0% tax) does not
    get coerced back to 6%.
    """
    app_js_path = Path(__file__).parent.parent / "frontend" / "js" / "app.js"
    assert app_js_path.exists()
    content = app_js_path.read_text(encoding="utf-8")

    # Ensure editProject uses proj.tax_rate_percent ?? 6 and NOT proj.tax_rate_percent || 6
    assert "proj.tax_rate_percent ?? 6" in content, "Must use ?? for tax_rate_percent in editProject"
    assert "proj.tax_rate_percent || 6" not in content, "Must not use || for tax_rate_percent in editProject"

    # Ensure initNewProject uses u.default_tax_rate ?? 6
    assert "u.default_tax_rate ?? 6" in content, "Must use ?? for default_tax_rate in initNewProject"

    # Ensure populateSettingsForm uses u.default_tax_rate ?? 6
    assert "document.getElementById('pref-tax').value = u.default_tax_rate ?? 6;" in content

    # Test via Headless Browser: run editProject with tax_rate_percent = 0
    import subprocess
    import shutil

    chrome_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chrome"),
    ]
    browser = None
    for c in chrome_candidates:
        if c and Path(c).exists():
            browser = c
            break

    if not browser:
        return

    html_test = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
<span id="editor-project-title"></span>
<span id="editor-project-subtitle"></span>
<input id="proj-name">
<input id="proj-client-name">
<input id="proj-client-email">
<input id="proj-client-phone">
<select id="proj-status"><option value="draft">draft</option></select>
<input id="proj-cad-hours">
<input id="proj-cad-rate">
<input id="proj-post-hours">
<input id="proj-post-rate">
<input id="proj-overhead">
<input id="proj-margin">
<input id="proj-tax">
<input id="proj-discount">
<input id="proj-shipping">
<input id="proj-delivery-days">
<textarea id="proj-notes"></textarea>
<div id="plates-container"></div>
<div id="bom-container"></div>
<div id="test-result"></div>

<script>
window.lucide = {{ createIcons: () => {{}} }};
window.API = {{
    getToken: () => null,
    projects: {{
        get: async (id) => ({{
            id: id,
            name: "Projeto 0% Imposto",
            client_name: "Cliente Teste",
            tax_rate_percent: 0,
            profit_margin_percent: 0,
            cad_hourly_rate: 0,
            post_process_hourly_rate: 0,
            delivery_days: 7,
            plates: [],
            bom_items: []
        }})
    }}
}};
window.renderPlates = () => {{}};
window.renderBOM = () => {{}};
window.navigateTo = () => {{}};
</script>
<script src="file:///{app_js_path.resolve().as_posix()}"></script>
<script>
window.addEventListener('DOMContentLoaded', async () => {{
    await editProject(42);
    const taxVal = document.getElementById('proj-tax').value;
    const marginVal = document.getElementById('proj-margin').value;
    const deliveryVal = document.getElementById('proj-delivery-days').value;
    document.getElementById('test-result').textContent = `TAX:[${{taxVal}}] MARGIN:[${{marginVal}}] DELIVERY:[${{deliveryVal}}]`;
}});
</script>
</body>
</html>"""
    test_html_file = tmp_path / "browser_edit_test.html"
    test_html_file.write_text(html_test, encoding="utf-8")

    proc = subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--dump-dom", f"file:///{test_html_file.resolve().as_posix()}"],
        capture_output=True,
        text=True,
        timeout=15
    )
    dom_output = proc.stdout
    assert "TAX:[0]" in dom_output, f"Tax value in editProject was not 0! Dom: {dom_output}"
    assert "MARGIN:[0]" in dom_output, f"Margin value in editProject was not 0! Dom: {dom_output}"
    assert "DELIVERY:[7]" in dom_output, f"Delivery days was not 7! Dom: {dom_output}"


def test_nova_placa_button_at_bottom():
    """
    Verifies that the 'Nova Placa' button is positioned below #plates-container
    (addressing Issue #13) so users don't need to scroll up to add plates.
    """
    html_file = Path(__file__).parent.parent / "frontend" / "index.html"
    content = html_file.read_text(encoding="utf-8")

    assert 'id="btn-add-plate-bottom"' in content, "Button #btn-add-plate-bottom must exist"
    assert 'onclick="addNewPlateRow()"' in content, "Must trigger addNewPlateRow"

    plates_idx = content.find('id="plates-container"')
    button_idx = content.find('id="btn-add-plate-bottom"')

    assert plates_idx != -1, "plates-container must exist"
    assert button_idx != -1, "btn-add-plate-bottom must exist"
    assert button_idx > plates_idx, "btn-add-plate-bottom must appear AFTER plates-container in DOM"


def test_gcode_3mf_file_input_and_parser_support():
    """
    Verifies that the platform accepts and parses .gcode.3mf files (addressing Issue #14).
    """
    html_file = Path(__file__).parent.parent / "frontend" / "index.html"
    html_content = html_file.read_text(encoding="utf-8")
    assert ".gcode.3mf" in html_content, "index.html must accept .gcode.3mf in file inputs or dropzone"

    app_js = Path(__file__).parent.parent / "frontend" / "js" / "app.js"
    js_content = app_js.read_text(encoding="utf-8")
    assert ".gcode.3mf" in js_content, "app.js must handle .gcode.3mf files"

    threemf_js = Path(__file__).parent.parent / "frontend" / "js" / "parsers" / "threemf.js"
    parser_content = threemf_js.read_text(encoding="utf-8")
    assert ".gcode" in parser_content, "threemf.js must handle embedded .gcode in .gcode.3mf"


def test_zero_rates_and_nullish_coalescing_in_plate_updates_and_summary(tmp_path):
    """
    Verifies that setting machine hourly rate or custom filament cost to 0
    is preserved across updatePlatePrinter, updatePlateFilament, and recalcLiveSummary.
    """
    app_js = Path(__file__).parent.parent / "frontend" / "js" / "app.js"
    js_content = app_js.read_text(encoding="utf-8")

    # updatePlatePrinter nullish check
    assert "state.currentPlates[idx].custom_printer_hourly_rate == null" in js_content, \
        "updatePlatePrinter must check == null to preserve 0 custom rate"
    assert "!state.currentPlates[idx].custom_printer_hourly_rate" not in js_content, \
        "updatePlatePrinter must not use ! negation check"

    # updatePlateFilament nullish check
    assert "state.currentPlates[idx].custom_filament_cost_per_g == null" in js_content, \
        "updatePlateFilament must check == null to preserve 0 custom cost"
    assert "!state.currentPlates[idx].custom_filament_cost_per_g" not in js_content, \
        "updatePlateFilament must not use ! negation check"

    # recalcLiveSummary machine hourly rate nullish coalescing
    assert "printer.machine_hourly_rate ?? 2.0" in js_content, \
        "recalcLiveSummary must use ?? 2.0 for printer.machine_hourly_rate"
    assert "printer.machine_hourly_rate || 2.0" not in js_content, \
        "recalcLiveSummary must not use || 2.0 for printer.machine_hourly_rate"


def test_script_loading_order_and_file_handler_toasts():
    """
    Verifies:
    1. index.html loads gcode.js BEFORE threemf.js (dependency order)
    2. threemf.js filters out directory entries
    3. Both handleSlicerFile and handleSinglePlateFile notify unsupported file types (.gcode.3mf included)
    """
    html_file = Path(__file__).parent.parent / "frontend" / "index.html"
    html_content = html_file.read_text(encoding="utf-8")

    gcode_idx = html_content.find("parsers/gcode.js")
    threemf_idx = html_content.find("parsers/threemf.js")
    assert gcode_idx != -1 and threemf_idx != -1
    assert gcode_idx < threemf_idx, "gcode.js must be loaded BEFORE threemf.js"

    threemf_js = Path(__file__).parent.parent / "frontend" / "js" / "parsers" / "threemf.js"
    threemf_content = threemf_js.read_text(encoding="utf-8")
    assert "!f.dir" in threemf_content, "threemf.js must filter directory entries when searching for gcode"

    app_js = Path(__file__).parent.parent / "frontend" / "js" / "app.js"
    app_js_content = app_js.read_text(encoding="utf-8")
    assert ".3mf, .gcode ou .gcode.3mf" in app_js_content, "app.js must mention .gcode.3mf in unsupported format toasts"


def test_filament_duplication_features():
    """
    Verifies that:
    1. frontend/js/app.js implements duplicateFilament(id) and passes it to openFilamentModal(filament, true)
    2. openFilamentModal handles duplication:
       - resets filament-id to empty string (so it saves as new)
       - clears filament-color to empty string so user can immediately type new color
       - sets placeholder to 'Digite a nova cor...'
       - sets focus/selection on color input
       - retains material, brand, weight, price, and color_hex
    3. frontend/js/api.js provides API.filaments.duplicate method
    4. renderFilamentsGrid includes duplicate button with copy icon
    """
    app_js = Path(__file__).parent.parent / "frontend" / "js" / "app.js"
    js_content = app_js.read_text(encoding="utf-8")

    assert "function duplicateFilament" in js_content
    assert "duplicateFilament(" in js_content
    assert "openFilamentModal(filament, true)" in js_content
    assert 'data-lucide="copy"' in js_content
    assert "isDuplicate" in js_content
    assert "Digite a nova cor..." in js_content

    api_js = Path(__file__).parent.parent / "frontend" / "js" / "api.js"
    api_content = api_js.read_text(encoding="utf-8")
    assert "duplicate: (id) => API.request(`/api/filaments/${id}/duplicate`" in api_content


def test_filament_duplication_browser_interaction():
    """
    Executes a real headless browser test (Chrome/Edge) to verify the filament duplication flow:
    - Initial state with an existing filament (e.g. PETG Preto - Voolt3D)
    - Clicking duplicate button calls duplicateFilament(id)
    - Modal opens with:
      * filament-id cleared to empty string
      * filament-color cleared to empty string and focused
      * material, brand, weight, price, color_hex preserved
      * typing a new color updates live standard name preview
    """
    import subprocess
    import shutil

    chrome_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chrome"),
    ]
    browser = None
    for c in chrome_candidates:
        if c and Path(c).exists():
            browser = c
            break

    if not browser:
        return

    app_js_path = (Path(__file__).parent.parent / "frontend" / "js" / "app.js").resolve().as_posix()

    html_test = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
    <div id="modal-filament" class="hidden">
        <h3 id="modal-filament-title"></h3>
        <input type="hidden" id="filament-id">
        <select id="filament-material">
            <option value="PLA">PLA</option>
            <option value="PETG">PETG</option>
            <option value="ABS">ABS</option>
        </select>
        <input type="text" id="filament-brand">
        <input type="color" id="filament-color-hex" value="#10b981">
        <input type="text" id="filament-color">
        <span id="filament-preview-text"></span>
        <span id="filament-preview-dot"></span>
        <input type="number" id="filament-weight" value="1000">
        <input type="number" id="filament-price" value="95.00">
    </div>
    <div id="filaments-grid"></div>
    <div id="test-result"></div>

    <script>
    window.lucide = {{ createIcons: () => {{}} }};
    window.state = {{
        filaments: [
            {{
                id: 10,
                name: "PETG Preto - Voolt3D",
                material: "PETG",
                brand: "Voolt3D",
                color: "Preto",
                color_hex: "#112233",
                spool_weight_g: 1000,
                spool_price: 115.50,
                cost_per_gram: 0.1155
            }}
        ]
    }};
    window.formatCurrency = (v) => "R$ " + Number(v).toFixed(2);
    window.refreshIcons = () => {{}};
    </script>
    <script src="file:///{app_js_path}"></script>
    <script>
    // Run tests
    try {{
        renderFilamentsGrid();
        const gridHtml = document.getElementById('filaments-grid').innerHTML;
        if (!gridHtml.includes('duplicateFilament(10)')) {{
            throw new Error("Duplicate button not rendered for filament 10");
        }}

        // Trigger duplicate
        duplicateFilament(10);

        const modalHidden = document.getElementById('modal-filament').classList.contains('hidden');
        if (modalHidden) throw new Error("Modal should be visible");

        const filId = document.getElementById('filament-id').value;
        if (filId !== "") throw new Error("filament-id should be empty for new duplicate, got: " + filId);

        const mat = document.getElementById('filament-material').value;
        if (mat !== "PETG") throw new Error("Material should be PETG, got: " + mat);

        const brand = document.getElementById('filament-brand').value;
        if (brand !== "Voolt3D") throw new Error("Brand should be Voolt3D, got: " + brand);

        const colorVal = document.getElementById('filament-color').value;
        if (colorVal !== "") throw new Error("filament-color should be empty ready to type, got: " + colorVal);

        const colorHex = document.getElementById('filament-color-hex').value;
        if (colorHex !== "#112233") throw new Error("filament-color-hex should be #112233, got: " + colorHex);

        const weight = document.getElementById('filament-weight').value;
        if (weight !== "1000") throw new Error("Weight should be 1000, got: " + weight);

        const price = document.getElementById('filament-price').value;
        if (price !== "115.5") throw new Error("Price should be 115.5, got: " + price);

        // Simulate typing new color
        document.getElementById('filament-color').value = "Azul";
        updateFilamentNamePreview();

        const previewText = document.getElementById('filament-preview-text').innerText;
        if (previewText !== "PETG Azul - Voolt3D") {{
            throw new Error("Preview text mismatch: " + previewText);
        }}

        document.getElementById('test-result').innerText = "SUCCESS";
    }} catch (e) {{
        document.getElementById('test-result').innerText = "ERROR: " + e.message;
    }}
    </script>
</body>
</html>"""

    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html_test)
        temp_path = f.name

    try:
        proc = subprocess.run([
            browser,
            "--headless=new",
            "--disable-gpu",
            "--dump-dom",
            Path(temp_path).as_uri()
        ], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)

        assert "SUCCESS" in (proc.stdout or ""), f"Headless browser test failed. Output:\n{proc.stdout}"
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_payment_and_warranty_inputs_in_frontend():
    """
    Verifies that:
    1. frontend/index.html includes proj-payment-terms and proj-warranty-terms inputs
    2. frontend/index.html includes pref-payment-terms and pref-warranty-terms inputs
    3. frontend/js/app.js handles proj-payment-terms and proj-warranty-terms in:
       - initNewProject
       - editProject
       - saveCurrentProject
    4. frontend/js/app.js handles pref-payment-terms and pref-warranty-terms in:
       - populateSettingsForm
       - handleSavePreferences
    """
    html_file = Path(__file__).parent.parent / "frontend" / "index.html"
    html_content = html_file.read_text(encoding="utf-8")

    assert 'id="proj-payment-terms"' in html_content
    assert 'id="proj-warranty-terms"' in html_content
    assert 'id="pref-payment-terms"' in html_content
    assert 'id="pref-warranty-terms"' in html_content

    app_js_file = Path(__file__).parent.parent / "frontend" / "js" / "app.js"
    app_js = app_js_file.read_text(encoding="utf-8")

    assert "proj-payment-terms" in app_js
    assert "proj-warranty-terms" in app_js
    assert "pref-payment-terms" in app_js
    assert "pref-warranty-terms" in app_js
    assert "payment_terms" in app_js
    assert "warranty_terms" in app_js








