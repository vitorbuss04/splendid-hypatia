import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os
import sys

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

async def hunt_bugs():
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
        print(f"Connected to Chrome CDP: {ws_url}")

        async with websockets.connect(ws_url) as ws:
            msg_id = 1
            console_msgs = []

            async def send(method, params=None):
                nonlocal msg_id
                mid = msg_id
                msg_id += 1
                payload = {"id": mid, "method": method, "params": params or {}}
                await ws.send(json.dumps(payload))
                while True:
                    raw = await ws.recv()
                    data = json.loads(raw)
                    if "method" in data:
                        if data["method"] in ("Runtime.consoleAPICalled", "Log.entryAdded"):
                            console_msgs.append(data["params"])
                        continue
                    if data.get("id") == mid:
                        return data

            async def evaluate(expr):
                resp = await send("Runtime.evaluate", {
                    "expression": expr,
                    "awaitPromise": True,
                    "returnByValue": True
                })
                if resp and "result" in resp and "result" in resp["result"]:
                    return resp["result"]["result"].get("value")
                return resp

            await send("Runtime.enable")
            await send("Log.enable")
            await asyncio.sleep(1)

            # Verification tests script
            tests_script = """
            (async () => {
                const results = [];

                // 1. Test 422 Toast formatting
                try {
                    // Register temporary user
                    const email = 'bug_hunter_' + Date.now() + '@test.com';
                    await API.auth.register(email, 'Pass12345!', 'Bug Hunter', 'Hunter Lab');
                    state.user = await API.auth.getMe();
                    document.getElementById('auth-modal')?.classList.add('hidden');
                    await loadAllData();

                    // Trigger 422
                    let caughtError = null;
                    try {
                        await API.projects.create({
                            name: 'Teste Validação 422',
                            tax_rate_percent: 150
                        });
                    } catch (e) {
                        caughtError = e.message;
                    }

                    results.push({
                        id: "BUG_422_TOAST",
                        confirmed: caughtError === '[object Object]' || (typeof caughtError === 'string' && caughtError.includes('[object Object]')),
                        evidence: { caughtError }
                    });
                } catch(e) {
                    results.push({ id: "BUG_422_TOAST", confirmed: false, error: e.message });
                }

                // 2. Test Material select onchange
                try {
                    openFilamentModal();
                    const matSelect = document.getElementById('filament-material');
                    const hasOnChange = matSelect.hasAttribute('onchange');
                    const hasOnInput = matSelect.hasAttribute('oninput');
                    
                    // Set material to PETG and trigger change only
                    matSelect.value = 'PETG';
                    matSelect.dispatchEvent(new Event('change', { bubbles: true }));
                    const previewText = document.getElementById('filament-preview-text')?.innerText || '';
                    const updatedOnOnlyChange = previewText.startsWith('PETG');

                    results.push({
                        id: "BUG_MATERIAL_ONCHANGE",
                        confirmed: !hasOnChange && !updatedOnOnlyChange,
                        evidence: { hasOnChange, hasOnInput, previewText, updatedOnOnlyChange }
                    });
                } catch(e) {
                    results.push({ id: "BUG_MATERIAL_ONCHANGE", confirmed: false, error: e.message });
                }

                // 3. Test Preview close button window.close()
                try {
                    // Check preview.html button attribute
                    const prevResp = await fetch('/preview');
                    const html = await prevResp.text();
                    const hasWindowClose = html.includes('window.close()');
                    const hasFallback = html.includes('window.location') || html.includes('history.back');

                    results.push({
                        id: "BUG_PREVIEW_CLOSE",
                        confirmed: hasWindowClose && !hasFallback,
                        evidence: { hasWindowClose, hasFallback }
                    });
                } catch(e) {
                    results.push({ id: "BUG_PREVIEW_CLOSE", confirmed: false, error: e.message });
                }

                // 4. Test Filament density input missing
                try {
                    const densityInput = document.getElementById('filament-density');
                    const saveFilamentCode = window.handleSaveFilament?.toString() || '';
                    const sendsDensity = saveFilamentCode.includes('density_g_cm3');

                    results.push({
                        id: "BUG_FILAMENT_DENSITY",
                        confirmed: !densityInput && !sendsDensity,
                        evidence: { hasDensityInput: !!densityInput, sendsDensity }
                    });
                } catch(e) {
                    results.push({ id: "BUG_FILAMENT_DENSITY", confirmed: false, error: e.message });
                }

                // 5. Test Plate time negative values
                try {
                    openNewProject();
                    navigateTo('project-editor');
                    const hInp = document.getElementById('plate-time-h-0');
                    const mInp = document.getElementById('plate-time-m-0');
                    if (mInp) {
                        mInp.value = '-10';
                        mInp.dispatchEvent(new Event('input', { bubbles: true }));
                        const hoursCalculated = state.currentPlates[0]?.print_time_hours;
                        results.push({
                            id: "BUG_PLATE_TIME_NEGATIVE",
                            confirmed: hoursCalculated < 0,
                            evidence: { hoursCalculated, inputValue: mInp.value }
                        });
                    }
                } catch(e) {
                    results.push({ id: "BUG_PLATE_TIME_NEGATIVE", confirmed: false, error: e.message });
                }

                // 6. Test Material and Status filter dropdowns in Filaments and Printers views
                try {
                    navigateTo('filaments');
                    const filMatFilter = document.getElementById('filament-material-filter');
                    navigateTo('printers');
                    const prnStatusFilter = document.getElementById('printer-status-filter');

                    results.push({
                        id: "FEAT_CATALOG_FILTERS",
                        confirmed: !filMatFilter && !prnStatusFilter,
                        evidence: { hasFilamentFilter: !!filMatFilter, hasPrinterFilter: !!prnStatusFilter }
                    });
                } catch(e) {
                    results.push({ id: "FEAT_CATALOG_FILTERS", confirmed: false, error: e.message });
                }

                return results;
            })()
            """

            res = await evaluate(tests_script)
            print("=== VERIFICATION RESULTS ===")
            print(json.dumps(res, indent=2, ensure_ascii=False))

    finally:
        proc.terminate()

if __name__ == "__main__":
    asyncio.run(hunt_bugs())
