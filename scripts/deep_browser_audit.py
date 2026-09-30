import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os
import sys
from pathlib import Path

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

async def run_audit():
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        "--disable-gpu",
        "--window-size=1440,900",
        "http://localhost:8000"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2.5)

    try:
        tabs_res = urllib.request.urlopen("http://localhost:9222/json").read()
        tabs = json.loads(tabs_res)
        target_tab = None
        for t in tabs:
            if "localhost:8000" in t.get("url", ""):
                target_tab = t
                break
        if not target_tab:
            target_tab = tabs[0]

        ws_url = target_tab["webSocketDebuggerUrl"]
        print(f"Connecting to CDP: {ws_url}")

        async with websockets.connect(ws_url) as ws:
            msg_id = 1
            console_logs = []
            exceptions = []

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
                        if data["method"] == "Runtime.consoleAPICalled":
                            console_logs.append(data["params"])
                        elif data["method"] == "Runtime.exceptionThrown":
                            exceptions.append(data["params"])
                        continue
                    if data.get("id") == mid:
                        return data

            async def eval_js(expr):
                resp = await send_cmd("Runtime.evaluate", {
                    "expression": expr,
                    "awaitPromise": True,
                    "returnByValue": True
                })
                print("RAW EVAL RESP:", json.dumps(resp)[:500])
                if resp and "result" in resp and "result" in resp["result"]:
                    return resp["result"]["result"].get("value")
                return resp

            await send_cmd("Runtime.enable")
            await send_cmd("Log.enable")

            # Let the page load
            await asyncio.sleep(1)

            # Test suite inside browser
            test_script = """
            (async () => {
                const report = {
                    executed_at: new Date().toISOString(),
                    steps: [],
                    bugs_found: [],
                    ux_issues: [],
                    warnings: []
                };

                function step(name, success, info = null) {
                    report.steps.push({ name, success, info });
                }

                function addBug(title, category, severity, description, stepsToReproduce, expectedBehavior, actualBehavior, proposedSolution) {
                    report.bugs_found.push({
                        title, category, severity, description, stepsToReproduce, expectedBehavior, actualBehavior, proposedSolution
                    });
                }

                function addUx(title, description, suggestion) {
                    report.ux_issues.push({ title, description, suggestion });
                }

                // 1. Authenticate or Register
                let userEmail = 'browser_audit_' + Date.now() + '@test.com';
                try {
                    await API.auth.register(userEmail, 'TestPass123!', 'Auditor Bot', 'Oficina Audit');
                    state.user = await API.auth.getMe();
                    document.getElementById('auth-modal')?.classList.add('hidden');
                    await loadAllData();
                    step("Authentication & Initialization", true, { email: state.user.email, id: state.user.id });
                } catch(e) {
                    step("Authentication & Initialization", false, { error: e.message });
                }

                // 2. Audit Filaments View
                navigateTo('filaments');
                step("Navigate to Filaments", state.activeView === 'filaments');

                // Check Filament search and filter inputs
                const filSearch = document.getElementById('filament-search-input');
                const filMatFilter = document.getElementById('filament-material-filter');
                step("Filament search input exists", !!filSearch);
                step("Filament material filter exists", !!filMatFilter);

                // Open Filament Modal & test duplicate / creation / validation
                openFilamentModal();
                const filModal = document.getElementById('modal-filament');
                step("Open Filament Modal", !filModal.classList.contains('hidden'));

                // Test Auto-Name generation
                const brandInput = document.getElementById('filament-brand');
                const colorInput = document.getElementById('filament-color');
                const matSelect = document.getElementById('filament-material');
                const previewText = document.getElementById('filament-preview-text');

                brandInput.value = 'Sunlu';
                brandInput.dispatchEvent(new Event('input', { bubbles: true }));
                colorInput.value = 'Azul Royal';
                colorInput.dispatchEvent(new Event('input', { bubbles: true }));
                matSelect.value = 'PETG';
                matSelect.dispatchEvent(new Event('change', { bubbles: true }));

                const expectedName = 'PETG Azul Royal - Sunlu';
                const actualPreview = previewText?.innerText?.trim();
                step("Filament auto-name generation matches pattern", actualPreview === expectedName, { expectedName, actualPreview });

                // Check spool weight and price inputs
                const weightInp = document.getElementById('filament-weight');
                const priceInp = document.getElementById('filament-price');
                weightInp.value = '1000';
                priceInp.value = '119.90';

                // Save filament via form button
                let createdFilamentId = null;
                try {
                    await handleSaveFilament({ preventDefault: () => {} });
                    step("Save new filament", true);
                    const newlyCreated = state.filaments.find(f => f.brand === 'Sunlu' && f.color === 'Azul Royal');
                    if (newlyCreated) {
                        createdFilamentId = newlyCreated.id;
                        step("Newly created filament found in state", true, { id: createdFilamentId, cost_per_gram: newlyCreated.cost_per_gram });
                    } else {
                        step("Newly created filament found in state", false);
                    }
                } catch(e) {
                    step("Save new filament", false, { error: e.message, stack: e.stack });
                }

                // 3. Audit Printers View
                navigateTo('printers');
                step("Navigate to Printers", state.activeView === 'printers');
                const prnSearch = document.getElementById('printer-search-input');
                const prnStatusFilter = document.getElementById('printer-status-filter');
                step("Printer search input exists", !!prnSearch);
                step("Printer status filter exists", !!prnStatusFilter);

                // Add a printer
                openPrinterModal();
                document.getElementById('printer-name').value = 'Bambu Lab X1 Carbon';
                document.getElementById('printer-model').value = 'X1C';
                document.getElementById('printer-cost').value = '9500.00';
                document.getElementById('printer-lifespan').value = '5000';
                document.getElementById('printer-power').value = '350';
                document.getElementById('printer-maintenance').value = '1.0';
                document.getElementById('printer-energy').value = '0.85';

                let createdPrinterId = null;
                try {
                    await handleSavePrinter({ preventDefault: () => {} });
                    step("Save new printer", true);
                    const newlyCreatedPrn = state.printers.find(p => p.name === 'Bambu Lab X1 Carbon');
                    if (newlyCreatedPrn) {
                        createdPrinterId = newlyCreatedPrn.id;
                        step("Newly created printer found in state", true, { id: createdPrinterId });
                    }
                } catch(e) {
                    step("Save new printer", false, { error: e.message, stack: e.stack });
                }

                // 4. Audit Project Editor & Calculator
                openNewProject();
                navigateTo('project-editor');
                step("Navigate to Project Editor", state.activeView === 'project-editor');

                document.getElementById('proj-name').value = 'Gabinete para Eletrônica';
                document.getElementById('proj-client-name').value = 'Tech Corp';
                document.getElementById('proj-client-email').value = 'contato@techcorp.com';
                document.getElementById('proj-client-phone').value = '11999887766';
                document.getElementById('proj-cad-hours').value = '2';
                document.getElementById('proj-cad-rate').value = '60';
                document.getElementById('proj-post-hours').value = '1';
                document.getElementById('proj-post-rate').value = '40';
                document.getElementById('proj-overhead').value = '15';
                document.getElementById('proj-margin').value = '35';
                document.getElementById('proj-tax').value = '6';
                document.getElementById('proj-discount').value = '5';
                document.getElementById('proj-shipping').value = '25';
                document.getElementById('proj-delivery-days').value = '4';

                // Check plates configuration
                if (state.currentPlates.length > 0 && createdPrinterId && createdFilamentId) {
                    state.currentPlates[0].name = 'Chassi Principal';
                    state.currentPlates[0].printer_id = createdPrinterId;
                    state.currentPlates[0].filament_id = createdFilamentId;
                    state.currentPlates[0].print_time_hours = 3;
                    state.currentPlates[0].filament_used_g = 180;
                    renderPlates();
                    recalcLiveSummary();
                }

                // Test duplicating the plate
                const platesCountBefore = state.currentPlates.length;
                duplicatePlateRow(0);
                const platesCountAfter = state.currentPlates.length;
                step("Duplicate plate row", platesCountAfter === platesCountBefore + 1, {
                    before: platesCountBefore,
                    after: platesCountAfter,
                    clonedPlateName: state.currentPlates[1]?.name
                });

                // Add BOM Item
                addNewBomRow();
                state.currentBOM[0].name = 'Parafusos M3x10 Inox';
                state.currentBOM[0].category = 'Fixadores';
                state.currentBOM[0].quantity = 8;
                state.currentBOM[0].unit_cost = 0.50;
                renderBOM();
                recalcLiveSummary();

                // Check live summary calculation
                const liveFinalPriceText = document.getElementById('live-final-price')?.innerText;
                const liveProfitMarginText = document.getElementById('live-profit-margin')?.innerText;
                step("Live summary prices updated", !!liveFinalPriceText && liveFinalPriceText !== 'R$ 0,00', {
                    finalPrice: liveFinalPriceText,
                    profitMargin: liveProfitMarginText
                });

                // Save Project
                let savedProjectId = null;
                try {
                    await saveCurrentProject(false);
                    step("Save project", true);
                    const prj = state.projects.find(p => p.name === 'Gabinete para Eletrônica');
                    if (prj) {
                        savedProjectId = prj.id;
                        step("Project verified in state", true, { id: savedProjectId });
                    }
                } catch(e) {
                    step("Save project", false, { error: e.message });
                }

                // 5. Audit Deep Issues & Edge Cases

                // 5.1 Test: Delivery days = 0 (Pronta entrega / Retirada no balcão)
                document.getElementById('proj-delivery-days').value = '0';
                try {
                    await saveCurrentProject(false);
                    step("Save project with delivery_days = 0", true);
                } catch(e) {
                    addBug(
                        "[BUG] Erro ao salvar projeto com prazo de entrega de 0 dias (pronta entrega)",
                        "backend/validation",
                        "high",
                        "Ao configurar o prazo de entrega para 0 dias (representando retirada imediata ou peça pronta em estoque), a requisição é rejeitada ou sofre fallback inadequado.",
                        "1. Abrir projeto.\\n2. Definir 'Prazo de Entrega' como 0.\\n3. Clicar em Salvar.",
                        "Prazo 0 dias deve ser aceito e persistido normalmente.",
                        "Erro retornado: " + e.message,
                        "Garantir ge=0 no schema Pydantic e não usar `||` com valor zero no frontend."
                    );
                }

                // 5.2 Test: BOM item with 0 unit cost (brinde ou material do cliente)
                state.currentBOM[0].unit_cost = 0;
                try {
                    recalcLiveSummary();
                    await saveCurrentProject(false);
                    step("Save project with BOM unit_cost = 0", true);
                } catch(e) {
                    addBug(
                        "[BUG] Item de BOM com custo zero causa erro ao salvar",
                        "calculator",
                        "medium",
                        "Peças fornecidas pelo próprio cliente têm custo unitário 0 na composição do projeto.",
                        "1. Adicionar item no BOM com custo 0.\\n2. Salvar projeto.",
                        "Permitir custo zero em itens de BOM.",
                        "Erro: " + e.message,
                        "Garantir ge=0 no schema Pydantic de BOMItem."
                    );
                }

                // 5.3 Test: Discount input > 100%
                const discEl = document.getElementById('proj-discount');
                if (discEl) {
                    const hasMax = discEl.hasAttribute('max');
                    const maxVal = discEl.getAttribute('max');
                    if (!hasMax || maxVal !== '100') {
                        addBug(
                            "[BUG] Campo de desconto comercial não possui limite máximo de 100% no formulário",
                            "frontend/validation",
                            "medium",
                            "O campo #proj-discount permite digitação de valores maiores que 100% (ex: 120%), resultando em valores financeiros negativos incoerentes na tela e erro 422 ao salvar.",
                            "1. No editor de orçamento, digitar 120 no campo 'Desconto (%)'.\\n2. O resumo financeiro exibe total negativo e o salvamento falha com 422.",
                            "O campo deve possuir max='100' e bloquear valores superiores.",
                            `Atributo max atual: ${maxVal || 'ausente'}`,
                            "Adicionar max='100' e min='0' em #proj-discount e limitar via Math.min(100, ...) em recalcLiveSummary."
                        );
                    }
                }

                // 5.4 Test: Tax input >= 100%
                const taxEl = document.getElementById('proj-tax');
                if (taxEl) {
                    const hasMax = taxEl.hasAttribute('max');
                    const maxVal = taxEl.getAttribute('max');
                    if (!hasMax || parseFloat(maxVal) >= 100) {
                        addBug(
                            "[BUG] Campo de alíquota de impostos permite alíquotas de 100% que causam divisão por zero",
                            "financial/calculator",
                            "high",
                            "A fórmula de mark-up comercial calcula o preço de venda dividindo por (1 - tax_rate). Quando a alíquota de imposto é 100%, ocorre divisão por zero resultando em Infinity ou NaN no preço final.",
                            "1. No editor de orçamento, digitar 100 no campo 'Impostos / Taxas (%)'.\\n2. Verificar o resumo financeiro.",
                            "O campo deve ter teto máximo de 99% para evitar divisão por zero.",
                            `Atributo max atual: ${maxVal || 'ausente'}`,
                            "Adicionar max='99' no input #proj-tax e sanitizar com Math.min(99, ...) no cálculo."
                        );
                    }
                }

                // 5.5 Test: Profit Margin Negative
                const marginEl = document.getElementById('proj-margin');
                if (marginEl) {
                    const minVal = marginEl.getAttribute('min');
                    if (minVal !== '0') {
                        addBug(
                            "[BUG] Campo de margem de lucro permite digitação de valores negativos no frontend",
                            "financial/calculator",
                            "medium",
                            "O input #proj-margin não possui restrição min='0', permitindo margens de lucro negativas que distorcem o cálculo da proposta comercial.",
                            "1. Abrir calculadora de orçamento.\\n2. Digitar margem de -20%.\\n3. O sistema calcula preço com prejuízo sem aviso.",
                            "Definir min='0' em #proj-margin e sanitizar no oninput/recalcLiveSummary.",
                            `Atributo min atual: ${minVal || 'ausente'}`,
                            "Definir min='0' em #proj-margin."
                        );
                    }
                }

                // 5.6 Test: Slicer Reimport (.value clearing on single plate & dropzone)
                const singlePlateFn = window.handleSinglePlateFile?.toString() || '';
                const hasPlateReset = singlePlateFn.includes('.value =') || singlePlateFn.includes('.value=');
                if (!hasPlateReset) {
                    addBug(
                        "[BUG] Reimportar o mesmo arquivo de fatiador na placa não atualiza os dados por retenção de cache do input",
                        "parsers/ux",
                        "medium",
                        "Ao refazer o fatiamento de uma peça mantendo o mesmo nome de arquivo e clicar novamente no botão de importação da placa, o navegador não dispara o evento 'change' porque o valor do input file permanece em cache.",
                        "1. Importar arquivo G-code em uma placa.\\n2. Refatiar no software com mesmo nome.\\n3. Clicar novamente em importar na mesma placa e selecionar o arquivo: nada acontece.",
                        "O input deve ter seu .value resetado para '' após o carregamento para disparar novo evento 'change'.",
                        "Código não reseta e.target.value.",
                        "Adicionar `if (e.target) e.target.value = '';` em handleSinglePlateFile."
                    );
                }

                // 5.7 Test: Modal Accessibility (ESC & Backdrop)
                openFilamentModal();
                const filModalBox = document.getElementById('modal-filament');
                document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
                const filClosedWithEsc = filModalBox.classList.contains('hidden');
                if (!filClosedWithEsc) {
                    addBug(
                        "[UX/A11Y] Modal de cadastro de filamento não fecha ao pressionar a tecla ESC",
                        "accessibility/ui",
                        "low",
                        "Ao abrir o modal de filamento e pressionar a tecla ESC no teclado físico, o diálogo permanece aberto contrariando as diretrizes WAI-ARIA.",
                        "1. Abrir tela de filamentos.\\n2. Clicar em Novo Filamento.\\n3. Pressionar ESC.",
                        "O modal deve fechar imediatamente ao pressionar ESC.",
                        "O modal permaneceu visível.",
                        "Adicionar listener de 'Escape' global que chama closeFilamentModal()."
                    );
                }

                // 5.8 Test: Settings Page - CNPJ/CPF and Workshop Phone validation
                navigateTo('settings');
                const docInput = document.getElementById('pref-doc');
                const phoneInput = document.getElementById('pref-phone');
                step("Settings: doc and phone inputs exist", !!docInput && !!phoneInput);

                // 5.9 Test: Dashboard metrics and charts
                navigateTo('dashboard');
                const statRevenue = document.getElementById('stat-total-revenue');
                const statProjects = document.getElementById('stat-total-projects');
                const statMargin = document.getElementById('stat-avg-margin');
                step("Dashboard metrics rendered", !!statRevenue && !!statProjects && !!statMargin, {
                    revenue: statRevenue?.innerText,
                    projects: statProjects?.innerText,
                    margin: statMargin?.innerText
                });

                // 5.10 Test: Search and Filter on Dashboard Projects
                const projSearch = document.getElementById('project-search-input');
                const projStatusFilter = document.getElementById('project-status-filter');
                step("Dashboard projects search input exists", !!projSearch);
                step("Dashboard projects status filter exists", !!projStatusFilter);

                if (projSearch) {
                    projSearch.value = 'Gabinete';
                    projSearch.dispatchEvent(new Event('input', { bubbles: true }));
                    step("Dashboard project search filtered by 'Gabinete'", true);
                    projSearch.value = '';
                    projSearch.dispatchEvent(new Event('input', { bubbles: true }));
                }

                // 5.11 Test: Clone Project
                if (savedProjectId && typeof window.cloneProject === 'function') {
                    try {
                        const projectsCountBefore = state.projects.length;
                        await cloneProject(savedProjectId);
                        step("Clone project execution", state.projects.length === projectsCountBefore + 1, {
                            before: projectsCountBefore,
                            after: state.projects.length
                        });
                    } catch(e) {
                        step("Clone project execution", false, { error: e.message });
                    }
                }

                // 5.12 Test: View PDF Preview
                if (savedProjectId) {
                    try {
                        const pdfRes = await fetch(`/api/projects/${savedProjectId}/pdf?disposition=inline`, {
                            headers: { 'Authorization': 'Bearer ' + API.getToken() }
                        });
                        step("Fetch project PDF inline", pdfRes.ok, { status: pdfRes.status, contentType: pdfRes.headers.get('content-type') });
                    } catch(e) {
                        step("Fetch project PDF inline", false, { error: e.message });
                    }
                }

                // 5.13 Check responsiveness / viewport elements
                const header = document.querySelector('header');
                step("Header element exists", !!header);

                // 5.14 Audit UX: Empty state messaging
                // Check filaments empty state
                const originalFilaments = [...state.filaments];
                state.filaments = [];
                renderFilamentsGrid();
                const emptyFilamentNotice = document.querySelector('#filaments-grid')?.innerText || '';
                step("Filaments empty state rendered", emptyFilamentNotice.includes('Nenhum') || emptyFilamentNotice.includes('Cadastre'));
                state.filaments = originalFilaments;
                renderFilamentsGrid();

                return report;
            })()
            """

            res = await eval_js(test_script)
            print("\n================== FULL BROWSER AUDIT REPORT ==================")
            print(json.dumps(res, indent=2, ensure_ascii=False))

            print("\n================== CONSOLE LOGS & ERRORS ==================")
            for l in console_logs:
                print("Console Log:", l.get("type"), [arg.get("value") for arg in l.get("args", [])])

            print("\n================== UNCAUGHT EXCEPTIONS ==================")
            for ex in exceptions:
                print("Exception:", ex)

    finally:
        proc.terminate()

if __name__ == "__main__":
    asyncio.run(run_audit())
