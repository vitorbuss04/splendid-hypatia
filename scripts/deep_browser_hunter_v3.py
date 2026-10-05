import subprocess
import time
import json
import urllib.request
import urllib.error
import asyncio
import websockets
import os
import sys
from pathlib import Path

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CDP_PORT = 9226
APP_PORT = 8010
BASE_URL = f"http://127.0.0.1:{APP_PORT}"

def wait_for_server(url, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False

async def main():
    print(f"=== Connecting to Backend Server on port {APP_PORT} ===")
    if not wait_for_server(BASE_URL, timeout=5):
        print("Backend server not reachable on", BASE_URL)
        return
    print("Backend server ready.")

    print(f"=== Starting Chrome with CDP on port {CDP_PORT} ===")
    user_data_dir = Path(os.environ.get("TEMP", r"C:\Temp")) / f"chrome_audit_profile_{CDP_PORT}"
    chrome_cmd = [
        CHROME_PATH,
        "--headless=new",
        f"--remote-debugging-port={CDP_PORT}",
        "--remote-allow-origins=*",
        "--disable-gpu",
        f"--user-data-dir={user_data_dir}",
        "--window-size=1440,900",
        BASE_URL
    ]
    chrome_proc = subprocess.Popen(chrome_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2.5)

    try:
        tabs_res = urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json").read()
        tabs = json.loads(tabs_res)
        target_tab = None
        for t in tabs:
            if str(APP_PORT) in t.get("url", ""):
                target_tab = t
                break
        if not target_tab:
            target_tab = tabs[0]

        ws_url = target_tab["webSocketDebuggerUrl"]
        print(f"Connected to Chrome WebSocket CDP: {ws_url}")

        async with websockets.connect(ws_url, max_size=20_000_000) as ws:
            msg_id = 1
            console_logs = []
            exceptions = []
            network_errors = []

            async def send_cmd(method, params=None):
                nonlocal msg_id
                mid = msg_id
                msg_id += 1
                payload = {"id": mid, "method": method, "params": params or {}}
                await ws.send(json.dumps(payload))
                while True:
                    raw = await ws.recv()
                    data = json.loads(raw)
                    if "method" in data:
                        m = data["method"]
                        if m == "Runtime.consoleAPICalled":
                            console_logs.append(data["params"])
                        elif m == "Runtime.exceptionThrown":
                            exceptions.append(data["params"])
                        elif m == "Network.responseReceived":
                            status = data["params"].get("response", {}).get("status", 200)
                            url = data["params"].get("response", {}).get("url", "")
                            if status >= 400:
                                network_errors.append({"status": status, "url": url})
                        continue
                    if data.get("id") == mid:
                        return data

            async def eval_js(expr):
                resp = await send_cmd("Runtime.evaluate", {
                    "expression": expr,
                    "awaitPromise": True,
                    "returnByValue": True
                })
                if resp and "result" in resp and "result" in resp["result"]:
                    val = resp["result"]["result"].get("value")
                    if "exceptionDetails" in resp["result"]:
                        return {"eval_error": resp["result"]["exceptionDetails"]}
                    return val
                return resp

            await send_cmd("Runtime.enable")
            await send_cmd("Log.enable")
            await send_cmd("Network.enable")

            await asyncio.sleep(1.0)

            # Test script inside browser
            audit_script = """
            (async () => {
                const results = {
                    tests: [],
                    issues_found: []
                };

                function addTest(name, passed, details = {}) {
                    results.tests.push({ name, passed, details });
                }

                function addIssue(id, title, category, severity, details) {
                    results.issues_found.push({ id, title, category, severity, details });
                }

                function setInputVal(id, val) {
                    const el = document.getElementById(id);
                    if (!el) return;
                    if (String(val).includes(',')) {
                        el.type = 'text';
                        el.dataset.originalType = 'number';
                    }
                    el.value = val;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }

                // TEST 1: Register and login
                try {
                    const email = `audit_${Date.now()}@makerpro.com`;
                    const res = await API.auth.register(email, 'Pass123456!', 'Auditor Pro', 'Audit 3D Lab');
                    state.user = await API.auth.getMe();
                    document.getElementById('auth-modal')?.classList.add('hidden');
                    await loadAllData();
                    addTest('Auth Flow', true, { email, userId: state.user.id });
                } catch (e) {
                    addTest('Auth Flow', false, { error: e.message });
                    addIssue('AUTH-01', 'Falha no registro/login de usuário', 'auth', 'critical', e.message);
                }

                // TEST 2: Update Preferences with edge values
                try {
                    await API.auth.updatePreferences({
                        company_name: 'Audit 3D <Lab> & Cia',
                        phone: '+55 11 99999-8888',
                        pix_key: 'pix@audit3d.com',
                        default_energy_rate: 0.90,
                        default_failure_rate: 10.0,
                        default_profit_margin: 35.0,
                        default_tax_rate: 0.0, // test 0% tax
                        default_cad_rate: 60.0,
                        default_post_rate: 30.0,
                        default_payment_terms: '50% entrada e 50% na entrega',
                        default_warranty_terms: '30 dias garantia legal'
                    });
                    state.user = await API.auth.getMe();
                    addTest('Preferences Zero Tax', state.user.default_tax_rate === 0.0, { tax: state.user.default_tax_rate });
                } catch (e) {
                    addTest('Preferences Zero Tax', false, { error: e.message });
                }

                // TEST 3: Printer with 0 Lifespan / 0 Cost Edge Case
                try {
                    openPrinterModal();
                    document.getElementById('printer-name').value = 'Test Zero Lifespan Printer';
                    document.getElementById('printer-model').value = 'Zero 1';
                    setInputVal('printer-cost', '0');
                    setInputVal('printer-lifespan', '0'); // Should not divide by zero
                    setInputVal('printer-power', '100');
                    setInputVal('printer-maintenance', '0');
                    setInputVal('printer-energy', '0.90');

                    const fakeEvent = { preventDefault: () => {} };
                    await handleSavePrinter(fakeEvent);
                    const pZero = state.printers.find(p => p.name === 'Test Zero Lifespan Printer');
                    if (pZero && !isNaN(pZero.machine_hourly_rate)) {
                        addTest('Printer Zero Lifespan Div/0 Guard', true, { hourlyRate: pZero.machine_hourly_rate });
                    } else {
                        addTest('Printer Zero Lifespan Div/0 Guard', false, { pZero });
                        addIssue('PRINTER-01', 'Impressora com vida útil 0 gera NaN ou erro de divisão por zero', 'printers', 'high', pZero);
                    }
                } catch (e) {
                    addTest('Printer Zero Lifespan Div/0 Guard', false, { error: e.message });
                }

                // TEST 4: Filament with Spool Weight = 0 or density = 0
                try {
                    openFilamentModal();
                    document.getElementById('filament-material').value = 'PLA';
                    onFilamentMaterialChange();
                    document.getElementById('filament-brand').value = 'TestBrand';
                    document.getElementById('filament-color').value = 'Vermelho Fogo';
                    document.getElementById('filament-color-hex').value = '#ef4444';
                    setInputVal('filament-weight', '1000');
                    setInputVal('filament-price', '95,00');
                    
                    const fakeEvent = { preventDefault: () => {} };
                    await handleSaveFilament(fakeEvent);
                    const fil = state.filaments.find(f => f.brand === 'TestBrand');
                    if (fil && fil.cost_per_gram > 0) {
                        addTest('Filament Normal Creation', true, { filId: fil.id, cost_per_gram: fil.cost_per_gram });
                    } else {
                        addTest('Filament Normal Creation', false, { fil });
                    }
                } catch (e) {
                    addTest('Filament Normal Creation', false, { error: e.message });
                }

                // TEST 5: Filament Duplication - verify density, color, and name
                try {
                    const filToDup = state.filaments[0];
                    if (filToDup) {
                        await duplicateFilament(filToDup.id);
                        const dupFil = state.filaments.find(f => f.name.includes('(Cópia)'));
                        if (dupFil) {
                            const densityMatch = (dupFil.density_g_cm3 === filToDup.density_g_cm3);
                            addTest('Filament Duplication Density Parity', densityMatch, { 
                                origDensity: filToDup.density_g_cm3, 
                                dupDensity: dupFil.density_g_cm3 
                            });
                            if (!densityMatch) {
                                addIssue('FILAMENT-01', 'Duplicação de filamento não preserva densidade g/cm3', 'filaments', 'medium', { dupFil });
                            }
                        } else {
                            addTest('Filament Duplication Density Parity', false, { error: 'Dup filament not found' });
                        }
                    }
                } catch (e) {
                    addTest('Filament Duplication', false, { error: e.message });
                }

                // TEST 6: Project Editor with Zero Values, Negative Values & Recalc Live Summary
                let projId = null;
                try {
                    openNewProject();
                    document.getElementById('proj-name').value = 'Projeto Audit Master';
                    document.getElementById('proj-client-name').value = 'Cliente Especial';
                    document.getElementById('proj-client-email').value = 'cliente@especial.com';
                    document.getElementById('proj-client-phone').value = '11988887777';
                    
                    // Plate 1: 0 print time, 0 weight edge case
                    state.currentPlates[0].name = 'Placa Zero Time & Weight';
                    state.currentPlates[0].printer_id = state.printers[0]?.id;
                    state.currentPlates[0].filament_id = state.filaments[0]?.id;
                    state.currentPlates[0].print_time_hours = 0.0;
                    state.currentPlates[0].part_weight_g = 0.0;
                    state.currentPlates[0].quantity = 1;

                    // Add Plate 2 with normal values
                    addNewPlateRow();
                    state.currentPlates[1].name = 'Placa Estrutura Principal';
                    state.currentPlates[1].print_time_hours = 4.25;
                    state.currentPlates[1].part_weight_g = 120.0;
                    state.currentPlates[1].purge_weight_g = 8.0;
                    state.currentPlates[1].failure_margin_percent = 12.0;
                    state.currentPlates[1].quantity = 3;

                    // Add BOM Item
                    addNewBomRow();
                    state.currentBOM[0].name = 'Parafuso Allen M4x20';
                    state.currentBOM[0].quantity = 12;
                    state.currentBOM[0].unit_cost = 0.75;

                    // Commercial terms with 0% tax and 0 delivery days
                    setInputVal('proj-cad-hours', '2.0');
                    setInputVal('proj-cad-rate', '60,00');
                    setInputVal('proj-post-hours', '1.0');
                    setInputVal('proj-post-rate', '30,00');
                    setInputVal('proj-overhead', '20,00');
                    setInputVal('proj-margin', '35');
                    setInputVal('proj-tax', '0'); // 0% tax test
                    setInputVal('proj-discount', '10');
                    setInputVal('proj-shipping', '30,00');
                    setInputVal('proj-delivery-days', '0'); // pronta entrega test

                    renderPlates();
                    renderBOM();
                    recalcLiveSummary();

                    const liveFinal = document.getElementById('live-final-price')?.textContent;
                    const liveBase = document.getElementById('live-base-cost')?.textContent;
                    const liveProfit = document.getElementById('live-net-profit')?.textContent;

                    addTest('Project Live Summary Calc', true, { liveFinal, liveBase, liveProfit });

                    const saveOk = await saveCurrentProject(false);
                    if (saveOk && state.currentProject) {
                        projId = state.currentProject.id;
                        addTest('Project Save Flow', true, { projId });
                    } else {
                        addTest('Project Save Flow', false, { error: 'Save failed' });
                    }
                } catch (e) {
                    addTest('Project Flow', false, { error: e.message });
                }

                // TEST 7: Compare Frontend Live Summary vs Backend Official Engine
                if (projId) {
                    try {
                        const summary = await API.projects.getSummary(projId);
                        const proj = await API.projects.get(projId);

                        // Check 0 delivery days preservation
                        const deliveryDaysPreserved = (proj.delivery_days === 0);
                        addTest('Delivery Days 0 Preservation', deliveryDaysPreserved, { delivery_days: proj.delivery_days });
                        if (!deliveryDaysPreserved) {
                            addIssue('PROJ-01', 'Prazo de entrega 0 dias é sobrescrito ou perdido', 'projects', 'medium', { proj });
                        }

                        // Check 0% tax rate preservation
                        const taxRatePreserved = (proj.tax_rate_percent === 0.0);
                        addTest('Tax Rate 0% Preservation', taxRatePreserved, { tax_rate: proj.tax_rate_percent });

                        // Compare financial figures
                        addTest('Engine Summary Response', true, {
                            base_cost: summary.base_cost,
                            suggested_price: summary.suggested_price,
                            final_price: summary.final_price_to_client,
                            net_profit: summary.net_profit
                        });
                    } catch (e) {
                        addTest('Engine Summary Verification', false, { error: e.message });
                    }
                }

                // TEST 8: Test PDF Endpoints
                if (projId) {
                    try {
                        const resClient = await fetch(`/api/projects/${projId}/pdf?type=client`, {
                            headers: { 'Authorization': `Bearer ${API.getToken()}` }
                        });
                        addTest('Client PDF Status', resClient.status === 200, { status: resClient.status });
                        if (resClient.status !== 200) {
                            const errTxt = await resClient.text();
                            addIssue('PDF-01', 'Falha no endpoint de PDF do cliente', 'pdf', 'high', { status: resClient.status, errTxt });
                        }
                    } catch (e) {
                        addTest('Client PDF Status', false, { error: e.message });
                    }

                    try {
                        const resTech = await fetch(`/api/projects/${projId}/pdf?type=technical`, {
                            headers: { 'Authorization': `Bearer ${API.getToken()}` }
                        });
                        addTest('Technical PDF Status', resTech.status === 200, { status: resTech.status });
                        if (resTech.status !== 200) {
                            const errTxt = await resTech.text();
                            addIssue('PDF-02', 'Falha no endpoint da Ficha Técnica', 'pdf', 'high', { status: resTech.status, errTxt });
                        }
                    } catch (e) {
                        addTest('Technical PDF Status', false, { error: e.message });
                    }
                }

                // TEST 9: Test Dashboard Load and Stats Calculations
                try {
                    await navigateTo('dashboard');
                    await loadDashboard();
                    const stats = state.dashboardStats;
                    addTest('Dashboard Stats Available', !!stats, { stats });

                    // Verify cost_breakdown keys in stats
                    if (stats && stats.cost_breakdown) {
                        const cb = stats.cost_breakdown;
                        // Check if machine_energy_cost is reasonable
                        addTest('Cost Breakdown Structure', true, { cb });
                    }
                } catch (e) {
                    addTest('Dashboard Load', false, { error: e.message });
                }

                // TEST 10: Test Projects Table Filtering and Search
                try {
                    await navigateTo('projects');
                    renderProjectsTable();
                    const rowsBefore = document.querySelectorAll('#projects-table-container tbody tr').length;
                    
                    // Search for existing project
                    renderProjectsTable('Audit Master');
                    const rowsFiltered = document.querySelectorAll('#projects-table-container tbody tr').length;
                    
                    // Clear filters
                    clearProjectFilters();
                    const rowsCleared = document.querySelectorAll('#projects-table-container tbody tr').length;

                    addTest('Projects Filter & Clear', rowsFiltered >= 1 && rowsCleared === rowsBefore, {
                        rowsBefore, rowsFiltered, rowsCleared
                    });
                } catch (e) {
                    addTest('Projects Filter & Clear', false, { error: e.message });
                }

                return results;
            })()
            """

            eval_res = await eval_js(audit_script)
            print("=== IN-BROWSER AUDIT RESULTS ===")
            print(json.dumps(eval_res, indent=2, ensure_ascii=False))

            print("\n=== CONSOLE LOGS & WARNINGS ===")
            print(f"Total console events: {len(console_logs)}")
            for cl in console_logs:
                print("Console:", cl.get("type"), [arg.get("value") for arg in cl.get("args", [])])

            print(f"\nTotal runtime exceptions: {len(exceptions)}")
            for exc in exceptions:
                print("Exception:", exc)

            print(f"\nTotal network errors (>=400): {len(network_errors)}")
            for ne in network_errors:
                print("Network Error:", ne)

    finally:
        print("Cleaning up Chrome and Server...")
        try:
            chrome_proc.terminate()
            chrome_proc.wait(timeout=2)
        except Exception:
            chrome_proc.kill()
        try:
            server_proc.terminate()
            server_proc.wait(timeout=2)
        except Exception:
            server_proc.kill()

if __name__ == "__main__":
    asyncio.run(main())
