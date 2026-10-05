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
CDP_PORT = 9247
APP_PORT = 8037
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
    db_path = Path("data/test_audit_v7.db")
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass
    env["DATABASE_URL"] = "sqlite:///data/test_audit_v7.db"
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
                    const email = `audit7_${Date.now()}@test.com`;
                    await API.auth.register(email, 'Pass123456!', 'Auditor V7', 'Audit Lab 7');
                    state.user = await API.auth.getMe();
                    document.getElementById('auth-modal')?.classList.add('hidden');
                    await loadAllData();
                    report('Auth Registration', true, { email });
                } catch (e) {
                    report('Auth Registration', false, { error: e.message });
                    addIssue('AUTH-ERR', 'Falha ao autenticar', 'auth', 'critical', e.message);
                }

                // 2. Test XSS in Filaments Grid color_hex attribute injection
                try {
                    window._xss_fil_color_fired = false;
                    // Attempt attribute breakout via color_hex: red; border: 1px solid" onerror="window._xss_fil_color_fired=true"
                    const xssPayloadColor = '"><img src=x onerror=window._xss_fil_color_fired=true data-xss="1';
                    
                    const filResp = await fetch('/api/filaments', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${API.getToken()}`
                        },
                        body: JSON.stringify({
                            name: 'Filamento XSS Hex',
                            brand: 'Marca Teste',
                            material: 'PLA',
                            color: 'Vermelho',
                            color_hex: xssPayloadColor,
                            spool_weight_g: 1000,
                            spool_price: 90
                        })
                    });
                    
                    const filData = await filResp.json();
                    await loadAllData();
                    renderFilamentsGrid();

                    // Check if DOM contains the injected img tag or if flag fired
                    const imgInjected = Boolean(document.querySelector('#filaments-grid img[onerror]'));
                    const xssFired = Boolean(window._xss_fil_color_fired);

                    report('Filament Grid Color Hex Sanitization', !imgInjected && !xssFired, {
                        imgInjected,
                        xssFired,
                        status: filResp.status
                    });

                    if (imgInjected || xssFired) {
                        addIssue(
                            'SEC-XSS-FILAMENT-COLOR-HEX',
                            'Vulnerabilidade de Cross-Site Scripting (XSS) no Grid de Filamentos por interpolação direta de color_hex no atributo style sem escapeHtml',
                            'security',
                            'high',
                            {
                                imgInjected,
                                xssFired,
                                file: 'frontend/js/app.js:3112-3113'
                            }
                        );
                    }
                } catch (e) {
                    report('Filament Color Hex XSS Test', false, { error: e.message });
                }

                // 3. Test Stored XSS via Project Status in Tables
                try {
                    window._xss_status_table_fired = false;
                    const xssStatusPayload = '<img src=x onerror=window._xss_status_table_fired=true data-xss-status="1">';

                    // Inject status directly via API
                    const projResp = await fetch('/api/projects', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${API.getToken()}`
                        },
                        body: JSON.stringify({
                            name: 'Projeto XSS Status',
                            status: xssStatusPayload,
                            plates: [{ name: 'P1', print_time_hours: 1, part_weight_g: 10 }]
                        })
                    });

                    const projData = await projResp.json();
                    await loadAllData();
                    renderRecentProjects();
                    renderProjectsTable();

                    const statusImgInjected = Boolean(document.querySelector('img[data-xss-status="1"]'));
                    const statusXssFired = Boolean(window._xss_status_table_fired);

                    report('Project Status Sanitization & Validation', !statusImgInjected && !statusXssFired, {
                        statusImgInjected,
                        statusXssFired,
                        createdStatus: projData.status
                    });

                    if (statusImgInjected || statusXssFired) {
                        addIssue(
                            'SEC-XSS-PROJECT-STATUS',
                            'Vulnerabilidade de Cross-Site Scripting (XSS) e ausência de validação de status de projeto nas listagens de orçamentos',
                            'security',
                            'high',
                            {
                                statusImgInjected,
                                statusXssFired,
                                explanation: 'p.status e formatStatus(p.status) são interpolados sem escapeHtml em renderRecentProjects (linha 1180) e renderProjectsTable (linha 1411), e status não possui validação de enum no backend'
                            }
                        );
                    }
                } catch (e) {
                    report('Project Status XSS Test', false, { error: e.message });
                }

                // 4. Test Blank Project Name Validation
                try {
                    const blankNameResp = await fetch('/api/projects', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${API.getToken()}`
                        },
                        body: JSON.stringify({
                            name: '    ',
                            plates: [{ name: 'P1', print_time_hours: 1, part_weight_g: 10 }]
                        })
                    });

                    // Should be rejected with 422 Unprocessable Entity
                    const blankRejected = blankNameResp.status === 422;
                    report('Project Blank Name Validation', blankRejected, {
                        status: blankNameResp.status
                    });

                    if (!blankRejected) {
                        addIssue(
                            'VAL-PROJECT-BLANK-NAME',
                            'API aceita criação e atualização de projetos com nome vazio ou contendo apenas espaços em branco',
                            'validation',
                            'medium',
                            {
                                status: blankNameResp.status,
                                explanation: 'ProjectBase e ProjectUpdate em backend/schemas.py não possuem validator validate_name_not_blank, ao contrário de PlateBase e BOMItemBase'
                            }
                        );
                    }
                } catch (e) {
                    report('Blank Project Name Test', false, { error: e.message });
                }

                // 5. Test Top Projects (Chart 4) Draft/Quoted Isolation
                try {
                    // Create an expensive DRAFT project
                    await fetch('/api/projects', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${API.getToken()}`
                        },
                        body: JSON.stringify({
                            name: 'Orçamento Fictício Rascunho R$ 99.000',
                            status: 'draft',
                            cad_hours: 500,
                            cad_hourly_rate: 100,
                            overhead_cost: 20000,
                            profit_margin_percent: 50,
                            plates: [{ name: 'P1', print_time_hours: 100, part_weight_g: 1000 }]
                        })
                    });

                    // Create a REALIZED project
                    await fetch('/api/projects', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${API.getToken()}`
                        },
                        body: JSON.stringify({
                            name: 'Projeto Aprovado Real R$ 300',
                            status: 'approved',
                            plates: [{ name: 'P1', print_time_hours: 2, part_weight_g: 50 }]
                        })
                    });

                    const stats = await API.projects.getDashboardStats();
                    const topProjects = stats.top_projects || [];
                    const topHasDraft = topProjects.some(p => p.status === 'draft' || p.status === 'quoted');

                    report('Top Projects Realized Isolation', !topHasDraft, {
                        topProjects: topProjects.map(p => ({ id: p.id, name: p.name, status: p.status, final_price: p.final_price }))
                    });

                    if (topHasDraft) {
                        addIssue(
                            'METRIC-TOP-PROJECTS-DRAFT-CONTAMINATION',
                            'Gráfico de Top Projetos (Chart 4) exibe orçamentos em Rascunho (draft) e Orçados (quoted) como Faturamento realizado',
                            'metrics',
                            'medium',
                            {
                                topProjectsCount: topProjects.length,
                                draftsInTop: topProjects.filter(p => p.status === 'draft' || p.status === 'quoted').map(p => p.name),
                                explanation: 'Linha 232 de project_routes.py filtra apenas if st != "cancelled", incluindo drafts no ranking de Faturamento e Lucro Líquido'
                            }
                        );
                    }
                } catch (e) {
                    report('Top Projects Isolation Test', false, { error: e.message });
                }

                // 6. Test Printer Duplicate Feature Presence
                try {
                    const hasDuplicateFn = typeof window.duplicatePrinter === 'function';
                    // Check if backend has duplicate printer endpoint
                    const printers = await API.printers.list();
                    let backendHasDup = false;
                    if (printers.length > 0) {
                        const dupResp = await fetch(`/api/printers/${printers[0].id}/duplicate`, {
                            method: 'POST',
                            headers: { 'Authorization': `Bearer ${API.getToken()}` }
                        });
                        backendHasDup = (dupResp.status === 200 || dupResp.status === 201);
                    }

                    report('Printer Duplicate Support', hasDuplicateFn && backendHasDup, {
                        hasDuplicateFn,
                        backendHasDup
                    });

                    if (!hasDuplicateFn || !backendHasDup) {
                        addIssue(
                            'FEAT-PRINTER-DUPLICATE',
                            'Ausência de funcionalidade de duplicação para impressoras no catálogo da oficina',
                            'feature',
                            'medium',
                            {
                                hasDuplicateFn,
                                backendHasDup,
                                explanation: 'Diferente de Filamentos, Placas, BOM e Projetos que possuem ação de duplicação, Impressoras não contam com endpoint nem ação na interface'
                            }
                        );
                    }
                } catch (e) {
                    report('Printer Duplicate Test', false, { error: e.message });
                }

                // 7. Test Negative Custom Rates in Plate Schemas
                try {
                    const negRateResp = await fetch('/api/projects', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${API.getToken()}`
                        },
                        body: JSON.stringify({
                            name: 'Projeto Taxa Negativa',
                            status: 'draft',
                            plates: [{
                                name: 'Placa Negativa',
                                custom_printer_hourly_rate: -15.0,
                                custom_filament_cost_per_g: -0.5,
                                print_time_hours: 1,
                                part_weight_g: 10
                            }]
                        })
                    });

                    // Negative rates should be rejected with 422
                    const negRejected = negRateResp.status === 422;
                    report('Plate Custom Negative Rates Validation', negRejected, {
                        status: negRateResp.status
                    });

                    if (!negRejected) {
                        addIssue(
                            'VAL-PLATE-NEGATIVE-RATES',
                            'API aceita taxas horárias e custos de filamento manuais negativos (custom_printer_hourly_rate e custom_filament_cost_per_g) na placa',
                            'validation',
                            'medium',
                            {
                                status: negRateResp.status,
                                explanation: 'PlateBase e PlateUpdate em backend/schemas.py não possuem restrição ge=0 para custom_printer_hourly_rate e custom_filament_cost_per_g'
                            }
                        );
                    }
                } catch (e) {
                    report('Negative Rates Test', false, { error: e.message });
                }

                // 8. Test Printer is_active Status field in Modal and Card
                try {
                    openPrinterModal();
                    const hasActiveInput = Boolean(document.getElementById('printer-is-active') || document.querySelector('#form-printer input[name="is_active"]'));
                    closePrinterModal();

                    report('Printer Active Status Input in Modal', hasActiveInput, {
                        hasActiveInput
                    });

                    if (!hasActiveInput) {
                        addIssue(
                            'UX-PRINTER-ACTIVE-STATUS',
                            'Filtro de status de impressoras (Inativas / Manutenção) inoperante por ausência de campo is_active no modal e salvamento',
                            'ux',
                            'medium',
                            {
                                hasActiveInput,
                                explanation: 'A interface possui filtro de status (#printer-status-filter), mas o formulário de impressora não tem campo para alternar entre ativa/inativa'
                            }
                        );
                    }
                } catch (e) {
                    report('Printer Active Status Test', false, { error: e.message });
                }

                return results;
            })()
            """

            eval_res = await eval_js(audit_script)
            print("=== AUDIT V7 RESULTS ===")
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
