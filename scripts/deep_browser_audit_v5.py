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
CDP_PORT = 9235
APP_PORT = 8020
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
    env["DATABASE_URL"] = "sqlite:///data/test_audit_v5.db"
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

                // 1. Register & Login
                try {
                    const email = `audit5_${Date.now()}@test.com`;
                    await API.auth.register(email, 'Pass123456!', 'Auditor V5', 'Lab Audit 5');
                    state.user = await API.auth.getMe();
                    document.getElementById('auth-modal')?.classList.add('hidden');
                    await loadAllData();
                    report('Auth Registration', true, { email });
                } catch (e) {
                    report('Auth Registration', false, { error: e.message });
                    addIssue('AUTH-ERR', 'Falha ao registrar usuário', 'auth', 'critical', e.message);
                }

                // 2. Test XSS in Printer and Filament Grids
                try {
                    // Create printer with potential XSS payload in name and model
                    const xssName = '<img src=x onerror=window._xss_printer=1>';
                    const pRes = await API.printers.create({
                        name: xssName,
                        model: '<b id="xss-model">TestModel</b>',
                        acquisition_cost: 1000,
                        lifespan_hours: 5000,
                        avg_power_watts: 150,
                        maintenance_cost_per_hour: 1,
                        energy_rate_kwh: 0.85
                    });
                    await loadAllData();
                    navigateTo('printers');
                    renderPrintersGrid();
                    const xssPrinterFired = Boolean(window._xss_printer);
                    const rawBoldInjected = Boolean(document.getElementById('xss-model'));
                    
                    report('Printer XSS Sanitization', !xssPrinterFired && !rawBoldInjected, {
                        xssPrinterFired, rawBoldInjected
                    });

                    if (xssPrinterFired || rawBoldInjected) {
                        addIssue(
                            'SEC-XSS-PRINTER',
                            'Vulnerabilidade de Cross-Site Scripting (XSS) no grid de impressoras por interpolação direta de nome e modelo sem escapeHtml',
                            'security',
                            'high',
                            { xssPrinterFired, rawBoldInjected }
                        );
                    }

                    // Create filament with potential XSS payload
                    const fRes = await API.filaments.create({
                        name: '<img src=x onerror=window._xss_fil=1>',
                        brand: '<b id="xss-brand">BrandX</b>',
                        material: 'PLA',
                        color: '<b id="xss-color">ColorX</b>',
                        color_hex: '#10b981',
                        spool_weight_g: 1000,
                        spool_price: 100,
                        density_g_cm3: 1.24
                    });
                    await loadAllData();
                    navigateTo('filaments');
                    renderFilamentsGrid();
                    const xssFilFired = Boolean(window._xss_fil);
                    const rawFilBoldInjected = Boolean(document.getElementById('xss-brand') || document.getElementById('xss-color'));
                    
                    report('Filament XSS Sanitization', !xssFilFired && !rawFilBoldInjected, {
                        xssFilFired, rawFilBoldInjected
                    });

                    if (xssFilFired || rawFilBoldInjected) {
                        addIssue(
                            'SEC-XSS-FILAMENT',
                            'Vulnerabilidade de Cross-Site Scripting (XSS) no grid de filamentos por interpolação direta de nome, marca e cor sem escapeHtml',
                            'security',
                            'high',
                            { xssFilFired, rawFilBoldInjected }
                        );
                    }
                } catch (e) {
                    report('XSS Testing', false, { error: e.message });
                }

                // 3. Test Filter Query XSS in Printer and Filament Search Empty States
                try {
                    navigateTo('filaments');
                    const xssQuery = '<img src=x onerror=window._xss_fil_filter=1>';
                    renderFilamentsGrid(xssQuery);
                    const xssFilFilterFired = Boolean(window._xss_fil_filter);
                    report('Filament Search Filter XSS', !xssFilFilterFired, { xssFilFilterFired });
                    if (xssFilFilterFired) {
                        addIssue(
                            'SEC-XSS-FIL-FILTER',
                            'Vulnerabilidade de XSS na mensagem de estado vazio do filtro de filamentos ao interpolar termo de busca sem escapeHtml',
                            'security',
                            'high',
                            { xssFilFilterFired }
                        );
                    }

                    navigateTo('printers');
                    const xssPrinterQuery = '<img src=x onerror=window._xss_printer_filter=1>';
                    renderPrintersGrid(xssPrinterQuery);
                    const xssPrinterFilterFired = Boolean(window._xss_printer_filter);
                    report('Printer Search Filter XSS', !xssPrinterFilterFired, { xssPrinterFilterFired });
                    if (xssPrinterFilterFired) {
                        addIssue(
                            'SEC-XSS-PRINTER-FILTER',
                            'Vulnerabilidade de XSS na mensagem de estado vazio do filtro de impressoras ao interpolar termo de busca sem escapeHtml',
                            'security',
                            'high',
                            { xssPrinterFilterFired }
                        );
                    }
                } catch (e) {
                    report('Search filter XSS', false, { error: e.message });
                }

                // 4. Test Plate Custom Rate fallback when printer or filament is deleted or invalid
                try {
                    openNewProject();
                    // Set plate with non-existent printer_id and filament_id
                    state.currentPlates = [{
                        name: 'Placa ID Órfão',
                        printer_id: 999999,
                        filament_id: 999999,
                        custom_printer_hourly_rate: 3.50,
                        custom_filament_cost_per_g: 0.15,
                        print_time_hours: 2.0,
                        part_weight_g: 50.0,
                        purge_weight_g: 0.0,
                        failure_margin_percent: 10.0,
                        quantity: 1
                    }];
                    renderPlates();
                    recalcLiveSummary();

                    // Check if manual input rate fields are visible in DOM or if user is locked out
                    const platesContainer = document.getElementById('plates-container');
                    const manualPrinterInput = platesContainer.querySelector('input[placeholder="2.50"]');
                    const manualFilamentInput = platesContainer.querySelector('input[placeholder="0.10"]');

                    // If printer_id is 999999, the select shows "Personalizada (Manual)",
                    // but because plate.printer_id is truthy, manual input is NOT rendered!
                    const hasManualPrinterInput = Boolean(manualPrinterInput);
                    const hasManualFilamentInput = Boolean(manualFilamentInput);

                    report('Orphan Plate ID Manual Input Visible', hasManualPrinterInput && hasManualFilamentInput, {
                        hasManualPrinterInput,
                        hasManualFilamentInput
                    });

                    if (!hasManualPrinterInput || !hasManualFilamentInput) {
                        addIssue(
                            'UX-ORPHAN-RATE-INPUT',
                            'Campos de taxa horária e custo de filamento manual ficam ocultos quando placa referencia ID inexistente/excluído de impressora ou filamento',
                            'ux',
                            'medium',
                            { hasManualPrinterInput, hasManualFilamentInput }
                        );
                    }
                } catch (e) {
                    report('Orphan plate test', false, { error: e.message });
                }

                // 5. Test Live Summary Negative and Extreme Calculation Discrepancies
                try {
                    openNewProject();
                    document.getElementById('proj-name').value = 'Projeto Teste Limites';
                    state.currentPlates = [{
                        name: 'Placa 1',
                        printer_id: null,
                        custom_printer_hourly_rate: 10.0,
                        filament_id: null,
                        custom_filament_cost_per_g: 0.10,
                        print_time_hours: 5.0,
                        part_weight_g: 100.0,
                        purge_weight_g: 0.0,
                        failure_margin_percent: 10.0,
                        quantity: 1
                    }];
                    renderPlates();

                    // Inject negative discount:
                    document.getElementById('proj-discount').value = '-20';
                    // Inject negative margin:
                    document.getElementById('proj-margin').value = '-10';
                    // Inject negative tax:
                    document.getElementById('proj-tax').value = '-5';

                    recalcLiveSummary();

                    const liveDiscountText = document.getElementById('live-discount-amount')?.textContent;
                    const liveFinalPriceText = document.getElementById('live-final-price')?.textContent;

                    // If discount is -20%, does frontend allow negative discount?
                    const allowedNegativeDiscount = liveDiscountText && liveDiscountText.includes('--');
                    
                    report('Negative Inputs Clamping in Live Summary', !allowedNegativeDiscount, {
                        liveDiscountText,
                        liveFinalPriceText
                    });

                    if (allowedNegativeDiscount) {
                        addIssue(
                            'CALC-NEGATIVE-CLAMP',
                            'Calculadora em tempo real (recalcLiveSummary) não aplica Math.max(0, ...) em descontos, margens e impostos, divergindo da validação da Engine do Backend',
                            'calculation',
                            'medium',
                            { liveDiscountText, liveFinalPriceText }
                        );
                    }
                } catch (e) {
                    report('Negative input test', false, { error: e.message });
                }

                // 6. Test Monthly Timeline Base Cost Distortion on Draft & Quoted projects
                try {
                    // Create an approved project
                    const pApproved = await API.projects.create({
                        name: 'Projeto Aprovado Real',
                        status: 'approved',
                        cad_hours: 2,
                        cad_hourly_rate: 50,
                        overhead_cost: 20,
                        profit_margin_percent: 30,
                        plates: [{
                            name: 'Placa A',
                            print_time_hours: 2.0,
                            part_weight_g: 100.0,
                            custom_printer_hourly_rate: 10.0,
                            custom_filament_cost_per_g: 0.10,
                            quantity: 1
                        }]
                    });

                    // Create 3 draft test projects with huge costs
                    const pDraft = await API.projects.create({
                        name: 'Orçamento Rascunho Teste',
                        status: 'draft',
                        cad_hours: 10,
                        cad_hourly_rate: 100,
                        overhead_cost: 500,
                        profit_margin_percent: 50,
                        plates: [{
                            name: 'Placa Draft',
                            print_time_hours: 20.0,
                            part_weight_g: 500.0,
                            custom_printer_hourly_rate: 20.0,
                            custom_filament_cost_per_g: 0.20,
                            quantity: 2
                        }]
                    });

                    const stats = await API.projects.getDashboardStats();
                    const currentMonthKey = (new Date()).toISOString().substring(0, 7);
                    const monthStat = stats.monthly_timeline.find(m => m.month_key === currentMonthKey);

                    // Check if monthStat base_cost includes the draft project
                    // pApproved base_cost is ~151, pDraft base_cost is ~2000+
                    const isDraftIncludedInMonthlyBaseCost = monthStat && monthStat.base_cost > 1000;
                    
                    report('Monthly Timeline Base Cost Isolation', !isDraftIncludedInMonthlyBaseCost, {
                        monthStat,
                        isDraftIncludedInMonthlyBaseCost
                    });

                    if (isDraftIncludedInMonthlyBaseCost) {
                        addIssue(
                            'METRIC-DRAFT-BASE-COST-LEAK',
                            'Gráfico temporal de Faturamento e Lucratividade (Chart 2) soma o Custo Base de orçamentos em Rascunho (draft) e Orçados (quoted), distorcendo a relação entre Faturamento e Custo da oficina',
                            'metrics',
                            'high',
                            {
                                monthlyRevenue: monthStat.revenue,
                                monthlyBaseCost: monthStat.base_cost,
                                monthlyNetProfit: monthStat.net_profit
                            }
                        );
                    }
                } catch (e) {
                    report('Monthly timeline test', false, { error: e.message });
                }

                // 7. Test PDF Preview Screen with missing params and special characters
                try {
                    // Test preview url with non-existent ID
                    const testUrl = `${window.location.origin}/preview.html?project_id=999999&type=client`;
                    const iframe = document.createElement('iframe');
                    iframe.src = testUrl;
                    iframe.style.display = 'none';
                    document.body.appendChild(iframe);
                    await new Promise(r => setTimeout(r, 1200));

                    // Verify if iframe loaded error state without crashing
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    const errorState = iframeDoc?.getElementById('error-state');
                    const isErrorVisible = errorState && !errorState.classList.contains('hidden');
                    report('PDF Preview 404 Graceful Handling', isErrorVisible, { isErrorVisible });

                    document.body.removeChild(iframe);
                } catch (e) {
                    report('PDF Preview test', false, { error: e.message });
                }

                return results;
            })()
            """

            eval_res = await eval_js(audit_script)
            print("=== AUDIT V5 RESULTS ===")
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
