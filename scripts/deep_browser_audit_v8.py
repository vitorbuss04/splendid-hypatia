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
CDP_PORT = 9248
APP_PORT = 8038
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
    db_path = Path("data/test_audit_v8.db")
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass
    env["DATABASE_URL"] = "sqlite:///data/test_audit_v8.db"
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
                    const email = `audit8_${Date.now()}@test.com`;
                    await API.auth.register(email, 'Pass123456!', 'Auditor V8', 'Audit Lab 8');
                    state.user = await API.auth.getMe();
                    document.getElementById('auth-modal')?.classList.add('hidden');
                    await loadAllData();
                    report('Auth Registration', true, { email });
                } catch (e) {
                    report('Auth Registration', false, { error: e.message });
                    addIssue('AUTH-ERR', 'Falha ao autenticar', 'auth', 'critical', e.message);
                }

                // 2. Test 3MF Parser: Purge/Flush Weight Discarded
                try {
                    // Create a synthetic 3MF zip with JSZip in memory
                    const zip = new JSZip();
                    const sliceInfoXml = `<?xml version="1.0" encoding="UTF-8"?>
                    <config>
                        <plate>
                            <metadata key="index" value="1"/>
                            <metadata key="name" value="Multi-Color Test"/>
                            <metadata key="prediction" value="7200"/>
                            <metadata key="weight" value="50.0"/>
                            <metadata key="flush_weight" value="35.5"/>
                            <filament id="1" used_g="50.0" flush_g="35.5" type="PLA" color="#FF0000" profile="Bambu PLA Basic @BBL X1C"/>
                        </plate>
                    </config>`;
                    zip.file("Metadata/slice_info.xml", sliceInfoXml);
                    const blob = await zip.generateAsync({ type: "blob" });
                    const file = new File([blob], "multicolor_test.3mf", { type: "application/zip" });

                    const parsedPlates = await parse3mfMetadata(file);
                    const plateResult = parsedPlates[0];

                    const purgeCaptured = plateResult.purge_weight_g > 0;
                    report('3MF Slicer Purge Weight Retention', purgeCaptured, {
                        expectedPurge: 35.5,
                        actualPurge: plateResult.purge_weight_g,
                        partWeight: plateResult.part_weight_g
                    });

                    if (!purgeCaptured) {
                        addIssue(
                            'SLICER-3MF-PURGE-WEIGHT-DISCARDED',
                            '[BUG/SLICER] Importação de arquivos 3MF descarta o peso de purga/flush (purge_weight_g = 0) na leitura de metadados do fatiador',
                            'slicer',
                            'high',
                            {
                                file: 'frontend/js/parsers/threemf.js:235',
                                expected: 35.5,
                                actual: plateResult.purge_weight_g,
                                explanation: 'O extrator parse3mfMetadata acumula flush_weight e flush_g na variável purgeGrams, porém na construção da placa (linha 235) fixa purge_weight_g: 0.0, descartando o desperdício de troca de cores do Bambu Studio / OrcaSlicer'
                            }
                        );
                    }
                } catch (e) {
                    report('3MF Purge Weight Retention Test', false, { error: e.message });
                }

                // 3. Test Blank / Whitespace Printer Name Validation
                try {
                    const blankPrinterResp = await fetch('/api/printers', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${API.getToken()}`
                        },
                        body: JSON.stringify({
                            name: '    ',
                            model: 'Ender 3 V3',
                            acquisition_cost: 2500,
                            lifespan_hours: 5000,
                            avg_power_watts: 150,
                            maintenance_cost_per_hour: 1.0,
                            energy_rate_kwh: 0.85
                        })
                    });

                    const printerRejected = blankPrinterResp.status === 422;
                    report('Printer Blank Name Validation', printerRejected, {
                        status: blankPrinterResp.status
                    });

                    if (!printerRejected) {
                        addIssue(
                            'VAL-PRINTER-BLANK-NAME',
                            '[BUG/VALIDATION] API e formulário aceitam cadastro e atualização de impressoras com nome vazio ou apenas espaços em branco',
                            'validation',
                            'medium',
                            {
                                status: blankPrinterResp.status,
                                file: 'backend/schemas.py:58-82 & frontend/js/app.js:2704',
                                explanation: 'PrinterBase e PrinterUpdate em backend/schemas.py não possuem restrição min_length=1 nem validator validate_name_not_blank, e handleSavePrinter não valida preenchimento antes de enviar'
                            }
                        );
                    }
                } catch (e) {
                    report('Printer Blank Name Test', false, { error: e.message });
                }

                // 4. Test Blank / Whitespace Filament Name Validation
                try {
                    const blankFilamentResp = await fetch('/api/filaments', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${API.getToken()}`
                        },
                        body: JSON.stringify({
                            name: '   ',
                            material: 'PLA',
                            brand: 'Marca X',
                            color: 'Preto',
                            color_hex: '#000000',
                            spool_weight_g: 1000,
                            spool_price: 90
                        })
                    });

                    const filamentRejected = blankFilamentResp.status === 422;
                    report('Filament Blank Name Validation', filamentRejected, {
                        status: blankFilamentResp.status
                    });

                    if (!filamentRejected) {
                        addIssue(
                            'VAL-FILAMENT-BLANK-NAME',
                            '[BUG/VALIDATION] API aceita cadastro e atualização de filamentos com nome vazio ou contendo apenas espaços em branco',
                            'validation',
                            'medium',
                            {
                                status: blankFilamentResp.status,
                                file: 'backend/schemas.py:95-121',
                                explanation: 'FilamentBase e FilamentUpdate em backend/schemas.py não possuem validação para impedir nomes vazios ou compostos exclusivamente por espaços em branco'
                            }
                        );
                    }
                } catch (e) {
                    report('Filament Blank Name Test', false, { error: e.message });
                }

                // 5. Test Default Rate Discrepancy when Plate has No Hardware Assigned
                try {
                    // Create project with plate having no printer and no filament and null custom rates
                    const unassignedPlateResp = await fetch('/api/projects', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${API.getToken()}`
                        },
                        body: JSON.stringify({
                            name: 'Projeto Placa Sem Hardware',
                            status: 'draft',
                            plates: [{
                                name: 'Placa 1',
                                printer_id: null,
                                filament_id: null,
                                custom_printer_hourly_rate: null,
                                custom_filament_cost_per_g: null,
                                print_time_hours: 10,
                                part_weight_g: 100,
                                purge_weight_g: 0,
                                quantity: 1
                            }]
                        })
                    });

                    const unassignedData = await unassignedPlateResp.json();
                    const backendMatCost = unassignedData.summary?.total_material_cost || 0;
                    const backendMachCost = unassignedData.summary?.total_machine_cost || 0;

                    // In frontend recalcLiveSummary:
                    // Fallback rates are 0.10/g (100g = R$ 10.00) and 2.50/h (10h = R$ 25.00)
                    // If backend sets 0.0, there is a divergence
                    const backendHasFallbacks = (backendMatCost > 0) && (backendMachCost > 0);
                    report('Unassigned Plate Engine Default Rates Consistency', backendHasFallbacks, {
                        backendMatCost,
                        backendMachCost,
                        frontendExpectedMatCost: 10.0,
                        frontendExpectedMachCost: 25.0
                    });

                    if (!backendHasFallbacks) {
                        addIssue(
                            'CALC-UNASSIGNED-PLATE-ZERO-COST',
                            '[BUG/CÁLCULO] Divergência de custos entre Frontend e Engine quando placa não possui impressora ou filamento associado (Backend zera os custos da placa)',
                            'calculation',
                            'high',
                            {
                                backendMatCost,
                                backendMachCost,
                                expectedMatCost: 10.0,
                                expectedMachCost: 25.0,
                                file: 'backend/engine.py:59-74 & 88-105 vs frontend/js/app.js:2029-2041',
                                explanation: 'Enquanto a calculadora do frontend adota fallbacks de R$ 0,10/g e R$ 2,50/h quando printer_id e filament_id são nulos, o backend engine.py zera os custos de filamento e máquina (R$ 0,00), distorcendo o custo base e a proposta final salva'
                            }
                        );
                    }
                } catch (e) {
                    report('Unassigned Plate Default Rates Test', false, { error: e.message });
                }

                // 6. Test Delivery Days Clearing Resetting to 3 Days
                try {
                    openNewProject();
                    const daysInput = document.getElementById('proj-delivery-days');
                    daysInput.value = '';
                    daysInput.dispatchEvent(new Event('input', { bubbles: true }));

                    // Trigger saveCurrentProject without navigating
                    document.getElementById('proj-name').value = 'Projeto Teste Prazo Vazio';
                    await saveCurrentProject(false);

                    const savedProject = state.currentProject;
                    const deliveryDaysVal = savedProject ? savedProject.delivery_days : null;

                    // Expected behavior: if user cleared input, it should save as null or 0, allowing dynamic estimation by print hours in pdf_service.py
                    const allowsNullOrDynamic = deliveryDaysVal === null;
                    report('Delivery Days Null/Dynamic Retention', allowsNullOrDynamic, {
                        savedDeliveryDays: deliveryDaysVal
                    });

                    if (!allowsNullOrDynamic && deliveryDaysVal === 3) {
                        addIssue(
                            'UX-DELIVERY-DAYS-HARDCODED-FALLBACK',
                            '[UX/BUG] Limpeza do campo Prazo de Entrega (proj-delivery-days) força valor fixo de 3 dias no salvamento impedindo cálculo dinâmico por horas de impressão',
                            'ux',
                            'low',
                            {
                                savedDeliveryDays: deliveryDaysVal,
                                file: 'frontend/js/app.js:2219',
                                explanation: 'saveCurrentProject utiliza parseInt(d, 10) || d < 0 ? 3 : d, sobrescrevendo a intenção do usuário de deixar o prazo em branco para cálculo automático proporcional ao tempo de impressão (suportado em pdf_service.py)'
                            }
                        );
                    }
                } catch (e) {
                    report('Delivery Days Retention Test', false, { error: e.message });
                }

                // 7. Test Filament Active Toggle presence in UI
                try {
                    openFilamentModal();
                    const hasActiveToggle = Boolean(document.getElementById('filament-is-active') || document.querySelector('#modal-filament input[name="is_active"]'));
                    closeFilamentModal();

                    report('Filament Active Status Toggle in Modal', hasActiveToggle, {
                        hasActiveToggle
                    });

                    if (!hasActiveToggle) {
                        addIssue(
                            'UX-FILAMENT-ACTIVE-STATUS-MISSING',
                            '[UX/FEAT] Ausência de controle de status ativo/inativo (is_active) no cadastro e edição de filamentos',
                            'ux',
                            'medium',
                            {
                                hasActiveToggle,
                                file: 'frontend/js/app.js:2914-3022 & frontend/index.html',
                                explanation: 'O modelo Filament no banco de dados possui a coluna is_active, mas a interface e o modal de filamentos não fornecem controle para inativar carretéis esgotados ou descontinuados'
                            }
                        );
                    }
                } catch (e) {
                    report('Filament Active Status Test', false, { error: e.message });
                }

                return results;
            })()
            """

            eval_res = await eval_js(audit_script)
            print("=== AUDIT V8 RESULTS ===")
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
