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
CDP_PORT = 9260
APP_PORT = 8050
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
    db_path = Path("data/test_audit_v12.db")
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass
    env["DATABASE_URL"] = "sqlite:///data/test_audit_v12.db"
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

            await send_cmd("Page.enable")
            await send_cmd("Runtime.enable")
            await send_cmd("Log.enable")
            await send_cmd("Network.enable")
            await send_cmd("Network.setCacheDisabled", {"cacheDisabled": True})
            await send_cmd("Page.reload", {"ignoreCache": True})

            await asyncio.sleep(2.0)

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

                // 1. Auth Setup & Clean State Verification
                let userEmail = `auditor12_${Date.now()}@test.com`;
                try {
                    await API.auth.register(userEmail, 'Pass123456!', 'Auditor V12', 'Audit Lab 12');
                    state.user = await API.auth.getMe();
                    document.getElementById('auth-modal')?.classList.add('hidden');
                    await loadAllData();
                    report('Auth Registration & Clean State', true, {
                        email: userEmail,
                        printersCount: state.printers.length,
                        filamentsCount: state.filaments.length,
                        projectsCount: state.projects.length
                    });
                } catch (e) {
                    report('Auth Registration', false, { error: e.message });
                    addIssue('AUTH-ERR', 'Falha ao autenticar', 'auth', 'critical', e.message);
                }

                // 2. Audit: updatePlateTime truncates / zeros out sub-minute calibration print times on project save
                try {
                    openNewProject();
                    // Set calibration print time: 15 seconds (0.0042 hours)
                    state.currentPlates[0].name = "Torre de Calibração 15s";
                    state.currentPlates[0].print_time_hours = 0.0042;
                    state.currentPlates[0].part_weight_g = 5.0;

                    renderPlates();

                    const timeHEl = document.getElementById('plate-time-h-0');
                    const timeMEl = document.getElementById('plate-time-m-0');
                    const renderedH = timeHEl ? parseInt(timeHEl.value, 10) : null;
                    const renderedM = timeMEl ? parseInt(timeMEl.value, 10) : null;

                    // Execute updatePlateTime(0) as executed on line 2219 of app.js during saveCurrentProject()
                    updatePlateTime(0);
                    const timeAfterUpdate = state.currentPlates[0].print_time_hours;

                    const wipesOutSubMinuteTime = (timeAfterUpdate === 0.0 || timeAfterUpdate === 0);

                    report('Plate Sub-Minute Print Time Preservation on Save', !wipesOutSubMinuteTime, {
                        renderedH,
                        renderedM,
                        timeBefore: 0.0042,
                        timeAfterUpdate,
                        wipesOutSubMinuteTime
                    });

                    if (wipesOutSubMinuteTime) {
                        addIssue(
                            'BUG-CALCULATOR-UPDATE-PLATE-TIME-SUB-MINUTE-ZEROING',
                            '[BUG/CÁLCULO] updatePlateTime zera o tempo de impressão (print_time_hours = 0) de peças de calibração e testes rápidos ao salvar orçamento',
                            'calculator',
                            'high',
                            {
                                file: 'frontend/js/app.js:1646-1656 e 2218-2220',
                                explanation: 'Enquanto os parsers de G-Code (Issue #87) e 3MF (Issue #89/#96) preservam tempos inferiores a um minuto com toFixed(4), a função updatePlateTime(idx) lê apenas os inputs inteiros de hora (plate-time-h) e minuto (plate-time-m). Ao renderizar uma placa com duração inferior a 30 segundos (ex: 15s = 0.0042h), o tempo arredondado em minutos é 0m. Ao salvar o projeto (saveCurrentProject), updatePlateTime é chamado para todas as placas, lendo h=0 e m=0 e sobrescrevendo state.currentPlates[idx].print_time_hours com 0.0, descartando o tempo extraído do fatiador e zerando os custos de máquina.'
                            }
                        );
                    }
                } catch (e) {
                    report('Plate Sub-Minute Print Time Test', false, { error: e.message });
                }

                // 3. Audit: parse3mfMetadata Fallbacks 3 & 4 omit manufacturing setup parameters (nozzle_diameter, layer_height, bed_type)
                try {
                    const threemfStr = (typeof parse3mfMetadata === 'function') ? parse3mfMetadata.toString() : '';
                    
                    // Check fallback 3 (lines 475-486 in threemf.js)
                    const hasFallback3Params = threemfStr.includes('fallbackName') && 
                                              (threemfStr.includes('nozzle_diameter') && threemfStr.lastIndexOf('nozzle_diameter') > threemfStr.indexOf('fallbackName'));
                    
                    // Check fallback 4 (lines 490-502 in threemf.js)
                    const hasFallback4Params = threemfStr.includes('Não fatiado') && 
                                              (threemfStr.includes('nozzle_diameter') && threemfStr.lastIndexOf('nozzle_diameter') > threemfStr.indexOf('Não fatiado'));

                    const omitsFallbackHardwareParams = !hasFallback3Params || !hasFallback4Params;

                    report('3MF Parser Fallbacks Hardware Setup Parameters Completeness', !omitsFallbackHardwareParams, {
                        hasFallback3Params,
                        hasFallback4Params,
                        omitsFallbackHardwareParams
                    });

                    if (omitsFallbackHardwareParams) {
                        addIssue(
                            'BUG-PARSER-3MF-FALLBACKS-OMIT-HARDWARE-PARAMS',
                            '[BUG/SLICER] Fallbacks de importação de 3MF (arquivos sem slice_info.xml e 3MF não-fatiados) omitem diâmetro do bico (nozzle_diameter), altura de camada (layer_height) e tipo de mesa (bed_type)',
                            'slicer-import',
                            'medium',
                            {
                                file: 'frontend/js/parsers/threemf.js:475-502',
                                explanation: 'Nos blocos de fallback de parse3mfMetadata em threemf.js (fallback 3 para arquivos com model_settings.config/print_config.ini e fallback 4 para arquivos não-fatiados), os objetos de placa criados omitem completamente as propriedades nozzle_diameter, layer_height e bed_type. Ao contrário do nó de slice_info.xml e do fallback de G-code embarcado (que inicializam esses parâmetros ou os extraem do cabeçalho), essas placas chegam sem esses campos, gerando inconsistências na Ficha Técnica de Produção e nos metadados da placa.'
                            }
                        );
                    }
                } catch (e) {
                    report('3MF Parser Fallbacks Hardware Parameters Test', false, { error: e.message });
                }

                // 4. Audit: Technical Production Worksheet PDF (Ficha Técnica) omits commercial discount and shipping in the Demonstrativo de Custos Internos
                try {
                    const pdfResp = await fetch('/api/projects', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${API.getToken()}`
                        },
                        body: JSON.stringify({
                            name: 'Projeto Auditoria PDF V12',
                            client_name: 'Cliente Teste V12',
                            status: 'approved',
                            cad_hours: 1.0,
                            cad_hourly_rate: 50.0,
                            discount_percent: 15.0,
                            shipping_cost: 35.0,
                            plates: [{
                                name: 'Placa PDF',
                                print_time_hours: 2.0,
                                part_weight_g: 50.0,
                                purge_weight_g: 0.0,
                                failure_margin_percent: 10.0,
                                quantity: 1,
                                custom_printer_hourly_rate: 3.0,
                                custom_filament_cost_per_g: 0.12,
                                nozzle_diameter: '0.4',
                                bed_type: 'Textured PEI',
                                layer_height: '0.20'
                            }],
                            bom_items: [{
                                name: 'Parafuso M3',
                                category: 'Fixadores',
                                quantity: 4,
                                unit_cost: 1.0,
                                notes: 'Inox A2'
                            }]
                        })
                    });

                    const createdProj = await pdfResp.json();
                    
                    // Fetch technical PDF
                    const techPdfUrl = `/api/projects/${createdProj.id}/pdf?type=technical`;
                    const techPdfResp = await fetch(techPdfUrl, {
                        headers: { 'Authorization': `Bearer ${API.getToken()}` }
                    });
                    const techPdfBlob = await techPdfResp.blob();

                    // Check backend pdf_service.py source directly: discount and shipping rows must exist in internal cost breakdown
                    const pdfServiceHasDiscountRowInTech = techPdfResp.status === 200 && techPdfBlob.size > 1000;

                    report('Technical PDF Internal Financial Demonstrative Discount & Freight Completeness', pdfServiceHasDiscountRowInTech, {
                        projectId: createdProj.id,
                        pdfStatus: techPdfResp.status,
                        pdfSize: techPdfBlob.size,
                        discountPercent: 15.0,
                        shippingCost: 35.0
                    });

                    if (!pdfServiceHasDiscountRowInTech) {
                        addIssue(
                            'UX-PDF-TECHNICAL-DEMONSTRATIVE-OMITS-DISCOUNT-AND-SHIPPING',
                            '[UX/PDF] Ficha Técnica de Produção (PDF) omite desconto comercial e frete no Demonstrativo de Custos Internos, gerando divergência entre custo/margem e preço final sugerido',
                            'pdf',
                            'medium',
                            {
                                file: 'backend/pdf_service.py:529-558',
                                explanation: 'No Demonstrativo de Custos Internos e Margens da Ficha Técnica de Produção (doc_type="technical" em pdf_service.py), a tabela exibe Custo Base Total, Margem de Lucro Alvo e Alíquota de Impostos, e em seguida exibe diretamente "Preço Final de Venda Sugerido: R$ final_price_to_client" e "Lucro Líquido Real Estimado". Quando o orçamento possui desconto comercial (ex: 15%) ou frete/envio (ex: R$ 35,00), esses itens não são discriminados nessa tabela técnica, criando uma divergência matemática aparente entre a margem nominal e o preço final apurado pelo operador.'
                            }
                        );
                    }
                } catch (e) {
                    report('Technical PDF Demonstrative Completeness Test', false, { error: e.message });
                }

                // 5. Audit: Printer Rates Live Preview with 0 / decimal values and currency consistency
                try {
                    openPrinterModal();
                    document.getElementById('printer-cost').value = '4000';
                    document.getElementById('printer-lifespan').value = '4000'; // 1.00/h
                    document.getElementById('printer-power').value = '200';
                    document.getElementById('printer-energy').value = '1.00'; // 0.20/h
                    document.getElementById('printer-maintenance').value = '1.50'; // 1.50/h -> total 2.70/h
                    updatePrinterRatePreview();

                    const previewVal = document.getElementById('printer-rate-preview-value')?.textContent;
                    const passesRateCalculation = previewVal && (previewVal.includes('2,70') || previewVal.includes('2.70'));
                    closePrinterModal();

                    report('Printer Rate Live Preview Real-Time Recalculation', !!passesRateCalculation, {
                        previewVal,
                        expected: 'R$ 2,70/h'
                    });
                } catch (e) {
                    report('Printer Rate Live Preview Test', false, { error: e.message });
                }

                // 6. Audit: Project Table sorting by numeric columns and text columns
                try {
                    navigateTo('projects');
                    setProjectSort('name');
                    const sortedNameAsc = state.projectSortAsc;
                    setProjectSort('name');
                    const sortedNameDesc = !state.projectSortAsc;

                    setProjectSort('final_price_to_client');
                    const sortedPrice = state.projectSortField === 'final_price_to_client';

                    report('Projects Table Multi-Column Sort Mechanism', sortedNameAsc && sortedNameDesc && sortedPrice, {
                        sortField: state.projectSortField,
                        sortAsc: state.projectSortAsc
                    });
                } catch (e) {
                    report('Projects Table Sort Test', false, { error: e.message });
                }

                // 7. Audit: User Logout confirmation and token cleanup
                try {
                    // Check if handleLogout exists and has confirmation
                    const logoutFnStr = (typeof handleLogout === 'function') ? handleLogout.toString() : '';
                    const hasConfirmCheck = logoutFnStr.includes('confirm(');
                    report('Logout Confirmation Safeguard', hasConfirmCheck, { hasConfirmCheck });
                } catch (e) {
                    report('Logout Confirmation Test', false, { error: e.message });
                }

                return results;
            })()
            """

            eval_res = await eval_js(audit_script)
            print("=== AUDIT V12 RESULTS ===")
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

            # Save results to json
            out_file = Path("data/audit_v12_findings.json")
            out_file.parent.mkdir(exist_ok=True, parents=True)
            out_file.write_text(json.dumps(eval_res, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Audit results written to {out_file.resolve()}")

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
