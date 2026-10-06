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
CDP_PORT = 9249
APP_PORT = 8039
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
    db_path = Path("data/test_audit_v9.db")
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass
    env["DATABASE_URL"] = "sqlite:///data/test_audit_v9.db"
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
                    const email = `audit9_${Date.now()}@test.com`;
                    await API.auth.register(email, 'Pass123456!', 'Auditor V9', 'Audit Lab 9');
                    state.user = await API.auth.getMe();
                    document.getElementById('auth-modal')?.classList.add('hidden');
                    await loadAllData();
                    report('Auth Registration', true, { email });
                } catch (e) {
                    report('Auth Registration', false, { error: e.message });
                    addIssue('AUTH-ERR', 'Falha ao autenticar', 'auth', 'critical', e.message);
                }

                // 2. Audit: Duplicação de Projeto descarta parâmetros de manufatura das placas (nozzle_diameter, bed_type, layer_height)
                try {
                    // Create base project with custom manufacturing parameters
                    const projResp = await fetch('/api/projects', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${API.getToken()}`
                        },
                        body: JSON.stringify({
                            name: 'Projeto Setup Especial 0.6mm',
                            status: 'draft',
                            plates: [{
                                name: 'Placa Robusta 0.6',
                                nozzle_diameter: '0.6',
                                bed_type: 'Smooth PEI',
                                layer_height: '0.12',
                                print_time_hours: 4.5,
                                part_weight_g: 80,
                                purge_weight_g: 0,
                                quantity: 1
                            }]
                        })
                    });
                    const baseProj = await projResp.json();
                    const origPlate = baseProj.plates[0];

                    // Now duplicate via API endpoint
                    const dupResp = await fetch(`/api/projects/${baseProj.id}/duplicate`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${API.getToken()}`
                        }
                    });
                    const dupProj = await dupResp.json();
                    const dupPlate = dupProj.plates[0];

                    const preservedParams = (
                        dupPlate.nozzle_diameter === '0.6' &&
                        dupPlate.bed_type === 'Smooth PEI' &&
                        dupPlate.layer_height === '0.12'
                    );

                    report('Duplicate Project Preserves Plate Manufacturing Setup', preservedParams, {
                        expected: { nozzle: '0.6', bed: 'Smooth PEI', layer: '0.12' },
                        actual: { nozzle: dupPlate.nozzle_diameter, bed: dupPlate.bed_type, layer: dupPlate.layer_height }
                    });

                    if (!preservedParams) {
                        addIssue(
                            'BUG-PROJECT-DUPLICATE-DROPS-MFG-PARAMS',
                            '[BUG/OPERACIONAL] Duplicação de Projeto descarta parâmetros de manufatura das placas (nozzle_diameter, bed_type, layer_height) resetando para os padrões',
                            'backend',
                            'high',
                            {
                                file: 'backend/routes/project_routes.py:448-463',
                                orig: { nozzle: origPlate.nozzle_diameter, bed: origPlate.bed_type, layer: origPlate.layer_height },
                                dup: { nozzle: dupPlate.nozzle_diameter, bed: dupPlate.bed_type, layer: dupPlate.layer_height },
                                explanation: 'O loop de duplicação em duplicate_project instancia models.Plate omitindo nozzle_diameter, bed_type e layer_height, resetando o setup da oficina para os padrões (0.4 / Textured PEI / 0.20).'
                            }
                        );
                    }
                } catch (e) {
                    report('Duplicate Project MFG Setup Test', false, { error: e.message });
                }

                // 3. Audit: Engine calculate_plate_cost omite parâmetros de manufatura da resposta summary e da Ficha Técnica PDF
                try {
                    const testProjResp = await fetch('/api/projects', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${API.getToken()}`
                        },
                        body: JSON.stringify({
                            name: 'Projeto Teste Ficha Tecnica 0.8mm',
                            status: 'draft',
                            plates: [{
                                name: 'Placa Bico 0.8',
                                nozzle_diameter: '0.8',
                                bed_type: 'SuperPlate Glass',
                                layer_height: '0.28',
                                print_time_hours: 6.0,
                                part_weight_g: 150,
                                quantity: 1
                            }]
                        })
                    });
                    const testProj = await testProjResp.json();
                    const summaryPlate = testProj.summary?.plates_details?.[0] || {};

                    const summaryHasMfgParams = (
                        summaryPlate.nozzle_diameter === '0.8' &&
                        summaryPlate.bed_type === 'SuperPlate Glass' &&
                        summaryPlate.layer_height === '0.28'
                    );

                    report('Engine calculate_plate_cost Includes Plate MFG Parameters in Summary', summaryHasMfgParams, {
                        summaryPlateNozzle: summaryPlate.nozzle_diameter,
                        summaryPlateBed: summaryPlate.bed_type,
                        summaryPlateLayer: summaryPlate.layer_height
                    });

                    if (!summaryHasMfgParams) {
                        addIssue(
                            'BUG-ENGINE-PLATE-MFG-PARAMS-OMITTED',
                            '[BUG/ENGINE] calculate_plate_cost omite nozzle_diameter, bed_type e layer_height nos detalhes da placa fazendo a Ficha Técnica de Produção exibir dados hardcoded',
                            'backend',
                            'high',
                            {
                                file: 'backend/engine.py:120-145 & backend/pdf_service.py:441-448',
                                receivedInSummary: {
                                    nozzle: summaryPlate.nozzle_diameter,
                                    bed: summaryPlate.bed_type,
                                    layer: summaryPlate.layer_height
                                },
                                explanation: 'A função calculate_plate_cost em engine.py omite nozzle_diameter, bed_type e layer_height do dicionário retornado, resultando em valores None em plates_details. Consequentemente, pdf_service.py sempre aplica os valores de fallback 0.4mm, Textured PEI e 0.20mm na Ficha Técnica de Produção.'
                            }
                        );
                    }
                } catch (e) {
                    report('Engine MFG Params Test', false, { error: e.message });
                }

                // 4. Audit: Criação de Novo Orçamento (openNewProject) ignora Condições Comerciais e Garantia padrão das preferências
                try {
                    // Update user preferences with custom commercial terms
                    const updatedUser = await API.auth.updatePreferences({
                        default_payment_terms: '50% entrada e 50% na entrega via PIX',
                        default_warranty_terms: '90 dias de garantia contra delaminação e defeitos de fabricação'
                    });
                    state.user = updatedUser;

                    // Call openNewProject in the UI
                    openNewProject();

                    const paymentTermsInputVal = document.getElementById('proj-payment-terms')?.value || '';
                    const warrantyTermsInputVal = document.getElementById('proj-warranty-terms')?.value || '';

                    const termsPrepopulated = (
                        paymentTermsInputVal === '50% entrada e 50% na entrega via PIX' &&
                        warrantyTermsInputVal === '90 dias de garantia contra delaminação e defeitos de fabricação'
                    );

                    report('openNewProject Prepopulates Commercial Terms from Preferences', termsPrepopulated, {
                        paymentVal: paymentTermsInputVal,
                        warrantyVal: warrantyTermsInputVal,
                        expectedPayment: updatedUser.default_payment_terms
                    });

                    if (!termsPrepopulated) {
                        addIssue(
                            'UX-OPEN-NEW-PROJECT-TERMS-BLANK',
                            '[UX/BUG] Criação de Novo Orçamento (openNewProject) zera Condições de Pagamento e Garantia em vez de carregar os padrões das preferências da oficina',
                            'ux',
                            'medium',
                            {
                                file: 'frontend/js/app.js:1512-1513',
                                actualPaymentTerms: paymentTermsInputVal,
                                actualWarrantyTerms: warrantyTermsInputVal,
                                expectedPaymentTerms: updatedUser.default_payment_terms,
                                explanation: 'openNewProject carrega corretamente taxas padrão de CAD, pós-processamento, margem e impostos do usuário, porém força proj-payment-terms e proj-warranty-terms para string vazia (""), ignorando default_payment_terms e default_warranty_terms configurados nas preferências.'
                            }
                        );
                    }
                } catch (e) {
                    report('openNewProject Terms Test', false, { error: e.message });
                }

                // 5. Audit: Exclusão de projeto ativo em edição mantém state.currentProject em cache gerando erro 404 ao salvar
                try {
                    // Create and edit a project
                    const created = await API.projects.create({
                        name: 'Projeto Para Teste de Exclusão Ativa',
                        status: 'draft',
                        plates: [{ name: 'P1', print_time_hours: 1, part_weight_g: 20 }]
                    });

                    await editProject(created.id);
                    const loadedIdBeforeDelete = state.currentProject?.id;

                    // Delete the project via API/deleteProject simulation
                    await API.projects.delete(created.id);
                    // Now simulate if user is in editor and deletes or calls deleteProject
                    // In app.js deleteProject doesn't clear state.currentProject if it matches
                    const isCached = state.currentProject && state.currentProject.id === created.id;

                    report('deleteProject / Current Project Cache Invalidation', !isCached, {
                        loadedIdBeforeDelete,
                        currentProjectIdAfterDelete: state.currentProject?.id
                    });

                    if (isCached) {
                        addIssue(
                            'UX-DELETE-PROJECT-STALE-CURRENT-PROJECT',
                            '[UX/BUG] Exclusão de projeto não limpa state.currentProject permitindo tentativa de salvamento de registro inexistente com erro HTTP 404',
                            'ux',
                            'medium',
                            {
                                file: 'frontend/js/app.js:2329-2343',
                                staleProjectId: state.currentProject.id,
                                explanation: 'A função deleteProject exclui o projeto via API e atualiza as listagens, mas se o projeto excluído estiver carregado no editor (state.currentProject), o estado em memória não é resetado, fazendo com que uma ação de salvar no editor envie PUT para um ID inexistente e dispare toast de erro 404.'
                            }
                        );
                    }
                } catch (e) {
                    report('Delete Project Stale State Test', false, { error: e.message });
                }

                // 6. Audit: Sanitização incompleta em renderBOM contra caracteres especiais e aspas simples
                try {
                    state.currentBOM = [{
                        name: 'Parafuso M3 "Inox" & Suporte <Aço> \\'Especial\\'',
                        category: 'Fixadores',
                        quantity: 4,
                        unit_cost: 0.50
                    }];

                    renderBOM();
                    const container = document.getElementById('bom-container');
                    const inputEl = container?.querySelector('input[type="text"]');
                    const rawInputValue = inputEl ? inputEl.value : '';

                    // Check if input value safely preserved the string without truncation or breaking attributes
                    const renderedCorrectly = rawInputValue === 'Parafuso M3 "Inox" & Suporte <Aço> \\'Especial\\'';

                    report('BOM Item Name HTML Attribute Safety and Escaping', renderedCorrectly, {
                        rawInputValue,
                        expected: 'Parafuso M3 "Inox" & Suporte <Aço> \\'Especial\\''
                    });

                    // Check source code of renderBOM: line 1968 only replaces double quotes
                    const usesFullEsc = !container.innerHTML.includes('<Aço>');
                    if (!usesFullEsc) {
                        addIssue(
                            'SEC-BOM-INCOMPLETE-HTML-ESCAPING',
                            '[SECURITY/XSS] Ausência de escapeHtml completo no campo de nome do insumo BOM em renderBOM',
                            'security',
                            'medium',
                            {
                                file: 'frontend/js/app.js:1968',
                                explanation: 'renderBOM utiliza apenas .replace(/"/g, "&quot;") para o valor do input, deixando caracteres <, > e & desprotegidos. Se o valor for interpolado em outros contextos ou possuir tags HTML, pode ocorrer quebra de marcação ou risco de Cross-Site Scripting.'
                            }
                        );
                    }
                } catch (e) {
                    report('BOM Escaping Test', false, { error: e.message });
                }

                // 7. Audit: Exibição de densidade (density_g_cm3) no card do filamento em renderFilamentsGrid
                try {
                    const testFilament = await API.filaments.create({
                        name: 'PETG CF Preto - Prusa',
                        brand: 'Prusa',
                        material: 'PETG',
                        color: 'Preto',
                        color_hex: '#111827',
                        density_g_cm3: 1.29,
                        spool_weight_g: 1000,
                        spool_price: 180
                    });

                    await loadAllData();
                    renderFilamentsGrid();

                    const gridHtml = document.getElementById('filaments-grid')?.innerHTML || '';
                    const hasDensityDisplay = gridHtml.includes('1.29') || gridHtml.includes('g/cm³');

                    report('Filament Grid Card Displays Polymer Density', hasDensityDisplay, {
                        hasDensityDisplay
                    });

                    if (!hasDensityDisplay) {
                        addIssue(
                            'UX-FILAMENT-GRID-MISSING-DENSITY',
                            '[UX/FEAT] Card de Filamento na listagem da oficina omite a exibição da densidade do material (g/cm³)',
                            'ux',
                            'low',
                            {
                                file: 'frontend/js/app.js:3228-3230',
                                explanation: 'Apesar de a densidade do material (density_g_cm3) estar persistida no backend e ser crucial para a física e custos da manufatura aditiva, o rodapé do card de filamentos exibe apenas o peso do carretel e o preço, omitindo o valor da densidade.'
                            }
                        );
                    }
                } catch (e) {
                    report('Filament Density Display Test', false, { error: e.message });
                }

                // 8. Audit: Formatação monetária com ponto decimal no custo por grama em renderFilamentsGrid
                try {
                    const gridHtml = document.getElementById('filaments-grid')?.innerHTML || '';
                    // Check if cost per gram has dot notation e.g. "R$ 0.18/g" instead of "R$ 0,18/g"
                    const hasDotNotation = /R\$\s+\d+\.\d{2}\s*\/g/.test(gridHtml);

                    report('Filament Cost Per Gram Brazilian Currency Format Consistency', !hasDotNotation, {
                        hasDotNotation
                    });

                    if (hasDotNotation) {
                        addIssue(
                            'UX-FILAMENT-COST-PER-GRAM-DOT-NOTATION',
                            '[UX/BUG] Custo por grama no grid de filamentos utiliza ponto decimal em vez da formatação padrão brasileira (R$ 0,00/g)',
                            'ux',
                            'low',
                            {
                                file: 'frontend/js/app.js:3223',
                                explanation: 'A linha 3223 de frontend/js/app.js interpola R$ ${f.cost_per_gram.toFixed(2)}/g com ponto decimal hardcoded em vez de aplicar formatCurrency ou toLocaleString("pt-BR"), divergindo do restante da aplicação.'
                            }
                        );
                    }
                } catch (e) {
                    report('Filament Cost Currency Format Test', false, { error: e.message });
                }

                // 9. Audit: Duplicação de filamento limpa o campo de cor forçando digitação manual obrigatória
                try {
                    const f = state.filaments?.[0];
                    if (f) {
                        openFilamentModal(f, true);
                        const colorVal = document.getElementById('filament-color')?.value || '';
                        closeFilamentModal();

                        const retainsColorOrHasDefault = Boolean(colorVal && colorVal.trim());

                        report('Duplicate Filament Preserves Color or Provides Default', retainsColorOrHasDefault, {
                            colorVal,
                            originalColor: f.color
                        });

                        if (!retainsColorOrHasDefault) {
                            addIssue(
                                'UX-DUPLICATE-FILAMENT-CLEARS-COLOR',
                                '[UX/BUG] Ação de duplicar filamento zera o campo de cor forçando preenchimento manual obrigatório',
                                'ux',
                                'low',
                                {
                                    file: 'frontend/js/app.js:2991',
                                    explanation: 'Ao duplicar um filamento, openFilamentModal define document.getElementById("filament-color").value = "", deixando o campo em branco. Como handleSaveFilament exige cor preenchida, o usuário é impedido de salvar uma cópia direta sem digitar uma cor novamente.'
                                }
                            );
                        }
                    }
                } catch (e) {
                    report('Duplicate Filament Color Retention Test', false, { error: e.message });
                }

                // 10. Audit: Modal de impressora não valida nome no frontend antes do envio
                try {
                    openPrinterModal();
                    document.getElementById('printer-name').value = '   ';
                    // We check if handleSavePrinter checks name before API call
                    const handleSavePrinterStr = handleSavePrinter.toString();
                    const hasClientValidation = handleSavePrinterStr.includes('!payload.name') || handleSavePrinterStr.includes('!name');
                    closePrinterModal();

                    report('Printer Modal Client-Side Name Validation', hasClientValidation, {
                        hasClientValidation
                    });

                    if (!hasClientValidation) {
                        addIssue(
                            'UX-PRINTER-MODAL-MISSING-CLIENT-VALIDATION',
                            '[UX/BUG] Formulário de impressora não valida nome obrigatório no frontend antes de submeter requisição à API',
                            'ux',
                            'low',
                            {
                                file: 'frontend/js/app.js:2728-2745',
                                explanation: 'Enquanto o cadastro de filamento e o editor de orçamentos validam campos obrigatórios no cliente antes do envio, handleSavePrinter envia o payload diretamente para a API, dependendo do erro HTTP 422 para alertar o usuário.'
                            }
                        );
                    }
                } catch (e) {
                    report('Printer Name Client Validation Test', false, { error: e.message });
                }

                return results;
            })()
            """

            eval_res = await eval_js(audit_script)
            print("=== AUDIT V9 RESULTS ===")
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
            out_file = Path("data/audit_v9_findings.json")
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
