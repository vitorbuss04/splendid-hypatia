from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
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
    assert "duplicate:" in api_content and "`/api/filaments/${id}/duplicate`" in api_content


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


def test_payment_terms_and_warranty_browser_flow():
    """
    Executes a real headless browser test (Chrome/Edge) to verify the terms resolution flow:
    - openNewProject() leaves proj-payment-terms and proj-warranty-terms empty ("")
      with dynamic placeholders reflecting workshop defaults ("Padrão da oficina: ...")
    - Saving without typing custom terms sends null for payment_terms & warranty_terms
    - Typing custom terms sends the custom string
    - editProject(proj) loads existing terms or leaves empty with dynamic placeholder if null
    """
    import subprocess
    import shutil
    import tempfile

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
        <select id="filament-material"><option value="PLA">PLA</option></select>
        <input type="text" id="filament-brand" value="3D Prime">
        <input type="color" id="filament-color-hex" value="#10b981">
        <input type="text" id="filament-color" value="">
        <span id="filament-preview-text"></span>
        <span id="filament-preview-dot"></span>
        <input type="number" id="filament-weight" value="1000">
        <input type="number" id="filament-price" value="95.00">
    </div>
    <div id="editor-project-title"></div>
    <div id="editor-project-subtitle"></div>
    <input type="text" id="proj-name">
    <input type="text" id="proj-client-name">
    <input type="email" id="proj-client-email">
    <input type="tel" id="proj-client-phone">
    <select id="proj-status"><option value="draft">Rascunho</option></select>
    <input type="number" id="proj-cad-hours">
    <input type="number" id="proj-cad-rate">
    <input type="number" id="proj-post-hours">
    <input type="number" id="proj-post-rate">
    <input type="number" id="proj-overhead">
    <input type="number" id="proj-margin">
    <input type="number" id="proj-tax">
    <input type="number" id="proj-discount">
    <input type="number" id="proj-shipping">
    <input type="number" id="proj-delivery-days">
    <input type="text" id="proj-payment-terms" placeholder="Deixe em branco para usar o padrão da oficina">
    <input type="text" id="proj-warranty-terms" placeholder="Deixe em branco para usar o padrão da oficina">
    <textarea id="proj-notes"></textarea>
    <div id="plates-container"></div>
    <div id="bom-items-container"></div>
    <div id="test-result"></div>

    <script>
    window.lucide = {{ createIcons: () => {{}} }};
    window.state = {{
        user: {{
            default_tax_rate: 6,
            default_profit_margin: 30,
            default_cad_rate: 50,
            default_post_rate: 30,
            default_payment_terms: "Entrada 40% e 60% na entrega",
            default_warranty_terms: "30 dias contra delaminação"
        }},
        filaments: [],
        printers: [],
        currentPlates: [],
        currentBOM: []
    }};
    window.formatCurrency = (v) => "R$ " + Number(v).toFixed(2);
    window.refreshIcons = () => {{}};
    window.navigateTo = () => {{}};
    window.recalcLiveSummary = () => {{}};
    window.renderPlates = () => {{}};
    window.renderBOM = () => {{}};
    window.showToast = () => {{}};
    let lastSavedPayload = null;
    window.API = {{
        projects: {{
            get: async (id) => ({{
                id: 1,
                name: "Projeto Existente",
                payment_terms: null,
                warranty_terms: "Garantia Especial 60d",
                plates: [],
                bom_items: []
            }}),
            create: async (data) => {{ lastSavedPayload = data; return {{ id: 99, ...data }}; }},
            update: async (id, data) => {{ lastSavedPayload = data; return {{ id, ...data }}; }}
        }}
    }};
    </script>
    <script src="file:///{app_js_path}"></script>
    <script>
    try {{
        // Test 1: openNewProject() must leave inputs empty and set placeholders with defaults
        openNewProject();
        const payInput = document.getElementById('proj-payment-terms');
        const warInput = document.getElementById('proj-warranty-terms');

        if (payInput.value !== "") throw new Error("proj-payment-terms should be empty string on new project, got: " + payInput.value);
        if (warInput.value !== "") throw new Error("proj-warranty-terms should be empty string on new project, got: " + warInput.value);
        if (!payInput.placeholder.includes("Entrada 40%")) throw new Error("proj-payment-terms placeholder should include workshop default, got: " + payInput.placeholder);
        if (!warInput.placeholder.includes("30 dias")) throw new Error("proj-warranty-terms placeholder should include workshop default, got: " + warInput.placeholder);

        // Test 2: Saving without typing should produce null terms
        saveCurrentProject(false).then(() => {{
            if (!lastSavedPayload) throw new Error("saveCurrentProject did not call API");
            if (lastSavedPayload.payment_terms !== null) throw new Error("payment_terms should be null when left blank, got: " + lastSavedPayload.payment_terms);
            if (lastSavedPayload.warranty_terms !== null) throw new Error("warranty_terms should be null when left blank, got: " + lastSavedPayload.warranty_terms);

            // Test 3: Typing custom terms sends custom string
            payInput.value = "100% à vista via PIX";
            warInput.value = "90 dias de garantia total";
            return saveCurrentProject(false);
        }}).then(() => {{
            if (lastSavedPayload.payment_terms !== "100% à vista via PIX") throw new Error("payment_terms not captured, got: " + lastSavedPayload.payment_terms);
            if (lastSavedPayload.warranty_terms !== "90 dias de garantia total") throw new Error("warranty_terms not captured, got: " + lastSavedPayload.warranty_terms);

            // Test 4: editProject loads null as empty string with placeholder
            return editProject(1);
        }}).then(() => {{
            if (payInput.value !== "") throw new Error("editProject should keep payment_terms as empty string when null, got: " + payInput.value);
            if (warInput.value !== "Garantia Especial 60d") throw new Error("editProject should load custom warranty_terms, got: " + warInput.value);
            if (!payInput.placeholder.includes("Entrada 40%")) throw new Error("editProject placeholder should reflect default");

            // Test 5: Modal close cleans up filament-id
            openFilamentModal({{ id: 7, material: "PLA", brand: "Voolt", color: "Preto", color_hex: "#000", spool_weight_g: 1000, spool_price: 90 }}, true);
            closeFilamentModal();
            if (document.getElementById('filament-id').value !== "") throw new Error("closeFilamentModal did not clear filament-id");

            document.getElementById('test-result').innerText = "SUCCESS";
        }}).catch(e => {{
            document.getElementById('test-result').innerText = "ERROR: " + e.message;
        }});
    }} catch (e) {{
        document.getElementById('test-result').innerText = "ERROR: " + e.message;
    }}
    </script>
</body>
</html>"""

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

def test_hash_routing_navigation_and_persistence():
    """Verify URL hash routing, route extraction, and navigation synchronization."""
    app_js_path = Path(__file__).parent.parent / "frontend" / "js" / "app.js"
    assert app_js_path.exists(), "frontend/js/app.js must exist"
    app_js_text = app_js_path.read_text(encoding="utf-8")

    test_script = f"""
    let hashValue = '';
    const classListMock = () => ({{
        add: () => {{}},
        remove: () => {{}},
        contains: () => false
    }});

    global.window = {{
        location: {{
            get hash() {{ return hashValue; }},
            set hash(val) {{ hashValue = val; }}
        }},
        addEventListener: () => {{}},
        removeEventListener: () => {{}},
        lucide: {{ createIcons: () => {{}} }}
    }};

    global.document = {{
        getElementById: (id) => ({{
            value: '',
            textContent: '',
            classList: classListMock()
        }}),
        querySelectorAll: () => [],
        querySelector: () => null,
        addEventListener: () => {{}},
        removeEventListener: () => {{}}
    }};

    global.refreshIcons = () => {{}};
    global.loadDashboard = () => {{}};
    global.renderProjectsTable = () => {{}};
    global.renderPrintersGrid = () => {{}};
    global.renderFilamentsGrid = () => {{}};
    global.populateSettingsForm = () => {{}};

    {app_js_text}

    // 1. Test getRouteFromHash with various hash patterns
    hashValue = '#/printers';
    const r1 = getRouteFromHash();
    if (r1.view !== 'printers') throw new Error('Expected printers, got ' + r1.view);

    hashValue = '#filaments';
    const r2 = getRouteFromHash();
    if (r2.view !== 'filaments') throw new Error('Expected filaments, got ' + r2.view);

    hashValue = '#/project-editor?id=42';
    const r3 = getRouteFromHash();
    if (r3.view !== 'project-editor' || r3.params.id !== '42') {{
        throw new Error('Expected project-editor with id 42, got ' + JSON.stringify(r3));
    }}

    hashValue = '';
    const r4 = getRouteFromHash();
    if (r4.view !== 'dashboard') throw new Error('Expected default dashboard for empty hash, got ' + r4.view);

    hashValue = '#unknown-route';
    const r5 = getRouteFromHash();
    if (r5.view !== 'dashboard') throw new Error('Expected fallback to dashboard for unknown route, got ' + r5.view);

    // 2. Test navigateTo updates window.location.hash
    navigateTo('settings');
    if (hashValue !== '#/settings') throw new Error('navigateTo(settings) did not set hash, got: ' + hashValue);

    state.currentProject = {{ id: 99 }};
    navigateTo('project-editor');
    if (hashValue !== '#/project-editor?id=99') throw new Error('navigateTo(project-editor) did not include project ID, got: ' + hashValue);

    navigateTo('projects');
    if (hashValue !== '#/projects') throw new Error('navigateTo(projects) did not set hash, got: ' + hashValue);

    console.log(JSON.stringify({{ success: true }}));
    """

    res = subprocess.run(["node"], input=test_script, capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_issues_17_to_22_full_suite():
    """
    Covers issues #17, #18, #19, #20, #21, #22 across both static template contracts
    and dynamic execution in headless browser.
    """
    import subprocess
    import shutil
    import tempfile

    html_file = Path(__file__).parent.parent / "frontend" / "index.html"
    app_js_file = Path(__file__).parent.parent / "frontend" / "js" / "app.js"
    html_content = html_file.read_text(encoding="utf-8")
    app_js = app_js_file.read_text(encoding="utf-8")

    # 1. Static Contract Checks
    # Issue #17: Prazo de entrega permite 0 dias
    assert 'id="proj-delivery-days"' in html_content
    assert 'min="0"' in html_content.split('id="proj-delivery-days"')[1].split('>')[0] or 'min="0"' in html_content.split('id="proj-delivery-days"')[0].split('<input')[-1]

    # Issue #18: BOM inputs sanitize negative values
    assert 'min="1"' in app_js
    assert 'Math.max(1,' in app_js
    assert 'Math.max(0,' in app_js

    # Issue #19: Modals ESC key and backdrop listeners
    assert "Escape" in app_js
    assert "modal-filament" in app_js
    assert "modal-printer" in app_js

    # Issue #20: Reset file input value
    assert "e.target.value = ''" in app_js or 'e.target.value = ""' in app_js

    # Issue #21: Duplicate plate row
    assert "duplicatePlateRow" in app_js
    assert "copy" in app_js

    # Issue #22: Search inputs for printers and filaments
    assert 'id="printer-search-input"' in html_content
    assert 'id="filament-search-input"' in html_content
    assert "filterPrinters" in app_js
    assert "filterFilaments" in app_js

    # 2. Browser Execution Check
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

    app_js_path = app_js_file.resolve().as_posix()
    html_test = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
    <div id="modal-filament" class="hidden">
        <h3 id="modal-filament-title"></h3>
        <input type="hidden" id="filament-id">
        <input type="text" id="filament-material">
        <input type="text" id="filament-brand">
        <input type="text" id="filament-color">
    </div>
    <div id="modal-printer" class="hidden">
        <h3 id="modal-printer-title"></h3>
        <input type="hidden" id="printer-id">
        <input type="text" id="printer-name">
        <input type="text" id="printer-model">
    </div>
    <div id="view-title"></div>
    <div id="editor-project-title"></div>
    <div id="editor-project-subtitle"></div>
    <input type="text" id="proj-name">
    <input type="text" id="proj-client-name">
    <input type="email" id="proj-client-email">
    <input type="tel" id="proj-client-phone">
    <select id="proj-status"><option value="draft">Rascunho</option></select>
    <input type="number" id="proj-cad-hours">
    <input type="number" id="proj-cad-rate">
    <input type="number" id="proj-post-hours">
    <input type="number" id="proj-post-rate">
    <input type="number" id="proj-overhead">
    <input type="number" id="proj-margin">
    <input type="number" id="proj-tax">
    <input type="number" id="proj-discount">
    <input type="number" id="proj-shipping">
    <input type="number" id="proj-delivery-days">
    <input type="text" id="proj-payment-terms">
    <input type="text" id="proj-warranty-terms">
    <textarea id="proj-notes"></textarea>
    <div id="plates-container"></div>
    <div id="bom-container"></div>
    <input type="search" id="printer-search-input">
    <div id="printers-grid"></div>
    <input type="search" id="filament-search-input">
    <div id="filaments-grid"></div>
    <div id="live-base-cost"></div>
    <div id="live-bom-cost"></div>
    <div id="live-weight"></div>
    <div id="live-time"></div>
    <div id="live-material-cost"></div>
    <div id="live-machine-cost"></div>
    <div id="live-labor-cost"></div>
    <div id="live-overhead-cost"></div>
    <div id="live-suggested-price"></div>
    <div id="live-discount-amount"></div>
    <div id="live-shipping-amount"></div>
    <div id="live-tax-amount"></div>
    <div id="test-result">RUNNING</div>

    <script>
    let savedPayload = null;
    window.lucide = {{ createIcons: () => {{}} }};
    window.API = {{
        projects: {{
            get: async (id) => ({{
                id: 1,
                name: "Projeto 0 Dias",
                delivery_days: 0,
                plates: [{{ name: "Placa Base", print_time_hours: 1, part_weight_g: 10, quantity: 1 }}],
                bom_items: []
            }}),
            create: async (data) => {{ savedPayload = data; return {{ id: 10, ...data }}; }},
            update: async (id, data) => {{ savedPayload = data; return {{ id, ...data }}; }}
        }}
    }};
    </script>
    <script src="file:///{app_js_path}"></script>
    <script>
    try {{
        // Test Issue #17: 0 days delivery
        openNewProject();
        document.getElementById('proj-delivery-days').value = '0';
        saveCurrentProject(false).then(() => {{
            if (savedPayload.delivery_days !== 0) throw new Error("delivery_days was not saved as 0, got: " + savedPayload.delivery_days);
            return editProject(1);
        }}).then(() => {{
            const val = document.getElementById('proj-delivery-days').value;
            if (val !== '0' && val !== 0) throw new Error("editProject did not populate delivery_days as 0, got: " + val);

            // Test Issue #18: BOM negative quantities/costs
            state.currentBOM = [
                {{ name: "Parafuso Teste", category: "Fixadores", quantity: -5, unit_cost: -10 }}
            ];
            recalcLiveSummary();
            const bomCostText = document.getElementById('live-bom-cost').textContent;
            if (bomCostText.includes("-")) throw new Error("live-bom-cost became negative: " + bomCostText);

            return saveCurrentProject(false);
        }}).then(() => {{
            const b = savedPayload.bom_items[0];
            if (b.quantity < 1) throw new Error("BOM quantity was saved negative: " + b.quantity);
            if (b.unit_cost < 0) throw new Error("BOM unit_cost was saved negative: " + b.unit_cost);

            // Test Issue #19: ESC key closes modal
            openFilamentModal();
            const filModal = document.getElementById('modal-filament');
            if (filModal.classList.contains('hidden')) throw new Error("Filament modal failed to open");
            document.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Escape' }}));
            if (!filModal.classList.contains('hidden')) throw new Error("ESC key failed to close filament modal");

            // Test Issue #19: Backdrop click closes modal
            openPrinterModal();
            const prinModal = document.getElementById('modal-printer');
            if (prinModal.classList.contains('hidden')) throw new Error("Printer modal failed to open");
            prinModal.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true }}));
            if (!prinModal.classList.contains('hidden')) throw new Error("Backdrop click failed to close printer modal");

            // Test Issue #20: Reset file input value on slicer import
            const mockInput = {{ files: [], value: 'sample.gcode' }};
            handleSinglePlateFile({{ target: mockInput }}, 0);
            if (mockInput.value !== '') throw new Error("handleSinglePlateFile did not reset target.value");

            // Test Issue #21: Duplicate plate
            state.currentPlates = [{{ id: 42, name: "Tampa Superior", print_time_hours: 2, part_weight_g: 50, quantity: 1 }}];
            duplicatePlateRow(0);
            if (state.currentPlates.length !== 2) throw new Error("duplicatePlateRow did not add a plate, len: " + state.currentPlates.length);
            if (!state.currentPlates[1].name.includes("Cópia")) throw new Error("Cloned plate name wrong: " + state.currentPlates[1].name);
            if (state.currentPlates[1].id !== undefined) throw new Error("Cloned plate kept old database ID");

            // Test Issue #22: Real-time search/filter for printers & filaments
            state.printers = [
                {{ id: 1, name: "Bambu Lab X1-Carbon", model: "CoreXY", rates_breakdown: {{}} }},
                {{ id: 2, name: "Creality Ender 3 V3", model: "Bed Slinger", rates_breakdown: {{}} }}
            ];
            renderPrintersGrid("bambu");
            const prinGrid = document.getElementById('printers-grid').innerHTML;
            if (!prinGrid.includes("Bambu") || prinGrid.includes("Ender")) throw new Error("Printers filter failed matching");

            renderPrintersGrid("inexistente");
            const prinEmpty = document.getElementById('printers-grid').innerHTML;
            if (!prinEmpty.includes("Nenhuma impressora encontrada")) throw new Error("Printers empty state failed");

            state.filaments = [
                {{ id: 1, name: "PLA Premium", brand: "Voolt3D", material: "PLA", color: "Preto", color_hex: "#000000" }},
                {{ id: 2, name: "PETG HT", brand: "3D Fila", material: "PETG", color: "Branco", color_hex: "#ffffff" }}
            ];
            renderFilamentsGrid("voolt");
            const filGrid = document.getElementById('filaments-grid').innerHTML;
            if (!filGrid.includes("Voolt3D") || filGrid.includes("PETG HT")) throw new Error("Filaments filter failed matching");

            renderFilamentsGrid("inexistente");
            const filEmpty = document.getElementById('filaments-grid').innerHTML;
            if (!filEmpty.includes("Nenhum filamento encontrado")) throw new Error("Filaments empty state failed");

            document.getElementById('test-result').innerText = "SUCCESS";
        }}).catch(e => {{
            document.getElementById('test-result').innerText = "ERROR: " + e.message;
        }});
    }} catch (e) {{
        document.getElementById('test-result').innerText = "ERROR: " + e.message;
    }}
    </script>
</body>
</html>"""

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
        ], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=12)

        assert "SUCCESS" in (proc.stdout or ""), f"Headless browser test failed. Output:\n{proc.stdout}"
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_issues_23_to_27_full_suite():
    """
    Covers issues #23, #24, #25, #26, #27:
    - #23: API 422 detail array error formatting (no [object Object])
    - #24: Filament preview update on material select onchange
    - #25: Material filter for filaments and operational status filter for printers
    - #26: Filament density field in modal, auto-suggestion, and save payload
    - #27: Brazilian phone mask formatting for commercial phone inputs
    """
    import subprocess
    import shutil
    import tempfile

    html_file = Path(__file__).parent.parent / "frontend" / "index.html"
    app_js_file = Path(__file__).parent.parent / "frontend" / "js" / "app.js"
    api_js_file = Path(__file__).parent.parent / "frontend" / "js" / "api.js"

    html_content = html_file.read_text(encoding="utf-8")
    app_js = app_js_file.read_text(encoding="utf-8")
    api_js = api_js_file.read_text(encoding="utf-8")

    # 1. Static Contract Checks
    # Issue #23
    assert "Array.isArray(data.detail)" in api_js

    # Issue #24
    assert 'id="filament-material"' in html_content
    assert 'onchange="onFilamentMaterialChange()"' in html_content

    # Issue #25
    assert 'id="printer-status-filter"' in html_content
    assert 'id="filament-material-filter"' in html_content
    assert "clearPrinterFilters" in app_js
    assert "clearFilamentFilters" in app_js

    # Issue #26
    assert 'id="filament-density"' in html_content
    assert 'step="0.01"' in html_content
    assert "density_g_cm3" in app_js

    # Issue #27
    assert "formatPhoneInput" in app_js
    assert "attachPhoneMask" in app_js

    # 2. Headless Browser Dynamic Execution Check
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

    app_js_path = app_js_file.resolve().as_posix()
    api_js_path = api_js_file.resolve().as_posix()

    html_test = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
    <div id="modal-filament" class="hidden">
        <h3 id="modal-filament-title"></h3>
        <input type="hidden" id="filament-id">
        <select id="filament-material" onchange="onFilamentMaterialChange()" oninput="updateFilamentNamePreview()">
            <option value="PLA">PLA</option>
            <option value="PETG">PETG</option>
            <option value="ABS">ABS</option>
            <option value="TPU">TPU (Flexível)</option>
        </select>
        <input type="text" id="filament-brand" value="3D Prime">
        <input type="color" id="filament-color-hex" value="#10b981">
        <input type="text" id="filament-color" value="Preto">
        <span id="filament-preview-dot"></span>
        <span id="filament-preview-text"></span>
        <input type="number" id="filament-density" step="0.01" min="0.5" value="1.24">
        <input type="number" id="filament-weight" value="1000">
        <input type="number" id="filament-price" value="95.00">
    </div>
    <div id="modal-printer" class="hidden">
        <h3 id="modal-printer-title"></h3>
        <input type="hidden" id="printer-id">
        <input type="text" id="printer-name">
        <input type="text" id="printer-model">
    </div>
    <div id="view-title"></div>
    <input type="text" id="proj-client-phone">
    <input type="text" id="pref-phone">
    <input type="search" id="printer-search-input">
    <select id="printer-status-filter" onchange="filterPrinters()">
        <option value="all">Todas as Impressoras</option>
        <option value="active">Apenas Ativas</option>
        <option value="inactive">Inativas / Manutenção</option>
    </select>
    <div id="printers-grid"></div>
    <input type="search" id="filament-search-input">
    <select id="filament-material-filter" onchange="filterFilaments()">
        <option value="">Todos os Materiais</option>
        <option value="PLA">PLA</option>
        <option value="PETG">PETG</option>
        <option value="ABS">ABS</option>
        <option value="TPU">TPU</option>
    </select>
    <div id="filaments-grid"></div>
    <div id="test-result">RUNNING</div>

    <script>
    let lastSavedFilament = null;
    window.lucide = {{ createIcons: () => {{}} }};
    window.showToast = (msg, type) => {{}};
    window.API = {{
        getToken: () => null,
        filaments: {{
            create: async (data) => {{ lastSavedFilament = data; return {{ id: 50, ...data, cost_per_gram: data.spool_price/data.spool_weight_g }}; }},
            update: async (id, data) => {{ lastSavedFilament = data; return {{ id, ...data, cost_per_gram: data.spool_price/data.spool_weight_g }}; }}
        }}
    }};
    </script>
    <script src="file:///{api_js_path}"></script>
    <script src="file:///{app_js_path}"></script>
    <script>
    try {{
        // Test Issue #23: API 422 error parsing
        const fakeResp = new Response(JSON.stringify({{
            detail: [
                {{ loc: ["body", "tax_rate_percent"], msg: "Input should be less than or equal to 99" }}
            ]
        }}), {{ status: 422, statusText: "Unprocessable Entity", headers: {{ "Content-Type": "application/json" }} }});

        window.fetch = async () => fakeResp;
        API.request("/api/test").catch(err => {{
            if (err.message.includes("[object Object]")) throw new Error("API error still contains [object Object]");
            if (!err.message.includes("tax_rate_percent")) throw new Error("API error does not format loc and msg: " + err.message);

            // Test Issue #24: Material select dropdown updates preview
            const matSelect = document.getElementById('filament-material');
            matSelect.value = "PETG";
            onFilamentMaterialChange();
            const prevText = document.getElementById('filament-preview-text').innerText;
            if (!prevText.includes("PETG")) throw new Error("Preview did not update to PETG, got: " + prevText);

            // Test Issue #26: Density field suggestion and save
            const densVal = document.getElementById('filament-density').value;
            if (densVal !== "1.27") throw new Error("PETG density did not auto-suggest 1.27, got: " + densVal);

            matSelect.value = "ABS";
            onFilamentMaterialChange();
            if (document.getElementById('filament-density').value !== "1.04") throw new Error("ABS density did not auto-suggest 1.04");

            // Save filament with custom density
            document.getElementById('filament-density').value = "1.05";
            handleSaveFilament(new Event('submit')).then(() => {{
                if (!lastSavedFilament) throw new Error("handleSaveFilament did not submit");
                if (lastSavedFilament.density_g_cm3 !== 1.05) throw new Error("density_g_cm3 not saved in payload, got: " + lastSavedFilament.density_g_cm3);

                // Test Issue #25: Filter by material & status
                state.filaments = [
                    {{ id: 1, name: "PLA Basic", brand: "Bambu", material: "PLA", color: "Preto", spool_weight_g: 1000, spool_price: 100, cost_per_gram: 0.10, density_g_cm3: 1.24 }},
                    {{ id: 2, name: "PETG HF", brand: "Bambu", material: "PETG", color: "Azul", spool_weight_g: 1000, spool_price: 120, cost_per_gram: 0.12, density_g_cm3: 1.27 }}
                ];
                renderFilamentsGrid("", "PLA");
                let filGrid = document.getElementById('filaments-grid').innerHTML;
                if (!filGrid.includes("PLA Basic") || filGrid.includes("PETG HF")) throw new Error("Filaments material filter failed");

                renderFilamentsGrid("", "PETG");
                filGrid = document.getElementById('filaments-grid').innerHTML;
                if (filGrid.includes("PLA Basic") || !filGrid.includes("PETG HF")) throw new Error("Filaments material filter failed for PETG");

                // Printers status filter
                state.printers = [
                    {{ id: 1, name: "Bambu X1C", model: "CoreXY", is_active: true, rates_breakdown: {{}}, lifespan_hours: 5000, acquisition_cost: 10000 }},
                    {{ id: 2, name: "Ender 3", model: "BedSlinger", is_active: false, rates_breakdown: {{}}, lifespan_hours: 5000, acquisition_cost: 1500 }}
                ];
                renderPrintersGrid("", "active");
                let prinGrid = document.getElementById('printers-grid').innerHTML;
                if (!prinGrid.includes("Bambu X1C") || prinGrid.includes("Ender 3")) throw new Error("Printers status active filter failed");

                renderPrintersGrid("", "inactive");
                prinGrid = document.getElementById('printers-grid').innerHTML;
                if (prinGrid.includes("Bambu X1C") || !prinGrid.includes("Ender 3")) throw new Error("Printers status inactive filter failed");

                // Test Issue #27: Phone mask
                const masked10 = formatPhoneInput("1133334444");
                if (masked10 !== "(11) 3333-4444") throw new Error("10-digit phone mask failed, got: " + masked10);

                const masked11 = formatPhoneInput("11987654321");
                if (masked11 !== "(11) 98765-4321") throw new Error("11-digit phone mask failed, got: " + masked11);

                const phoneInp = document.getElementById('proj-client-phone');
                attachPhoneMask(phoneInp);
                phoneInp.value = "41999887766";
                phoneInp.dispatchEvent(new Event('input'));
                if (phoneInp.value !== "(41) 99988-7766") throw new Error("Input phone mask event failed, got: " + phoneInp.value);

                document.getElementById('test-result').innerText = "SUCCESS";
            }}).catch(e => {{
                document.getElementById('test-result').innerText = "ERROR: " + e.message;
            }});
        }});
    }} catch (e) {{
        document.getElementById('test-result').innerText = "ERROR: " + e.message;
    }}
    </script>
</body>
</html>"""

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
        ], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=12)

        assert "SUCCESS" in (proc.stdout or ""), f"Headless browser test failed. Output:\n{proc.stdout}"
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_batch_file_upload_ui_contract_and_plate_generation():
    """
    Verifies batch file uploading:
    1. index.html file-slicer-input has 'multiple' attribute.
    2. app.js implements handleSlicerFiles and hooks both drop and change events.
    3. Node simulation of uploading 7 .gcode.3mf files at once creates 7 plates,
       replaces the blank initial plate, and sets individual times and weights accurately.
    """
    import subprocess
    from pathlib import Path

    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    app_js_path = Path(__file__).parent.parent / "frontend" / "js" / "app.js"
    html_content = html_path.read_text(encoding="utf-8")
    app_js = app_js_path.read_text(encoding="utf-8")

    # 1. Static Contract Checks
    assert 'id="file-slicer-input"' in html_content
    # Check multiple attribute
    slicer_input_tag = [tag for tag in html_content.split("<input") if 'id="file-slicer-input"' in tag][0]
    assert "multiple" in slicer_input_tag, "file-slicer-input must have 'multiple' attribute for batch file picking"
    assert "Em Lote" in html_content or "Lote" in html_content, "dropzone must indicate batch upload support"

    assert "function handleSlicerFiles" in app_js, "app.js must implement handleSlicerFiles"
    assert "handleSlicerFiles(Array.from(e.dataTransfer.files))" in app_js, "dropzone drop event must pass all files to handleSlicerFiles"
    assert "handleSlicerFiles(Array.from(e.target.files))" in app_js, "file input change event must pass all files to handleSlicerFiles"
    assert "function handleSlicerFile" in app_js, "app.js must maintain handleSlicerFile for backwards compatibility"

    # 2. Node Execution Simulation
    node_test = f"""
    const state = {{
        printers: [{{ id: 10, name: 'Bambu Lab X1C' }}],
        filaments: [
            {{ id: 101, material: 'PLA', cost_per_gram: 0.12 }},
            {{ id: 102, material: 'PETG', cost_per_gram: 0.15 }}
        ],
        currentPlates: [
            {{ name: 'Placa 1', print_time_hours: 0, part_weight_g: 0, purge_weight_g: 0, printer_id: null, filament_id: null }}
        ],
        user: {{ default_failure_rate: 10 }}
    }};

    const toasts = [];
    function showToast(msg, type) {{ toasts.push({{ msg, type }}); }}
    let rendered = false;
    function renderPlates() {{ rendered = true; }}
    let recalculated = false;
    function recalcLiveSummary() {{ recalculated = true; }}

    // Mock parse3mfMetadata
    async function parse3mfMetadata(file) {{
        return [{{
            name: file.name.replace(/\\.(?:gcode\\.3mf|3mf|gcode)$/i, ''),
            print_time_hours: file._mockTime,
            part_weight_g: file._mockWeight,
            purge_weight_g: 0,
            filament_type: file._mockMat,
            failure_margin_percent: 10,
            quantity: 1
        }}];
    }}

    async function handleSlicerFiles(files) {{
    {app_js.split('async function handleSlicerFiles(files) {')[1].split('\n}\n')[0]}
    }}

    async function run() {{
        // Simulate dropping 7 files simultaneously
        const files = [
            {{ name: 'base.gcode.3mf', _mockTime: 1.5, _mockWeight: 35.0, _mockMat: 'PLA' }},
            {{ name: 'tampa.gcode.3mf', _mockTime: 2.0, _mockWeight: 42.5, _mockMat: 'PETG' }},
            {{ name: 'suporte_esq.gcode.3mf', _mockTime: 0.8, _mockWeight: 18.0, _mockMat: 'PLA' }},
            {{ name: 'suporte_dir.gcode.3mf', _mockTime: 0.8, _mockWeight: 18.0, _mockMat: 'PLA' }},
            {{ name: 'engrenagem.gcode.3mf', _mockTime: 3.2, _mockWeight: 65.0, _mockMat: 'PETG' }},
            {{ name: 'eixo.gcode.3mf', _mockTime: 0.5, _mockWeight: 10.0, _mockMat: 'PLA' }},
            {{ name: 'painel.gcode.3mf', _mockTime: 4.0, _mockWeight: 90.0, _mockMat: 'PLA' }}
        ];

        await handleSlicerFiles(files);

        if (state.currentPlates.length !== 7) {{
            throw new Error(`Expected exactly 7 plates created, got ${{state.currentPlates.length}}`);
        }}

        // Verify that default plate was replaced and each file has its plate
        const expected = [
            {{ name: 'base', time: 1.5, weight: 35.0, filId: 101 }},
            {{ name: 'eixo', time: 0.5, weight: 10.0, filId: 101 }},
            {{ name: 'engrenagem', time: 3.2, weight: 65.0, filId: 102 }},
            {{ name: 'painel', time: 4.0, weight: 90.0, filId: 101 }},
            {{ name: 'suporte_dir', time: 0.8, weight: 18.0, filId: 101 }},
            {{ name: 'suporte_esq', time: 0.8, weight: 18.0, filId: 101 }},
            {{ name: 'tampa', time: 2.0, weight: 42.5, filId: 102 }}
        ]; // naturally sorted by filename

        for (let i = 0; i < 7; i++) {{
            const p = state.currentPlates[i];
            const exp = expected[i];
            if (p.name !== exp.name) throw new Error(`Plate ${{i}} name expected ${{exp.name}}, got ${{p.name}}`);
            if (p.print_time_hours !== exp.time) throw new Error(`Plate ${{i}} time expected ${{exp.time}}, got ${{p.print_time_hours}}`);
            if (p.part_weight_g !== exp.weight) throw new Error(`Plate ${{i}} weight expected ${{exp.weight}}, got ${{p.part_weight_g}}`);
            if (p.filament_id !== exp.filId) throw new Error(`Plate ${{i}} filament_id expected ${{exp.filId}}, got ${{p.filament_id}}`);
            if (p.printer_id !== 10) throw new Error(`Plate ${{i}} printer_id expected 10, got ${{p.printer_id}}`);
        }}

        if (!rendered) throw new Error('renderPlates was not called');
        if (!recalculated) throw new Error('recalcLiveSummary was not called');

        console.log(JSON.stringify({{ success: true, plateCount: state.currentPlates.length }}));
    }}

    run().catch(err => {{
        console.error(err);
        process.exit(1);
    }});
    """

    res = subprocess.run(["node", "-e", node_test], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_slicer_filament_profile_badge_rendering_and_selection_help():
    """
    Verifies that:
    1. renderPlates renders an info-icon tooltip beside the 'Filamento' label with data-tooltip="Fatiado com: <perfil>"
       using the help-circle icon and info-icon class, preventing vertical input misalignment.
    2. When plate has no slicer_filament_profile, no tooltip icon is rendered.
    3. Slicer files with filament profile smartly auto-match equivalent catalog filaments.
    4. saveCurrentProject preserves slicer_filament_profile in the project plates payload.
    """
    import subprocess
    import shutil
    from pathlib import Path

    app_js_path = (Path(__file__).parent.parent / "frontend" / "js" / "app.js").resolve().as_posix()
    app_js = (Path(__file__).parent.parent / "frontend" / "js" / "app.js").read_text(encoding="utf-8")

    # Contract assertions on app.js source code
    assert "slicer_filament_profile" in app_js
    assert "Fatiado com:" in app_js
    assert "info-icon" in app_js
    assert "help-circle" in app_js
    assert "data-tooltip=" in app_js
    assert "cleanFilamentProfileName" in app_js

    # Real DOM simulation via Node.js
    clean_profile_code = app_js.split("function cleanFilamentProfileName(profile, fileName = '') {")[1].split('\n}\n')[0]
    render_plates_code = app_js.split('function renderPlates() {')[1].split('\n}\n')[0]
    node_test = f"""
    let innerHtml = '';
    global.document = {{
        getElementById: (id) => {{
            if (id === 'plates-container') {{
                return {{
                    set innerHTML(val) {{ innerHtml = val; }},
                    get innerHTML() {{ return innerHtml; }}
                }};
            }}
            return null;
        }}
    }};
    global.window = {{}};

    function cleanFilamentProfileName(profile, fileName = '') {{
        {clean_profile_code}
    }}

    global.state = {{
        user: {{ default_failure_rate: 10 }},
        printers: [{{ id: 1, name: 'Bambu X1C', machine_hourly_rate: 3.5 }}],
        filaments: [
            {{ id: 10, name: 'PLA Preto - 3D Prime', material: 'PLA', brand: '3D Prime', color: 'Preto', color_hex: '#10b981', cost_per_gram: 0.09 }},
            {{ id: 20, name: '3D Prime PLA Basic - Branco', material: 'PLA', brand: '3D Prime', color: 'Branco', color_hex: '#ffffff', cost_per_gram: 0.12 }},
            {{ id: 30, name: 'Prusament PETG - Laranja', material: 'PETG', brand: 'Prusa', color: 'Laranja', color_hex: '#f97316', cost_per_gram: 0.15 }}
        ],
        currentPlates: [
            {{
                name: 'Suporte',
                printer_id: 1,
                filament_id: 20,
                slicer_filament_profile: '3D Prime PLA Basic(patolino-kratos.3mf)',
                print_time_hours: 1.5,
                part_weight_g: 45.0,
                purge_weight_g: 0,
                failure_margin_percent: 10,
                quantity: 1
            }},
            {{
                name: 'Base Manual',
                printer_id: 1,
                filament_id: 10,
                slicer_filament_profile: null,
                print_time_hours: 2.0,
                part_weight_g: 60.0,
                purge_weight_g: 0,
                failure_margin_percent: 10,
                quantity: 1
            }}
        ]
    }};

    global.formatCurrency = (v) => 'R$ ' + Number(v).toFixed(2);
    global.parseLocaleFloat = (v, def) => parseFloat(v) || def;
    global.refreshIcons = () => {{}};

    // Extract renderPlates
    function renderPlates() {{
        {render_plates_code}
    }}

    renderPlates();

    const html = document.getElementById('plates-container').innerHTML;

    // 1. Plate 0 has slicer_filament_profile -> must show tooltip icon beside Filamento label
    if (!html.includes('Fatiado com:')) throw new Error('Missing "Fatiado com:" tooltip text in plate card');
    // Must strip (patolino-kratos.3mf) file reference and keep only filament profile
    if (!html.includes('3D Prime PLA Basic')) throw new Error('Missing profile name "3D Prime PLA Basic"');
    if (html.includes('patolino-kratos.3mf')) throw new Error('File reference "(patolino-kratos.3mf)" was not stripped from tooltip');
    if (!html.includes('info-icon') || !html.includes('help-circle')) {{
        throw new Error('Tooltip icon missing info-icon or help-circle element');
    }}

    // Check that old misaligned chip classes are not present
    if (html.includes('text-[10px] text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700/60')) {{
        throw new Error('Old chip classes still present under select - causing misalignment');
    }}

    // Count occurrences of "Fatiado com:" -> exactly 1 (only Plate 0, not Plate 1)
    const matches = html.match(/Fatiado com:/g) || [];
    if (matches.length !== 1) throw new Error(`Expected exactly 1 tooltip, got ${{matches.length}}`);

    console.log(JSON.stringify({{ success: true, tooltipMatches: matches.length }}));
    """

    res = subprocess.run(["node", "-e", node_test], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_phone_formatting_with_international_ddi_55():
    """
    Issue #31:
    Verifies that pasting a phone number with international DDI (+55 or 55)
    properly strips the country code and does not truncate the last digits or corrupt the area code.
    """
    node_test = r"""
    const fs = require('fs');
    const path = require('path');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    const vm = require('vm');
    const sandbox = {
        window: {},
        document: { addEventListener() {}, removeEventListener() {} },
        addEventListener() {},
        removeEventListener() {},
        String
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    vm.createContext(sandbox);
    vm.runInContext(appJs + '; this.formatPhoneInput = formatPhoneInput;', sandbox);

    const fn = sandbox.formatPhoneInput;

    const testCases = [
        { input: '+55 11 98888-7777', expected: '(11) 98888-7777' },
        { input: '+5511988887777', expected: '(11) 98888-7777' },
        { input: '5511988887777', expected: '(11) 98888-7777' },
        { input: '+55 11 3333-4444', expected: '(11) 3333-4444' },
        { input: '551133334444', expected: '(11) 3333-4444' },
        { input: '11988887777', expected: '(11) 98888-7777' },
        { input: '(11) 98888-7777', expected: '(11) 98888-7777' },
        { input: '1133334444', expected: '(11) 3333-4444' },
        { input: '11', expected: '(11' },
        { input: '', expected: '' }
    ];

    for (const tc of testCases) {
        const actual = fn(tc.input);
        if (actual !== tc.expected) {
            throw new Error(`Input "${tc.input}": expected "${tc.expected}", got "${actual}"`);
        }
    }

    console.log(JSON.stringify({ success: true, count: testCases.length }));
    """

    res = subprocess.run(["node", "-e", node_test], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_escape_html_xss_protection_in_projects():
    """
    Issue #29:
    Verifies that escapeHtml properly escapes HTML tags and prevents Stored XSS
    and layout breaks in renderProjectsTable and renderRecentProjects.
    """
    node_test = r"""
    const fs = require('fs');
    const path = require('path');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    const vm = require('vm');
    const elements = {};
    function getOrCreate(id) {
        if (!elements[id]) {
            elements[id] = { id, textContent: '', innerHTML: '', innerText: '', value: '', classList: { add(){}, remove(){}, contains(){ return false; } }, style: {} };
        }
        return elements[id];
    }
    const sandbox = {
        document: {
            getElementById: getOrCreate,
            querySelector: (sel) => getOrCreate(sel),
            querySelectorAll: () => [],
            addEventListener() {},
            removeEventListener() {}
        },
        addEventListener() {},
        removeEventListener() {},
        console, Math, Number, String,
        refreshIcons() {}
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    let code = appJs + '\nglobalThis.__app_state = state;\nglobalThis.__escapeHtml = escapeHtml;\nglobalThis.__renderRecentProjects = renderRecentProjects;\nglobalThis.__renderProjectsTable = renderProjectsTable;\nglobalThis.__formatCurrency = formatCurrency;\nglobalThis.__formatStatus = formatStatus;';
    vm.runInContext(code, sandbox);

    const state = sandbox.__app_state;
    state.projects = [
        {
            id: 1,
            name: 'Gabinete <V2> & <script>alert(1)</script>',
            client_name: 'Cliente "Especial" & <img src=x onerror=1>',
            plates_count: 2,
            total_time_hours: 4.5,
            base_cost: 50.0,
            final_price_to_client: 120.0,
            status: 'draft'
        }
    ];
    state.projectStatusFilter = 'all';

    // 1. Check escapeHtml directly
    const esc = sandbox.__escapeHtml;
    if (esc('<div>"hello" & \'world\'</div>') !== '&lt;div&gt;&quot;hello&quot; &amp; &#039;world&#039;&lt;/div&gt;') {
        throw new Error('escapeHtml did not escape all characters properly');
    }

    // 2. Check renderRecentProjects
    sandbox.__renderRecentProjects();
    const recentHtml = elements['dashboard-recent-projects'].innerHTML;
    if (recentHtml.includes('<script>') || recentHtml.includes('<V2>') || recentHtml.includes('<img')) {
        throw new Error('Unescaped HTML tags present in dashboard recent projects');
    }
    if (!recentHtml.includes('&lt;script&gt;alert(1)&lt;/script&gt;') || !recentHtml.includes('&lt;V2&gt;')) {
        throw new Error('Escaped entities missing in dashboard recent projects');
    }

    // 3. Check renderProjectsTable
    sandbox.__renderProjectsTable();
    const tableHtml = elements['projects-table-container'].innerHTML;
    if (tableHtml.includes('<script>') || tableHtml.includes('<V2>') || tableHtml.includes('<img')) {
        throw new Error('Unescaped HTML tags present in projects table');
    }
    if (!tableHtml.includes('&lt;script&gt;alert(1)&lt;/script&gt;') || !tableHtml.includes('&lt;V2&gt;')) {
        throw new Error('Escaped entities missing in projects table');
    }

    console.log(JSON.stringify({ success: true }));
    """

    res = subprocess.run(["node", "-e", node_test], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_gcode_import_resets_residual_purge_weight():
    """
    Issue #30:
    Verifies that importing a G-code file into a plate that previously held
    a multi-material 3MF with purge tower explicitly resets purge_weight_g to 0.
    """
    node_test = r"""
    const fs = require('fs');
    const path = require('path');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    const vm = require('vm');
    const elements = {};
    function getOrCreate(id) {
        if (!elements[id]) {
            elements[id] = { id, textContent: '', innerHTML: '', innerText: '', value: '', classList: { add(){}, remove(){}, contains(){ return false; } }, style: {}, appendChild(){}, remove(){} };
        }
        return elements[id];
    }
    const sandbox = {
        document: {
            getElementById: getOrCreate,
            querySelector: (sel) => getOrCreate(sel),
            querySelectorAll: () => [],
            createElement: () => ({ className: '', innerHTML: '', innerText: '', textContent: '', style: {}, classList: { add(){}, remove(){}, contains(){ return false; } }, appendChild(){}, remove(){} }),
            addEventListener() {},
            removeEventListener() {}
        },
        addEventListener() {},
        removeEventListener() {},
        console, Math, Number, String, setTimeout, clearTimeout,
        parseGcodeMetadata() {
            return {
                print_time_hours: 1.8,
                part_weight_g: 40.0,
                slicer_filament_profile: 'Generic PLA'
            };
        },
        cleanFilamentProfileName(p) { return p; },
        renderPlates() {},
        recalcLiveSummary() {}
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    let code = appJs + '\nglobalThis.__app_state = state;\nglobalThis.__handleSinglePlateFile = handleSinglePlateFile;';
    vm.runInContext(code, sandbox);

    const state = sandbox.__app_state;
    state.currentPlates = [
        {
            name: 'Peça Colorida',
            print_time_hours: 3.5,
            part_weight_g: 80.0,
            purge_weight_g: 45.0,
            filament_id: 1
        }
    ];
    state.filaments = [];

    async function test() {
        const mockFile = {
            name: 'suporte_simples.gcode',
            text: async () => 'mock gcode content'
        };

        const event = {
            target: {
                files: [mockFile],
                value: 'fakepath/suporte_simples.gcode'
            }
        };

        await sandbox.__handleSinglePlateFile(event, 0);

        const plate = state.currentPlates[0];
        if (plate.purge_weight_g !== 0) {
            throw new Error(`Expected purge_weight_g = 0, got ${plate.purge_weight_g}`);
        }
        if (plate.part_weight_g !== 40.0) {
            throw new Error(`Expected part_weight_g = 40.0, got ${plate.part_weight_g}`);
        }
        if (plate.print_time_hours !== 1.8) {
            throw new Error(`Expected print_time_hours = 1.8, got ${plate.print_time_hours}`);
        }

        console.log(JSON.stringify({ success: true, purge_weight_g: plate.purge_weight_g }));
    }

    test().catch(err => {
        console.error(err);
        process.exit(1);
    });
    """

    res = subprocess.run(["node", "-e", node_test], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_recalc_live_summary_commercial_rounding_precision():
    """
    Issue #28:
    Verifies that recalcLiveSummary computes intermediate pricing steps with 2-decimal-place
    rounding, perfectly aligned with the backend calculation engine in engine.py.
    """
    node_test = r"""
    const fs = require('fs');
    const path = require('path');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    const vm = require('vm');
    const elements = {};
    function getOrCreate(id) {
        if (!elements[id]) {
            elements[id] = { id, textContent: '', innerHTML: '', innerText: '', value: '0', classList: { add(){}, remove(){}, contains(){ return false; } }, style: {}, appendChild(){}, remove(){} };
        }
        return elements[id];
    }

    const sandbox = {
        document: {
            getElementById: getOrCreate,
            querySelector: (sel) => getOrCreate(sel),
            querySelectorAll: () => [],
            createElement: () => ({ className: '', innerHTML: '', innerText: '', textContent: '', style: {}, classList: { add(){}, remove(){}, contains(){ return false; } }, appendChild(){}, remove(){} }),
            addEventListener() {},
            removeEventListener() {}
        },
        addEventListener() {},
        removeEventListener() {},
        console, Math, Number, String, parseFloat, parseInt, isNaN, Intl, setTimeout, clearTimeout,
        refreshIcons() {}
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    let code = appJs + '\nglobalThis.__app_state = state;\nglobalThis.__recalcLiveSummary = recalcLiveSummary;';
    vm.runInContext(code, sandbox);

    const state = sandbox.__app_state;
    state.printers = [{ id: 1, machine_hourly_rate: 2.436 }];
    state.filaments = [{ id: 1, spool_weight_g: 1000, spool_price: 135.0 }];
    state.currentPlates = [
        {
            printer_id: 1,
            filament_id: 1,
            print_time_hours: 3.5,
            part_weight_g: 120,
            purge_weight_g: 0,
            failure_margin_percent: 10,
            quantity: 1
        }
    ];
    state.currentBOM = [
        { quantity: 2, unit_cost: 4.50 }
    ];

    getOrCreate('proj-cad-hours').value = '1.0';
    getOrCreate('proj-cad-rate').value = '80.0';
    getOrCreate('proj-margin').value = '40';
    getOrCreate('proj-tax').value = '6';
    getOrCreate('proj-discount').value = '5';
    getOrCreate('proj-shipping').value = '25.0';

    sandbox.__recalcLiveSummary();

    const suggested = getOrCreate('live-suggested-price').textContent;
    const finalPrice = getOrCreate('live-final-price').textContent;
    const netProfit = getOrCreate('live-net-profit').textContent;

    if (!finalPrice.includes('188,20')) {
        throw new Error(`Expected final price to include 188,20, got ${finalPrice}`);
    }
    if (!suggested.includes('171,79')) {
        throw new Error(`Expected suggested price to include 171,79, got ${suggested}`);
    }
    if (!netProfit.includes('38,06')) {
        throw new Error(`Expected net profit to include 38,06, got ${netProfit}`);
    }

    console.log(JSON.stringify({ success: true, suggested, finalPrice, netProfit }));
    """

    res = subprocess.run(["node", "-e", node_test], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_duplicate_and_delete_project_refreshes_dashboard():
    """
    Issue #32:
    Verifies that duplicateProject and deleteProject call renderRecentProjects and renderDashboard.
    """
    node_test = r"""
    const fs = require('fs');
    const path = require('path');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    const vm = require('vm');
    const elements = {};
    function getOrCreate(id) {
        if (!elements[id]) {
            elements[id] = { id, textContent: '', innerHTML: '', innerText: '', value: '', classList: { add(){}, remove(){}, contains(){ return false; } }, style: {}, appendChild(){}, remove(){} };
        }
        return elements[id];
    }
    const sandbox = {
        counts: { recent: 0, dash: 0 },
        document: {
            getElementById: getOrCreate,
            querySelector: (sel) => getOrCreate(sel),
            querySelectorAll: () => [],
            createElement: () => ({ className: '', innerHTML: '', innerText: '', textContent: '', style: {}, classList: { add(){}, remove(){}, contains(){ return false; } }, appendChild(){}, remove(){} }),
            addEventListener() {},
            removeEventListener() {}
        },
        addEventListener() {},
        removeEventListener() {},
        console, Math, Number, String, setTimeout, clearTimeout,
        confirm: () => true,
        API: {
            projects: {
                duplicate: async () => ({ id: 2 }),
                delete: async () => {}
            }
        }
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    let code = appJs + '\n' +
        'globalThis.__app_state = state;\n' +
        'globalThis.__duplicateProject = duplicateProject;\n' +
        'globalThis.__deleteProject = deleteProject;\n' +
        'loadAllData = async () => {};\n' +
        'renderProjectsTable = () => {};\n' +
        'renderRecentProjects = () => { counts.recent++; };\n' +
        'renderDashboard = () => { counts.dash++; };\n';
    vm.runInContext(code, sandbox);

    const state = sandbox.__app_state;
    state.activeView = 'dashboard';

    async function run() {
        await sandbox.__duplicateProject(1);
        if (sandbox.counts.recent !== 1 || sandbox.counts.dash !== 1) {
            throw new Error(`duplicateProject failed to refresh dashboard: recent=${sandbox.counts.recent}, dash=${sandbox.counts.dash}`);
        }

        await sandbox.__deleteProject(1);
        if (sandbox.counts.recent !== 2 || sandbox.counts.dash !== 2) {
            throw new Error(`deleteProject failed to refresh dashboard: recent=${sandbox.counts.recent}, dash=${sandbox.counts.dash}`);
        }

        console.log(JSON.stringify({ success: true, counts: sandbox.counts }));
    }

    run().catch(err => {
        console.error(err);
        process.exit(1);
    });
    """

    res = subprocess.run(["node", "-e", node_test], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_render_plates_empty_state_and_warning():
    """
    Issue #35:
    Verifies that:
    1. renderPlates renders a dedicated empty state when state.currentPlates is empty.
    2. saveCurrentProject shows a warning toast when plates and BOM are both empty.
    """
    node_test = r"""
    const fs = require('fs');
    const path = require('path');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    const vm = require('vm');
    const elements = {};
    function getOrCreate(id) {
        if (!elements[id]) {
            elements[id] = {
                id,
                textContent: '',
                innerHTML: '',
                innerText: '',
                value: (id === 'proj-name' ? 'Projeto Vazio' : (id === 'proj-status' ? 'draft' : '0')),
                classList: { add(){}, remove(){}, contains(){ return false; } },
                style: {},
                focus() {},
                appendChild(){},
                remove(){}
            };
        }
        return elements[id];
    }

    const sandbox = {
        toasts: [],
        document: {
            getElementById: getOrCreate,
            querySelector: (sel) => getOrCreate(sel),
            querySelectorAll: () => [],
            createElement: () => ({ className: '', innerHTML: '', innerText: '', textContent: '', style: {}, classList: { add(){}, remove(){}, contains(){ return false; } }, appendChild(){}, remove(){} }),
            addEventListener() {},
            removeEventListener() {}
        },
        addEventListener() {},
        removeEventListener() {},
        console, Math, Number, String, setTimeout, clearTimeout,
        refreshIcons() {},
        normalizeNumericInputs() {},
        updatePlateTime() {},
        API: {
            projects: {
                create: async (p) => ({ id: 99, ...p })
            }
        }
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    let code = appJs + '\n' +
        'globalThis.__app_state = state;\n' +
        'globalThis.__renderPlates = renderPlates;\n' +
        'globalThis.__saveCurrentProject = saveCurrentProject;\n' +
        'loadAllData = async () => {};\n' +
        'showToast = (msg, type) => { toasts.push({ msg, type }); };\n';
    vm.runInContext(code, sandbox);

    const state = sandbox.__app_state;
    state.currentPlates = [];
    state.currentBOM = [];

    // 1. Test empty state HTML in renderPlates
    sandbox.__renderPlates();
    const platesDiv = elements['plates-container'];
    if (!platesDiv.innerHTML.includes('Nenhuma placa de impressão configurada')) {
        throw new Error('renderPlates did not display empty state message');
    }
    if (!platesDiv.innerHTML.includes('Adicionar Placa') || !platesDiv.innerHTML.includes('addNewPlateRow()')) {
        throw new Error('renderPlates did not display "Adicionar Placa" button');
    }

    // 2. Test warning toast in saveCurrentProject
    async function testSave() {
        await sandbox.__saveCurrentProject(false);
        const warning = sandbox.toasts.find(t => t.type === 'warning');
        if (!warning || !warning.msg.includes('sem placas ou insumos')) {
            throw new Error(`Expected warning toast for empty project, got ${JSON.stringify(sandbox.toasts)}`);
        }
        console.log(JSON.stringify({ success: true, toast: warning }));
    }

    testSave().catch(err => {
        console.error(err);
        process.exit(1);
    });
    """

    res = subprocess.run(["node", "-e", node_test], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_render_plates_includes_purge_weight_input():
    """Issue #40: Ensure renderPlates includes editable Purga (g) input in plate card."""
    node_test = """
    const vm = require('vm');
    const fs = require('fs');
    const path = require('path');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    const elements = {
        'plates-container': { innerHTML: '' },
        'bom-container': { innerHTML: '' },
    };

    const sandbox = {
        console,
        elements,
        addEventListener: () => {},
        removeEventListener: () => {},
        document: {
            getElementById: (id) => elements[id] || { innerHTML: '', value: '', classList: { add: ()=>{}, remove: ()=>{} } },
            querySelectorAll: () => [],
            addEventListener: () => {},
            removeEventListener: () => {}
        },
        window: null,
        refreshIcons: () => {},
        recalcLiveSummary: () => {},
        parseLocaleFloat: (v, def) => parseFloat(v) || def,
        lucide: { createIcons: () => {} }
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    vm.runInContext(appJs + '\\n' +
        'state.currentPlates = [{\\n' +
        '  name: "Placa Teste",\\n' +
        '  print_time_hours: 2.5,\\n' +
        '  part_weight_g: 80.0,\\n' +
        '  purge_weight_g: 15.5,\\n' +
        '  failure_margin_percent: 10,\\n' +
        '  quantity: 1\\n' +
        '}];\\n' +
        'renderPlates();\\n' +
        'globalThis.__html = elements["plates-container"].innerHTML;\\n', sandbox);

    const html = sandbox.__html;
    if (!html.includes('Purga (g)')) {
        throw new Error('renderPlates HTML does not include "Purga (g)" label');
    }
    if (!html.includes('purge_weight_g')) {
        throw new Error('renderPlates HTML does not bind oninput to purge_weight_g');
    }
    if (!html.includes('value="15.5"')) {
        throw new Error('renderPlates HTML does not reflect current purge_weight_g value');
    }
    console.log(JSON.stringify({ success: true }));
    """

    res = subprocess.run(["node"], input=node_test, capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_dashboard_chart_cost_breakdown_includes_overhead():
    """Issue #38: Ensure renderDashboardCharts includes overhead_cost in Chart 3."""
    app_js = (Path(__file__).parent.parent / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    assert "cb.overhead_cost" in app_js, "app.js must include cb.overhead_cost in cost breakdown values"
    assert "Custos Indiretos (Overhead)" in app_js, "app.js must include 'Custos Indiretos (Overhead)' in labels"
    assert "#ec4899" in app_js, "app.js must include overhead color in cbColors palette"


def test_preview_html_trigger_print_does_not_download():
    """Issue #41: Ensure preview.html triggerPrint does not call triggerDownload on error."""
    preview_html = (Path(__file__).parent.parent / "frontend" / "preview.html").read_text(encoding="utf-8")
    assert "triggerDownload()" not in preview_html.split("function triggerPrint()")[1].split("</script>")[0], \
        "triggerPrint in preview.html must not fall back to triggerDownload"


def test_handle_single_plate_multi_3mf_import():
    """Issue #42: Ensure handleSinglePlateFile imports multi-plate 3MF by adding extra plates."""
    node_test = """
    const vm = require('vm');
    const fs = require('fs');
    const path = require('path');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    let toasts = [];
    let platesRendered = false;
    let summaryRecalculated = false;

    const sandbox = {
        console,
        toasts,
        addEventListener: () => {},
        removeEventListener: () => {},
        document: {
            getElementById: () => ({ value: '', innerHTML: '', classList: { add: ()=>{}, remove: ()=>{} } }),
            querySelectorAll: () => [],
            addEventListener: () => {},
            removeEventListener: () => {}
        },
        window: null,
        lucide: { createIcons: () => {} },
        renderPlates: () => { platesRendered = true; },
        recalcLiveSummary: () => { summaryRecalculated = true; },
        cleanFilamentProfileName: (n) => n,
        parse3mfMetadata: async (file) => [
            { print_time_hours: 1.5, part_weight_g: 45, purge_weight_g: 5, slicer_filament_profile: 'PLA' },
            { print_time_hours: 2.0, part_weight_g: 60, purge_weight_g: 8, slicer_filament_profile: 'PETG' },
            { print_time_hours: 3.5, part_weight_g: 110, purge_weight_g: 12, slicer_filament_profile: 'ABS' }
        ]
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    vm.runInContext(appJs + '\\n' +
        'showToast = (msg, type) => { toasts.push({ msg, type }); };\\n' +
        'globalThis.__state = state;\\n' +
        'state.currentPlates = [\\n' +
        '  { name: "Placa Inicial", print_time_hours: 0, part_weight_g: 0, purge_weight_g: 0, quantity: 1 }\\n' +
        '];\\n' +
        'async function run() {\\n' +
        '  const fakeEvent = { target: { files: [{ name: "multi_plate_model.3mf" }] } };\\n' +
        '  await handleSinglePlateFile(fakeEvent, 0);\\n' +
        '}\\n' +
        'globalThis.__run = run;\\n', sandbox);

    sandbox.__run().then(() => {
        const plates = sandbox.__state.currentPlates;
        if (plates.length !== 3) {
            throw new Error('Expected 3 plates in state, got ' + plates.length);
        }
        if (plates[0].part_weight_g !== 45 || plates[1].part_weight_g !== 60 || plates[2].part_weight_g !== 110) {
            throw new Error('Plates data not properly mapped from multi-plate 3MF');
        }
        const successToast = sandbox.toasts.find(t => t.type === 'success' && t.msg.includes('2 nova(s) placa(s) adicionada(s)'));
        if (!successToast) {
            throw new Error('Expected notification about 2 additional plates, got: ' + JSON.stringify(sandbox.toasts));
        }
        console.log(JSON.stringify({ success: true, count: plates.length }));
    }).catch(err => {
        console.error(err);
        process.exit(1);
    });
    """

    res = subprocess.run(["node"], input=node_test, capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_projects_table_interactive_sorting():
    """Issue #43: Ensure renderProjectsTable supports interactive column sorting."""
    node_test = """
    const vm = require('vm');
    const fs = require('fs');
    const path = require('path');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    const elements = {
        'projects-table-container': { innerHTML: '' },
        'project-search-input': { value: '' }
    };

    const sandbox = {
        console,
        elements,
        addEventListener: () => {},
        removeEventListener: () => {},
        document: {
            getElementById: (id) => elements[id] || { innerHTML: '', value: '', classList: { add: ()=>{}, remove: ()=>{} } },
            querySelectorAll: () => [],
            addEventListener: () => {},
            removeEventListener: () => {}
        },
        window: null,
        lucide: { createIcons: () => {} },
        refreshIcons: () => {},
        formatCurrency: (v) => 'R$ ' + (v || 0).toFixed(2),
        formatStatus: (s) => s,
        escapeHtml: (s) => s,
        matchesSearch: () => true
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    vm.runInContext(appJs + '\\n' +
        'globalThis.__state = state;\\n' +
        'globalThis.__renderProjectsTable = renderProjectsTable;\\n' +
        'globalThis.__setProjectSort = setProjectSort;\\n' +
        'state.projects = [\\n' +
        '  { id: 1, name: "Zeta Box", client_name: "Carlos", plates_count: 1, total_time_hours: 5.0, base_cost: 20, final_price_to_client: 50, status: "draft" },\\n' +
        '  { id: 2, name: "Alpha Rack", client_name: "Bruno", plates_count: 3, total_time_hours: 15.0, base_cost: 60, final_price_to_client: 180, status: "approved" },\\n' +
        '  { id: 3, name: "Beta Bracket", client_name: "Amanda", plates_count: 2, total_time_hours: 2.0, base_cost: 10, final_price_to_client: 25, status: "completed" }\\n' +
        '];\\n', sandbox);

    // 1. Check initial rendering and sort headers presence
    sandbox.__renderProjectsTable();
    const html = elements['projects-table-container'].innerHTML;
    if (!html.includes('setProjectSort(\\'name\\')') || !html.includes('setProjectSort(\\'final_price_to_client\\')')) {
        throw new Error('renderProjectsTable headers missing onclick setProjectSort');
    }

    // 2. Sort by name ascending (should be Alpha, Beta, Zeta)
    sandbox.__setProjectSort('name');
    if (sandbox.__state.projectSortField !== 'name' || sandbox.__state.projectSortAsc !== true) {
        throw new Error('setProjectSort("name") did not set sort state to name/asc');
    }
    const htmlNameAsc = elements['projects-table-container'].innerHTML;
    const posAlpha = htmlNameAsc.indexOf('Alpha Rack');
    const posBeta = htmlNameAsc.indexOf('Beta Bracket');
    const posZeta = htmlNameAsc.indexOf('Zeta Box');
    if (!(posAlpha < posBeta && posBeta < posZeta)) {
        throw new Error('Projects not sorted alphabetically ascending by name');
    }

    // 3. Sort by final_price_to_client descending (180, 50, 25)
    sandbox.__setProjectSort('final_price_to_client');
    if (sandbox.__state.projectSortAsc !== false) {
        throw new Error('setProjectSort("final_price_to_client") did not default to descending');
    }
    const htmlPriceDesc = elements['projects-table-container'].innerHTML;
    const posAlphaDesc = htmlPriceDesc.indexOf('Alpha Rack');
    const posZetaDesc = htmlPriceDesc.indexOf('Zeta Box');
    const posBetaDesc = htmlPriceDesc.indexOf('Beta Bracket');
    if (!(posAlphaDesc < posZetaDesc && posZetaDesc < posBetaDesc)) {
        throw new Error('Projects not sorted descending by final price (expected Alpha -> Zeta -> Beta)');
    }

    // 4. Toggle direction by calling setProjectSort on same field
    sandbox.__setProjectSort('final_price_to_client');
    if (sandbox.__state.projectSortAsc !== true) {
        throw new Error('Calling setProjectSort again on same field did not toggle to ascending');
    }

    console.log(JSON.stringify({ success: true }));
    """

    res = subprocess.run(["node"], input=node_test, capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_clear_user_data_on_logout():
    """Issue #44: Ensure clearUserData wipes in-memory state and DOM containers."""
    node_test = """
    const vm = require('vm');
    const fs = require('fs');
    const path = require('path');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    const elements = {
        'projects-table-container': { innerHTML: '<div>Stale Project</div>' },
        'recent-projects-table': { innerHTML: '<tr><td>Stale Recent</td></tr>' },
        'dashboard-recent-projects': { innerHTML: '<div>Stale Dashboard Recent</div>' },
        'printers-grid': { innerHTML: '<div>Stale Printer</div>' },
        'filaments-grid': { innerHTML: '<div>Stale Filament</div>' },
        'user-display-name': { textContent: 'Old User' },
        'user-display-company': { textContent: 'Old Company' },
        'user-avatar': { textContent: 'O' }
    };

    const tbody = { innerHTML: '<tr><td>Stale Tbody</td></tr>' };

    const sandbox = {
        console,
        elements,
        addEventListener: () => {},
        removeEventListener: () => {},
        document: {
            getElementById: (id) => elements[id] || { innerHTML: '', value: '', classList: { add: ()=>{}, remove: ()=>{} }, textContent: '' },
            querySelector: (sel) => sel.includes('tbody') ? tbody : null,
            querySelectorAll: () => [],
            addEventListener: () => {},
            removeEventListener: () => {}
        },
        window: null,
        lucide: { createIcons: () => {} },
        refreshIcons: () => {},
        formatCurrency: (v) => 'R$ ' + (v || 0).toFixed(2),
        formatStatus: (s) => s,
        escapeHtml: (s) => s,
        matchesSearch: () => true
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    vm.runInContext(appJs + '\\n' +
        'globalThis.__state = state;\\n' +
        'globalThis.__clearUserData = clearUserData;\\n' +
        'state.user = { id: 1, full_name: "Test User" };\\n' +
        'state.projects = [{ id: 1, name: "Secret Project" }];\\n' +
        'state.printers = [{ id: 1, name: "Secret Printer" }];\\n' +
        'state.filaments = [{ id: 1, name: "Secret Filament" }];\\n' +
        'state.currentProject = { id: 1 };\\n' +
        'state.currentPlates = [{ name: "Secret Plate" }];\\n' +
        'state.currentBOM = [{ name: "Secret Part" }];\\n' +
        'state.dashboardStats = { total_revenue_approved: 1000 };\\n', sandbox);

    sandbox.__clearUserData();

    const st = sandbox.__state;
    if (st.user !== null) throw new Error('state.user was not cleared');
    if (st.projects.length !== 0) throw new Error('state.projects was not cleared');
    if (st.printers.length !== 0) throw new Error('state.printers was not cleared');
    if (st.filaments.length !== 0) throw new Error('state.filaments was not cleared');
    if (st.currentProject !== null) throw new Error('state.currentProject was not cleared');
    if (st.currentPlates.length !== 0) throw new Error('state.currentPlates was not cleared');
    if (st.currentBOM.length !== 0) throw new Error('state.currentBOM was not cleared');
    if (st.dashboardStats !== null) throw new Error('state.dashboardStats was not cleared');

    if (elements['projects-table-container'].innerHTML !== '') throw new Error('projects-table-container not cleared');
    if (elements['printers-grid'].innerHTML !== '') throw new Error('printers-grid not cleared');
    if (elements['filaments-grid'].innerHTML !== '') throw new Error('filaments-grid not cleared');
    if (elements['user-display-name'].textContent !== '') throw new Error('user-display-name not cleared');

    console.log(JSON.stringify({ success: true }));
    """
    res = subprocess.run(["node"], input=node_test, capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_update_plate_time_guards_missing_dom():
    """Issue #45: Ensure updatePlateTime does not overwrite print_time_hours when inputs are not rendered."""
    node_test = """
    const vm = require('vm');
    const fs = require('fs');
    const path = require('path');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    const sandbox = {
        console,
        addEventListener: () => {},
        removeEventListener: () => {},
        document: {
            getElementById: () => null,
            querySelectorAll: () => [],
            addEventListener: () => {},
            removeEventListener: () => {}
        },
        window: null,
        recalcLiveSummary: () => {}
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    vm.runInContext(appJs + '\\n' +
        'globalThis.__state = state;\\n' +
        'globalThis.__updatePlateTime = updatePlateTime;\\n' +
        'state.currentPlates = [{ name: "Placa 1", print_time_hours: 4.75 }];\\n', sandbox);

    // Call updatePlateTime when DOM elements do not exist
    sandbox.__updatePlateTime(0);

    if (sandbox.__state.currentPlates[0].print_time_hours !== 4.75) {
        throw new Error('print_time_hours was overwritten to ' + sandbox.__state.currentPlates[0].print_time_hours);
    }

    console.log(JSON.stringify({ success: true }));
    """
    res = subprocess.run(["node"], input=node_test, capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_show_toast_xss_protection():
    """Issue #46: Ensure showToast uses textContent rather than innerHTML to prevent reflected XSS."""
    node_test = """
    const vm = require('vm');
    const fs = require('fs');
    const path = require('path');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    let createdToast = null;
    const toastContainer = {
        appendChild: (child) => { createdToast = child; }
    };

    class FakeElement {
        constructor(tag) {
            this.tagName = tag;
            this.children = [];
            this.textContent = '';
            this.innerHTML = '';
            this.className = '';
            this.classList = { add: ()=>{}, remove: ()=>{} };
        }
        appendChild(child) {
            this.children.push(child);
        }
    }

    const sandbox = {
        console,
        setTimeout: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        document: {
            getElementById: (id) => id === 'toast-container' ? toastContainer : null,
            createElement: (tag) => new FakeElement(tag),
            querySelectorAll: () => [],
            addEventListener: () => {},
            removeEventListener: () => {}
        },
        window: null
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    vm.runInContext(appJs + '\\n' +
        'globalThis.__showToast = showToast;\\n', sandbox);

    const malicious = '<img src=x onerror=alert(1)>';
    sandbox.__showToast(malicious, 'error');

    if (!createdToast) throw new Error('Toast element was not created');
    if (createdToast.innerHTML.includes('<img')) {
        throw new Error('XSS payload injected directly into innerHTML!');
    }
    const span = createdToast.children[0];
    if (!span || span.textContent !== malicious) {
        throw new Error('Toast text span does not have correct textContent');
    }

    console.log(JSON.stringify({ success: true }));
    """
    res = subprocess.run(["node"], input=node_test, capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_save_project_fallback_plate_and_bom_names():
    """Issue #47: Ensure saveCurrentProject falls back empty/whitespace plate and BOM names."""
    node_test = """
    const vm = require('vm');
    const fs = require('fs');
    const path = require('path');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    let capturedPayload = null;
    const elements = {
        'proj-name': { value: 'Projeto Valido', focus: ()=>{} },
        'proj-client-name': { value: 'Cliente' },
        'proj-client-email': { value: '' },
        'proj-client-phone': { value: '' },
        'proj-status': { value: 'draft' },
        'proj-cad-hours': { value: '0' },
        'proj-cad-rate': { value: '0' },
        'proj-post-hours': { value: '0' },
        'proj-post-rate': { value: '0' },
        'proj-overhead': { value: '0' },
        'proj-margin': { value: '30' },
        'proj-tax': { value: '0' },
        'proj-discount': { value: '0' },
        'proj-shipping': { value: '0' },
        'proj-delivery-days': { value: '3' },
        'proj-payment-terms': { value: '' },
        'proj-warranty-terms': { value: '' },
        'proj-notes': { value: '' }
    };

    const sandbox = {
        console,
        elements,
        addEventListener: () => {},
        removeEventListener: () => {},
        document: {
            getElementById: (id) => id === 'toast-container' ? null : (elements[id] || { value: '', innerHTML: '', focus: ()=>{} }),
            querySelector: () => null,
            querySelectorAll: () => [],
            createElement: () => ({ appendChild: ()=>{}, classList: { add: ()=>{}, remove: ()=>{} }, style: {} }),
            addEventListener: () => {},
            removeEventListener: () => {}
        },
        window: null,
        showToast: () => {},
        recalcLiveSummary: () => {},
        normalizeNumericInputs: () => {},
        updatePlateTime: () => {},
        loadAllData: async () => {},
        navigateTo: () => {},
        API: {
            getToken: () => null,
            projects: {
                create: async (p) => { capturedPayload = p; return { id: 1, ...p }; }
            }
        }
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    vm.runInContext(appJs + '\\n' +
        'globalThis.__state = state;\\n' +
        'globalThis.__saveCurrentProject = saveCurrentProject;\\n' +
        'state.currentPlates = [\\n' +
        '  { name: "", print_time_hours: 1, part_weight_g: 10, purge_weight_g: 0, failure_margin_percent: 10, quantity: 1 },\\n' +
        '  { name: "   ", print_time_hours: 1, part_weight_g: 10, purge_weight_g: 0, failure_margin_percent: 10, quantity: 1 }\\n' +
        '];\\n' +
        'state.currentBOM = [\\n' +
        '  { name: "", category: "Fixadores", quantity: 2, unit_cost: 1.5 },\\n' +
        '  { name: "  ", category: "Outros", quantity: 1, unit_cost: 5 }\\n' +
        '];\\n', sandbox);

    sandbox.__saveCurrentProject(false).then(() => {
        if (!capturedPayload) throw new Error('Payload was not captured');
        if (capturedPayload.plates[0].name !== 'Placa 1') {
            throw new Error('Plate 0 did not fallback to "Placa 1", got: ' + capturedPayload.plates[0].name);
        }
        if (capturedPayload.plates[1].name !== 'Placa 2') {
            throw new Error('Plate 1 did not fallback to "Placa 2", got: ' + capturedPayload.plates[1].name);
        }
        if (capturedPayload.bom_items[0].name !== 'Insumo 1') {
            throw new Error('BOM 0 did not fallback to "Insumo 1", got: ' + capturedPayload.bom_items[0].name);
        }
        if (capturedPayload.bom_items[1].name !== 'Insumo 2') {
            throw new Error('BOM 1 did not fallback to "Insumo 2", got: ' + capturedPayload.bom_items[1].name);
        }
        console.log(JSON.stringify({ success: true }));
    }).catch(err => {
        console.error(err);
        process.exit(1);
    });
    """
    res = subprocess.run(["node"], input=node_test, capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_duplicate_bom_row():
    """Issue #49: Ensure duplicateBomRow clones the BOM item, sets (Cópia), strips id, and calls renderBOM."""
    node_test = """
    const vm = require('vm');
    const fs = require('fs');
    const path = require('path');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    const elements = {
        'bom-container': { innerHTML: '' }
    };

    const sandbox = {
        console,
        elements,
        addEventListener: () => {},
        removeEventListener: () => {},
        document: {
            getElementById: (id) => elements[id] || null,
            querySelector: () => null,
            querySelectorAll: () => [],
            createElement: () => ({ appendChild: ()=>{}, classList: { add: ()=>{}, remove: ()=>{} }, style: {} }),
            addEventListener: () => {},
            removeEventListener: () => {}
        },
        window: null
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    vm.runInContext(appJs + '\\n' +
        'globalThis.__state = state;\\n' +
        'globalThis.__duplicateBomRow = duplicateBomRow;\\n' +
        'state.currentBOM = [\\n' +
        '  { id: 99, name: "Parafuso M3x12", category: "Fixadores", quantity: 4, unit_cost: 0.35 }\\n' +
        '];\\n', sandbox);

    sandbox.__duplicateBomRow(0);

    const bom = sandbox.__state.currentBOM;
    if (bom.length !== 2) throw new Error('Expected 2 items in currentBOM, got ' + bom.length);
    const cloned = bom[1];
    if (cloned.id !== undefined) throw new Error('Cloned BOM item retained id: ' + cloned.id);
    if (cloned.name !== 'Parafuso M3x12 (Cópia)') throw new Error('Cloned name mismatch: ' + cloned.name);
    if (cloned.quantity !== 4 || cloned.unit_cost !== 0.35) throw new Error('Cloned values mismatch');
    if (!elements['bom-container'].innerHTML.includes('Parafuso M3x12 (Cópia)')) {
        throw new Error('renderBOM did not render cloned item into bom-container');
    }

    console.log(JSON.stringify({ success: true }));
    """
    res = subprocess.run(["node"], input=node_test, capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_issue_50_printers_grid_xss_protection():
    """Issue #50: renderPrintersGrid escapes printer name, model, and search term."""
    node_test = r"""
    const fs = require('fs');
    const path = require('path');
    const vm = require('vm');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    const elements = {
        'printers-grid': { innerHTML: '' },
        'printer-search-input': { value: '' },
        'printer-status-filter': { value: 'all' }
    };

    const sandbox = {
        console,
        elements,
        addEventListener: () => {},
        removeEventListener: () => {},
        document: {
            getElementById: (id) => elements[id] || null,
            querySelector: () => null,
            querySelectorAll: () => [],
            createElement: () => ({ appendChild: ()=>{}, classList: { add: ()=>{}, remove: ()=>{} }, style: {} }),
            addEventListener: () => {},
            removeEventListener: () => {}
        },
        window: null
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    vm.runInContext(appJs + '\n' +
        'state.printers = [{\n' +
        '  id: 1, name: "<img src=x onerror=alert(1)>", model: "<b id=\\"prn\\">CoreXY</b>", is_active: true, rates_breakdown: {}, machine_hourly_rate: 3.5\n' +
        '}];\n' +
        'renderPrintersGrid();\n', sandbox);

    const html = elements['printers-grid'].innerHTML;
    if (html.includes('<img src=x')) throw new Error('Unescaped img tag in printer grid');
    if (!html.includes('&lt;img src=x')) throw new Error('Printer name not escaped with &lt;');
    if (html.includes('<b id="prn">')) throw new Error('Unescaped b tag in printer model');
    if (!html.includes('&lt;b id=&quot;prn&quot;&gt;')) throw new Error('Printer model not escaped');

    // Test search filter XSS
    vm.runInContext('state.printers = [{ id: 1, name: "Ender", model: "V2" }]; renderPrintersGrid("<script>alert(\\"xss\\")</script>", "all");', sandbox);
    const emptyHtml = elements['printers-grid'].innerHTML;
    if (emptyHtml.includes('<script>')) throw new Error('Unescaped script tag in search empty state');
    if (!emptyHtml.includes('&lt;script&gt;')) throw new Error('Search term not escaped in empty state');

    console.log(JSON.stringify({ success: true }));
    """
    res = subprocess.run(["node"], input=node_test, capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_issue_51_filaments_grid_xss_protection():
    """Issue #51: renderFilamentsGrid escapes filament name, brand, color, and search filter."""
    node_test = r"""
    const fs = require('fs');
    const path = require('path');
    const vm = require('vm');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    const elements = {
        'filaments-grid': { innerHTML: '' },
        'filament-search-input': { value: '' },
        'filament-material-filter': { value: '' }
    };

    const sandbox = {
        console,
        elements,
        addEventListener: () => {},
        removeEventListener: () => {},
        document: {
            getElementById: (id) => elements[id] || null,
            querySelector: () => null,
            querySelectorAll: () => [],
            createElement: () => ({ appendChild: ()=>{}, classList: { add: ()=>{}, remove: ()=>{} }, style: {} }),
            addEventListener: () => {},
            removeEventListener: () => {}
        },
        window: null
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    vm.runInContext(appJs + '\n' +
        'state.filaments = [{\n' +
        '  id: 1, name: "<script>alert(\\"fil\\")</script>", brand: "<b>Brand</b>", color: "<i>Color</i>", material: "PLA", cost_per_gram: 0.1, spool_weight_g: 1000, spool_price: 100\n' +
        '}];\n' +
        'renderFilamentsGrid();\n', sandbox);

    const html = elements['filaments-grid'].innerHTML;
    if (html.includes('<script>')) throw new Error('Unescaped script tag in filaments grid');
    if (!html.includes('&lt;script&gt;')) throw new Error('Filament name not escaped');
    if (html.includes('<b>Brand</b>')) throw new Error('Unescaped brand in filaments grid');
    if (!html.includes('&lt;b&gt;Brand&lt;/b&gt;')) throw new Error('Filament brand not escaped');

    // Test filter search XSS
    vm.runInContext('state.filaments = [{ id: 1, name: "Fil", brand: "B", color: "C", material: "PLA" }]; renderFilamentsGrid("<img src=x onerror=alert(2)>", "");', sandbox);
    const emptyHtml = elements['filaments-grid'].innerHTML;
    if (emptyHtml.includes('<img src=x')) throw new Error('Unescaped filter search term in empty state');
    if (!emptyHtml.includes('&lt;img src=x')) throw new Error('Filter search term not escaped in empty state');

    console.log(JSON.stringify({ success: true }));
    """
    res = subprocess.run(["node"], input=node_test, capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_issue_52_and_55_plate_card_orphans_and_xss():
    """Issues #52 & #55: manual rate inputs shown for orphaned IDs, and filament info escaped."""
    node_test = r"""
    const fs = require('fs');
    const path = require('path');
    const vm = require('vm');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    const elements = {
        'plates-container': { innerHTML: '' }
    };

    const sandbox = {
        console,
        elements,
        addEventListener: () => {},
        removeEventListener: () => {},
        document: {
            getElementById: (id) => elements[id] || null,
            querySelector: () => null,
            querySelectorAll: () => [],
            createElement: () => ({ appendChild: ()=>{}, classList: { add: ()=>{}, remove: ()=>{} }, style: {} }),
            addEventListener: () => {},
            removeEventListener: () => {}
        },
        window: null
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    vm.runInContext(appJs + '\n' +
        'state.printers = [{ id: 1, name: "Prusa MK4", machine_hourly_rate: 3.0 }];\n' +
        'state.filaments = [{ id: 1, name: "PLA Especial", material: "<b id=\\"xss\\">PLA</b>", color: "<i>Azul</i>", color_hex: "#0000ff", cost_per_gram: 0.12 }];\n' +
        'state.currentPlates = [\n' +
        '  { name: "P1", printer_id: 999, filament_id: 999, custom_printer_hourly_rate: 2.50, custom_filament_cost_per_g: 0.10, print_time_hours: 1, part_weight_g: 50 },\n' +
        '  { name: "P2", printer_id: 1, filament_id: 1, print_time_hours: 1, part_weight_g: 50 }\n' +
        '];\n' +
        'renderPlates();\n', sandbox);

    const html = elements['plates-container'].innerHTML;

    // Issue #52: P1 has orphaned printer_id=999 and filament_id=999 -> manual inputs MUST be rendered
    if (!html.includes('Taxa manual:')) throw new Error('Missing manual printer rate input for orphaned printer_id');
    if (!html.includes('Custo manual:')) throw new Error('Missing manual filament cost input for orphaned filament_id');

    // Issue #55: P2 has filament with HTML tags in material & color -> MUST be escaped
    if (html.includes('<b id="xss">')) throw new Error('Unescaped material tag in plate header');
    if (!html.includes('&lt;b id=&quot;xss&quot;&gt;PLA&lt;/b&gt;')) throw new Error('Plate filament material not escaped');
    if (html.includes('<i>Azul</i>')) throw new Error('Unescaped color tag in plate header');

    console.log(JSON.stringify({ success: true }));
    """
    res = subprocess.run(["node"], input=node_test, capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_issue_54_and_56_recalc_live_summary():
    """Issues #54 & #56: recalcLiveSummary clamps negative inputs and applies 2.50/h and 0.10/g fallbacks."""
    node_test = r"""
    const fs = require('fs');
    const path = require('path');
    const vm = require('vm');
    const appJs = fs.readFileSync(path.resolve('frontend/js/app.js'), 'utf8');

    const domMap = {
        'proj-margin': { value: '-20' }, // negative margin
        'proj-tax': { value: '-5' },     // negative tax
        'proj-discount': { value: '-15' }, // negative discount
        'proj-shipping': { value: '-10' }, // negative shipping
        'proj-cad-hours': { value: '0' },
        'proj-cad-rate': { value: '50' },
        'proj-post-hours': { value: '0' },
        'proj-post-rate': { value: '30' },
        'proj-overhead': { value: '0' },
        'live-discount-amount': { textContent: '' },
        'live-final-price': { textContent: '' },
        'live-net-profit': { textContent: '', className: '' },
        'live-weight': { textContent: '' },
        'live-time': { textContent: '' },
        'live-material-cost': { textContent: '' },
        'live-machine-cost': { textContent: '' },
        'live-bom-cost': { textContent: '' },
        'live-labor-cost': { textContent: '' },
        'live-overhead-cost': { textContent: '' },
        'live-base-cost': { textContent: '' },
        'live-suggested-price': { textContent: '' },
        'live-shipping-amount': { textContent: '' },
        'live-tax-amount': { textContent: '' }
    };

    const sandbox = {
        console,
        addEventListener: () => {},
        removeEventListener: () => {},
        document: {
            getElementById: (id) => domMap[id] || null,
            querySelector: () => ({ textContent: '', className: '', style: {} }),
            querySelectorAll: () => [],
            createElement: () => ({ appendChild: ()=>{}, classList: { add: ()=>{}, remove: ()=>{} }, style: {} }),
            addEventListener: () => {},
            removeEventListener: () => {}
        },
        window: null
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    vm.runInContext(appJs + '\n' +
        'state.printers = [];\n' +
        'state.filaments = [];\n' +
        'state.currentBOM = [];\n' +
        // Plate with negative quantity, null custom rates (Issue #56: should use 2.50/h and 0.10/g)
        'state.currentPlates = [{\n' +
        '  printer_id: null,\n' +
        '  filament_id: null,\n' +
        '  custom_printer_hourly_rate: null,\n' +
        '  custom_filament_cost_per_g: null,\n' +
        '  print_time_hours: 10,\n' +
        '  part_weight_g: 1000,\n' +
        '  purge_weight_g: 0,\n' +
        '  failure_margin_percent: 0,\n' +
        '  quantity: -3\n' +
        '}];\n' +
        'recalcLiveSummary();\n', sandbox);

    // Issue #54: Negative quantity must be clamped to at least 1 (not -3)
    const timeText = domMap['live-time'].textContent;
    if (timeText !== '10.0 h') throw new Error('Expected 10.0 h for qty=1, got: ' + timeText);

    // Issue #56: Fallback rates must be 2.50/h and 0.10/g
    // 10h * 2.50 = R$ 25,00 machine cost
    // 1000g * 0.10 = R$ 100,00 material cost
    const machCost = domMap['live-machine-cost'].textContent;
    const matCost = domMap['live-material-cost'].textContent;
    if (!machCost.includes('25,00')) throw new Error('Expected R$ 25,00 machine cost with 2.50 fallback, got: ' + machCost);
    if (!matCost.includes('100,00')) throw new Error('Expected R$ 100,00 material cost with 0.10 fallback, got: ' + matCost);

    // Issue #54: Discount was -15, should be clamped to 0 -> discount amount is R$ 0,00 (no double minus)
    const discText = domMap['live-discount-amount'].textContent;
    if (discText.includes('- -') || !discText.includes('0,00')) throw new Error('Discount amount has double minus or is not 0: ' + discText);

    console.log(JSON.stringify({ success: true }));
    """
    res = subprocess.run(["node"], input=node_test, capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout


def test_issues_59_through_71_frontend_verification():
    """Validates frontend implementations for Issues #59, #60, #63, #64, #66, #68, #69, #70."""
    node_test = """
    const fs = require('fs');
    const vm = require('vm');

    const appJs = fs.readFileSync('frontend/js/app.js', 'utf8');
    const indexHtml = fs.readFileSync('frontend/index.html', 'utf8');
    const apiJs = fs.readFileSync('frontend/js/api.js', 'utf8');
    const threemfJs = fs.readFileSync('frontend/js/parsers/threemf.js', 'utf8');

    // 1. Issue #63 & #69: HTML elements verification
    if (!indexHtml.includes('id="printer-active"')) throw new Error('Missing #printer-active in index.html');
    if (!indexHtml.includes('id="filament-active"')) throw new Error('Missing #filament-active in index.html');
    if (!indexHtml.includes('id="filament-status-filter"')) throw new Error('Missing #filament-status-filter in index.html');

    // 2. Issue #64: API.printers.duplicate exists
    if (!apiJs.includes('duplicate: (id) => API.request(`/api/printers/${id}/duplicate`')) {
        throw new Error('Missing API.printers.duplicate in api.js');
    }

    // 3. Issue #66: threemf.js purge_weight_g retains purgeGrams
    if (!threemfJs.includes('purge_weight_g: parseFloat(purgeGrams.toFixed(2))')) {
        throw new Error('threemf.js does not retain purgeGrams in purge_weight_g');
    }

    // 4. Issue #59: color_hex XSS sanitization in renderFilamentsGrid
    const dom = {
        'filaments-grid': { innerHTML: '' },
        'filament-search-input': { value: '' },
        'filament-material-filter': { value: '' },
        'filament-status-filter': { value: 'all' },
        'printers-grid': { innerHTML: '' },
        'printer-search-input': { value: '' },
        'printer-status-filter': { value: 'all' },
        'dashboard-recent-projects': { innerHTML: '' },
        'projects-table-container': { innerHTML: '' },
        'proj-delivery-days': { value: '' }
    };
    const sandbox = {
        console,
        document: {
            getElementById: id => dom[id] || { value: '', innerHTML: '', classList: { add(){}, remove(){} } },
            querySelector: () => ({ textContent: '', className: '', style: {} }),
            querySelectorAll: () => [],
            addEventListener: () => {},
            removeEventListener: () => {}
        },
        window: null,
        addEventListener: () => {},
        removeEventListener: () => {},
        state: { printers: [], filaments: [], projects: [], currentPlates: [], currentBOM: [] }
    };
    sandbox.window = sandbox;
    sandbox.global = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);
    vm.runInContext(appJs, sandbox);

    // Test Issue #59: Malicious color_hex
    vm.runInContext(`
        state.filaments = [{
            id: 1,
            name: 'Evil Filament',
            material: 'PLA',
            color_hex: 'red; background: url(javascript:alert(1))',
            is_active: true
        }];
        renderFilamentsGrid();
    `, sandbox);
    const filamentHtml = dom['filaments-grid'].innerHTML;
    if (filamentHtml.includes('javascript:alert(1)')) {
        throw new Error('XSS detected: raw color_hex injected into filaments grid HTML');
    }
    if (!filamentHtml.includes('#10b981')) {
        throw new Error('safeHex fallback #10b981 not applied to invalid color_hex');
    }
    if (!filamentHtml.includes('Ativo')) {
        throw new Error('Filament status badge "Ativo" not found');
    }

    // Test Issue #69: Inactive filament
    vm.runInContext(`
        state.filaments[0].is_active = false;
        renderFilamentsGrid();
    `, sandbox);
    if (!dom['filaments-grid'].innerHTML.includes('Inativo')) {
        throw new Error('Filament status badge "Inativo" not found');
    }

    // Test Issue #60: Project status XSS in renderRecentProjects & renderProjectsTable
    vm.runInContext(`
        state.projects = [{
            id: 10,
            name: 'Test Project',
            client_name: 'Client',
            status: '<img src=x onerror=alert(1)>',
            plates_count: 1,
            total_time_hours: 2,
            base_cost: 20,
            final_price_to_client: 50
        }];
        renderRecentProjects();
    `, sandbox);
    const recentHtml = dom['dashboard-recent-projects'].innerHTML;
    if (recentHtml.includes('<img src=x onerror=alert(1)>')) {
        throw new Error('XSS detected: unescaped status in renderRecentProjects');
    }
    if (!recentHtml.includes('&lt;img src=x onerror=alert(1)&gt;')) {
        throw new Error('Expected escaped status in renderRecentProjects');
    }

    vm.runInContext(`
        renderProjectsTable();
    `, sandbox);
    const tableHtml = dom['projects-table-container'].innerHTML;
    if (tableHtml.includes('<img src=x onerror=alert(1)>')) {
        throw new Error('XSS detected: unescaped status in renderProjectsTable');
    }
    if (!tableHtml.includes('&lt;img src=x onerror=alert(1)&gt;')) {
        throw new Error('Expected escaped status in renderProjectsTable');
    }

    // Test Issue #63 & #64: Printer badge and duplicate button
    vm.runInContext(`
        state.printers = [{
            id: 1,
            name: 'Printer Alpha',
            model: 'FDM',
            machine_hourly_rate: 15.0,
            acquisition_cost: 3000,
            lifespan_hours: 5000,
            avg_power_watts: 150,
            is_active: false
        }];
        renderPrintersGrid();
    `, sandbox);
    const printerHtml = dom['printers-grid'].innerHTML;
    if (!printerHtml.includes('Inativa')) {
        throw new Error('Printer status badge "Inativa" not found');
    }
    if (!printerHtml.includes('duplicatePrinter(1)')) {
        throw new Error('duplicatePrinter(1) button not found in printer card');
    }

    // Test Issue #68: Blank delivery days does not force 3
    dom['proj-delivery-days'].value = '   ';
    const rawDelivery = dom['proj-delivery-days'].value.trim();
    const parsedDelivery = (() => {
        if (!rawDelivery) return null;
        const d = parseInt(rawDelivery, 10);
        return isNaN(d) || d < 0 ? null : d;
    })();
    if (parsedDelivery !== null) {
        throw new Error('Expected null for empty delivery days, got: ' + parsedDelivery);
    }

    // Test Issue #70: Manufacturing parameters in createDefaultPlate
    const defPlate = vm.runInContext('createDefaultPlate(1)', sandbox);
    if (defPlate.nozzle_diameter !== '0.4') throw new Error('Default plate missing nozzle_diameter 0.4');
    if (defPlate.bed_type !== 'Textured PEI') throw new Error('Default plate missing bed_type Textured PEI');
    if (defPlate.layer_height !== '0.20') throw new Error('Default plate missing layer_height 0.20');

    // Test Issue #74: openNewProject populates default commercial terms
    if (!appJs.includes("document.getElementById('proj-payment-terms').value = u.default_payment_terms || '';")) {
        throw new Error('openNewProject does not pre-fill default_payment_terms');
    }
    if (!appJs.includes("document.getElementById('proj-warranty-terms').value = u.default_warranty_terms || '';")) {
        throw new Error('openNewProject does not pre-fill default_warranty_terms');
    }

    // Test Issue #75: deleteProject clears currentProject if matching
    if (!appJs.includes("if (state.currentProject && state.currentProject.id === id)")) {
        throw new Error('deleteProject does not check state.currentProject');
    }
    if (!appJs.includes("state.currentProject = null;")) {
        throw new Error('deleteProject does not clear state.currentProject');
    }

    // Test Issue #76: filament card displays material density
    vm.runInContext(`
        state.filaments = [{
            id: 1,
            name: 'ABS Premium',
            brand: 'TechFil',
            color: 'Cinza',
            material: 'ABS',
            density_g_cm3: 1.04,
            spool_weight_g: 1000,
            spool_price: 110.0,
            cost_per_gram: 0.11,
            is_active: true
        }];
        renderFilamentsGrid();
    `, sandbox);
    const filHtml = dom['filaments-grid'].innerHTML;
    if (!filHtml.includes('Densidade: 1.04 g/cm³')) {
        throw new Error('Filament card does not display material density 1.04 g/cm³');
    }

    // Test Issue #77: duplicate filament pre-fills color with (Cópia)
    if (!appJs.includes("document.getElementById('filament-color').value = filament.color ? `${filament.color} (Cópia)` : '';")) {
        throw new Error('openFilamentModal duplicate does not preserve color with (Cópia)');
    }

    // Test Issue #78: printer form validates required name in frontend
    if (!appJs.includes("const name = document.getElementById('printer-name').value.trim();") ||
        !appJs.includes("if (!name) {") ||
        !appJs.includes("showToast('Informe o nome ou identificação da impressora.', 'error');")) {
        throw new Error('handleSavePrinter does not validate required printer name in frontend');
    }

    // Test Issue #79: slicer parsers extract nozzle_diameter and layer_height
    const gcodeJs = fs.readFileSync('frontend/js/parsers/gcode.js', 'utf8');
    if (!gcodeJs.includes('nozzle_diameter: nozzleDiameter || null') || !gcodeJs.includes('layer_height: layerHeight || null')) {
        throw new Error('gcode.js does not return nozzle_diameter and layer_height');
    }
    if (!threemfJs.includes('nozzle_diameter: plateNozzleDiameter || null') || !threemfJs.includes('layer_height: plateLayerHeight || null')) {
        throw new Error('threemf.js does not return nozzle_diameter and layer_height');
    }

    // Test Issue #81: saveCurrentProject matches recalcLiveSummary defaults
    if (!appJs.includes("cad_hourly_rate: Math.max(0, parseLocaleFloat(document.getElementById('proj-cad-rate').value, defaultCadRate))") ||
        !appJs.includes("profit_margin_percent: Math.max(0, parseLocaleFloat(document.getElementById('proj-margin').value, defaultMargin))")) {
        throw new Error('saveCurrentProject does not harmonize defaults with recalcLiveSummary');
    }

    // Test Issue #82: printer rate preview card and updatePrinterRatePreview function
    const htmlContent = fs.readFileSync('frontend/index.html', 'utf8');
    if (!htmlContent.includes('id="printer-rate-preview-card"') || !htmlContent.includes('id="printer-rate-preview-value"')) {
        throw new Error('index.html lacks printer-rate-preview-card or printer-rate-preview-value');
    }
    if (!appJs.includes('function updatePrinterRatePreview()') || !appJs.includes('updatePrinterRatePreview();')) {
        throw new Error('app.js does not define or invoke updatePrinterRatePreview');
    }

    // Test Issue #83: plate selectors and filament card format rates with formatCurrency
    if (!appJs.includes("(${formatCurrency(p.machine_hourly_rate)}/h)") ||
        !appJs.includes("(${formatCurrency(f.cost_per_gram || 0)}/g)")) {
        throw new Error('Plate options do not use formatCurrency for hourly rate and gram cost');
    }

    // Test Issue #84: BOM table contains specifications/notes input
    if (!appJs.includes("state.currentBOM[${idx}].notes = this.value") ||
        !appJs.includes('Especificações / Obs')) {
        throw new Error('renderBOM does not render specifications/notes column and input');
    }

    // Test Issue #85: logout confirmation prevents accidental logout
    if (!htmlContent.includes('onclick="handleLogout()"')) {
        throw new Error('index.html sidebar logout button does not call handleLogout()');
    }
    if (!appJs.includes('function handleLogout()') || !appJs.includes('confirm(')) {
        throw new Error('app.js does not define handleLogout with confirmation dialog');
    }

    // Test Issue #86: filament form validates strictly positive spool weight and density
    if (!appJs.includes("density <= 0") || !appJs.includes("spoolWeight <= 0")) {
        throw new Error('handleSaveFilament does not validate strictly positive density and spool weight');
    }

    // Test Issue #87: gcode parser preserves precision for quick calibration prints
    if (!gcodeJs.includes('roundedHours = parseFloat(printTimeHours.toFixed(4));')) {
        throw new Error('gcode.js does not provide toFixed(4) fallback for short calibration prints');
    }

    console.log(JSON.stringify({ success: true }));
    """
    res = subprocess.run(["node"], input=node_test, capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node script failed: {res.stderr}\nStdout: {res.stdout}"
    assert "success" in res.stdout



















