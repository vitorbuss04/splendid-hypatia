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
    db_path = Path("data/test_audit_v11.db")
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass
    env["DATABASE_URL"] = "sqlite:///data/test_audit_v11.db"
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
                    const email = `audit11_${Date.now()}@test.com`;
                    await API.auth.register(email, 'Pass123456!', 'Auditor V11', 'Audit Lab 11');
                    state.user = await API.auth.getMe();
                    document.getElementById('auth-modal')?.classList.add('hidden');
                    await loadAllData();
                    report('Auth Registration', true, { email });
                } catch (e) {
                    report('Auth Registration', false, { error: e.message });
                    addIssue('AUTH-ERR', 'Falha ao autenticar', 'auth', 'critical', e.message);
                }

                // 2. Audit: handleSinglePlateFile omits nozzle_diameter, layer_height, bed_type from single plate import
                try {
                    openNewProject();
                    const singlePlateFnStr = handleSinglePlateFile.toString();
                    const hasGcodeNozzleAssignment = singlePlateFnStr.includes("nozzle_diameter = meta.nozzle_diameter") || singlePlateFnStr.includes("p.nozzle_diameter = meta.nozzle_diameter");
                    const has3mfNozzleAssignmentOnTargetPlate = singlePlateFnStr.includes("state.currentPlates[plateIdx].nozzle_diameter = plates[0].nozzle_diameter");
                    
                    const omitsHardwareParamsOnSinglePlate = !hasGcodeNozzleAssignment && !has3mfNozzleAssignmentOnTargetPlate;

                    report('Single Plate Slicer File Hardware Setup Parameters Extraction', !omitsHardwareParamsOnSinglePlate, {
                        hasGcodeNozzleAssignment,
                        has3mfNozzleAssignmentOnTargetPlate,
                        omitsHardwareParamsOnSinglePlate
                    });

                    if (omitsHardwareParamsOnSinglePlate) {
                        addIssue(
                            'BUG-SLICER-SINGLE-PLATE-OMITS-HARDWARE-PARAMS',
                            '[BUG/SLICER] Importação individual de arquivo 3MF e G-Code via handleSinglePlateFile descarta diâmetro do bico (nozzle_diameter), altura de camada (layer_height) e tipo de mesa (bed_type)',
                            'frontend',
                            'high',
                            {
                                file: 'frontend/js/app.js:2586-2705',
                                explanation: 'Enquanto o parser de G-Code (parseGcodeMetadata) e o leitor de 3MF (parse3mfMetadata) extraem com sucesso nozzle_diameter, layer_height e bed_type do fatiador, a função handleSinglePlateFile nunca atribui esses valores a state.currentPlates[plateIdx]. Como resultado, ao importar um arquivo 3MF ou G-Code diretamente em um card de placa existente, os parâmetros de manufatura permanecem inalterados com os padrões genéricos (0.4mm, 0.20mm, Textured PEI), descartando as configurações reais de fatiamento.'
                            }
                        );
                    }
                } catch (e) {
                    report('Single Plate Hardware Parameters Test', false, { error: e.message });
                }

                // 3. Audit: threemf.js premature toFixed(2) rounding truncates short calibration prints
                try {
                    const threemfStr = (typeof parse3mfMetadata === 'function') ? parse3mfMetadata.toString() : '';
                    const hasPrematureFixed2 = (
                        threemfStr.includes('print_time_hours: parseFloat(printTimeHours.toFixed(2))') ||
                        threemfStr.includes('parseFloat((secs / 3600).toFixed(2))')
                    );

                    // Test with simulated seconds = 15s (0.00416 hours)
                    const simulatedHours = 15 / 3600;
                    const truncatedFixed2 = parseFloat(simulatedHours.toFixed(2));

                    report('3MF Parser Short Print Time Precision', !hasPrematureFixed2, {
                        hasPrematureFixed2,
                        simulatedHours,
                        truncatedFixed2
                    });

                    if (hasPrematureFixed2) {
                        addIssue(
                            'BUG-PARSER-3MF-PREMATURE-ROUNDING',
                            '[BUG/PARSER] Leitor de arquivos 3MF (threemf.js) zera o tempo de impressão (print_time_hours = 0) para peças de calibração ou testes rápidos devido a arredondamento prematuro toFixed(2)',
                            'frontend',
                            'medium',
                            {
                                file: 'frontend/js/parsers/threemf.js:278 e 461',
                                explanation: 'Em threemf.js (linhas 278 e 461), o tempo em horas é calculado com parseFloat(printTimeHours.toFixed(2)) e parseFloat((secs / 3600).toFixed(2)). Para impressões de calibração rápidas (tempo inferior a 18 segundos), o valor em horas é menor que 0.005h e é arredondado para 0.00h, fazendo a placa ser importada com tempo zerado. No leitor de G-Code isso foi corrigido na Issue #87 com fallback toFixed(4), mas o leitor de 3MF permaneceu vulnerável ao arredondamento prematuro.'
                            }
                        );
                    }
                } catch (e) {
                    report('3MF Parser Precision Test', false, { error: e.message });
                }

                // 4. Audit: threemf.js multi-material purge/flush weight drops subsequent filaments
                try {
                    const threemfStr = (typeof parse3mfMetadata === 'function') ? parse3mfMetadata.toString() : '';
                    const dropsMultiFilamentFlush = threemfStr.includes('if (flushG > 0 && purgeGrams === 0)');

                    report('3MF Parser Multi-Filament Flush Purge Accumulation', !dropsMultiFilamentFlush, {
                        dropsMultiFilamentFlush
                    });

                    if (dropsMultiFilamentFlush) {
                        addIssue(
                            'BUG-PARSER-3MF-MULTI-FILAMENT-PURGE-LOSS',
                            '[BUG/SLICER] Leitor de 3MF (threemf.js) descarta o peso de purga/flush dos filamentos subsequentes em impressões multi-materiais (Bambu AMS)',
                            'frontend',
                            'high',
                            {
                                file: 'frontend/js/parsers/threemf.js:243-245',
                                explanation: 'Na linha 243 de threemf.js, ao iterar sobre as tags <filament> de uma placa fatiada no Bambu Studio ou OrcaSlicer, a condição if (flushG > 0 && purgeGrams === 0) purgeGrams += flushG; faz com que apenas o primeiro filamento tenha seu flush_g somado. A partir do segundo filamento, purgeGrams já é maior que zero, ignorando completamente o flush de todos os demais carretéis e subestimando expressivamente o custo real de desperdício em peças coloridas.'
                            }
                        );
                    }
                } catch (e) {
                    report('3MF Multi-Filament Flush Test', false, { error: e.message });
                }

                // 5. Audit: handleSavePrinter missing numeric validation on lifespan_hours and negative rates
                try {
                    openPrinterModal();
                    const savePrinterStr = handleSavePrinter.toString();
                    const hasLifespanPositiveCheck = (
                        savePrinterStr.includes('lifespan_hours <= 0') ||
                        savePrinterStr.includes('lifespan <= 0') ||
                        savePrinterStr.includes('lifespan_hours <')
                    );
                    closePrinterModal();

                    report('Printer Modal Client-Side Numeric Lifespan Validation', hasLifespanPositiveCheck, {
                        hasLifespanPositiveCheck
                    });

                    if (!hasLifespanPositiveCheck) {
                        addIssue(
                            'UX-PRINTER-MODAL-MISSING-NUMERIC-VALIDATION',
                            '[UX/BUG] Modal de impressora não valida vida útil estritamente positiva (lifespan_hours > 0) nem impede valores negativos no frontend antes de submeter requisição à API',
                            'ux',
                            'medium',
                            {
                                file: 'frontend/js/app.js:2781-2804',
                                explanation: 'Enquanto o modal de filamento foi protegido contra valores zerados ou negativos na Issue #86, handleSavePrinter em app.js valida apenas se o campo nome foi preenchido. Se o operador digitar 0 ou valor negativo na vida útil (printer-lifespan) ou custos, a requisição é disparada diretamente à API, que retorna erro HTTP 422 (Input should be greater than 0) exibido como toast genérico em vez de foco no campo com mensagem amigável.'
                            }
                        );
                    }
                } catch (e) {
                    report('Printer Modal Numeric Validation Test', false, { error: e.message });
                }

                // 6. Audit: handleSavePreferences missing numeric bounds validation for tax and negative values
                try {
                    const savePrefStr = handleSavePreferences.toString();
                    const hasTaxBoundsCheck = (
                        savePrefStr.includes('tax > 99') ||
                        savePrefStr.includes('tax_rate > 99') ||
                        savePrefStr.includes('default_tax_rate > 99') ||
                        savePrefStr.includes('Math.min(99')
                    );

                    report('Preferences Client-Side Tax Rate Bounds Validation', hasTaxBoundsCheck, {
                        hasTaxBoundsCheck
                    });

                    if (!hasTaxBoundsCheck) {
                        addIssue(
                            'UX-PREFERENCES-MISSING-TAX-BOUNDS-VALIDATION',
                            '[UX/BUG] Formulário de Preferências da Oficina não valida limites nos campos percentuais (alíquota de impostos até 99% e valores não-negativos) antes de submeter requisição à API',
                            'ux',
                            'low',
                            {
                                file: 'frontend/js/app.js:3340-3356',
                                explanation: 'Em handleSavePreferences, os valores de default_tax_rate, default_profit_margin e default_failure_rate são convertidos com parseLocaleFloat sem validação de limites ou Math.max(0, Math.min(99, ...)). Como o schema UserPreferencesUpdate no backend exige Field(None, ge=0, le=99.0), valores acima de 99% ou negativos disparam erro HTTP 422 na API.'
                            }
                        );
                    }
                } catch (e) {
                    report('Preferences Tax Rate Bounds Test', false, { error: e.message });
                }

                return results;
            })()
            """

            eval_res = await eval_js(audit_script)
            print("=== AUDIT V11 RESULTS ===")
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
            out_file = Path("data/audit_v11_findings.json")
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
