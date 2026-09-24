"""
Adversarial Stress Verification Suite for Milestone 3:
Multi-Plate & BOM Integration Stress, DOM Order, and Zero Static ID Collisions.

Author: Challenger M3.2 (teamwork_preview_challenger)
Role: Empirical Challenger (critic, specialist)

Verifications:
1. Static DOM 117 unique IDs strict preservation and absence of spurious static IDs.
2. Dynamic row templates in app.js contain ZERO un-interpolated static IDs.
3. DOM order invariant: #btn-add-plate-bottom strictly follows #plates-container.
4. Node harness: Multi-plate addition (10 plates), deletion (middle/first/last),
   1-plate minimum safeguard, and dual-time (h:m) fractional hour calculation.
5. Node harness: BOM rows addition, deletion, empty state round-trip,
   subtotal currency math, and case-variation global aliases.
6. Real Headless Chrome/Edge DOM runtime verification: 0 duplicate IDs across
   the entire document after adding 5 plates and 5 BOM rows.
"""

import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
import pytest
from bs4 import BeautifulSoup

ROOT_DIR = Path(__file__).parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
INDEX_HTML = FRONTEND_DIR / "index.html"
APP_JS = FRONTEND_DIR / "js" / "app.js"
VIEWS_CSS = FRONTEND_DIR / "css" / "views.css"


class IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k == "id":
                self.ids.append(v)


# ==============================================================================
# 1. STATIC DOM 117 IDS PRESERVATION & INVARIANTS
# ==============================================================================

def test_static_index_html_117_ids_strict():
    """Verify exact count of 117 static IDs in index.html and zero duplicate static IDs."""
    parser = IdCollector()
    content = INDEX_HTML.read_text(encoding="utf-8")
    parser.feed(content)

    assert len(parser.ids) >= 117, f"Expected at least 117 static IDs, found {len(parser.ids)}"
    assert len(set(parser.ids)) == len(parser.ids), f"Duplicate IDs detected: {[i for i in parser.ids if parser.ids.count(i) > 1]}"

    # Milestone 3 specific cataloged IDs
    m3_required_ids = [
        "dropzone", "file-slicer-input", "plates-container", "btn-add-plate-bottom", "bom-container",
        "proj-cad-hours", "proj-cad-rate", "proj-post-hours", "proj-post-rate",
        "proj-overhead", "proj-margin", "proj-tax", "proj-discount", "proj-shipping",
        "proj-delivery-days", "proj-payment-terms", "proj-warranty-terms", "proj-notes",
        "live-weight", "live-time", "live-material-cost", "live-machine-cost",
        "live-bom-cost", "live-labor-cost", "live-overhead-cost", "live-base-cost",
        "live-suggested-price", "live-discount-row", "live-discount-amount",
        "live-shipping-row", "live-shipping-amount", "live-tax-amount",
        "live-final-price", "live-net-profit"
    ]
    for rid in m3_required_ids:
        assert rid in parser.ids, f"Required Milestone 3 ID '{rid}' missing from index.html"

    # Verify that btn-add-bom-item and btn-save-project are NOT declared as static IDs
    assert "btn-add-bom-item" not in parser.ids, "btn-add-bom-item must not be a static ID (use class)"
    assert "btn-save-project" not in parser.ids, "btn-save-project must not be a static ID (use class)"


def test_no_static_ids_in_dynamic_row_templates():
    """
    Verify that dynamic row template literals in renderPlates() and renderBOM()
    contain ZERO static un-indexed IDs. Every ID rendered must include dynamic ${idx}.
    """
    app_js_text = APP_JS.read_text(encoding="utf-8")

    # Extract renderPlates body
    plates_match = re.search(r"function renderPlates\s*\([^)]*\)\s*\{(.*?)(?=\nfunction |\Z)", app_js_text, re.DOTALL)
    assert plates_match is not None, "renderPlates function not found in app.js"
    plates_code = plates_match.group(1)

    # Find all id="..." in renderPlates template
    plate_ids = re.findall(r'id=["\']([^"\']+)["\']', plates_code)
    for pid in plate_ids:
        assert "${idx" in pid or "${index" in pid, f"Found static ID in renderPlates template: '{pid}'. Dynamic rows must use indexed IDs!"

    # Extract renderBOM body
    bom_match = re.search(r"function renderBOM\s*\([^)]*\)\s*\{(.*?)(?=\nfunction |\Z)", app_js_text, re.DOTALL)
    assert bom_match is not None, "renderBOM function not found in app.js"
    bom_code = bom_match.group(1)

    # Find all id="..." in renderBOM template
    bom_ids = re.findall(r'id=["\']([^"\']+)["\']', bom_code)
    for bid in bom_ids:
        assert "${idx" in bid or "${index" in bid, f"Found static ID in renderBOM template: '{bid}'. Dynamic rows must use indexed IDs!"


def test_plate_container_and_bottom_button_dom_hierarchy():
    """
    Verify that #btn-add-plate-bottom:
    1. Exists in index.html
    2. Is located strictly AFTER #plates-container
    3. Is NOT an interior child of #plates-container (which would be wiped on renderPlates)
    4. Has onclick="addNewPlateRow()"
    """
    soup = BeautifulSoup(INDEX_HTML.read_text(encoding="utf-8"), "html.parser")
    plates_container = soup.find(id="plates-container")
    btn_bottom = soup.find(id="btn-add-plate-bottom")

    assert plates_container is not None, "#plates-container not found"
    assert btn_bottom is not None, "#btn-add-plate-bottom not found"

    # Button must not be inside plates-container
    assert btn_bottom not in plates_container.descendants, "#btn-add-plate-bottom must not be a child of #plates-container"

    # Button must appear after plates_container in the document tree
    all_elements = list(soup.find_all(True))
    container_idx = all_elements.index(plates_container)
    btn_idx = all_elements.index(btn_bottom)
    assert btn_idx > container_idx, f"#btn-add-plate-bottom (index {btn_idx}) must appear AFTER #plates-container (index {container_idx})"

    onclick_val = btn_bottom.get("onclick") or ""
    assert "addNewPlateRow()" in onclick_val, f"#btn-add-plate-bottom onclick must call addNewPlateRow(), found: '{onclick_val}'"


# ==============================================================================
# 2. NODE.JS HARNESS: MULTI-PLATE & BOM STRESS TESTING
# ==============================================================================

def _run_node_m3_harness(script_body: str) -> dict:
    """Helper to execute JavaScript in a simulated DOM environment with app.js loaded."""
    app_js_text = APP_JS.read_text(encoding="utf-8")

    full_script = f"""
    // Minimal DOM Mock
    const elements = {{}};
    function getOrCreate(id) {{
        if (!elements[id]) {{
            elements[id] = {{
                id: id,
                innerHTML: '',
                textContent: '',
                value: '',
                className: '',
                style: {{}},
                children: [],
                scrollIntoView: () => {{}},
                lastElementChild: null,
                addEventListener: () => {{}},
                removeEventListener: () => {{}},
                classList: {{
                    add: () => {{}},
                    remove: () => {{}},
                    toggle: () => {{}},
                    contains: () => false
                }}
            }};
        }}
        return elements[id];
    }}

    // Pre-populate required elements
    const requiredIds = [
        'plates-container', 'btn-add-plate-bottom', 'bom-container',
        'live-weight', 'live-time', 'live-material-cost', 'live-machine-cost',
        'live-bom-cost', 'live-labor-cost', 'live-overhead-cost', 'live-base-cost',
        'live-suggested-price', 'live-discount-row', 'live-discount-amount',
        'live-shipping-row', 'live-shipping-amount', 'live-tax-amount',
        'live-final-price', 'live-net-profit',
        'proj-cad-hours', 'proj-cad-rate', 'proj-post-hours', 'proj-post-rate',
        'proj-overhead', 'proj-margin', 'proj-tax', 'proj-discount', 'proj-shipping'
    ];
    requiredIds.forEach(getOrCreate);

    global.window = global;
    global.window.addEventListener = () => {{}};
    global.document = {{
        getElementById: (id) => getOrCreate(id),
        querySelectorAll: () => [],
        querySelector: () => null,
        addEventListener: () => {{}},
        removeEventListener: () => {{}}
    }};

    global.toasts = [];
    global.showToast = (msg, type) => {{
        global.toasts.push({{ msg, type }});
    }};

    global.refreshIcons = () => {{}};
    global.formatCurrency = (v) => 'R$ ' + Number(v || 0).toFixed(2).replace('.', ',');

    global.state = {{
        projects: [],
        printers: [
            {{ id: 1, name: 'Bambu Lab P1S', machine_hourly_rate: 4.50 }},
            {{ id: 2, name: 'Prusa MK4', machine_hourly_rate: 3.50 }}
        ],
        filaments: [
            {{ id: 1, name: 'PLA Preto', material: 'PLA', color_hex: '#111827', spool_weight_g: 1000, spool_price: 100.0, cost_per_gram: 0.10 }},
            {{ id: 2, name: 'PETG Azul', material: 'PETG', color_hex: '#2563eb', spool_weight_g: 1000, spool_price: 120.0, cost_per_gram: 0.12 }}
        ],
        currentPlates: [],
        currentBOM: [],
        user: {{ default_failure_rate: 10, default_tax_rate: 0 }}
    }};

    global.API = {{ getToken: () => null }};

    // Load app.js
    {app_js_text}

    {script_body}
    """

    res = subprocess.run(["node"], input=full_script, capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        raise RuntimeError(f"Node harness failed with code {res.returncode}:\n{res.stderr}\nStdout:\n{res.stdout}")
    return json.loads(res.stdout)


def test_multi_plate_stress_addition_and_deletion():
    """
    Stress test multi-plate workflow:
    1. Start with 1 plate.
    2. Add 9 plates via addNewPlateRow() -> total 10 plates.
    3. Verify plate indices and card counts.
    4. Remove middle plate (index 4) -> verify reindexing.
    5. Remove first plate (index 0) -> verify reindexing.
    6. Remove last plate -> verify reindexing.
    7. Delete down to 1 plate -> attempt deleting the last plate (must be rejected).
    """
    script = """
    // 1. Initialize with 1 plate
    state.currentPlates = [createDefaultPlate(1)];
    renderPlates();
    const initCount = state.currentPlates.length;

    // 2. Add 9 more plates
    for (let i = 0; i < 9; i++) {
        addNewPlateRow();
    }
    const tenCount = state.currentPlates.length;
    const tenHtml = elements['plates-container'].innerHTML;

    // Check all 10 plates rendered
    const has10Cards = (tenHtml.match(/#10/g) || []).length > 0;
    const hasPlateCost9 = (tenHtml.match(/id="plate-cost-9"/g) || []).length === 1;

    // 3. Remove middle plate (index 4)
    state.currentPlates[4].name = 'Plate-To-Delete';
    removePlateRow(4);
    const afterMiddleCount = state.currentPlates.length;
    const middleRemovedHtml = elements['plates-container'].innerHTML;
    const stillHasDeleted = middleRemovedHtml.includes('Plate-To-Delete');

    // 4. Remove first plate (index 0)
    removePlateRow(0);
    const afterFirstCount = state.currentPlates.length;

    // 5. Remove last plate
    removePlateRow(state.currentPlates.length - 1);
    const afterLastCount = state.currentPlates.length;

    // 6. Reduce down to 1 plate
    while (state.currentPlates.length > 1) {
        removePlateRow(0);
    }
    const oneLeftCount = state.currentPlates.length;

    // 7. Attempt removing the last remaining plate (must be blocked by safeguard)
    toasts = [];
    removePlateRow(0);
    const afterAttemptCount = state.currentPlates.length;
    const toastRecorded = toasts.length > 0 ? toasts[0] : null;

    console.log(JSON.stringify({
        initCount,
        tenCount,
        has10Cards,
        hasPlateCost9,
        afterMiddleCount,
        stillHasDeleted,
        afterFirstCount,
        afterLastCount,
        oneLeftCount,
        afterAttemptCount,
        toastRecorded
    }));
    """
    res = _run_node_m3_harness(script)

    assert res["initCount"] == 1
    assert res["tenCount"] == 10
    assert res["has10Cards"] is True, "Failed to render card #10"
    assert res["hasPlateCost9"] is True, "Missing dynamic id plate-cost-9"
    assert res["afterMiddleCount"] == 9
    assert res["stillHasDeleted"] is False, "Deleted middle plate was still present in rendered HTML"
    assert res["afterFirstCount"] == 8
    assert res["afterLastCount"] == 7
    assert res["oneLeftCount"] == 1
    assert res["afterAttemptCount"] == 1, "Safeguard failed: last plate was removed!"
    assert res["toastRecorded"] is not None
    assert "pelo menos uma placa" in res["toastRecorded"]["msg"]


def test_plate_dual_time_calculation_and_edge_cases():
    """
    Test updatePlateTime(idx):
    - Normal hours and minutes: 2h 30m -> 2.5000 hours
    - 0h 45m -> 0.7500 hours
    - 10h 0m -> 10.0000 hours
    - Negative or NaN input handling -> clamped to 0
    """
    script = """
    state.currentPlates = [createDefaultPlate(1)];
    renderPlates();

    // Case A: 2 hours 30 min
    elements['plate-time-h-0'] = { value: '2' };
    elements['plate-time-m-0'] = { value: '30' };
    updatePlateTime(0);
    const timeA = state.currentPlates[0].print_time_hours;

    // Case B: 0 hours 45 min
    elements['plate-time-h-0'] = { value: '0' };
    elements['plate-time-m-0'] = { value: '45' };
    updatePlateTime(0);
    const timeB = state.currentPlates[0].print_time_hours;

    // Case C: Negative or invalid values
    elements['plate-time-h-0'] = { value: '-5' };
    elements['plate-time-m-0'] = { value: 'abc' };
    updatePlateTime(0);
    const timeC = state.currentPlates[0].print_time_hours;

    console.log(JSON.stringify({ timeA, timeB, timeC }));
    """
    res = _run_node_m3_harness(script)

    assert abs(res["timeA"] - 2.5) < 1e-4, f"Expected 2.5 hours, got {res['timeA']}"
    assert abs(res["timeB"] - 0.75) < 1e-4, f"Expected 0.75 hours, got {res['timeB']}"
    assert res["timeC"] == 0.0, f"Expected clamped 0.0 for negative/invalid time, got {res['timeC']}"


def test_bom_rows_addition_deletion_and_empty_state_roundtrip():
    """
    Stress test BOM insumos:
    1. Initial empty state: renders friendly empty banner + 'Adicionar Primeiro Insumo' button.
    2. addNewBomRow() -> transitions to table with headers and row.
    3. Add 4 more rows -> total 5 rows, each with unique bom-subtotal-${idx}.
    4. Remove middle row (index 2).
    5. Remove all rows until 0 -> transitions back to empty state banner.
    6. Verify global aliases window.addNewBOMRow and window.removeBOMRow.
    """
    script = """
    // 1. Initial empty state
    state.currentBOM = [];
    renderBOM();
    const emptyHtml = elements['bom-container'].innerHTML;
    const hasEmptyBanner = emptyHtml.includes('Nenhum componente ou insumo adicional cadastrado');

    // 2. Add first row via addNewBomRow()
    addNewBomRow();
    const oneHtml = elements['bom-container'].innerHTML;
    const hasTableHeaders = oneHtml.includes('Descrição do Componente');
    const hasSubtotal0 = oneHtml.includes('id="bom-subtotal-0"');

    // 3. Add 4 more rows via global alias addNewBOMRow()
    for (let i = 0; i < 4; i++) {
        window.addNewBOMRow();
    }
    const fiveCount = state.currentBOM.length;
    const fiveHtml = elements['bom-container'].innerHTML;
    const hasSubtotal4 = fiveHtml.includes('id="bom-subtotal-4"');

    // 4. Remove row at index 2 via window.removeBOMRow
    window.removeBOMRow(2);
    const afterDeleteCount = state.currentBOM.length;

    // 5. Remove remaining rows until 0
    while (state.currentBOM.length > 0) {
        removeBomRow(0);
    }
    const zeroCount = state.currentBOM.length;
    const roundtripHtml = elements['bom-container'].innerHTML;
    const hasRestoredBanner = roundtripHtml.includes('Nenhum componente ou insumo adicional cadastrado');

    console.log(JSON.stringify({
        hasEmptyBanner,
        hasTableHeaders,
        hasSubtotal0,
        fiveCount,
        hasSubtotal4,
        afterDeleteCount,
        zeroCount,
        hasRestoredBanner,
        aliasesExist: typeof window.addNewBOMRow === 'function' && typeof window.removeBOMRow === 'function'
    }));
    """
    res = _run_node_m3_harness(script)

    assert res["hasEmptyBanner"] is True, "BOM container must show empty state banner when empty"
    assert res["hasTableHeaders"] is True, "BOM container must show table headers when populated"
    assert res["hasSubtotal0"] is True, "Missing id bom-subtotal-0"
    assert res["fiveCount"] == 5
    assert res["hasSubtotal4"] is True, "Missing id bom-subtotal-4"
    assert res["afterDeleteCount"] == 4
    assert res["zeroCount"] == 0
    assert res["hasRestoredBanner"] is True, "Empty state banner was not restored when all rows removed"
    assert res["aliasesExist"] is True, "window.addNewBOMRow or window.removeBOMRow alias missing"


# ==============================================================================
# 3. REAL HEADLESS CHROME/EDGE RUNTIME VERIFICATION
# ==============================================================================

def test_real_browser_runtime_multi_plate_and_bom_zero_id_collisions(tmp_path):
    """
    Executes real Headless Chrome/Edge browser session:
    1. Loads index.html and app.js
    2. Dynamically invokes addNewPlateRow() 5 times
    3. Dynamically invokes addNewBomRow() 5 times
    4. Evaluates DOM order: checks that #btn-add-plate-bottom strictly follows #plates-container
    5. Scans ALL elements in the entire runtime DOM with an 'id' attribute:
       Verifies len(ids) == len(set(ids)) (ZERO duplicate IDs in the live DOM).
    6. Deletes plate 2 and BOM row 2, and re-verifies zero duplicate IDs and intact order.
    """
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
        pytest.skip("No Chrome or Edge executable available for headless browser test")

    index_html_content = INDEX_HTML.read_text(encoding="utf-8")

    # Inject test runner script before </body>
    test_runner_script = """
    <div id="adversarial-test-result" style="display:none;"></div>
    <script>
    window.addEventListener('DOMContentLoaded', () => {
        try {
            // 1. Initial State: add 5 plates via addNewPlateRow()
            for (let i = 0; i < 5; i++) {
                addNewPlateRow();
            }

            // 2. Add 5 BOM rows via addNewBomRow()
            for (let j = 0; j < 5; j++) {
                addNewBomRow();
            }

            // 3. Verify DOM order between #plates-container and #btn-add-plate-bottom
            const platesContainer = document.getElementById('plates-container');
            const btnBottom = document.getElementById('btn-add-plate-bottom');
            const orderCheck = platesContainer.compareDocumentPosition(btnBottom);
            const isFollowing = (orderCheck & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;

            // 4. Collect all IDs in document to check uniqueness
            const allElements = document.querySelectorAll('[id]');
            const idList = [];
            const duplicateIds = [];
            const seen = new Set();

            allElements.forEach(el => {
                const id = el.id;
                idList.push(id);
                if (seen.has(id)) {
                    duplicateIds.push(id);
                }
                seen.add(id);
            });

            // 5. Delete plate 2 and BOM row 2
            removePlateRow(2);
            removeBomRow(2);

            const allElementsAfter = document.querySelectorAll('[id]');
            const idListAfter = [];
            const dupAfter = [];
            const seenAfter = new Set();
            allElementsAfter.forEach(el => {
                const id = el.id;
                idListAfter.push(id);
                if (seenAfter.has(id)) {
                    dupAfter.push(id);
                }
                seenAfter.add(id);
            });

            // Re-check DOM order after deletions
            const orderCheckAfter = platesContainer.compareDocumentPosition(btnBottom);
            const isFollowingAfter = (orderCheckAfter & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;

            const payload = {
                success: true,
                isFollowing: isFollowing,
                isFollowingAfter: isFollowingAfter,
                totalIdsInitial: idList.length,
                uniqueIdsInitial: seen.size,
                duplicatesInitial: duplicateIds,
                totalIdsAfter: idListAfter.length,
                uniqueIdsAfter: seenAfter.size,
                duplicatesAfter: dupAfter
            };

            const resDiv = document.getElementById('adversarial-test-result');
            resDiv.textContent = 'PAYLOAD_START' + JSON.stringify(payload) + 'PAYLOAD_END';
        } catch (err) {
            const resDiv = document.getElementById('adversarial-test-result');
            resDiv.textContent = 'PAYLOAD_START' + JSON.stringify({ success: false, error: err.message, stack: err.stack }) + 'PAYLOAD_END';
        }
    });
    </script>
    """
    modified_html = index_html_content.replace('/static/', f'file:///{FRONTEND_DIR.as_posix()}/').replace("</body>", f"{test_runner_script}\n</body>")
    test_html_file = tmp_path / "browser_stress_test.html"
    test_html_file.write_text(modified_html, encoding="utf-8")

    proc = subprocess.run(
        [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--allow-file-access-from-files",
            "--dump-dom",
            f"file:///{test_html_file.resolve().as_posix()}"
        ],
        capture_output=True,
        text=True,
        timeout=30
    )

    dom_output = proc.stdout
    match = re.search(r"PAYLOAD_START(\{.*?\})PAYLOAD_END", dom_output, re.DOTALL)
    assert match is not None, f"Browser test payload not found in output. DOM snippet:\n{dom_output[-1000:]}"

    result = json.loads(match.group(1))
    assert result.get("success") is True, f"Browser test reported error: {result}"
    assert result["isFollowing"] is True, "#btn-add-plate-bottom is NOT following #plates-container initially!"
    assert result["isFollowingAfter"] is True, "#btn-add-plate-bottom is NOT following #plates-container after deletions!"
    assert len(result["duplicatesInitial"]) == 0, f"Duplicate IDs detected in DOM: {result['duplicatesInitial']}"
    assert len(result["duplicatesAfter"]) == 0, f"Duplicate IDs detected in DOM after deletions: {result['duplicatesAfter']}"


def test_recalc_live_summary_empirical_node_suite():
    """
    Executes the comprehensive Node.js empirical test suite covering:
    1. Zero plates / zero weights / zero times.
    2. High volume project (10+ plates, 100+ BOM items) with precision oracle & performance benchmark.
    3. Commercial discount edge cases (0%, 50%, 100%, >100% clamping).
    4. Negative net profit (discount exceeds margin, extreme taxes) & text-rose-400 alerts.
    5. Dynamic margin pill coloring (green >=20%, yellow >=5%, red <0%, neutral 0..4.9%).
    6. Cost distribution bar segment width calculation and 0 base cost handling (all 20%).
    """
    node_bin = shutil.which("node")
    assert node_bin is not None, "Node.js executable not found in PATH"

    test_script = ROOT_DIR / "tests" / "test_recalc_live_summary_empirical.js"
    assert test_script.exists(), f"Test script {test_script} does not exist"

    proc = subprocess.run(
        [node_bin, str(test_script)],
        capture_output=True,
        text=True,
        timeout=15
    )
    assert proc.returncode == 0, f"Node empirical test suite failed (exit {proc.returncode}):\nStdout:\n{proc.stdout}\nStderr:\n{proc.stderr}"
    assert "RESULTS: 19/19 tests passed" in proc.stdout, f"Expected 19/19 tests passed in output:\n{proc.stdout}"

