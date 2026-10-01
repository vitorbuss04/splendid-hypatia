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
CDP_PORT = 9223
APP_PORT = 8005
BASE_URL = f"http://127.0.0.1:{APP_PORT}"

async def main():
    print(f"=== Checking Backend Server on {BASE_URL} ===")
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=2) as resp:
            print("Backend health status:", resp.status)
    except Exception as e:
        print("Backend not reachable:", e)
        return

    print(f"=== Starting Headless Chrome on CDP port {CDP_PORT} ===")
    user_data_dir = Path(os.environ.get("TEMP", r"C:\Temp")) / "chrome_audit_profile_9223"
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
                        return {"error": resp["result"]["exceptionDetails"]}
                    return val
                return resp

            await send_cmd("Runtime.enable")
            await send_cmd("Log.enable")
            await send_cmd("Network.enable")
            await asyncio.sleep(1.0)

            print("=== RUNNING IN-BROWSER AUTOMATED TESTS ===")

            audit_js = """
            (async () => {
                const results = {
                    steps: [],
                    bugs_found: []
                };

                function logStep(name, success, details = {}) {
                    results.steps.push({ name, success, details });
                }

                function recordBug(id, title, category, severity, details) {
                    results.bugs_found.push({ id, title, category, severity, details });
                }

                // STEP 1: Registration and Authentication Flow
                try {
                    const testEmail = `audit_${Date.now()}@makerstudio.com`;
                    const regRes = await API.auth.register(testEmail, 'StrongPass123!', 'Vitor Maker', 'Maker Studio 3D');
                    state.user = await API.auth.getMe();
                    document.getElementById('auth-modal')?.classList.add('hidden');
                    await loadAllData();
                    logStep('Auth Registration', true, { email: testEmail, userId: state.user.id });
                } catch (e) {
                    logStep('Auth Registration', false, { error: e.message });
                    recordBug('AUTH-01', 'Falha no fluxo de registro inicial', 'auth', 'high', e.message);
                }

                // STEP 2: Preferences update
                try {
                    await API.auth.updatePreferences({
                        phone: '11987654321',
                        pix_key: 'contato@makerstudio.com',
                        default_energy_rate: 0.95,
                        default_failure_rate: 8.0,
                        default_profit_margin: 45.0,
                        default_tax_rate: 8.5,
                        default_cad_rate: 75.0,
                        default_post_rate: 35.0,
                        default_payment_terms: '50% entrada e 50% na retirada',
                        default_warranty_terms: '90 dias contra empenamento térmico'
                    });
                    state.user = await API.auth.getMe();
                    logStep('Preferences Update', true, { margin: state.user.default_profit_margin });
                } catch (e) {
                    logStep('Preferences Update', false, { error: e.message });
                }

                // STEP 3: Printer Creation and Testing
                try {
                    openPrinterModal();
                    document.getElementById('printer-name').value = 'Bambu Lab X1 Carbon';
                    document.getElementById('printer-model').value = 'X1C Combo';
                    document.getElementById('printer-cost').value = '9500,00';
                    document.getElementById('printer-lifespan').value = '6000';
                    document.getElementById('printer-power').value = '350';
                    document.getElementById('printer-maintenance').value = '1,50';
                    document.getElementById('printer-energy').value = '0,95';

                    // Trigger save
                    const fakeEvent = { preventDefault: () => {} };
                    await handleSavePrinter(fakeEvent);
                    const p = state.printers.find(pr => pr.name === 'Bambu Lab X1 Carbon');
                    if (p) {
                        logStep('Printer Creation', true, { printerId: p.id, hourlyRate: p.machine_hourly_rate });
                    } else {
                        logStep('Printer Creation', false, { error: 'Printer not found in state' });
                    }
                } catch (e) {
                    logStep('Printer Creation', false, { error: e.message });
                }

                // STEP 4: Filament Creation with Density & Standardized Name
                try {
                    openFilamentModal();
                    document.getElementById('filament-material').value = 'PETG';
                    onFilamentMaterialChange();
                    document.getElementById('filament-brand').value = '3D Fila';
                    document.getElementById('filament-color').value = 'Azul Translúcido';
                    document.getElementById('filament-color-hex').value = '#0284c7';
                    document.getElementById('filament-weight').value = '1000';
                    document.getElementById('filament-price').value = '119,90';
                    
                    const densityVal = document.getElementById('filament-density').value;
                    const fakeEvent = { preventDefault: () => {} };
                    await handleSaveFilament(fakeEvent);
                    const f = state.filaments.find(fil => fil.brand === '3D Fila');
                    if (f) {
                        logStep('Filament Creation', true, { filamentId: f.id, costPerGram: f.cost_per_gram, density: f.density_g_cm3 });
                    } else {
                        logStep('Filament Creation', false, { error: 'Filament not found in state' });
                    }
                } catch (e) {
                    logStep('Filament Creation', false, { error: e.message });
                }

                // STEP 5: Project Editor Workflow with Special Characters & Adversarial Strings
                let createdProjId = null;
                try {
                    openNewProject();

                    // Fill project info with technical industrial characters: <V2>, &, quotes
                    document.getElementById('proj-name').value = 'Suporte <V2> Náutico & Especial';
                    document.getElementById('proj-client-name').value = 'Alpha & Omega Engenharia <Ltda>';
                    document.getElementById('proj-client-email').value = 'contato@alphaomega.com.br';
                    document.getElementById('proj-client-phone').value = '11988887777';
                    document.getElementById('proj-notes').value = 'Tolerâncias críticas < 0.2mm & acabamento sem marcas.';

                    // Setup Plate 1
                    state.currentPlates[0].name = 'Base Inferior <A>';
                    state.currentPlates[0].printer_id = state.printers[0]?.id;
                    state.currentPlates[0].filament_id = state.filaments[0]?.id;
                    state.currentPlates[0].print_time_hours = 3.5;
                    state.currentPlates[0].part_weight_g = 145.0;
                    state.currentPlates[0].purge_weight_g = 12.0;
                    state.currentPlates[0].failure_margin_percent = 10.0;
                    state.currentPlates[0].quantity = 2;

                    // Duplicate Plate 1 -> creates Plate 2
                    duplicatePlateRow(0);
                    state.currentPlates[1].name = 'Tampa Superior <B>';
                    state.currentPlates[1].print_time_hours = 1.75;
                    state.currentPlates[1].part_weight_g = 68.0;
                    state.currentPlates[1].quantity = 2;

                    // Setup BOM Items
                    state.currentBOM = [
                        { name: 'Parafuso M3x16 <Inox> & Porca', category: 'Fixadores', quantity: 8, unit_cost: 0.85, notes: 'Aço inox 316' },
                        { name: 'Inserto Latão M3 Recartilhado', category: 'Insertos', quantity: 4, unit_cost: 1.25, notes: '' }
                    ];

                    // Commercial adjustments
                    document.getElementById('proj-cad-hours').value = '1.5';
                    document.getElementById('proj-cad-rate').value = '80,00';
                    document.getElementById('proj-post-hours').value = '0.5';
                    document.getElementById('proj-post-rate').value = '40,00';
                    document.getElementById('proj-overhead').value = '15,00';
                    document.getElementById('proj-margin').value = '40';
                    document.getElementById('proj-tax').value = '6';
                    document.getElementById('proj-discount').value = '5';
                    document.getElementById('proj-shipping').value = '25,00';
                    document.getElementById('proj-delivery-days').value = '4';

                    renderPlates();
                    renderBOM();
                    recalcLiveSummary();

                    // Read Live Summary numbers from DOM
                    const liveDom = {
                        weight: document.getElementById('live-weight')?.textContent,
                        time: document.getElementById('live-time')?.textContent,
                        materialCost: document.getElementById('live-material-cost')?.textContent,
                        machineCost: document.getElementById('live-machine-cost')?.textContent,
                        bomCost: document.getElementById('live-bom-cost')?.textContent,
                        laborCost: document.getElementById('live-labor-cost')?.textContent,
                        overheadCost: document.getElementById('live-overhead-cost')?.textContent,
                        baseCost: document.getElementById('live-base-cost')?.textContent,
                        suggestedPrice: document.getElementById('live-suggested-price')?.textContent,
                        finalPrice: document.getElementById('live-final-price')?.textContent,
                        netProfit: document.getElementById('live-net-profit')?.textContent,
                    };

                    // Save Project (stay on page false)
                    const saveOk = await saveCurrentProject(false);
                    if (saveOk && state.currentProject) {
                        createdProjId = state.currentProject.id;
                        logStep('Project Creation', true, { projectId: createdProjId, liveDom });
                    } else {
                        logStep('Project Creation', false, { error: 'Failed to save project' });
                    }
                } catch (e) {
                    logStep('Project Creation', false, { error: e.message });
                }

                // STEP 6: Validate Live Summary against Backend Official Engine
                if (createdProjId) {
                    try {
                        const summary = await API.projects.getSummary(createdProjId);
                        logStep('Summary Calculation Comparison', true, {
                            backend_base_cost: summary.base_cost,
                            backend_suggested_price: summary.suggested_price,
                            backend_final_price: summary.final_price_to_client,
                            backend_net_profit: summary.net_profit
                        });
                    } catch (e) {
                        logStep('Summary Calculation Comparison', false, { error: e.message });
                    }
                }

                // STEP 7: Test PDF Generation Endpoint (Client and Technical)
                if (createdProjId) {
                    try {
                        const resClient = await fetch(`/api/projects/${createdProjId}/pdf?type=client`, {
                            headers: { 'Authorization': `Bearer ${API.getToken()}` }
                        });
                        if (resClient.ok) {
                            logStep('Client PDF Generation', true, { status: resClient.status });
                        } else {
                            const errText = await resClient.text();
                            logStep('Client PDF Generation', false, { status: resClient.status, error: errText });
                            recordBug('PDF-01', 'Falha HTTP 500 no PDF do Cliente com caracteres especiais (<V2>, &)', 'pdf', 'high', { status: resClient.status, error: errText });
                        }
                    } catch (e) {
                        logStep('Client PDF Generation', false, { error: e.message });
                    }

                    try {
                        const resTech = await fetch(`/api/projects/${createdProjId}/pdf?type=technical`, {
                            headers: { 'Authorization': `Bearer ${API.getToken()}` }
                        });
                        if (resTech.ok) {
                            logStep('Technical PDF Generation', true, { status: resTech.status });
                        } else {
                            const errText = await resTech.text();
                            logStep('Technical PDF Generation', false, { status: resTech.status, error: errText });
                            recordBug('PDF-02', 'Falha HTTP 500 na Ficha Técnica com caracteres especiais (<A>, &)', 'pdf', 'high', { status: resTech.status, error: errText });
                        }
                    } catch (e) {
                        logStep('Technical PDF Generation', false, { error: e.message });
                    }
                }

                // STEP 8: Test Dashboard Metrics and Charts
                try {
                    await navigateTo('dashboard');
                    await loadDashboard();
                    const stats = state.dashboardStats;
                    logStep('Dashboard Load', true, {
                        total_projects: stats?.total_projects,
                        pipeline_revenue: stats?.pipeline_revenue,
                        total_revenue_approved: stats?.total_revenue_approved,
                        cost_breakdown: stats?.cost_breakdown
                    });
                } catch (e) {
                    logStep('Dashboard Load', false, { error: e.message });
                }

                return results;
            })()
            """

            eval_res = await eval_js(audit_js)
            print("=== IN-BROWSER AUDIT RESULTS ===")
            print(json.dumps(eval_res, indent=2, ensure_ascii=False))

            print("\n=== CONSOLE LOGS & ERRORS ===")
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
        print("Cleaning up Chrome...")
        try:
            chrome_proc.terminate()
            chrome_proc.wait(timeout=2)
        except Exception:
            chrome_proc.kill()

if __name__ == "__main__":
    asyncio.run(main())
