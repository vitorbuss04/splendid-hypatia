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
CDP_PORT = 9245
APP_PORT = 8035
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
    db_path = Path("data/test_audit_v6.db")
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass
    env["DATABASE_URL"] = "sqlite:///data/test_audit_v6.db"
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
                    elif data.get("id") == mid:
                        return data

            async def eval_js(expression):
                resp = await send_cmd("Runtime.evaluate", {
                    "expression": expression,
                    "awaitPromise": True,
                    "returnByValue": True
                })
                if "result" in resp and "result" in resp["result"]:
                    val = resp["result"]["result"].get("value")
                    if "exceptionDetails" in resp["result"]:
                        return {"eval_error": resp["result"]["exceptionDetails"]}
                    return val
                return resp

            await send_cmd("Runtime.enable")
            await send_cmd("Log.enable")
            await send_cmd("Network.enable")

            await asyncio.sleep(1.0)

            audit_script = """
            (async () => {
                const results = {
                    tests: [],
                    issues: []
                };

                function report(testName, passed, details = {}) {
                    results.tests.push({ name: testName, passed, details });
                }

                function addIssue(id, title, category, severity, details) {
                    results.issues.push({ id, title, category, severity, details });
                }

                // 1. Auth Setup
                try {
                    const email = `audit6_${Date.now()}@test.com`;
                    await API.auth.register(email, 'Pass123456!', 'Auditor V6', 'Audit Lab 6');
                    state.user = await API.auth.getMe();
                    document.getElementById('auth-modal')?.classList.add('hidden');
                    await loadAllData();
                    report('Auth Registration', true, { email });
                } catch (e) {
                    report('Auth Registration', false, { error: e.message });
                    addIssue('AUTH-ERR', 'Falha ao autenticar', 'auth', 'critical', e.message);
                }

                // 2. Test XSS in Plate Filament Badge / Select in renderPlates
                try {
                    // Create filament with HTML injection payload in material and color
                    const xssFilament = await API.filaments.create({
                        name: 'PETG Vermelho XSS',
                        brand: 'Marca Segura',
                        material: '<b id="xss-plate-mat">PETG</b>',
                        color: '<img src=x onerror=window._xss_plate_fil=1>',
                        color_hex: '#ef4444',
                        spool_weight_g: 1000,
                        spool_price: 110,
                        density_g_cm3: 1.27
                    });
                    await loadAllData();

                    openNewProject();
                    state.currentPlates = [{
                        name: 'Placa Teste XSS',
                        printer_id: null,
                        filament_id: xssFilament.id,
                        custom_printer_hourly_rate: 2.5,
                        custom_filament_cost_per_g: null,
                        print_time_hours: 1.0,
                        part_weight_g: 50.0,
                        purge_weight_g: 0.0,
                        failure_margin_percent: 10.0,
                        quantity: 1
                    }];
                    renderPlates();

                    const xssPlateFired = Boolean(window._xss_plate_fil);
                    const rawPlateMatInjected = Boolean(document.getElementById('xss-plate-mat'));

                    report('Plate Filament Badge XSS Sanitization', !xssPlateFired && !rawPlateMatInjected, {
                        xssPlateFired, rawPlateMatInjected
                    });

                    if (xssPlateFired || rawPlateMatInjected) {
                        addIssue(
                            'SEC-XSS-PLATE-FILAMENT',
                            'Vulnerabilidade de Cross-Site Scripting (XSS) no card da placa (renderPlates) por interpolação direta de material e cor do filamento sem escapeHtml',
                            'security',
                            'high',
                            { xssPlateFired, rawPlateMatInjected }
                        );
                    }
                } catch (e) {
                    report('Plate Filament XSS test', false, { error: e.message });
                }

                // 3. Test Active Quotes KPI logic with 'approved' status
                try {
                    // Create projects across statuses: draft, quoted, approved, in_production, completed, cancelled
                    const pDraft = await API.projects.create({
                        name: 'Projeto Rascunho',
                        status: 'draft',
                        plates: [{ name: 'P1', print_time_hours: 1, part_weight_g: 20 }]
                    });
                    const pQuoted = await API.projects.create({
                        name: 'Projeto Orçado',
                        status: 'quoted',
                        plates: [{ name: 'P1', print_time_hours: 1, part_weight_g: 20 }]
                    });
                    const pApproved = await API.projects.create({
                        name: 'Projeto Aprovado',
                        status: 'approved',
                        plates: [{ name: 'P1', print_time_hours: 1, part_weight_g: 20 }]
                    });
                    const pInProd = await API.projects.create({
                        name: 'Projeto Em Produção',
                        status: 'in_production',
                        plates: [{ name: 'P1', print_time_hours: 1, part_weight_g: 20 }]
                    });

                    const stats = await API.projects.getDashboardStats();
                    // Let's check stats.active_quotes:
                    // Currently backend does: if st in ["draft", "quoted", "in_production"]: active_quotes += 1
                    // Total projects created: 4. draft (1) + quoted (1) + approved (1) + in_production (1).
                    // Notice that 'approved' was excluded! active_quotes will be 3 instead of 4 (or 2 if only pipeline).
                    const includesApprovedInActive = stats.active_quotes >= 4;
                    const approvedExcludedAnomaly = (stats.active_quotes === 3);

                    report('Active Quotes Status Consistency', includesApprovedInActive, {
                        active_quotes: stats.active_quotes,
                        approvedExcludedAnomaly
                    });

                    if (approvedExcludedAnomaly) {
                        addIssue(
                            'KPI-ACTIVE-QUOTES-APPROVED-EXCLUDED',
                            'Contador de "Orçamentos Ativos" (active_quotes) omite projetos com status "aprovado" (approved), gerando queda inconsistente na métrica durante a transição operacional',
                            'metrics',
                            'medium',
                            {
                                active_quotes: stats.active_quotes,
                                explanation: "Projetos em draft, quoted e in_production são somados, mas approved é ignorado no backend (project_routes.py:208) e no frontend (app.js:740)"
                            }
                        );
                    }
                } catch (e) {
                    report('Active Quotes KPI test', false, { error: e.message });
                }

                // 4. Test Workshop Cost Breakdown (Chart 3) contamination with draft/quoted projects
                try {
                    // Create an expensive draft project that should NOT count in actual workshop costs
                    const hugeDraft = await API.projects.create({
                        name: 'Rascunho Fictício Gigante',
                        status: 'draft',
                        cad_hours: 100,
                        cad_hourly_rate: 100, // R$ 10.000 labor
                        overhead_cost: 5000,
                        profit_margin_percent: 50,
                        plates: [{
                            name: 'Super Placa',
                            print_time_hours: 200,
                            part_weight_g: 5000,
                            custom_printer_hourly_rate: 15.0, // R$ 3000 machine
                            custom_filament_cost_per_g: 0.15, // R$ 750 mat
                            quantity: 1
                        }]
                    });

                    const stats = await API.projects.getDashboardStats();
                    const cb = stats.cost_breakdown;

                    // If draft is counted, cb.labor_cost will be > 10000, cb.overhead_cost > 5000
                    const isDraftContaminatingCostBreakdown = cb.labor_cost >= 10000 || cb.overhead_cost >= 5000;

                    report('Workshop Cost Breakdown draft isolation', !isDraftContaminatingCostBreakdown, {
                        cost_breakdown: cb,
                        isDraftContaminatingCostBreakdown
                    });

                    if (isDraftContaminatingCostBreakdown) {
                        addIssue(
                            'METRIC-COST-BREAKDOWN-DRAFT-CONTAMINATION',
                            'Gráfico de Estrutura de Custos da Oficina (Chart 3) soma custos e lucros de orçamentos em Rascunho (draft) e Orçados (quoted), distorcendo as despesas reais operacionais',
                            'metrics',
                            'high',
                            {
                                material_cost: cb.material_cost,
                                labor_cost: cb.labor_cost,
                                overhead_cost: cb.overhead_cost,
                                net_profit: cb.net_profit
                            }
                        );
                    }
                } catch (e) {
                    report('Cost breakdown draft test', false, { error: e.message });
                }

                // 5. Test Settings Preferences -> New Project Propagation
                try {
                    // Update user preferences to custom values
                    const customPrefs = {
                        company_name: 'Studio Teste 3D',
                        full_name: 'Engenheiro Chefe',
                        phone: '11987654321',
                        pix_key: 'chave@pix.com',
                        default_energy_rate: 1.15,
                        default_profit_margin: 45.0,
                        default_tax_rate: 12.0,
                        default_failure_rate: 15.0,
                        default_cad_rate: 85.0,
                        default_post_rate: 45.0,
                        default_payment_terms: '50% entrada e 50% na retirada',
                        default_warranty_terms: '90 dias contra defeitos de camadas'
                    };
                    await API.auth.updatePreferences(customPrefs);
                    state.user = await API.auth.getMe();

                    // Open new project
                    openNewProject();

                    // Check if openNewProject populated the inputs with user defaults
                    const cadRateVal = parseFloat(document.getElementById('proj-cad-rate').value);
                    const postRateVal = parseFloat(document.getElementById('proj-post-rate').value);
                    const marginVal = parseFloat(document.getElementById('proj-margin').value);
                    const taxVal = parseFloat(document.getElementById('proj-tax').value);
                    const plateFailureVal = state.currentPlates[0]?.failure_margin_percent;

                    const prefsPropagated = (
                        cadRateVal === 85.0 &&
                        postRateVal === 45.0 &&
                        marginVal === 45.0 &&
                        taxVal === 12.0 &&
                        plateFailureVal === 15.0
                    );

                    report('Preferences propagation to New Project', prefsPropagated, {
                        cadRateVal, postRateVal, marginVal, taxVal, plateFailureVal
                    });

                    if (!prefsPropagated) {
                        addIssue(
                            'UX-PREF-PROPAGATION',
                            'Preferências do usuário de taxas e margens não são propagadas corretamente ao abrir Novo Orçamento',
                            'ux',
                            'medium',
                            { cadRateVal, postRateVal, marginVal, taxVal, plateFailureVal }
                        );
                    }
                } catch (e) {
                    report('Preferences propagation test', false, { error: e.message });
                }

                // 6. Test Time Input edge case (minutes > 59 or decimal in plate time)
                try {
                    openNewProject();
                    const hInp = document.getElementById('plate-time-h-0');
                    const mInp = document.getElementById('plate-time-m-0');
                    if (hInp && mInp) {
                        hInp.value = '2';
                        mInp.value = '90'; // User entered 90 minutes instead of 1h 30m
                        updatePlateTime(0);

                        const calculatedHours = state.currentPlates[0].print_time_hours;
                        // 2h + 90m = 3.5h
                        const expectedHours = 3.5;
                        const mathOk = Math.abs(calculatedHours - expectedHours) < 0.001;
                        
                        // Now re-render plates: does it normalize to 3h 30m or remain 2h 90m?
                        renderPlates();
                        const newH = document.getElementById('plate-time-h-0')?.value;
                        const newM = document.getElementById('plate-time-m-0')?.value;
                        
                        report('Plate Time Excess Minutes Handling', mathOk, {
                            calculatedHours,
                            renderedH: newH,
                            renderedM: newM
                        });
                    }
                } catch (e) {
                    report('Time excess minutes test', false, { error: e.message });
                }

                // 7. Test PDF Preview Screen with both client and technical documents
                try {
                    const testProj = await API.projects.create({
                        name: 'Orçamento Preview Teste',
                        client_name: 'Cliente VIP',
                        status: 'quoted',
                        delivery_days: 5,
                        plates: [{
                            name: 'Placa Única',
                            print_time_hours: 4.5,
                            part_weight_g: 120.0,
                            purge_weight_g: 15.0,
                            quantity: 2
                        }],
                        bom_items: [{
                            name: 'Parafuso M3x20',
                            category: 'Fixadores',
                            quantity: 8,
                            unit_cost: 0.75
                        }]
                    });

                    // Check client PDF download endpoint response
                    const clientPdfResp = await fetch(`/api/projects/${testProj.id}/pdf?type=client`, {
                        headers: { "Authorization": `Bearer ${API.getToken()}` }
                    });
                    const clientPdfOk = clientPdfResp.status === 200 && clientPdfResp.headers.get("content-type") === "application/pdf";

                    // Check technical PDF download endpoint response
                    const techPdfResp = await fetch(`/api/projects/${testProj.id}/pdf?type=technical`, {
                        headers: { "Authorization": `Bearer ${API.getToken()}` }
                    });
                    const techPdfOk = techPdfResp.status === 200 && techPdfResp.headers.get("content-type") === "application/pdf";

                    report('PDF Endpoints Generation (Client & Technical)', clientPdfOk && techPdfOk, {
                        clientStatus: clientPdfResp.status,
                        technicalStatus: techPdfResp.status
                    });

                    if (!clientPdfOk || !techPdfOk) {
                        addIssue(
                            'PDF-GEN-ERR',
                            'Falha na geração de PDF comercial ou técnico no backend',
                            'backend',
                            'high',
                            { clientStatus: clientPdfResp.status, techStatus: techPdfResp.status }
                        );
                    }
                } catch (e) {
                    report('PDF preview generation test', false, { error: e.message });
                }

                // 8. Test Manual Rate Fallback Divergence (DOM input vs recalcLiveSummary vs saveCurrentProject)
                try {
                    openNewProject();
                    state.currentPlates = [{
                        name: 'Placa Taxa Divergência',
                        printer_id: null,
                        filament_id: null,
                        custom_printer_hourly_rate: null,
                        custom_filament_cost_per_g: null,
                        print_time_hours: 10.0,
                        part_weight_g: 1000.0,
                        purge_weight_g: 0.0,
                        failure_margin_percent: 0.0,
                        quantity: 1
                    }];
                    renderPlates();
                    recalcLiveSummary();

                    const printerInput = document.querySelector('input[placeholder="2.50"]');
                    const filamentInput = document.querySelector('input[placeholder="0.10"]');
                    const displayedPrinterRate = parseFloat(printerInput?.value);
                    const displayedFilamentRate = parseFloat(filamentInput?.value);

                    const liveMachineCostText = document.getElementById('live-machine-cost')?.textContent || '';
                    const liveMaterialCostText = document.getElementById('live-material-cost')?.textContent || '';

                    // In DOM inputs: displays 2.50 and 0.10.
                    // Expected cost if using displayed inputs:
                    // 10h * 2.50 = R$ 25,00.
                    // 1000g * 0.10 = R$ 100,00.
                    // But recalcLiveSummary lines 2027 & 2037 fall back to 0.09 and 2.0:
                    // machine cost: 10h * 2.00 = R$ 20,00.
                    // material cost: 1000g * 0.09 = R$ 90,00.
                    const isMachineRateDivergent = liveMachineCostText.includes('20,00') && displayedPrinterRate === 2.5;
                    const isFilamentRateDivergent = liveMaterialCostText.includes('90,00') && displayedFilamentRate === 0.1;

                    report('Manual Rate Fallback Parity', !isMachineRateDivergent && !isFilamentRateDivergent, {
                        displayedPrinterRate,
                        liveMachineCostText,
                        displayedFilamentRate,
                        liveMaterialCostText,
                        isMachineRateDivergent,
                        isFilamentRateDivergent
                    });

                    if (isMachineRateDivergent || isFilamentRateDivergent) {
                        addIssue(
                            'CALC-MANUAL-RATE-FALLBACK-DIVERGENCE',
                            'Divergência entre taxa exibida no input da placa (R$ 2,50/h e R$ 0,10/g) e o cálculo da calculadora ao vivo (recalcLiveSummary usa R$ 2,00/h e R$ 0,09/g)',
                            'calculation',
                            'high',
                            {
                                displayedPrinterRate,
                                liveMachineCost: liveMachineCostText,
                                displayedFilamentRate,
                                liveMaterialCost: liveMaterialCostText,
                                explanation: "Inputs da placa usam fallback de 2.50 e 0.10 (linhas 1733, 1767 e saveCurrentProject 2224-2225), enquanto recalcLiveSummary (linhas 2027 e 2037) usa fallback de 0.09 e 2.0"
                            }
                        );
                    }
                } catch (e) {
                    report('Rate divergence test', false, { error: e.message });
                }

                return results;
            })()
            """

            eval_res = await eval_js(audit_script)
            print("=== AUDIT V6 RESULTS ===")
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
