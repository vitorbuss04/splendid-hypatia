#!/usr/bin/env python3
"""
GitHub Issues Synchronizer for 3D Print Calc Pro (Splendid Hypatia)
Synchronizes user feedback and bug fixes with GitHub issues via REST API.
"""

import os
import sys
import json
import subprocess
import urllib.request
import urllib.error

REPO = "vitorbuss04/splendid-hypatia"
API_BASE = f"https://api.github.com/repos/{REPO}"

ISSUES_DEF = [
    {
        "number": 1,
        "title": "Cadastrar filamento: peso do carretel só aceita valores ímpares (ex: 1001) e rejeita 1000g",
        "labels": ["bug", "frontend", "ux"],
        "body": """### Descrição do Problema
Ao cadastrar um carretel de filamento, o campo de peso (em gramas) só aceitava valores ímpares como 1001g, rejeitando o valor padrão da indústria (1000g).

### Causa Raiz
O elemento `<input type="number" id="filament-weight">` no arquivo `frontend/index.html` possuía simultaneamente os atributos `min="1"` e `step="50"`. Pela especificação HTML5, o valor válido deve cumprir `(valor - min) % step === 0`. Portanto, `(1000 - 1) % 50 = 49 != 0` (inválido), enquanto `(1001 - 1) % 50 = 0` (válido).

### Solução Implementada
1. Alterado atributo no HTML para `step="any"` e `min="1"`.
2. Implementada validação numérica flexível no frontend (`frontend/js/app.js`) e backend Pydantic (`backend/schemas.py`).
3. Adicionada cobertura de testes automatizados em `tests/test_api.py` e `tests/test_frontend_inputs.py` para pesos comuns (250g, 500g, 1000g, 1001g).""",
        "comment": "Resolvido no commit 86ad9aa e verificado na suíte de testes pytest."
    },
    {
        "number": 2,
        "title": "Cadastrar filamento: preço do carretel só aceita inteiros e bloqueia centavos (ex: 56,50)",
        "labels": ["bug", "financial", "frontend"],
        "body": """### Descrição do Problema
O cadastro do filamento não aceitava valores com centavos (ex: R$ 56,50), forçando o preenchimento de números inteiros. Como se trata de precificação financeira, valores fracionários são fundamentais para o cálculo exato do custo por grama.

### Causa Raiz
O input HTML continha `step="1"` (padrão de `<input type="number">`), bloqueando decimais. Além disso, a inserção com vírgula ou no formato monetário brasileiro `56,50` ou `R$ 56,50` falhava no navegador.

### Solução Implementada
1. No HTML `frontend/index.html`, atualizado `filament-price` para `step="any"`.
2. No JavaScript `frontend/js/app.js`:
   - Implementada função `parseLocaleFloat` com suporte completo a moeda brasileira (`R$ 56,50`, `56,50`, `1.200,50`) e internacional (`56.50`).
   - Adicionado listener global `paste` com parsing monetário.
3. No backend, schema e banco utilizam `float` com precisão adequada para centavos e custo por grama com alta precisão decimal.
4. Coberto por testes unitários e de integração em `tests/test_api.py` e `tests/test_frontend_inputs.py`.""",
        "comment": "Resolvido no commit 86ad9aa e verificado na suíte de testes pytest."
    },
    {
        "number": 3,
        "title": "Cadastrar impressora: vida útil em horas rejeita valores redondos (5000h)",
        "labels": ["bug", "printers", "frontend"],
        "body": """### Descrição do Problema
Ao cadastrar uma impressora 3D, o campo de vida útil estimada em horas rejeitava o valor padrão recomendado de 5000h (e outros valores redondos como 3000h), aceitando apenas valores com step mismatch (ex: 5001h, 3001h).

### Causa Raiz
O campo `<input type="number" id="printer-lifespan">` possuía `step="100"` combinado com `min="1"`. Como `(5000 - 1) % 100 = 99 != 0`, o valor 5000h gerava `stepMismatch`, enquanto valores incomuns como 5001h eram aceitos.

### Solução Implementada
1. Alterado `step="any"` e `min="1"` em `frontend/index.html`.
2. Implementado `parseLocaleFloat` com fallback seguro para `5000` em `handleSavePrinter`.
3. Verificado cálculo de taxa horária de depreciação `acquisition_cost / lifespan_hours` com valores decimais e redondos no motor de custos (`backend/engine.py`).
4. Coberto por testes em `tests/test_api.py` e `tests/test_frontend_inputs.py`.""",
        "comment": "Resolvido no commit 86ad9aa e verificado na suíte de testes pytest."
    },
    {
        "number": 4,
        "title": "Input numérico decimal: digitação de vírgula limpa o valor no navegador",
        "labels": ["bug", "frontend", "ux"],
        "body": """### Descrição do Problema
Ao digitar uma vírgula em campos numéricos (`<input type="number">`), listeners anteriores tentavam concatenar `.` diretamente na propriedade `.value` (`target.value += '.'`). Em navegadores como Google Chrome e Microsoft Edge, atribuir uma string terminada em ponto (como `56.`) a um `input[type="number"]` viola o algoritmo de sanitização do padrão HTML5, resultando na limpeza imediata do campo (`value = ""`).

### Causa Raiz
No padrão HTML5, `input[type="number"].value` não aceita `.` sem dígitos subsequentes. A execução de fallback `target.value += '.'` nos listeners de `beforeinput` e `keydown` limpava o valor digitado pelo usuário.

### Solução Implementada
1. Implementada alternância dinâmica de modo de entrada: no evento `focusin`, o input transiciona para `type="text"` com `inputMode="decimal"`, permitindo digitação fluida de números, vírgula e ponto sem sanitização destrutiva do navegador.
2. No evento `focusout`, o valor é normalizado via `parseLocaleFloat` e o tipo é restaurado com segurança para `number`.
3. Adicionada função `normalizeNumericInputs()` chamada antes do salvamento de projetos, filamentos, impressoras e preferências.
4. Coberto por testes unitários e de navegador real em `tests/test_frontend_inputs.py`.""",
        "comment": "Resolvido e verificado com testes automatizados em headless Chrome e pytest."
    }
]

def get_github_token():
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        p = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            text=True,
            capture_output=True
        )
        for line in p.stdout.splitlines():
            if line.startswith("password="):
                return line[9:]
    except Exception as e:
        print(f"Warning: could not get credentials via git credential helper: {e}")
    return None

def api_request(url, method="GET", data=None, token=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Splendid-Hypatia-IssueSync/1.0"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def sync():
    token = get_github_token()
    if not token:
        print("ERRO: Token do GitHub não encontrado. Configure GITHUB_TOKEN ou autentique via git credential.")
        sys.exit(1)

    print(f"Sincronizando issues com o repositório {REPO}...")

    # Fetch existing issues
    try:
        existing_issues = api_request(f"{API_BASE}/issues?state=all", token=token)
    except urllib.error.HTTPError as e:
        print(f"Erro ao listar issues: {e.code} {e.reason}")
        print(e.read().decode("utf-8"))
        sys.exit(1)

    existing_by_num = {i["number"]: i for i in existing_issues}

    for item in ISSUES_DEF:
        num = item["number"]
        if num in existing_by_num:
            # Update issue
            print(f"Atualizando Issue #{num}: {item['title']}...")
            patch_data = {
                "title": item["title"],
                "body": item["body"],
                "labels": item["labels"],
                "state": "closed",
                "state_reason": "completed"
            }
            updated = api_request(f"{API_BASE}/issues/{num}", method="PATCH", data=patch_data, token=token)
            print(f"  -> Issue #{num} atualizada e fechada como resolvida: {updated['html_url']}")
        else:
            # Create issue
            print(f"Criando Issue: {item['title']}...")
            post_data = {
                "title": item["title"],
                "body": item["body"],
                "labels": item["labels"]
            }
            created = api_request(f"{API_BASE}/issues", method="POST", data=post_data, token=token)
            created_num = created["number"]
            print(f"  -> Issue #{created_num} criada: {created['html_url']}")

            # Close issue as completed
            close_data = {
                "state": "closed",
                "state_reason": "completed"
            }
            api_request(f"{API_BASE}/issues/{created_num}", method="PATCH", data=close_data, token=token)

            # Add comment
            comment_data = {
                "body": f"✅ **Resolvido**: {item['comment']}"
            }
            api_request(f"{API_BASE}/issues/{created_num}/comments", method="POST", data=comment_data, token=token)
            print(f"  -> Issue #{created_num} fechada como resolvida com sucesso!")

    print("\nTodas as 4 issues foram sincronizadas e marcadas como resolvidas no GitHub!")

if __name__ == "__main__":
    sync()
