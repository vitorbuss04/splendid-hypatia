"""
Adversarial Stress Verification Suite for Milestone 2: Dashboard & Navigation.
Author: Challenger M2.1 (teamwork_preview_challenger)

Tests:
1. Dashboard rendering with 0 projects (onboarding banner visibility vs hidden table)
2. Dashboard rendering with 1, 5, and 10+ projects (table row count, stat counters)
3. Status badge styling and text formatting on all 6 statuses (draft, quoted, approved, in_production, completed, cancelled)
4. CSS styling verification for all status badges and contrast/visibility
5. Navigation shell integrity and active link classes
"""

import json
import re
import subprocess
from pathlib import Path
from bs4 import BeautifulSoup
import pytest

ROOT_DIR = Path(__file__).parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
INDEX_HTML = FRONTEND_DIR / "index.html"
COMPONENTS_CSS = FRONTEND_DIR / "css" / "components.css"
APP_JS = FRONTEND_DIR / "js" / "app.js"

ALL_STATUSES = ["draft", "quoted", "approved", "in_production", "completed", "cancelled"]
STATUS_LABELS_PT = {
    "draft": "Rascunho",
    "quoted": "Orçado",
    "approved": "Aprovado",
    "in_production": "Em Produção",
    "completed": "Concluído",
    "cancelled": "Cancelado"
}


# ==============================================================================
# 1. STATIC DOM & HTML CHECKS
# ==============================================================================

def test_dashboard_and_navigation_static_dom_structure():
    """Verify static DOM structure in index.html for dashboard and navigation."""
    content = INDEX_HTML.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")

    # 1. Navigation items
    nav_ids = ["nav-dashboard", "nav-projects", "nav-printers", "nav-filaments", "nav-settings"]
    for nid in nav_ids:
        el = soup.find(id=nid)
        assert el is not None, f"Missing navigation element #{nid}"
        assert f"navigateTo('{nid.replace('nav-', '')}')" in (el.get("onclick") or "")

    # 2. Dashboard stat counters
    stat_ids = ["stat-projects-count", "stat-active-quotes", "stat-printers-count", "stat-filaments-count"]
    for sid in stat_ids:
        el = soup.find(id=sid)
        assert el is not None, f"Missing stat counter #{sid}"

    # 3. Empty account banner
    banner = soup.find(id="dashboard-empty-banner")
    assert banner is not None, "Missing #dashboard-empty-banner"
    assert "hidden" in banner.get("class", []), "#dashboard-empty-banner must be initially hidden"

    # 4. Recent projects container
    recent = soup.find(id="dashboard-recent-projects")
    assert recent is not None, "Missing #dashboard-recent-projects"

    # 5. Project filter chips
    chips = soup.find_all(class_=re.compile(r"\bproject-filter-chip\b"))
    assert len(chips) >= 7, f"Expected at least 7 status filter chips (all + 6 statuses), found {len(chips)}"
    chip_statuses = [c.get("data-status") for c in chips]
    assert "all" in chip_statuses
    for st in ALL_STATUSES:
        assert st in chip_statuses, f"Missing filter chip for status '{st}'"


# ==============================================================================
# 2. STATUS BADGE CSS STYLING
# ==============================================================================

def test_status_badge_styling_all_statuses():
    """Verify that all 6 statuses have explicit CSS rules with colors and backgrounds."""
    css_content = COMPONENTS_CSS.read_text(encoding="utf-8")

    # Check that base badge styling covers all 6 badges
    for status in ALL_STATUSES:
        badge_class = f".badge-{status}"
        assert badge_class in css_content, f"CSS must declare {badge_class}"

        # Extract definition for this badge
        # Pattern looks for .badge-{status} { ... }
        pattern = re.compile(rf"{re.escape(badge_class)}\s*\{{([^}}]+)\}}", re.DOTALL)
        match = pattern.search(css_content)
        assert match is not None, f"CSS rule body not found for {badge_class}"
        body = match.group(1)

        assert "background-color" in body, f"{badge_class} missing background-color"
        assert "color" in body, f"{badge_class} missing text color"
        assert "border" in body, f"{badge_class} missing border styling"


# ==============================================================================
# 3. NODE.JS RUNTIME VERIFICATION (EMPIRICAL ORACLE)
# ==============================================================================

def _run_node_harness(script_body: str) -> dict:
    """Helper to run a Node.js test harness that loads app.js functions and returns JSON result."""
    app_js_text = APP_JS.read_text(encoding="utf-8")

    full_script = f"""
    // Minimal DOM environment for app.js testing
    const classListMock = (initialClasses = []) => {{
        const classes = new Set(initialClasses);
        return {{
            add: (c) => classes.add(c),
            remove: (c) => classes.delete(c),
            contains: (c) => classes.has(c),
            toggle: (c, force) => {{
                if (force === undefined) {{
                    classes.has(c) ? classes.delete(c) : classes.add(c);
                }} else if (force) {{
                    classes.add(c);
                }} else {{
                    classes.delete(c);
                }}
            }},
            toArray: () => Array.from(classes)
        }};
    }};

    const elements = {{
        'stat-projects-count': {{ textContent: '', innerHTML: '', classList: classListMock() }},
        'stat-printers-count': {{ textContent: '', innerHTML: '', classList: classListMock() }},
        'stat-filaments-count': {{ textContent: '', innerHTML: '', classList: classListMock() }},
        'stat-active-quotes': {{ textContent: '', innerHTML: '', classList: classListMock() }},
        'dashboard-empty-banner': {{ textContent: '', innerHTML: '', classList: classListMock(['hidden']) }},
        'dashboard-recent-projects': {{ textContent: '', innerHTML: '', classList: classListMock() }},
        'projects-table-container': {{ textContent: '', innerHTML: '', classList: classListMock() }},
        'project-search-input': {{ value: '', classList: classListMock() }}
    }};

    global.window = {{
        addEventListener: () => {{}},
        removeEventListener: () => {{}},
        lucide: {{ createIcons: () => {{}} }}
    }};

    const chipsMock = [
        {{ status: 'all', className: '', getAttribute: (a) => a === 'data-status' ? 'all' : '' }},
        {{ status: 'draft', className: '', getAttribute: (a) => a === 'data-status' ? 'draft' : '' }},
        {{ status: 'quoted', className: '', getAttribute: (a) => a === 'data-status' ? 'quoted' : '' }},
        {{ status: 'approved', className: '', getAttribute: (a) => a === 'data-status' ? 'approved' : '' }},
        {{ status: 'in_production', className: '', getAttribute: (a) => a === 'data-status' ? 'in_production' : '' }},
        {{ status: 'completed', className: '', getAttribute: (a) => a === 'data-status' ? 'completed' : '' }},
        {{ status: 'cancelled', className: '', getAttribute: (a) => a === 'data-status' ? 'cancelled' : '' }}
    ];
    global.chipsMock = chipsMock;

    global.document = {{
        getElementById: (id) => elements[id] || null,
        querySelectorAll: (selector) => {{
            if (selector === '.project-filter-chip') return chipsMock;
            return [];
        }},
        querySelector: (selector) => null,
        addEventListener: () => {{}},
        removeEventListener: () => {{}}
    }};

    global.refreshIcons = () => {{}};
    global.formatCurrency = (v) => 'R$ ' + Number(v || 0).toFixed(2);

    // Global state mock
    global.state = {{
        projects: [],
        printers: [],
        filaments: [],
        user: {{ full_name: 'Test Tester', company_name: 'Test Workshop', email: 'test@workshop.com' }},
        projectStatusFilter: 'all'
    }};

    // Stub API object
    global.API = {{
        pdf: {{ preview: () => {{}} }},
        projects: {{ list: async () => [] }},
        printers: {{ list: async () => [] }},
        filaments: {{ list: async () => [] }}
    }};

    // Extract formatStatus, renderDashboard, renderRecentProjects, renderProjectsTable
    {app_js_text}

    {script_body}
    """

    res = subprocess.run(["node"], input=full_script, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Node harness failed: {res.stderr}\nStdout: {res.stdout}")
    return json.loads(res.stdout)


def test_dashboard_rendering_0_projects():
    """
    Empirical Oracle Test 1:
    - Clean account (0 projects, 0 printers, 0 filaments):
      -> empty banner VISIBLE (no 'hidden' class)
      -> recent table HIDDEN (renders empty placeholder, NO <table>)
    - Non-clean account (0 projects, but 1 printer):
      -> empty banner HIDDEN ('hidden' class present)
      -> recent table renders empty placeholder
    """
    script = """
    // Case 1A: 0 projects, 0 printers, 0 filaments
    state.projects = [];
    state.printers = [];
    state.filaments = [];
    renderDashboard();

    const banner1Hidden = elements['dashboard-empty-banner'].classList.contains('hidden');
    const recentHtml1 = elements['dashboard-recent-projects'].innerHTML;
    const statProjects1 = elements['stat-projects-count'].textContent;
    const statActive1 = elements['stat-active-quotes'].textContent;

    // Case 1B: 0 projects, but 1 printer
    state.printers = [{ id: 1, name: 'Ender 3' }];
    renderDashboard();

    const banner2Hidden = elements['dashboard-empty-banner'].classList.contains('hidden');
    const recentHtml2 = elements['dashboard-recent-projects'].innerHTML;

    console.log(JSON.stringify({
        case1A: {
            bannerHidden: banner1Hidden,
            hasTable: recentHtml1.includes('<table'),
            hasEmptyPlaceholder: recentHtml1.includes('Nenhum orçamento cadastrado ainda'),
            statProjects: statProjects1,
            statActive: statActive1
        },
        case1B: {
            bannerHidden: banner2Hidden,
            hasTable: recentHtml2.includes('<table'),
            hasEmptyPlaceholder: recentHtml2.includes('Nenhum orçamento cadastrado ainda')
        }
    }));
    """
    result = _run_node_harness(script)

    # 1A: Clean account
    assert result["case1A"]["bannerHidden"] is False, "Empty banner must NOT be hidden when account is completely empty"
    assert result["case1A"]["hasTable"] is False, "No table should be rendered when projects count is 0"
    assert result["case1A"]["hasEmptyPlaceholder"] is True, "Empty placeholder must be displayed"
    assert result["case1A"]["statProjects"] == 0 or result["case1A"]["statProjects"] == "0"
    assert result["case1A"]["statActive"] == 0 or result["case1A"]["statActive"] == "0"

    # 1B: Account with 1 printer
    assert result["case1B"]["bannerHidden"] is True, "Empty banner MUST be hidden when user already has a printer"
    assert result["case1B"]["hasTable"] is False, "No table should be rendered when projects count is 0"
    assert result["case1B"]["hasEmptyPlaceholder"] is True, "Empty placeholder must still be displayed in recent table"


def test_dashboard_rendering_1_5_and_10_plus_projects():
    """
    Empirical Oracle Test 2:
    - 1 project: renders table with 1 row, banner is hidden, stat-projects-count = 1
    - 5 projects: renders table with 5 rows, stat-projects-count = 5
    - 12 projects: recent table capped at 5 rows (slice(0, 5)), stat-projects-count = 12
    """
    script = """
    function makeDummyProject(id, status = 'draft') {
        return {
            id: id,
            name: `Projeto Teste ${id}`,
            client_name: `Cliente ${id}`,
            plates_count: 2,
            total_time_hours: 4.5,
            base_cost: 35.0,
            final_price_to_client: 75.0,
            status: status
        };
    }

    // 1 Project
    state.projects = [makeDummyProject(1, 'draft')];
    state.printers = [];
    state.filaments = [];
    renderDashboard();

    const bannerHidden1 = elements['dashboard-empty-banner'].classList.contains('hidden');
    const recentHtml1 = elements['dashboard-recent-projects'].innerHTML;
    const rows1 = (recentHtml1.match(/<tr class="hover:bg-slate-800/g) || []).length;
    const stat1 = elements['stat-projects-count'].textContent;
    const active1 = elements['stat-active-quotes'].textContent;

    // 5 Projects
    state.projects = [
        makeDummyProject(1, 'draft'),
        makeDummyProject(2, 'quoted'),
        makeDummyProject(3, 'approved'),
        makeDummyProject(4, 'in_production'),
        makeDummyProject(5, 'completed')
    ];
    renderDashboard();

    const recentHtml5 = elements['dashboard-recent-projects'].innerHTML;
    const rows5 = (recentHtml5.match(/<tr class="hover:bg-slate-800/g) || []).length;
    const stat5 = elements['stat-projects-count'].textContent;
    const active5 = elements['stat-active-quotes'].textContent;

    // 12 Projects (10+)
    const twelve = [];
    for (let i = 1; i <= 12; i++) {
        twelve.push(makeDummyProject(i, i % 2 === 0 ? 'completed' : 'quoted'));
    }
    state.projects = twelve;
    renderDashboard();

    const recentHtml12 = elements['dashboard-recent-projects'].innerHTML;
    const rows12 = (recentHtml12.match(/<tr class="hover:bg-slate-800/g) || []).length;
    const stat12 = elements['stat-projects-count'].textContent;
    const active12 = elements['stat-active-quotes'].textContent;

    console.log(JSON.stringify({
        one: { bannerHidden: bannerHidden1, rows: rows1, stat: stat1, active: active1, hasTable: recentHtml1.includes('<table') },
        five: { rows: rows5, stat: stat5, active: active5, hasTable: recentHtml5.includes('<table') },
        twelve: { rows: rows12, stat: stat12, active: active12, hasTable: recentHtml12.includes('<table') }
    }));
    """
    result = _run_node_harness(script)

    # 1 Project assertions
    assert result["one"]["bannerHidden"] is True, "Empty banner must be hidden when 1 project exists"
    assert result["one"]["hasTable"] is True, "Table must be rendered when 1 project exists"
    assert result["one"]["rows"] == 1, f"Expected exactly 1 row, got {result['one']['rows']}"
    assert int(result["one"]["stat"]) == 1
    assert int(result["one"]["active"]) == 1

    # 5 Projects assertions
    assert result["five"]["hasTable"] is True
    assert result["five"]["rows"] == 5, f"Expected exactly 5 rows, got {result['five']['rows']}"
    assert int(result["five"]["stat"]) == 5
    # Active quotes: draft(1), quoted(1), in_production(1) -> 3 active
    assert int(result["five"]["active"]) == 3

    # 12 Projects assertions (10+)
    assert result["twelve"]["hasTable"] is True
    assert result["twelve"]["rows"] == 5, f"Recent table MUST cap at 5 rows, got {result['twelve']['rows']}"
    assert int(result["twelve"]["stat"]) == 12
    # 6 odd projects are 'quoted' (active)
    assert int(result["twelve"]["active"]) == 6


def test_status_badge_formatting_all_statuses():
    """
    Empirical Oracle Test 3:
    Verify formatStatus() output and badge class rendering for all 6 statuses.
    """
    script = """
    const statuses = ['draft', 'quoted', 'approved', 'in_production', 'completed', 'cancelled'];
    const results = {};
    for (const s of statuses) {
        results[s] = formatStatus(s);
    }
    // Test fallback for unknown status
    results['unknown_custom'] = formatStatus('unknown_custom');

    console.log(JSON.stringify(results));
    """
    res = _run_node_harness(script)

    for st in ALL_STATUSES:
        expected_label = STATUS_LABELS_PT[st]
        assert res[st] == expected_label, f"Status '{st}' formatted as '{res[st]}', expected '{expected_label}'"

    assert res["unknown_custom"] == "unknown_custom", "Unknown status should fallback to original string"


def test_projects_view_multi_criteria_filtering():
    """
    Empirical Oracle Test 4:
    Verify that renderProjectsTable() filters by both text query and status chip correctly.
    """
    script = """
    state.projects = [
        { id: 1, name: 'Engrenagem Helicoidal', client_name: 'Oficina Alpha', plates_count: 1, total_time_hours: 2, base_cost: 20, final_price_to_client: 50, status: 'draft' },
        { id: 2, name: 'Suporte GoPro', client_name: 'João Ciclista', plates_count: 1, total_time_hours: 1.5, base_cost: 15, final_price_to_client: 40, status: 'approved' },
        { id: 3, name: 'Gabinete Raspberry Pi', client_name: 'Oficina Alpha', plates_count: 2, total_time_hours: 5, base_cost: 45, final_price_to_client: 110, status: 'completed' },
        { id: 4, name: 'Vaso Voronoi', client_name: 'Maria Decor', plates_count: 1, total_time_hours: 8, base_cost: 60, final_price_to_client: 150, status: 'draft' }
    ];

    // Filter 1: All
    renderProjectsTable('', 'all');
    const htmlAll = elements['projects-table-container'].innerHTML;
    const rowsAll = (htmlAll.match(/<tr class="hover:bg-slate-800/g) || []).length;

    // Filter 2: Text search 'Oficina'
    renderProjectsTable('Oficina', 'all');
    const htmlText = elements['projects-table-container'].innerHTML;
    const rowsText = (htmlText.match(/<tr class="hover:bg-slate-800/g) || []).length;

    // Filter 3: Status 'draft'
    renderProjectsTable('', 'draft');
    const htmlDraft = elements['projects-table-container'].innerHTML;
    const rowsDraft = (htmlDraft.match(/<tr class="hover:bg-slate-800/g) || []).length;

    // Filter 4: Combined search 'Oficina' + status 'draft' (Project 1 only)
    renderProjectsTable('Oficina', 'draft');
    const htmlCombined = elements['projects-table-container'].innerHTML;
    const rowsCombined = (htmlCombined.match(/<tr class="hover:bg-slate-800/g) || []).length;

    // Filter 5: No matches
    renderProjectsTable('InexistenteXYZ', 'all');
    const htmlEmpty = elements['projects-table-container'].innerHTML;
    const rowsEmpty = (htmlEmpty.match(/<tr class="hover:bg-slate-800/g) || []).length;
    const hasEmptyFeedback = htmlEmpty.includes('Nenhum projeto encontrado');

    console.log(JSON.stringify({
        rowsAll,
        rowsText,
        rowsDraft,
        rowsCombined,
        rowsEmpty,
        hasEmptyFeedback
    }));
    """
    res = _run_node_harness(script)

    assert res["rowsAll"] == 4, f"Expected 4 rows for 'all', got {res['rowsAll']}"
    assert res["rowsText"] == 2, f"Expected 2 rows for 'Oficina', got {res['rowsText']}"
    assert res["rowsDraft"] == 2, f"Expected 2 rows for 'draft', got {res['rowsDraft']}"
    assert res["rowsCombined"] == 1, f"Expected 1 row for 'Oficina' + 'draft', got {res['rowsCombined']}"
    assert res["rowsEmpty"] == 0, f"Expected 0 rows for nonexistent query, got {res['rowsEmpty']}"
    assert res["hasEmptyFeedback"] is True, "Empty search should display 'Nenhum projeto encontrado'"


def test_browser_headless_dashboard_and_navigation(tmp_path):
    """
    Empirical Oracle Test 5 (Headless Chrome/Edge):
    Executes actual browser rendering on index.html verifying:
    1. Navigation transitions (navigateTo toggles .hidden on views and active classes on nav buttons).
    2. Dynamic dashboard updates in real DOM for 0 projects, 1 project, and 10 projects.
    3. Status badge rendering and classes in browser DOM.
    """
    chrome_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    browser = next((c for c in chrome_candidates if Path(c).exists()), None)
    if not browser:
        pytest.skip("No Chrome or Edge browser available")

    # Read index.html and inject test runner script
    index_content = INDEX_HTML.read_text(encoding="utf-8")
    js_dir = (FRONTEND_DIR / "js").resolve().as_posix()
    index_content = index_content.replace("/static/js/", f"file:///{js_dir}/")
    
    # We inject a test harness before </body> that tests DOM state and writes JSON into #browser-test-output
    test_snippet = """
    <div id="browser-test-output"></div>
    <script>
    window.addEventListener('DOMContentLoaded', () => {
        try {
            const results = {};

            // 1. Initial State
            results.initialDashboardHidden = document.getElementById('view-dashboard').classList.contains('hidden');
            results.initialBannerHidden = document.getElementById('dashboard-empty-banner').classList.contains('hidden');

            // 2. Test 0 projects (clean account)
            state.projects = [];
            state.printers = [];
            state.filaments = [];
            renderDashboard();

            results.cleanBannerHidden = document.getElementById('dashboard-empty-banner').classList.contains('hidden');
            results.recentHasTableClean = !!document.querySelector('#dashboard-recent-projects table');
            results.recentHasPlaceholder = document.getElementById('dashboard-recent-projects').innerHTML.includes('Nenhum orçamento cadastrado ainda');

            // 3. Test 1 project
            state.projects = [{
                id: 1,
                name: 'Projeto 1',
                client_name: 'Cliente Alpha',
                plates_count: 1,
                total_time_hours: 2.0,
                base_cost: 20.0,
                final_price_to_client: 50.0,
                status: 'draft'
            }];
            renderDashboard();

            results.oneProjBannerHidden = document.getElementById('dashboard-empty-banner').classList.contains('hidden');
            results.oneProjRows = document.querySelectorAll('#dashboard-recent-projects tbody tr').length;
            results.oneProjBadge = !!document.querySelector('#dashboard-recent-projects .badge-draft');

            // 4. Test 10 projects (cap at 5 rows)
            const statuses = ['draft', 'quoted', 'approved', 'in_production', 'completed', 'cancelled'];
            state.projects = [];
            for (let i = 1; i <= 10; i++) {
                state.projects.push({
                    id: i,
                    name: 'Projeto ' + i,
                    client_name: 'Cliente ' + i,
                    plates_count: 1,
                    total_time_hours: 1.0,
                    base_cost: 10.0,
                    final_price_to_client: 30.0,
                    status: statuses[(i - 1) % statuses.length]
                });
            }
            renderDashboard();

            results.tenProjRows = document.querySelectorAll('#dashboard-recent-projects tbody tr').length;
            results.statProjectsText = document.getElementById('stat-projects-count').textContent;

            // 5. Test Navigation transition
            navigateTo('projects');
            results.navDashboardHidden = document.getElementById('view-dashboard').classList.contains('hidden');
            results.navProjectsHidden = document.getElementById('view-projects').classList.contains('hidden');
            results.navProjectsActive = document.getElementById('nav-projects').classList.contains('bg-blue-600');

            document.getElementById('browser-test-output').textContent = JSON.stringify(results);
        } catch (e) {
            document.getElementById('browser-test-output').textContent = JSON.stringify({ error: e.toString(), stack: e.stack });
        }
    });
    </script>
    """

    injected_html = index_content.replace("</body>", f"{test_snippet}\n</body>")
    test_file = tmp_path / "index_test.html"
    test_file.write_text(injected_html, encoding="utf-8")

    proc = subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--dump-dom", f"file:///{test_file.resolve().as_posix()}"],
        capture_output=True,
        text=True,
        timeout=15
    )

    soup = BeautifulSoup(proc.stdout, "html.parser")
    out_div = soup.find(id="browser-test-output")
    assert out_div is not None, "Browser failed to dump DOM or #browser-test-output missing"
    assert out_div.text.strip(), "No output written by browser test harness"

    data = json.loads(out_div.text)
    assert "error" not in data, f"Browser encountered JavaScript error: {data.get('error')}\n{data.get('stack')}"

    # Assertions
    assert data["initialDashboardHidden"] is False, "Dashboard view should initially be visible"
    assert data["cleanBannerHidden"] is False, "Empty banner must be visible when account has 0 items"
    assert data["recentHasTableClean"] is False, "Recent projects must not have a table when 0 projects"
    assert data["recentHasPlaceholder"] is True, "Recent projects must show empty placeholder"

    assert data["oneProjBannerHidden"] is True, "Empty banner must be hidden when 1 project exists"
    assert data["oneProjRows"] == 1, "Expected 1 row for 1 project"
    assert data["oneProjBadge"] is True, "Badge .badge-draft must be present in recent row"

    assert data["tenProjRows"] == 5, f"Recent projects must be capped at 5 rows, got {data['tenProjRows']}"
    assert int(data["statProjectsText"]) == 10, f"Stat counter must show 10, got {data['statProjectsText']}"

    assert data["navDashboardHidden"] is True, "Dashboard view must be hidden after navigateTo('projects')"
    assert data["navProjectsHidden"] is False, "Projects view must be visible after navigateTo('projects')"
    assert data["navProjectsActive"] is True, "nav-projects button must have active class bg-blue-600"


def test_adversarial_filter_projects_stress_cases():
    """
    Adversarial Challenge 1 & 2:
    Empirically test filterProjects() & renderProjectsTable():
    1. Mixed case in search query (e.g. eNgReNaGeM, mEcÂnIcA).
    2. Special literal characters in query ([PRO], #01, (v2.0), 45°, 50x).
    3. Regex metacharacters without regex injection crash ([, ], *, +, ?, \\, (, ), ^, $, .).
    4. Empty query ("") and whitespace-only query ("   ").
    5. Status chip selection for all 6 statuses and chip styling classes.
    6. Combined search + status filtering (matching and disjoint sets).
    7. clearProjectFilters() resetting search text, chip state, and restoring all items.
    """
    script = """
    state.projects = [
        { id: 1, name: 'Engrenagem Cilíndrica #01 [PRO]', client_name: 'Oficina Mecânica São José', plates_count: 2, total_time_hours: 4.5, base_cost: 30, final_price_to_client: 80, status: 'draft' },
        { id: 2, name: 'Case Raspberry Pi 4 (v2.0)', client_name: 'TechMaker Soluções', plates_count: 1, total_time_hours: 2.0, base_cost: 15, final_price_to_client: 45, status: 'quoted' },
        { id: 3, name: 'Action Figure - Dragão Articulado', client_name: 'Lucas Coleções', plates_count: 3, total_time_hours: 12.0, base_cost: 65, final_price_to_client: 180, status: 'approved' },
        { id: 4, name: 'Gabarito de Corte 45°', client_name: 'Oficina Mecânica São José', plates_count: 1, total_time_hours: 3.0, base_cost: 25, final_price_to_client: 60, status: 'in_production' },
        { id: 5, name: 'Chaveiro Personalizado (Lote 50x)', client_name: 'Marketing Corp', plates_count: 5, total_time_hours: 10.0, base_cost: 50, final_price_to_client: 150, status: 'completed' },
        { id: 6, name: 'Luminária Litofania 100x150mm', client_name: 'Ana Carolina', plates_count: 2, total_time_hours: 8.5, base_cost: 40, final_price_to_client: 110, status: 'cancelled' }
    ];

    const results = {};

    // 1. Mixed Case Project Name
    elements['project-search-input'].value = 'eNgReNaGeM';
    filterProjects();
    results.mixedProjNameRows = (elements['projects-table-container'].innerHTML.match(/<tr class="hover:bg-slate-800/g) || []).length;

    // 2. Mixed Case Client Name
    elements['project-search-input'].value = 'mEcÂnIcA';
    filterProjects();
    results.mixedClientRows = (elements['projects-table-container'].innerHTML.match(/<tr class="hover:bg-slate-800/g) || []).length;

    // 3. Special Characters
    const specialQueries = ['[PRO]', '#01', '(v2.0)', '45°', '50x'];
    results.specials = {};
    for (const sq of specialQueries) {
        elements['project-search-input'].value = sq;
        filterProjects();
        results.specials[sq] = (elements['projects-table-container'].innerHTML.match(/<tr class="hover:bg-slate-800/g) || []).length;
    }

    // 4. Regex Metacharacters Safety
    const dangerousQueries = ['[', ']', '*', '+', '?', '\\\\', '(', ')', '^', '$', '.'];
    results.regexSafe = true;
    for (const dq of dangerousQueries) {
        try {
            elements['project-search-input'].value = dq;
            filterProjects();
        } catch (e) {
            results.regexSafe = false;
        }
    }

    // 5. Empty and Whitespace-only
    elements['project-search-input'].value = '';
    filterProjects();
    results.emptyRows = (elements['projects-table-container'].innerHTML.match(/<tr class="hover:bg-slate-800/g) || []).length;

    elements['project-search-input'].value = '   ';
    filterProjects();
    results.whitespaceRows = (elements['projects-table-container'].innerHTML.match(/<tr class="hover:bg-slate-800/g) || []).length;

    // 6. Status Chip Selection across all 6 statuses
    results.statusCounts = {};
    results.chipClasses = {};
    const statuses = ['draft', 'quoted', 'approved', 'in_production', 'completed', 'cancelled'];
    for (const st of statuses) {
        elements['project-search-input'].value = '';
        setProjectStatusFilter(st);
        results.statusCounts[st] = (elements['projects-table-container'].innerHTML.match(/<tr class="hover:bg-slate-800/g) || []).length;
        const activeChip = chipsMock.find(c => c.status === st);
        results.chipClasses[st] = activeChip ? activeChip.className : '';
    }

    // 7. Combined Search + Status Filtering
    elements['project-search-input'].value = 'Oficina';
    setProjectStatusFilter('draft');
    results.combOficinaDraft = (elements['projects-table-container'].innerHTML.match(/<tr class="hover:bg-slate-800/g) || []).length;

    setProjectStatusFilter('in_production');
    results.combOficinaProd = (elements['projects-table-container'].innerHTML.match(/<tr class="hover:bg-slate-800/g) || []).length;

    setProjectStatusFilter('completed');
    results.combOficinaComp = (elements['projects-table-container'].innerHTML.match(/<tr class="hover:bg-slate-800/g) || []).length;
    results.emptyFeedbackShown = elements['projects-table-container'].innerHTML.includes('Nenhum projeto encontrado');

    // 8. clearProjectFilters()
    clearProjectFilters();
    results.clearedInputValue = elements['project-search-input'].value;
    results.clearedStatusFilter = state.projectStatusFilter;
    results.clearedRows = (elements['projects-table-container'].innerHTML.match(/<tr class="hover:bg-slate-800/g) || []).length;

    console.log(JSON.stringify(results));
    """
    res = _run_node_harness(script)

    assert res["mixedProjNameRows"] == 1, "Mixed-case project name should match 1 row"
    assert res["mixedClientRows"] == 2, "Mixed-case client name should match 2 rows"
    for sq, cnt in res["specials"].items():
        assert cnt >= 1, f"Special query '{sq}' should find at least 1 match, got {cnt}"
    assert res["regexSafe"] is True, "Special regex metacharacters must not throw errors in filterProjects()"
    assert res["emptyRows"] == 6, "Empty query should return all 6 projects"
    assert res["whitespaceRows"] == 6, "Whitespace-only query should return all 6 projects"

    # Status chips
    for st, cnt in res["statusCounts"].items():
        assert cnt == 1, f"Each status should match exactly 1 project, '{st}' matched {cnt}"
        assert "bg-blue-600/20" in res["chipClasses"][st], f"Active chip for '{st}' must have active styling"

    # Combined filters
    assert res["combOficinaDraft"] == 1, "Oficina + draft should match 1 project"
    assert res["combOficinaProd"] == 1, "Oficina + in_production should match 1 project"
    assert res["combOficinaComp"] == 0, "Oficina + completed should match 0 projects (disjoint sets)"
    assert res["emptyFeedbackShown"] is True, "Empty state feedback must be displayed for 0 matches"

    # Clear filters
    assert res["clearedInputValue"] == "", "Search input must be empty after clearProjectFilters()"
    assert res["clearedStatusFilter"] == "all", "Status filter must reset to 'all'"
    assert res["clearedRows"] == 6, "All projects must be restored after clearProjectFilters()"


def test_adversarial_browser_headless_search_and_chips(tmp_path):
    """
    Adversarial Challenge 2 (Headless Browser Integration):
    Tests real DOM user interaction in headless Chrome/Edge:
    - Typing mixed case query into #project-search-input and dispatching 'input' event
    - Clicking status filter chips and verifying table updates
    - Clicking 'Limpar Filtros' button in empty search state
    """
    chrome_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    browser = next((c for c in chrome_candidates if Path(c).exists()), None)
    if not browser:
        pytest.skip("No Chrome or Edge browser available")

    index_content = INDEX_HTML.read_text(encoding="utf-8")
    js_dir = (FRONTEND_DIR / "js").resolve().as_posix()
    index_content = index_content.replace("/static/js/", f"file:///{js_dir}/")

    test_snippet = """
    <div id="browser-search-output"></div>
    <script>
    window.addEventListener('DOMContentLoaded', () => {
        try {
            const results = {};

            // Seed state with sample projects
            state.projects = [
                { id: 1, name: 'Engrenagem Cilíndrica', client_name: 'Oficina Alpha', plates_count: 2, total_time_hours: 4.5, base_cost: 30, final_price_to_client: 80, status: 'draft' },
                { id: 2, name: 'Suporte Drone', client_name: 'TechMaker', plates_count: 1, total_time_hours: 2.0, base_cost: 15, final_price_to_client: 45, status: 'quoted' },
                { id: 3, name: 'Braço Robótico', client_name: 'Oficina Alpha', plates_count: 3, total_time_hours: 12.0, base_cost: 65, final_price_to_client: 180, status: 'approved' }
            ];

            // Render initial table
            navigateTo('projects');
            renderProjectsTable('', 'all');

            const tableRows = () => document.querySelectorAll('#projects-table-container tbody tr').length;
            results.initialRows = tableRows();

            // 1. Simulate typing mixed-case search
            const searchInput = document.getElementById('project-search-input');
            searchInput.value = 'dRoNe';
            searchInput.dispatchEvent(new Event('input', { bubbles: true }));
            results.searchDroneRows = tableRows();

            // 2. Click status chip 'draft' while query is drone -> 0 rows
            const draftChip = document.querySelector('.project-filter-chip[data-status="draft"]');
            if (draftChip) draftChip.click();
            results.disjointRows = tableRows();
            results.emptyVisible = document.getElementById('projects-table-container').innerHTML.includes('Nenhum projeto encontrado');

            // 3. Clear search input, keeping draft chip -> 1 row
            searchInput.value = '';
            searchInput.dispatchEvent(new Event('input', { bubbles: true }));
            results.draftOnlyRows = tableRows();

            // 4. Click 'Todos' chip -> 3 rows
            const allChip = document.querySelector('.project-filter-chip[data-status="all"]');
            if (allChip) allChip.click();
            results.allRows = tableRows();

            document.getElementById('browser-search-output').textContent = JSON.stringify(results);
        } catch (e) {
            document.getElementById('browser-search-output').textContent = JSON.stringify({ error: e.toString(), stack: e.stack });
        }
    });
    </script>
    """

    injected_html = index_content.replace("</body>", f"{test_snippet}\n</body>")
    test_file = tmp_path / "search_test.html"
    test_file.write_text(injected_html, encoding="utf-8")

    proc = subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--dump-dom", f"file:///{test_file.resolve().as_posix()}"],
        capture_output=True,
        text=True,
        timeout=15
    )

    soup = BeautifulSoup(proc.stdout, "html.parser")
    out_div = soup.find(id="browser-search-output")
    assert out_div is not None, "Browser failed to dump DOM or #browser-search-output missing"
    assert out_div.text.strip(), "No output written by browser search test harness"

    data = json.loads(out_div.text)
    assert "error" not in data, f"Browser encountered JavaScript error: {data.get('error')}\n{data.get('stack')}"

    assert data["initialRows"] == 3, f"Expected 3 initial rows, got {data['initialRows']}"
    assert data["searchDroneRows"] == 1, f"Search 'dRoNe' should match 1 row, got {data['searchDroneRows']}"
    assert data["disjointRows"] == 0, f"Disjoint search + draft should match 0 rows, got {data['disjointRows']}"
    assert data["emptyVisible"] is True, "Empty state notice must be visible for 0 matches"
    assert data["draftOnlyRows"] == 1, f"Draft chip with empty query should match 1 row, got {data['draftOnlyRows']}"
    assert data["allRows"] == 3, f"Clicking 'Todos' chip should restore all 3 rows, got {data['allRows']}"


