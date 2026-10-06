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
CDP_PORT = 9259
APP_PORT = 8049
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
    db_path = Path("data/test_audit_v10.db")
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass
    env["DATABASE_URL"] = "sqlite:///data/test_audit_v10.db"
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
                    const email = `audit10_${Date.now()}@test.com`;
                    await API.auth.register(email, 'Pass123456!', 'Auditor V10', 'Audit Lab 10');
                    state.user = await API.auth.getMe();
                    document.getElementById('auth-modal')?.classList.add('hidden');
                    await loadAllData();
                    report('Auth Registration', true, { email });
                } catch (e) {
                    report('Auth Registration', false, { error: e.message });
                    addIssue('AUTH-ERR', 'Falha ao autenticar', 'auth', 'critical', e.message);
                }

                // 2. Audit: Divergência de fallback entre recalcLiveSummary e saveCurrentProject com inputs vazios
                try {
                    openNewProject();
                    // Limpar inputs de CAD rate, Post rate e Margem para simular usuário apagando os campos
                    document.getElementById('proj-cad-rate').value = '';
                    document.getElementById('proj-post-rate').value = '';
                    document.getElementById('proj-margin').value = '';
                    document.getElementById('proj-cad-hours').value = '2';
                    document.getElementById('proj-post-hours').value = '1';

                    recalcLiveSummary();
                    const liveLaborCostText = document.getElementById('live-labor-cost')?.textContent || '';
                    const liveBaseCostText = document.getElementById('live-base-cost')?.textContent || '';

                    // In recalcLiveSummary: cadRate falls back to 50, postRate falls back to 30.
                    // Expected live labor cost: 2*50 + 1*30 = 130.
                    // In saveCurrentProject: lines 2228, 2230, 2232 use fallback 0:
                    // cad_hourly_rate: parseLocaleFloat(..., 0), post_process_hourly_rate: parseLocaleFloat(..., 0), margin: parseLocaleFloat(..., 0)
                    
                    const saveStr = saveCurrentProject.toString();
                    const hasSaveFallbackDivergence = (
                        saveStr.includes("parseLocaleFloat(document.getElementById('proj-cad-rate').value, 0)") ||
                        saveStr.includes("parseLocaleFloat(document.getElementById('proj-post-rate').value, 0)") ||
                        saveStr.includes("parseLocaleFloat(document.getElementById('proj-margin').value, 0)")
                    );

                    report('Commercial Rate Fallback Consistency', !hasSaveFallbackDivergence, {
                        liveLaborCostText,
                        hasSaveFallbackDivergence
                    });

                    if (hasSaveFallbackDivergence) {
                        addIssue(
                            'BUG-FINANCIAL-RATE-FALLBACK-DIVERGENCE',
                            '[BUG/CÁLCULO] Divergência de fallback entre o resumo em tempo real e o salvamento quando campos de Taxa CAD, Pós-processamento e Margem são esvaziados',
                            'frontend',
                            'high',
                            {
                                file: 'frontend/js/app.js:2099-2113 vs 2228-2232',
                                explanation: 'Enquanto recalcLiveSummary aplica fallbacks de 50 para cad-rate, 30 para post-rate e 30 para margin, saveCurrentProject passa fallback 0 para parseLocaleFloat nestes mesmos campos. Se o usuário apagar o conteúdo dos inputs, a tela exibe valores calculados (ex: R$ 130 de mão de obra), mas o projeto é salvo com taxa 0 no backend, gerando discrepância financeira.'
                            }
                        );
                    }
                } catch (e) {
                    report('Commercial Rate Fallback Test', false, { error: e.message });
                }

                // 3. Audit: Ausência de pré-visualização em tempo real da tarifa horária calculada no modal de impressora
                try {
                    openPrinterModal();
                    const modalPrinterEl = document.getElementById('modal-printer');
                    const hasLiveHourlyRatePreview = Boolean(
                        modalPrinterEl && (
                            modalPrinterEl.querySelector('#printer-rate-preview') ||
                            modalPrinterEl.querySelector('.printer-rate-preview') ||
                            modalPrinterEl.innerText.includes('Tarifa Calculada')
                        )
                    );
                    closePrinterModal();

                    report('Printer Modal Real-Time Rate Preview', hasLiveHourlyRatePreview, {
                        hasLiveHourlyRatePreview
                    });

                    if (!hasLiveHourlyRatePreview) {
                        addIssue(
                            'UX-PRINTER-MODAL-NO-RATE-PREVIEW',
                            '[UX/FEAT] Modal de impressora não exibe pré-visualização em tempo real da tarifa horária resultante (R$/h) durante a edição dos parâmetros',
                            'ux',
                            'medium',
                            {
                                file: 'frontend/index.html:1327-1388 e frontend/js/app.js:2691-2760',
                                explanation: 'Ao preencher custo de aquisição, vida útil, potência média, taxa de energia e manutenção, o usuário não recebe nenhuma indicação visual de quanto será a tarifa por hora resultante (T_máquina = D_hora + Manutenção + E_hora). O cálculo só é descoberto após salvar e visualizar o card no catálogo.'
                            }
                        );
                    }
                } catch (e) {
                    report('Printer Modal Rate Preview Test', false, { error: e.message });
                }

                // 4. Audit: Dropdowns de impressora e filamento nas placas utilizam toFixed(2) com ponto decimal em vez de formatCurrency
                try {
                    // Create printer and filament first
                    const pr = await API.printers.create({
                        name: 'Bambu Lab X1-Carbon Test',
                        model: 'CoreXY',
                        acquisition_cost: 9500,
                        lifespan_hours: 6000,
                        avg_power_watts: 200,
                        maintenance_cost_per_hour: 1.5,
                        energy_rate_kwh: 0.90
                    });
                    const fl = await API.filaments.create({
                        name: 'PLA Carbono Preto - Teste',
                        brand: '3D Lab',
                        material: 'PLA',
                        color: 'Preto Carbono',
                        color_hex: '#111827',
                        spool_weight_g: 1000,
                        spool_price: 180,
                        density_g_cm3: 1.25
                    });
                    await loadAllData();
                    openNewProject();

                    const plateSelectPr = document.querySelector('#plates-container select');
                    const platePrOptionsHtml = plateSelectPr ? plateSelectPr.innerHTML : '';
                    const hasPrDotNotation = /R\$\s*\d+\.\d{2}\/h/.test(platePrOptionsHtml);

                    const plateSelectFl = document.querySelectorAll('#plates-container select')[1];
                    const plateFlOptionsHtml = plateSelectFl ? plateSelectFl.innerHTML : '';
                    const hasFlDotNotation = /R\$\s*\d+\.\d{2}\/g/.test(plateFlOptionsHtml);

                    report('Plate Select Rates Brazilian Currency Formatting', (!hasPrDotNotation && !hasFlDotNotation), {
                        hasPrDotNotation,
                        hasFlDotNotation,
                        printerOptionSample: platePrOptionsHtml.slice(0, 120),
                        filamentOptionSample: plateFlOptionsHtml.slice(0, 120)
                    });

                    if (hasPrDotNotation || hasFlDotNotation) {
                        addIssue(
                            'UX-PLATE-SELECT-RATES-DOT-NOTATION',
                            '[UX/BUG] Seletores de impressora e filamento no card da placa formatam tarifas com ponto decimal americano (ex: R$ 2.50/h e R$ 0.18/g) em vez de formatCurrency (R$ 2,50/h e R$ 0,18/g)',
                            'ux',
                            'low',
                            {
                                file: 'frontend/js/app.js:1730 e 1763',
                                explanation: 'Nas linhas 1730 e 1763 de app.js, as opções do select concatenam R$ ${p.machine_hourly_rate.toFixed(2)}/h e R$ ${(Number(f.cost_per_gram) || 0).toFixed(2)}/g com ponto decimal hardcoded em vez de aplicar formatCurrency ou toLocaleString("pt-BR"), divergindo do padrão monetário nacional adotado no restante da aplicação.'
                            }
                        );
                    }
                } catch (e) {
                    report('Plate Select Rates Currency Test', false, { error: e.message });
                }

                // 5. Audit: Ausência de campo de notas / especificações na linha de insumos BOM
                try {
                    openNewProject();
                    addNewBomRow();
                    const bomContainer = document.getElementById('bom-container');
                    const bomInputs = bomContainer ? Array.from(bomContainer.querySelectorAll('input, select, textarea')) : [];
                    const hasNotesInput = bomInputs.some(inp => 
                        inp.placeholder?.toLowerCase().includes('obs') || 
                        inp.placeholder?.toLowerCase().includes('nota') ||
                        inp.getAttribute('oninput')?.includes('notes') ||
                        inp.name === 'notes'
                    );

                    report('BOM Item Row Notes Field Availability', hasNotesInput, {
                        hasNotesInput,
                        inputCount: bomInputs.length
                    });

                    if (!hasNotesInput) {
                        addIssue(
                            'FEAT-BOM-ROW-MISSING-NOTES-INPUT',
                            '[UX/FEAT] Ausência de campo de especificações/observações (notes) na linha de insumos (BOM) da calculadora de orçamentos',
                            'ux',
                            'medium',
                            {
                                file: 'frontend/js/app.js:1963-2013 e frontend/index.html',
                                explanation: 'Embora a entidade BOMItem no banco de dados e no schema Pydantic possua a coluna "notes" para guardar link de fornecedor, rosca, código do componente ou observações técnicas, a tabela renderizada em renderBOM() não disponibiliza nenhum input ou campo para o operador visualizar ou editar essas anotações.'
                            }
                        );
                    }
                } catch (e) {
                    report('BOM Notes Field Test', false, { error: e.message });
                }

                // 6. Audit: Botão de Logout encerra a sessão imediatamente sem confirmação prévia
                try {
                    const logoutBtn = document.querySelector('.sidebar-logout-btn');
                    const logoutOnClick = logoutBtn?.getAttribute('onclick') || '';
                    const hasConfirmation = logoutOnClick.includes('confirm') || logoutOnClick.includes('handleLogout');

                    report('Logout Action Confirmation Guard', hasConfirmation, {
                        hasConfirmation,
                        logoutOnClick
                    });

                    if (!hasConfirmation) {
                        addIssue(
                            'UX-LOGOUT-MISSING-CONFIRMATION',
                            '[UX/BUG] Ação de logout na barra lateral encerra a sessão imediatamente sem confirmação do usuário causando risco de perda de dados',
                            'ux',
                            'medium',
                            {
                                file: 'frontend/index.html:233 e frontend/js/api.js:114-117',
                                explanation: 'O botão de logout dispara diretamente API.auth.logout(), limpando o token JWT e o estado em memória sem exibir caixa de confirmação. Se o operador clicar no ícone por engano enquanto edita um orçamento longo, todos os dados não salvos são perdidos.'
                            }
                        );
                    }
                } catch (e) {
                    report('Logout Confirmation Guard Test', false, { error: e.message });
                }

                // 7. Audit: Modal de Filamento não valida densidade ou peso positivo no cliente antes do envio
                try {
                    openFilamentModal();
                    const handleSaveFilamentStr = handleSaveFilament.toString();
                    const hasClientNumericValidation = (
                        (handleSaveFilamentStr.includes('spool_weight_g <= 0') || handleSaveFilamentStr.includes('weight <= 0')) &&
                        (handleSaveFilamentStr.includes('density_g_cm3 <= 0') || handleSaveFilamentStr.includes('density <= 0'))
                    );
                    closeFilamentModal();

                    report('Filament Modal Client-Side Numeric Validation', hasClientNumericValidation, {
                        hasClientNumericValidation
                    });

                    if (!hasClientNumericValidation) {
                        addIssue(
                            'UX-FILAMENT-MODAL-MISSING-NUMERIC-VALIDATION',
                            '[UX/BUG] Formulário de filamento não valida valores estritamente positivos para peso do carretel e densidade no frontend antes de submeter requisição à API',
                            'ux',
                            'low',
                            {
                                file: 'frontend/js/app.js:3036-3065',
                                explanation: 'handleSaveFilament valida apenas se brand e color foram preenchidos. Se o operador acidentalmente digitar 0 ou valor negativo para o peso do carretel ou densidade, a requisição é enviada à API resultando em erro HTTP 422 em vez de validação amigável e foco no campo incorreto.'
                            }
                        );
                    }
                } catch (e) {
                    report('Filament Modal Numeric Validation Test', false, { error: e.message });
                }

                // 8. Audit: Parser de G-code arredonda tempo para 2 casas decimais prematuramente truncando impressões curtas
                try {
                    const sampleGcode = `;FLAVOR:Marlin\\n;TIME:15\\n;Filament used: 1.2g\\n;MATERIAL:PLA\\nG28\\n`;
                    const parsed = parseGcodeMetadata(sampleGcode, 'teste.gcode');
                    const hasTimeHoursTruncated = parsed.print_time_hours === 0 && parsed.part_weight_g > 0;

                    report('GCode Parser Short Print Time Precision', !hasTimeHoursTruncated, {
                        print_time_hours: parsed.print_time_hours,
                        part_weight_g: parsed.part_weight_g
                    });

                    if (hasTimeHoursTruncated) {
                        addIssue(
                            'BUG-PARSER-GCODE-PREMATURE-ROUNDING',
                            '[BUG/PARSER] Leitor de G-Code zera o tempo de impressão (print_time_hours = 0) para peças de calibração ou testes rápidos devido a arredondamento prematuro toFixed(2)',
                            'frontend',
                            'medium',
                            {
                                file: 'frontend/js/parsers/gcode.js:270',
                                explanation: 'Em gcode.js linha 270, print_time_hours é retornado como parseFloat(printTimeHours.toFixed(2)). Para impressões rápidas com menos de 18 segundos (comuns em testes de fluxo, calibração de retração ou scripts de purge), printTimeHours (15s / 3600 = 0.0041h) é arredondado para 0.00h, fazendo a placa ser importada com tempo zerado.'
                            }
                        );
                    }
                } catch (e) {
                    report('GCode Parser Precision Test', false, { error: e.message });
                }

                return results;
            })()
            """

            eval_res = await eval_js(audit_script)
            print("=== AUDIT V10 RESULTS ===")
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
            out_file = Path("data/audit_v10_findings.json")
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
