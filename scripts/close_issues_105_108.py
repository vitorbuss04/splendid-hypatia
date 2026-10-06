import subprocess
import urllib.request
import urllib.error
import json
import sys
import time

REPO = "vitorbuss04/splendid-hypatia"
API_BASE = f"https://api.github.com/repos/{REPO}"

def get_token():
    p = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        text=True,
        capture_output=True
    )
    for line in p.stdout.splitlines():
        if line.startswith("password="):
            return line[9:]
    return None

CLOSING_ACTIONS = [
    {
        "issue_number": 105,
        "comment": """## Correção Implementada & Verificada (Issue #105)

### 1. Causa Raiz Identificada
No motor de cálculo (`backend/engine.py`), `calculate_plate_cost` e `calculate_project_summary` aplicavam arredondamento direto para 2 casas decimais (`round(print_time_hours, 2)` e `round(total_time_hours, 2)`). Para peças de calibração ultra-rápidas ou testes de retração com duração inferior a 18 segundos (< 0.005h, ex: 15s = 0.0042h), o arredondamento retornava `0.0`. Além disso, o sumário financeiro do projeto somava os valores já truncados para `0.0`, retornando `total_print_time_hours: 0.0` no endpoint `/api/projects/{id}`.

### 2. Modificações Implementadas
- **Preservação de Precisão em `backend/engine.py` (`calculate_plate_cost`)**:
  Adicionada regra de fallback de precisão: se `print_time_hours > 0` e `round(print_time_hours, 2) == 0.0`, utiliza `round(print_time_hours, 4)` tanto para o tempo unitário (`unit_print_time_hours`) quanto para o tempo total da placa (`total_time_hours`).
- **Preservação em `backend/engine.py` (`calculate_project_summary`)**:
  Aplicado o mesmo fallback para `total_print_time_hours` no resumo financeiro do projeto, garantindo que o tempo total acumulado reflita exatamente a soma das durações sub-métricas sem truncamento prematuro.

### 3. Verificação Automatizada
- Teste unitário `test_issue_105_engine_preserves_sub_minute_print_hours` em `tests/test_api.py`.
- 195/195 testes aprovados na suíte de testes (`pytest`).
"""
    },
    {
        "issue_number": 106,
        "comment": """## Correção Implementada & Verificada (Issue #106)

### 1. Causa Raiz Identificada
Em `backend/pdf_service.py`, tanto a Proposta Comercial para clientes (`doc_type="client"`) quanto a Ficha Técnica de Produção (`doc_type="technical"`) utilizavam a formatação fixa `{hours:.1f} h` nas colunas de tempo das placas. Para qualquer peça de calibração rápida ou teste com duração inferior a 0.05h (3 minutos), o valor gerado era `0.0 h`, transmitindo a impressão equivocada de que o tempo de máquina não havia sido registrado.

### 2. Modificações Implementadas
- **Função Utilitária `format_pdf_hours` em `backend/pdf_service.py`**:
  Implementada lógica de formatação adaptativa para relatórios:
  - Se `hours <= 0`: `"0.0 h"`
  - Se `hours < 0.1` (menos de 6 minutos):
    - Se `round(hours * 60) < 1`: formato submétrico explícito `<1 min (~Xs)` (ex: `<1 min (~15s)`)
    - Caso contrário: minutos arredondados (`X min`, ex: `3 min`)
  - Se `hours >= 0.1`: formatação padrão `{hours:.1f} h`
- **Tabelas do PDF**:
  Substituída a interpolação direta por chamadas a `format_pdf_hours` na tabela de placas do cliente (linha 263) e nas colunas de tempo unitário e tempo total da Ficha Técnica (linhas 485 e 489).

### 3. Verificação Automatizada
- Teste unitário e de renderização de PDF `test_issue_106_pdf_format_hours_short_and_sub_minute_prints` em `tests/test_api.py`.
- 195/195 testes aprovados na suíte de testes (`pytest`).
"""
    },
    {
        "issue_number": 107,
        "comment": """## Correção Implementada & Verificada (Issue #107)

### 1. Causa Raiz Identificada
No extrator de metadados de G-Code (`frontend/js/parsers/gcode.js` e espelho Python `tests/test_parsers.py`), o bloco de correspondência de peso de filamento (`filament used [g]`) executava busca regex global de números na linha inteira. Em fatiadores que emitem identificadores com índices entre colchetes ou parênteses antes do separador de atribuição (ex: `; filament used [g] [1] = 45.2`, `; filament used [0] [g] = 30.0` ou `; filament used [g] (extruder 2) = 18.5`), o número do slot/extrusor era capturado e somado indevidamente à massa consumida.

### 2. Modificações Implementadas
- **Isolamento de Atribuição em `frontend/js/parsers/gcode.js`**:
  Identificação do último separador (`=` ou `:`) e extração de números exclusivamente a partir da porção posterior ao separador, descartando quaisquer números presentes nos identificadores de ferramenta/slot.
- **Espelho Python em `tests/test_parsers.py`**:
  Alinhada a mesma lógica de divisão por separador na função `python_parse_gcode`.

### 3. Verificação Automatizada
- Teste Python e Node.js `test_issue_107_gcode_filament_weight_ignores_prefix_indices` em `tests/test_parsers.py`.
- 195/195 testes aprovados na suíte de testes (`pytest`).
"""
    },
    {
        "issue_number": 108,
        "comment": """## Correção Implementada & Verificada (Issue #108)

### 1. Causa Raiz Identificada
Na função `recalcLiveSummary()` em `frontend/js/app.js`, o texto de resumo de cada placa (`plate-summary-text-${idx}`) e o KPI de tempo total na barra lateral (`live-time`) utilizavam `.toFixed(1)h`. Para impressões rápidas de teste (< 0.1h), os componentes exibiam `0.0h` e `0.0 h`, gerando divergência visual em relação à badge do input de tempo que exibia `<1 min (~Xs)`.

### 2. Modificações Implementadas
- **Harmonização Visual em `frontend/js/app.js` (`recalcLiveSummary`)**:
  - Resumo da placa: se `plateTotalTime > 0 && plateTotalTime < 0.1`, formata como `<1m (~Xs)` (para sub-minuto) ou `${min}min`.
  - KPI lateral: se `totalTimeHours > 0 && totalTimeHours < 0.1`, formata como `<1 min (~Xs)` ou `${min} min`.
- **Cache-Busting em `frontend/index.html`**:
  Incrementada a versão dos assets para `?v=1.3.9`.

### 3. Verificação Automatizada
- Teste automatizado `test_issue_108_recalc_live_summary_formats_sub_minute_and_short_times` em `tests/test_frontend_inputs.py`.
- 195/195 testes aprovados na suíte de testes (`pytest`).
"""
    }
]

def close_issues():
    token = get_token()
    if not token:
        print("ERROR: Could not retrieve GitHub token.")
        sys.exit(1)

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "SplendidHypatia-Closer"
    }

    for action in CLOSING_ACTIONS:
        num = action["issue_number"]
        comment_body = action["comment"]

        # 1. Post resolution comment
        comment_url = f"{API_BASE}/issues/{num}/comments"
        req = urllib.request.Request(
            comment_url,
            data=json.dumps({"body": comment_body}).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                print(f"Comment posted on Issue #{num}")
        except Exception as e:
            print(f"Error posting comment on Issue #{num}: {e}")

        # 2. Close the issue
        patch_url = f"{API_BASE}/issues/{num}"
        patch_req = urllib.request.Request(
            patch_url,
            data=json.dumps({"state": "closed"}).encode("utf-8"),
            headers=headers,
            method="PATCH"
        )
        try:
            with urllib.request.urlopen(patch_req) as resp:
                print(f"Issue #{num} closed successfully!")
        except Exception as e:
            print(f"Error closing Issue #{num}: {e}")

        time.sleep(1)

if __name__ == "__main__":
    close_issues()
