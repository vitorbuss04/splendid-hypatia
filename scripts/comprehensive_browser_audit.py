import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os
import sys

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:8001"

async def run_comprehensive_audit():
    print(f"Starting Chrome for audit on {BASE_URL}...", flush=True)
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        "--disable-gpu",
        "--window-size=1440,900",
        BASE_URL
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2.0)

    try:
        tabs_res = urllib.request.urlopen("http://localhost:9222/json").read()
        tabs = json.loads(tabs_res)
        target_tab = None
        for t in tabs:
            if "8001" in t.get("url", ""):
                target_tab = t
                break
        if not target_tab:
            target_tab = tabs[0]

        ws_url = target_tab["webSocketDebuggerUrl"]
        print(f"Connected to Chrome CDP: {ws_url}", flush=True)

        async with websockets.connect(ws_url, max_size=10_000_000) as ws:
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
                if resp and "result" in resp and "result" in resp["result"]:
                    return resp["result"]["result"].get("value")
                return resp

            await send_cmd("Runtime.enable")
            await send_cmd("Log.enable")
            await asyncio.sleep(1.0)

            # Step 1: Register and login
            step1 = """
            (async () => {
                const email = 'audit_bot_' + Date.now() + '@test.com';
                await API.auth.register(email, 'Pass12345!', 'Audit Bot', 'Oficina Teste');
                state.user = await API.auth.getMe();
                document.getElementById('auth-modal')?.classList.add('hidden');
                await loadAllData();
                return { email: state.user.email, id: state.user.id };
            })()
            """
            r1 = await eval_js(step1)
            print("Step 1 (Auth):", r1, flush=True)

            # Step 2: Test Printers
            step2 = """
            (async () => {
                const results = [];
                openPrinterModal();
                document.getElementById('printer-name').value = 'Bambu Lab P1S Combo';
                document.getElementById('printer-model').value = 'P1S';
                document.getElementById('printer-cost').value = '5500.00';
                document.getElementById('printer-lifespan').value = '5000';
                document.getElementById('printer-power').value = '160';
                document.getElementById('printer-maintenance').value = '1.20';
                document.getElementById('printer-energy').value = '0.85';
                await handleSavePrinter({ preventDefault: () => {} });
                
                const prn = state.printers.find(p => p.name === 'Bambu Lab P1S Combo');
                results.push({ name: 'create_printer', success: !!prn, rate: prn?.machine_hourly_rate });

                // Test search and filter
                const searchInp = document.getElementById('printer-search-input');
                if (searchInp) {
                    searchInp.value = 'P1S';
                    filterPrinters();
                    results.push({ name: 'filter_printers', found: document.querySelectorAll('#printers-grid .card-dark').length });
                    searchInp.value = '';
                    filterPrinters();
                }
                return results;
            })()
            """
            r2 = await eval_js(step2)
            print("Step 2 (Printers):", r2, flush=True)

            # Step 3: Test Filaments
            step3 = """
            (async () => {
                const results = [];
                openFilamentModal();
                document.getElementById('filament-brand').value = 'Polymaker';
                document.getElementById('filament-brand').dispatchEvent(new Event('input', { bubbles: true }));
                document.getElementById('filament-material').value = 'ABS';
                document.getElementById('filament-material').dispatchEvent(new Event('change', { bubbles: true }));
                document.getElementById('filament-color').value = 'Preto Fosco';
                document.getElementById('filament-color').dispatchEvent(new Event('input', { bubbles: true }));
                document.getElementById('filament-weight').value = '1000';
                document.getElementById('filament-price').value = '135.00';
                await handleSaveFilament({ preventDefault: () => {} });

                const fil = state.filaments.find(f => f.brand === 'Polymaker' && f.material === 'ABS');
                results.push({ name: 'create_filament', success: !!fil, cost_per_g: fil?.cost_per_gram });

                // Test duplicate
                if (fil) {
                    openFilamentModal(fil, true);
                    document.getElementById('filament-color').value = 'Cinza Claro';
                    document.getElementById('filament-color').dispatchEvent(new Event('input', { bubbles: true }));
                    await handleSaveFilament({ preventDefault: () => {} });
                    const dup = state.filaments.find(f => f.brand === 'Polymaker' && f.color === 'Cinza Claro');
                    results.push({ name: 'duplicate_filament', success: !!dup, cost_per_g: dup?.cost_per_gram });
                }
                return results;
            })()
            """
            r3 = await eval_js(step3)
            print("Step 3 (Filaments):", r3, flush=True)

            # Step 4: Test Project Editor & Saving
            step4 = """
            (async () => {
                const results = [];
                openNewProject();
                document.getElementById('proj-name').value = 'Caixa Estanque IoT';
                document.getElementById('proj-client-name').value = 'SensorTech';
                document.getElementById('proj-client-phone').value = '11988887777';
                document.getElementById('proj-client-phone').dispatchEvent(new Event('input', { bubbles: true }));
                
                // Check phone formatting
                const formattedPhone = document.getElementById('proj-client-phone').value;
                results.push({ name: 'phone_mask', value: formattedPhone });

                // Configure Plate
                if (state.currentPlates.length > 0) {
                    state.currentPlates[0].name = 'Gabinete Superior';
                    state.currentPlates[0].print_time_hours = 3.5;
                    state.currentPlates[0].part_weight_g = 120;
                    state.currentPlates[0].failure_margin_percent = 10;
                    state.currentPlates[0].quantity = 1;
                    renderPlates();
                }

                // Add BOM
                addNewBomRow();
                if (state.currentBOM.length > 0) {
                    state.currentBOM[0].name = 'O-ring Silicone 45mm';
                    state.currentBOM[0].category = 'Outros';
                    state.currentBOM[0].quantity = 2;
                    state.currentBOM[0].unit_cost = 4.50;
                    renderBOM();
                }

                document.getElementById('proj-cad-hours').value = '1.0';
                document.getElementById('proj-cad-rate').value = '80.0';
                document.getElementById('proj-margin').value = '40';
                document.getElementById('proj-tax').value = '6';
                document.getElementById('proj-discount').value = '5';
                document.getElementById('proj-shipping').value = '25.0';
                document.getElementById('proj-delivery-days').value = '4';

                recalcLiveSummary();

                const feSummary = {
                    base_cost: document.getElementById('live-base-cost')?.innerText,
                    final_price: document.getElementById('live-final-price')?.innerText,
                    net_profit: document.getElementById('live-net-profit')?.innerText,
                    suggested_price: document.getElementById('live-suggested-price')?.innerText
                };
                results.push({ name: 'frontend_summary', summary: feSummary });

                // Save without navigating away
                const saved = await saveCurrentProject(false);
                results.push({ name: 'save_project', success: saved, id: state.currentProject?.id });

                if (state.currentProject?.id) {
                    const beSummary = await API.projects.getSummary(state.currentProject.id);
                    results.push({
                        name: 'backend_summary',
                        base_cost: beSummary.base_cost,
                        final_price: beSummary.final_price_to_client,
                        net_profit: beSummary.net_profit,
                        suggested_price: beSummary.suggested_price
                    });
                }

                return results;
            })()
            """
            r4 = await eval_js(step4)
            print("Step 4 (Project Editor):", json.dumps(r4, indent=2, ensure_ascii=False), flush=True)

            # Step 5: Test PDF generation
            step5 = """
            (async () => {
                if (!state.currentProject?.id) return { error: 'No project' };
                const resClient = await fetch(`/api/projects/${state.currentProject.id}/pdf?type=client&disposition=inline`, {
                    headers: { 'Authorization': 'Bearer ' + API.getToken() }
                });
                const resTech = await fetch(`/api/projects/${state.currentProject.id}/pdf?type=technical&disposition=inline`, {
                    headers: { 'Authorization': 'Bearer ' + API.getToken() }
                });
                return {
                    client_pdf: { ok: resClient.ok, status: resClient.status, len: (await resClient.blob()).size },
                    tech_pdf: { ok: resTech.ok, status: resTech.status, len: (await resTech.blob()).size }
                };
            })()
            """
            r5 = await eval_js(step5)
            print("Step 5 (PDF):", r5, flush=True)

            # Step 6: Test Deep Edge Cases & Bugs
            step6 = """
            (async () => {
                const bugs = [];

                // Bug Test 1: Slicer File Re-import
                // Check if file input has onchange that resets value
                const fileInputs = document.querySelectorAll('input[type="file"]');
                let fileInputsResetValue = true;
                fileInputs.forEach(fi => {
                    const onchangeStr = fi.getAttribute('onchange') || '';
                    // Does handleSinglePlateFile or dropzone reset target.value?
                });

                // Bug Test 2: HTML injection / XSS in Project Name or Client Name
                document.getElementById('proj-name').value = 'Gabinete <b>Bold</b> & <script>alert(1)</script>';
                document.getElementById('proj-client-name').value = 'Cliente "Special" & Co.';
                await saveCurrentProject(false);
                navigateTo('projects');
                const projectCard = document.querySelector('#projects-table-body, #view-projects');
                const htmlContent = projectCard ? projectCard.innerHTML : '';
                if (htmlContent.includes('<script>alert(1)</script>')) {
                    bugs.push({
                        title: "[SECURITY/XSS] Falta de sanitização contra XSS nos nomes de projetos e clientes",
                        severity: "high",
                        detail: "Script tags inseridas no nome do projeto ou cliente são renderizadas sem escape."
                    });
                }

                // Bug Test 3: Division by zero when plate print time and weight are 0
                openNewProject();
                state.currentPlates[0].print_time_hours = 0;
                state.currentPlates[0].part_weight_g = 0;
                state.currentPlates[0].purge_weight_g = 0;
                renderPlates();
                recalcLiveSummary();
                const platePillText = document.getElementById('plate-summary-text-0')?.textContent || '';
                const baseCostText = document.getElementById('live-base-cost')?.textContent || '';
                if (baseCostText.includes('NaN') || platePillText.includes('NaN')) {
                    bugs.push({
                        title: "[BUG] Placa com peso e tempo zerados exibe NaN na interface",
                        severity: "medium",
                        detail: "A placa com valores zerados calculou NaN no custo ou resumo."
                    });
                }

                // Bug Test 4: Project with Delivery Days = 0 in PDF
                // Does PDF render 0 days correctly as pronta entrega?
                document.getElementById('proj-delivery-days').value = '0';
                await saveCurrentProject(false);
                const pdfRes = await fetch(`/api/projects/${state.currentProject.id}/pdf?type=client`, {
                    headers: { 'Authorization': 'Bearer ' + API.getToken() }
                });
                if (!pdfRes.ok) {
                    bugs.push({
                        title: "[BUG] Falha na geração do PDF para projeto com prazo de pronta entrega (0 dias)",
                        severity: "high",
                        detail: "A API retornou erro ao gerar PDF quando delivery_days é 0."
                    });
                }

                // Bug Test 5: Keyboard accessibility for modals (ESC key)
                openFilamentModal();
                const filModal = document.getElementById('modal-filament');
                document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
                if (!filModal.classList.contains('hidden')) {
                    bugs.push({
                        title: "[A11Y] Modal de filamentos não fecha ao pressionar a tecla ESC",
                        severity: "low",
                        detail: "O modal de filamentos permaneceu aberto após pressionar a tecla Escape."
                    });
                }
                closeFilamentModal();

                openPrinterModal();
                const prnModal = document.getElementById('modal-printer');
                document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
                if (!prnModal.classList.contains('hidden')) {
                    bugs.push({
                        title: "[A11Y] Modal de impressoras não fecha ao pressionar a tecla ESC",
                        severity: "low",
                        detail: "O modal de impressoras permaneceu aberto após pressionar a tecla Escape."
                    });
                }
                closePrinterModal();

                // Bug Test 6: Check Backdrop click on modals
                openPrinterModal();
                prnModal.dispatchEvent(new MouseEvent('click', { bubbles: true, target: prnModal }));
                // Note: backdrop click closes modal if event target is the backdrop
                closePrinterModal();

                return bugs;
            })()
            """
            r6 = await eval_js(step6)
            print("Step 6 (Bugs & Edge Cases):", json.dumps(r6, indent=2, ensure_ascii=False), flush=True)

            print("\nConsole logs captured:", len(console_logs), flush=True)
            for cl in console_logs:
                print("  Console:", cl.get("type"), [a.get("value") for a in cl.get("args", [])], flush=True)

            print("\nUncaught exceptions captured:", len(exceptions), flush=True)
            for ex in exceptions:
                print("  Exception:", ex, flush=True)

    finally:
        proc.terminate()

if __name__ == "__main__":
    asyncio.run(run_comprehensive_audit())
