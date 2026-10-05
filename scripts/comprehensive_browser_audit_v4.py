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
CDP_PORT = 9228
APP_PORT = 8015
BASE_URL = f"http://127.0.0.1:{APP_PORT}"

def wait_for_server(url, timeout=12):
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
    print(f"=== Starting Backend Server on port {APP_PORT} ===")
    env = os.environ.copy()
    env["PORT"] = str(APP_PORT)
    env["APP_ENV"] = "test"
    env["DATABASE_URL"] = "sqlite:///data/test_audit.db"
    env["DB_SCHEMA"] = ""

    server_cmd = [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(APP_PORT)]
    server_proc = subprocess.Popen(server_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if not wait_for_server(BASE_URL, timeout=12):
        print("Backend server failed to start!")
        server_proc.terminate()
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

                // ==================== TEST 1: Register and Seed User ====================
                let user1 = null;
                try {
                    const email = `audit_user_${Date.now()}@testlab.com`;
                    const res = await API.auth.register(email, 'Pass123456!', 'Test Auditor', 'Studio 3D Alpha');
                    state.user = await API.auth.getMe();
                    document.getElementById('auth-modal')?.classList.add('hidden');
                    await loadAllData();
                    user1 = state.user;
                    addTest('User 1 Registration', true, { email, userId: state.user.id });
                } catch (e) {
                    addTest('User 1 Registration', false, { error: e.message });
                    addIssue('AUTH-01', 'Falha no registro de usuário inicial', 'auth', 'critical', e.message);
                }

                // ==================== TEST 2: Create Printer & Filament ====================
                let testPrinter = null;
                let testFilament = null;
                try {
                    openPrinterModal();
                    document.getElementById('printer-name').value = 'Prusa MK4S Workhorse';
                    document.getElementById('printer-model').value = 'MK4S';
                    setInputVal('printer-cost', '5500,00');
                    setInputVal('printer-lifespan', '8000');
                    setInputVal('printer-power', '180');
                    setInputVal('printer-maintenance', '1,20');
                    setInputVal('printer-energy', '0,92');

                    const fakeEvent = { preventDefault: () => {} };
                    await handleSavePrinter(fakeEvent);
                    testPrinter = state.printers.find(p => p.name.includes('Prusa MK4S'));
                    addTest('Printer Creation', !!testPrinter, { printer: testPrinter });
                } catch (e) {
                    addTest('Printer Creation', false, { error: e.message });
                }

                try {
                    openFilamentModal();
                    document.getElementById('filament-material').value = 'PETG';
                    onFilamentMaterialChange();
                    document.getElementById('filament-brand').value = 'Prusament';
                    document.getElementById('filament-color').value = 'Preto Carbono';
                    document.getElementById('filament-color-hex').value = '#1e293b';
                    setInputVal('filament-weight', '1000');
                    setInputVal('filament-price', '135,00');

                    const fakeEvent = { preventDefault: () => {} };
                    await handleSaveFilament(fakeEvent);
                    testFilament = state.filaments.find(f => f.brand === 'Prusament');
                    addTest('Filament Creation', !!testFilament, { filament: testFilament });
                } catch (e) {
                    addTest('Filament Creation', false, { error: e.message });
                }

                // ==================== TEST 3: Create Project with Multiple Plates & BOM ====================
                let createdProjId = null;
                try {
                    openNewProject();
                    document.getElementById('proj-name').value = 'Gabinete Servidor Mini-ITX';
                    document.getElementById('proj-client-name').value = 'Tech Labs Informática';
                    document.getElementById('proj-client-email').value = 'compras@techlabs.com.br';
                    document.getElementById('proj-client-phone').value = '11977778888';

                    // Plate 1: Front Panel
                    state.currentPlates[0].name = 'Painel Frontal Mesh';
                    state.currentPlates[0].printer_id = testPrinter?.id;
                    state.currentPlates[0].filament_id = testFilament?.id;
                    state.currentPlates[0].quantity = 2;
                    // Test Dual time inputs
                    document.getElementById('plate-time-h-0').value = '3';
                    document.getElementById('plate-time-m-0').value = '45';
                    updatePlateTime(0);
                    state.currentPlates[0].part_weight_g = 160.0;
                    state.currentPlates[0].purge_weight_g = 12.0;
                    state.currentPlates[0].failure_margin_percent = 8.0;

                    // Add Plate 2: Top Cover
                    addNewPlateRow();
                    state.currentPlates[1].name = 'Tampa Superior com Furação';
                    state.currentPlates[1].printer_id = testPrinter?.id;
                    state.currentPlates[1].filament_id = testFilament?.id;
                    state.currentPlates[1].quantity = 1;
                    document.getElementById('plate-time-h-1').value = '2';
                    document.getElementById('plate-time-m-1').value = '15';
                    updatePlateTime(1);
                    state.currentPlates[1].part_weight_g = 95.0;
                    state.currentPlates[1].purge_weight_g = 5.0;
                    state.currentPlates[1].failure_margin_percent = 5.0;

                    // Add BOM items
                    addNewBomRow();
                    state.currentBOM[0].name = 'Inserto Rosqueado M3 Latão';
                    state.currentBOM[0].category = 'Insertos';
                    state.currentBOM[0].quantity = 16;
                    state.currentBOM[0].unit_cost = 0.45;

                    addNewBomRow();
                    state.currentBOM[1].name = 'Parafuso M3x8 Abaulado Inox';
                    state.currentBOM[1].category = 'Fixadores';
                    state.currentBOM[1].quantity = 16;
                    state.currentBOM[1].unit_cost = 0.25;

                    // Commercial terms
                    setInputVal('proj-cad-hours', '1.5');
                    setInputVal('proj-cad-rate', '70,00');
                    setInputVal('proj-post-hours', '0.75');
                    setInputVal('proj-post-rate', '35,00');
                    setInputVal('proj-overhead', '25,00');
                    setInputVal('proj-margin', '35');
                    setInputVal('proj-tax', '6');
                    setInputVal('proj-discount', '5');
                    setInputVal('proj-shipping', '28,50');
                    setInputVal('proj-delivery-days', '5');
                    document.getElementById('proj-notes').value = 'Usinar insertos a quente com ferro de solda 260C.';

                    renderPlates();
                    renderBOM();
                    recalcLiveSummary();

                    const livePrice = document.getElementById('live-final-price')?.textContent;
                    const liveBase = document.getElementById('live-base-cost')?.textContent;
                    const liveProfit = document.getElementById('live-net-profit')?.textContent;

                    addTest('Project 1 Live Pricing Rendered', !!livePrice, { livePrice, liveBase, liveProfit });

                    const saveOk = await saveCurrentProject(false);
                    if (saveOk && state.currentProject) {
                        createdProjId = state.currentProject.id;
                        addTest('Project 1 Saved Successfully', true, { projId: createdProjId });
                    } else {
                        addTest('Project 1 Saved Successfully', false, { error: 'Failed to save' });
                    }
                } catch (e) {
                    addTest('Project 1 Flow', false, { error: e.message });
                }

                // ==================== TEST 4: Math Consistency Check (Frontend vs Engine) ====================
                if (createdProjId) {
                    try {
                        const summary = await API.projects.getSummary(createdProjId);
                        const livePrice = parseLocaleFloat(document.getElementById('live-final-price')?.textContent, 0);
                        const enginePrice = summary.final_price_to_client;
                        const diffPrice = Math.abs(livePrice - enginePrice);

                        const liveProfit = parseLocaleFloat(document.getElementById('live-net-profit')?.textContent, 0);
                        const engineProfit = summary.net_profit;
                        const diffProfit = Math.abs(liveProfit - engineProfit);

                        addTest('Live Price vs Engine Price Consistency', diffPrice < 0.05, {
                            livePrice,
                            enginePrice,
                            diffPrice
                        });

                        addTest('Live Profit vs Engine Profit Consistency', diffProfit < 0.05, {
                            liveProfit,
                            engineProfit,
                            diffProfit
                        });

                        if (diffPrice >= 0.05 || diffProfit >= 0.05) {
                            addIssue('CALC-01', 'Divergência matemática entre o cálculo ao vivo do Frontend e o Backend Engine', 'pricing', 'high', {
                                livePrice, enginePrice, diffPrice, liveProfit, engineProfit, diffProfit
                            });
                        }
                    } catch (e) {
                        addTest('Math Consistency Check', false, { error: e.message });
                    }
                }

                // ==================== TEST 5: Security / Session Data Leak on Logout ====================
                try {
                    // Inspect in-memory state before logout
                    const projsBefore = state.projects?.length || 0;
                    const printersBefore = state.printers?.length || 0;
                    const filBefore = state.filaments?.length || 0;

                    // Trigger Logout
                    API.auth.logout();

                    // Check what remains in state and in the DOM behind the modal
                    const projsAfter = state.projects?.length || 0;
                    const printersAfter = state.printers?.length || 0;
                    const filAfter = state.filaments?.length || 0;
                    const currentProjAfter = state.currentProject;
                    const dashboardStatsAfter = state.dashboardStats;

                    // Check if DOM still shows projects in table
                    const tableRows = document.querySelectorAll('#projects-table-container tbody tr').length;
                    const kpiRevenue = document.getElementById('kpi-revenue')?.textContent;

                    const stateCleared = (projsAfter === 0 && printersAfter === 0 && filAfter === 0 && currentProjAfter === null && dashboardStatsAfter === null);
                    
                    addTest('Logout Session Cleanup in Memory & DOM', stateCleared, {
                        projsBefore, projsAfter,
                        printersBefore, printersAfter,
                        filBefore, filAfter,
                        tableRowsRemaining: tableRows,
                        kpiRevenueRemaining: kpiRevenue
                    });

                    if (!stateCleared || tableRows > 0) {
                        addIssue(
                            'SEC-01',
                            'Logout não limpa estado em memória (state.projects, state.printers, state.filaments) nem remove dados da interface DOM',
                            'security',
                            'high',
                            {
                                projsAfter, printersAfter, filAfter, tableRows, kpiRevenue
                            }
                        );
                    }
                } catch (e) {
                    addTest('Logout Test', false, { error: e.message });
                }

                // ==================== TEST 6: Multi-tenant Login Clean State ====================
                try {
                    // Register User 2
                    const email2 = `user2_${Date.now()}@cleanstate.com`;
                    await API.auth.register(email2, 'Pass123456!', 'User Two', 'Oficina Dois');
                    state.user = await API.auth.getMe();
                    document.getElementById('auth-modal')?.classList.add('hidden');
                    await loadAllData();

                    const user2Projs = state.projects?.length || 0;
                    const user2Printers = state.printers?.length || 0;
                    const user2Filaments = state.filaments?.length || 0;

                    const user2Clean = (user2Projs === 0 && user2Printers === 0 && user2Filaments === 0);
                    addTest('New User Account 100% Clean', user2Clean, {
                        user2Projs, user2Printers, user2Filaments
                    });

                    if (!user2Clean) {
                        addIssue('TENANT-01', 'Novo usuário herda ou visualiza dados residuais do usuário anterior', 'multi-tenant', 'critical', {
                            user2Projs, user2Printers, user2Filaments
                        });
                    }
                } catch (e) {
                    addTest('User 2 Clean State', false, { error: e.message });
                }

                // ==================== TEST 7: Plate Time updatePlateTime Bug Inspection ====================
                try {
                    openNewProject();
                    state.currentPlates = [
                        { name: 'Placa Teste', print_time_hours: 4.5, part_weight_g: 100, quantity: 1 }
                    ];
                    // Intentionally test calling updatePlateTime when DOM elements do not exist
                    // (e.g. before renderPlates or programmatically or on non-rendered index)
                    const oldTime = state.currentPlates[0].print_time_hours;
                    
                    // Simulate element missing:
                    const missingElemTest = document.getElementById('plate-time-h-999'); // null
                    // If updatePlateTime is called on index 999 where elements don't exist:
                    state.currentPlates[1] = { name: 'Placa Sem DOM', print_time_hours: 7.2 };
                    updatePlateTime(1); // will look for plate-time-h-1 which might or might not exist
                    const timeAfter = state.currentPlates[1].print_time_hours;

                    addTest('updatePlateTime null DOM guard', timeAfter === 7.2, {
                        expected: 7.2,
                        actual: timeAfter
                    });

                    if (timeAfter !== 7.2) {
                        addIssue(
                            'DATA-01',
                            'updatePlateTime zera silenciosamente o tempo de impressão para 0 quando os elementos de input não existem no DOM',
                            'data-integrity',
                            'medium',
                            { expected: 7.2, actual: timeAfter }
                        );
                    }
                } catch (e) {
                    addTest('updatePlateTime test', false, { error: e.message });
                }

                // ==================== TEST 8: Empty Plate Name & Empty BOM Name Save ====================
                try {
                    openNewProject();
                    document.getElementById('proj-name').value = 'Projeto Validação Nomes Vazios';
                    state.currentPlates = [
                        { name: '', print_time_hours: 1.0, part_weight_g: 50.0, quantity: 1 }
                    ];
                    state.currentBOM = [
                        { name: '', category: 'Fixadores', quantity: 1, unit_cost: 1.0 }
                    ];
                    renderPlates();
                    renderBOM();
                    const saveRes = await saveCurrentProject(false);
                    if (saveRes && state.currentProject) {
                        const savedProj = state.currentProject;
                        const savedPlateName = savedProj.plates[0]?.name;
                        const savedBomName = savedProj.bom_items[0]?.name;
                        addTest('Empty Plate and BOM Names Handling', true, {
                            savedPlateName,
                            savedBomName
                        });
                        if (savedPlateName === '' || savedBomName === '') {
                            addIssue(
                                'VALIDATION-01',
                                'Placas e itens de BOM aceitam nomes vazios ao salvar, gerando itens sem identificação na proposta e no PDF',
                                'validation',
                                'medium',
                                { savedPlateName, savedBomName }
                            );
                        }
                    }
                } catch (e) {
                    addTest('Empty names test', false, { error: e.message });
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
