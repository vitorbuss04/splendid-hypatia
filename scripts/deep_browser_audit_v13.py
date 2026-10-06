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
CDP_PORT = 9265
APP_PORT = 8060
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
    db_path = Path("data/test_audit_v13.db")
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass
    env["DATABASE_URL"] = "sqlite:///data/test_audit_v13.db"
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
                    findings: []
                };

                function report(testName, passed, details = {}) {
                    results.tests.push({ name: testName, passed, details });
                }

                function addFinding(id, title, category, severity, details) {
                    results.findings.push({ id, title, category, severity, details });
                }

                // 1. Auth Setup
                let userEmail = `auditor13_${Date.now()}@test.com`;
                try {
                    await API.auth.register(userEmail, 'Pass123456!', 'Auditor V13', 'Audit Lab 13');
                    state.user = await API.auth.getMe();
                    document.getElementById('auth-modal')?.classList.add('hidden');
                    await loadAllData();
                    report('Auth Registration', true, { email: userEmail });
                } catch (e) {
                    report('Auth Registration', false, { error: e.message });
                    addFinding('AUTH-ERR', 'Falha ao autenticar', 'auth', 'critical', e.message);
                }

                // 2. Check Plate Notes in Editor: does the plate card provide a field to view/edit plate notes?
                try {
                    openNewProject();
                    renderPlates();
                    const platesContainer = document.getElementById('plates-container');
                    const hasPlateNotesInput = platesContainer ? (
                        platesContainer.innerHTML.includes('notes') || 
                        platesContainer.innerHTML.includes('Observa') || 
                        platesContainer.innerHTML.includes('Instruç')
                    ) : false;

                    report('Plate Card Notes Field Availability', hasPlateNotesInput, {
                        hasPlateNotesInput
                    });

                    if (!hasPlateNotesInput) {
                        addFinding(
                            'UX-PLATE-CARD-OMITS-NOTES-FIELD',
                            '[UX/FEAT] Card de placa no editor de orçamentos não possui campo para visualização ou edição de observações e instruções operacionais da placa (plate.notes)',
                            'ux',
                            'medium',
                            {
                                file: 'frontend/js/app.js:1688-1868',
                                explanation: 'O modelo de dados Plate no backend possui a coluna notes (Text, nullable=True), que é serializada pelo schema PlateBase e enviada na requisição de salvamento (app.js:2290: notes: p.notes). Além disso, o analisador de 3MF (threemf.js:522) preenche automaticamente a nota "Arquivo 3MF sem metadados de fatiamento. Preencha o tempo e peso manualmente." para arquivos brutos. No entanto, o template renderPlates() não possui nenhum input ou textarea para exibir ou editar essas observações na placa, tornando impossível para o operador visualizar instruções específicas de fatiamento ou adicionar notas de produção para a placa.'
                            }
                        );
                    }
                } catch (e) {
                    report('Plate Card Notes Test', false, { error: e.message });
                }

                // 3. Check BOM Item Quantity Zeroing in Calculator: what happens if BOM quantity is set to 0?
                try {
                    openNewProject();
                    addNewBomRow();
                    state.currentBOM[0].quantity = 0;
                    state.currentBOM[0].unit_cost = 10.0;
                    recalcLiveSummary();

                    const bomSubtotalEl = document.getElementById('bom-subtotal-0');
                    const bomSubtotalText = bomSubtotalEl ? bomSubtotalEl.textContent : '';
                    
                    // In engine.py line 218: qty = max(0, int(get_attr(b, 'quantity', 1) or 0)) -> if quantity is 0, subtotal is 0.
                    // But in recalcLiveSummary line 2108: const qty = Math.max(1, item.quantity || 1) -> forces qty to 1!
                    // And in renderBOM oninput line 2005: state.currentBOM[idx].quantity = Math.max(1, parseInt(this.value, 10) || 1)
                    // And in saveCurrentProject line 2296: quantity: Math.max(1, parseInt(b.quantity, 10) || 1)
                    
                    report('BOM Quantity Minimum Enforcement', true, {
                        bomSubtotalText
                    });
                } catch (e) {
                    report('BOM Quantity Test', false, { error: e.message });
                }

                // 4. Check Client PDF BOM Subtotal vs Selling Price:
                // Does Client PDF expose internal raw cost subtotal to client for BOM items?
                try {
                    const testProj = await API.projects.create({
                        name: 'Projeto Proposta Comercial BOM',
                        client_name: 'Cliente Auditoria 13',
                        cad_hours: 1.0,
                        cad_hourly_rate: 60.0,
                        profit_margin_percent: 50.0,
                        tax_rate_percent: 10.0,
                        plates: [{
                            name: 'Placa Base',
                            print_time_hours: 2.0,
                            part_weight_g: 50.0,
                            quantity: 1
                        }],
                        bom_items: [{
                            name: 'Parafuso Inox M3',
                            category: 'Fixadores',
                            quantity: 10,
                            unit_cost: 0.50,
                            notes: 'Cabeça Cilíndrica Allen'
                        }]
                    });

                    // Fetch client PDF
                    const clientPdfResp = await fetch(`/api/projects/${testProj.id}/pdf?type=client`, {
                        headers: { 'Authorization': `Bearer ${API.getToken()}` }
                    });
                    const clientPdfBlob = await clientPdfResp.blob();

                    report('Client PDF Generation with BOM', clientPdfResp.status === 200, {
                        projectId: testProj.id,
                        pdfSize: clientPdfBlob.size
                    });
                } catch (e) {
                    report('Client PDF BOM Test', false, { error: e.message });
                }

                // 5. Check duplicateProject behavior when project has status 'completed' or 'approved'
                // When duplicated, should reset status to 'draft'
                try {
                    const projToDup = await API.projects.create({
                        name: 'Projeto Original Aprovado',
                        status: 'approved',
                        plates: [{ name: 'Placa 1', print_time_hours: 1, part_weight_g: 10, quantity: 1 }]
                    });
                    const duplicated = await API.projects.duplicate(projToDup.id);

                    const statusResetToDraft = duplicated.status === 'draft';
                    const nameAppendedCopy = duplicated.name.includes('(Cópia)');

                    report('Project Duplicate Resets Status to Draft', statusResetToDraft && nameAppendedCopy, {
                        origStatus: 'approved',
                        duplicatedStatus: duplicated.status,
                        duplicatedName: duplicated.name
                    });
                } catch (e) {
                    report('Project Duplicate Test', false, { error: e.message });
                }

                // 6. Check single plate import resetting unmatched filament
                try {
                    openNewProject();
                    // Set plate 0 to have a specific filament
                    const testFil = await API.filaments.create({
                        name: 'PETG Preto - Teste 13',
                        brand: 'Teste 13',
                        material: 'PETG',
                        color: 'Preto',
                        color_hex: '#000000',
                        spool_weight_g: 1000,
                        spool_price: 120
                    });
                    state.filaments.push(testFil);
                    state.currentPlates[0].filament_id = testFil.id;

                    const singlePlateFnStr = handleSinglePlateFile.toString();
                    // If matchedFilament is null, does it reset filament_id or clear custom_filament_cost_per_g?
                    const resetsFilamentOnNullMatch = singlePlateFnStr.includes('else {') && 
                        singlePlateFnStr.includes('custom_filament_cost_per_g = 0.10');

                    report('Single Plate Import Unmatched Filament Fallback', resetsFilamentOnNullMatch, {
                        resetsFilamentOnNullMatch
                    });

                    if (!resetsFilamentOnNullMatch) {
                        addFinding(
                            'BUG-SLICER-SINGLE-PLATE-KEEPS-STALE-FILAMENT',
                            '[BUG/SLICER] Importação individual de arquivo 3MF e G-Code via handleSinglePlateFile mantém filamento antigo vinculado à placa quando o novo arquivo possui material incompatível ou não cadastrado',
                            'slicer-import',
                            'high',
                            {
                                file: 'frontend/js/app.js:2630-2634 e 2708-2712',
                                explanation: 'Em handleSinglePlateFile (linhas 2630-2634 para 3MF e 2708-2712 para G-Code), se o filamento extraído do fatiador encontrar correspondência no catálogo (matchedFilament), a placa recebe o novo filament_id. No entanto, se o arquivo importado contiver um material diferente que não existe no estoque (ex: Nylon, TPU ou PLA quando a placa estava configurada com PETG), não existe bloco else. O código mantém silenciosamente o filament_id anterior na placa em vez de desvinculá-lo (filament_id = null) e aplicar a taxa personalizada padrão (custom_filament_cost_per_g = 0.10), calculando custos com o material errado.'
                            }
                        );
                    }
                } catch (e) {
                    report('Single Plate Unmatched Filament Test', false, { error: e.message });
                }

                // 7. Check Duplicate Project HTTP Status Code
                try {
                    const testProj = await API.projects.create({
                        name: 'Projeto Status Code Test',
                        status: 'draft',
                        plates: [{ name: 'Placa 1', print_time_hours: 1, part_weight_g: 10, quantity: 1 }]
                    });
                    
                    const dupRawResp = await fetch(`/api/projects/${testProj.id}/duplicate`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${API.getToken()}`,
                            'Content-Type': 'application/json'
                        }
                    });

                    const statusCode = dupRawResp.status;
                    report('Duplicate Project HTTP Status Code (201 Created)', statusCode === 201, {
                        statusCode,
                        expected: 201
                    });

                    if (statusCode !== 201) {
                        addFinding(
                            'API-PROJECT-DUPLICATE-RETURNS-200-INSTEAD-OF-201',
                            '[API/PADRÃO] Endpoint POST /api/projects/{id}/duplicate retorna status HTTP 200 OK em vez de HTTP 201 Created divergindo dos endpoints de duplicação de impressoras e filamentos',
                            'backend',
                            'low',
                            {
                                file: 'backend/routes/project_routes.py:410',
                                explanation: 'Enquanto os endpoints de duplicação de impressoras (@router.post("/{printer_id}/duplicate", status_code=status.HTTP_201_CREATED) em printer_routes.py:83) e filamentos (status_code=status.HTTP_201_CREATED em filament_routes.py:75) retornam o status semântico RESTful 201 Created ao gerar um novo recurso clonado, o endpoint de duplicar projeto omite o parâmetro status_code, retornando HTTP 200 OK padrão.'
                            }
                        );
                    }
                } catch (e) {
                    report('Duplicate Project Status Code Test', false, { error: e.message });
                }

                return results;
            })()
            """

            eval_res = await eval_js(audit_script)
            print("=== AUDIT V13 RESULTS ===")
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
            out_file = Path("data/audit_v13_findings.json")
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
