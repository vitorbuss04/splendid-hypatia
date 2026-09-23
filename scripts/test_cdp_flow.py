import subprocess
import time
import json
import urllib.request
import socket
import os
import base64
import hashlib
import struct

def make_ws_handshake(sock, host, port, path):
    key = base64.b64encode(os.urandom(16)).decode('utf-8')
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n\r\n"
    )
    sock.sendall(req.encode('utf-8'))
    resp = sock.recv(4096).decode('utf-8')
    assert "101" in resp, f"Handshake failed: {resp}"

def send_ws_frame(sock, text):
    data = text.encode('utf-8')
    length = len(data)
    frame = bytearray()
    frame.append(0x81) # fin + text opcode
    
    # client must mask
    mask_key = os.urandom(4)
    if length < 126:
        frame.append(0x80 | length)
    elif length < 65536:
        frame.append(0x80 | 126)
        frame.extend(struct.pack("!H", length))
    else:
        frame.append(0x80 | 127)
        frame.extend(struct.pack("!Q", length))
    
    frame.extend(mask_key)
    masked = bytearray(b ^ mask_key[i % 4] for i, b in enumerate(data))
    frame.extend(masked)
    sock.sendall(frame)

def recv_ws_frame(sock):
    header = sock.recv(2)
    if not header:
        return None
    b1, b2 = header[0], header[1]
    length = b2 & 0x7f
    if length == 126:
        length = struct.unpack("!H", sock.recv(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", sock.recv(8))[0]
    
    data = bytearray()
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            break
        data.extend(chunk)
    return data.decode('utf-8', errors='ignore')

def run_test():
    cmd = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--headless=new",
        "--remote-debugging-port=9222",
        "--disable-gpu",
        "http://localhost:8000"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)
    try:
        res = urllib.request.urlopen("http://localhost:9222/json").read().decode('utf-8')
        tabs = json.loads(res)
        target_tab = None
        for t in tabs:
            if "localhost:8000" in t.get("url", ""):
                target_tab = t
                break
        assert target_tab, "Target tab not found!"
        ws_url = target_tab["webSocketDebuggerUrl"]
        # parse ws://localhost:9222/devtools/page/...
        path = ws_url.split("9222")[1]
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("localhost", 9222))
        make_ws_handshake(s, "localhost", 9222, path)
        print("Connected to Chrome CDP WebSocket!")

        def cdp_call(method, params=None, msg_id=1):
            req = {"id": msg_id, "method": method, "params": params or {}}
            send_ws_frame(s, json.dumps(req))
            while True:
                resp_text = recv_ws_frame(s)
                if not resp_text:
                    return None
                resp = json.loads(resp_text)
                if resp.get("id") == msg_id:
                    return resp

        # 1. Enable console and runtime
        cdp_call("Runtime.enable", msg_id=1)
        
        # 2. Check DOM and log in or register
        script_eval = """
        (async () => {
            // Check auth modal
            const authModal = document.getElementById('auth-modal');
            const isLoggedIn = authModal.classList.contains('hidden');
            let res = { isLoggedIn };
            
            // Try to register/login test user
            try {
                const regRes = await API.auth.login('vitor@example.com', '123456').catch(async () => {
                    return await API.auth.register('vitor@example.com', '123456', 'Vitor Test', 'Oficina');
                });
                res.authSuccess = true;
                await initApp();
            } catch(e) {
                res.authError = e.message;
            }
            
            // Open filament modal
            openFilamentModal();
            const fWeight = document.getElementById('filament-weight');
            const fPrice = document.getElementById('filament-price');
            
            res.initialWeight = fWeight.value;
            res.initialPrice = fPrice.value;
            res.weightStep = fWeight.getAttribute('step');
            res.priceStep = fPrice.getAttribute('step');
            res.weightMin = fWeight.getAttribute('min');
            res.priceMin = fPrice.getAttribute('min');
            res.weightType = fWeight.type;
            res.priceType = fPrice.type;

            // Test setting/typing 1000g in weight
            fWeight.focus();
            fWeight.value = '1000';
            fWeight.blur();
            res.weightValidity1000 = {
                valid: fWeight.checkValidity(),
                stepMismatch: fWeight.validity.stepMismatch,
                rangeUnderflow: fWeight.validity.rangeUnderflow,
                valueMissing: fWeight.validity.valueMissing
            };

            // Test setting/typing 56,50 in price
            fPrice.focus();
            fPrice.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));
            // Simulate typing
            fPrice.value = '56,50';
            res.priceWhileFocused = {
                value: fPrice.value,
                type: fPrice.type,
                datasetOriginalType: fPrice.dataset.originalType
            };

            // Blur
            fPrice.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
            fPrice.blur();
            res.priceAfterBlur = {
                value: fPrice.value,
                type: fPrice.type,
                valid: fPrice.checkValidity(),
                stepMismatch: fPrice.validity.stepMismatch,
                badInput: fPrice.validity.badInput
            };

            // Now test printer lifespan
            openPrinterModal();
            const pLifespan = document.getElementById('printer-lifespan');
            pLifespan.focus();
            pLifespan.value = '5000';
            pLifespan.blur();
            res.printerLifespanValidity = {
                value: pLifespan.value,
                valid: pLifespan.checkValidity(),
                stepMismatch: pLifespan.validity.stepMismatch
            };

            return res;
        })()
        """
        eval_res = cdp_call("Runtime.evaluate", {
            "expression": script_eval,
            "awaitPromise": True,
            "returnByValue": True
        }, msg_id=2)
        print("EVAL RESULT:")
        print(json.dumps(eval_res, indent=2))
        
    finally:
        proc.terminate()

if __name__ == "__main__":
    run_test()
