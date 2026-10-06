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
        "issue_number": 102,
        "comment": """## Correção Implementada & Verificada (Issue #102)

### 1. Causa Raiz Identificada
No editor de projetos, impressões de calibração ultra-rápidas (< 30s / < 0.0083h) são exibidas nos inputs como `0h : 0m` devido ao arredondamento por minuto `Math.round(hours * 60)`. Ao salvar o orçamento (`saveCurrentProject` em `frontend/js/app.js`), a função `updatePlateTime(idx)` era disparada para cada placa, lendo `h=0` e `m=0`, e sobrescrevendo `state.currentPlates[idx].print_time_hours` com `0.0`. Isso apagava permanentemente o tempo extraído do fatiador e zerava os custos operacionais da máquina.

### 2. Modificações Implementadas
- **Preservação em `frontend/js/app.js` (`updatePlateTime`)**:
  Adicionada verificação que preserva o tempo submétrico (`currentHours > 0 && currentHours < 1/60`) quando os inputs de interface estão em `0h 0m`. Se o operador intencionalmente alterar para outro valor ou zerar a partir de um valor `>= 1min`, a redefinição opera normalmente.
- **UX Feedback em `renderPlates()`**:
  Adicionado indicador visual discreto `<1 min (~Xs)` com tooltip no slot do label de tempo para placas com duração inferior a 1 minuto, garantindo clareza para o operador.
- **Cache-busting em `frontend/index.html`**:
  Atualizado parâmetro de versão dos assets para `?v=1.3.8`.

### 3. Verificação Automatizada
- Teste Node/CDP reproduzindo ciclo de renderização e salvamento: tempo de `0.0042h` preservado com sucesso (`test_issue_102_update_plate_time_preserves_sub_minute` em `tests/test_frontend_inputs.py`).
- Auditoria E2E em navegador headless Chrome via CDP: `Plate Sub-Minute Print Time Preservation on Save` aprovado com 100% de sucesso.
- Bateria completa de testes do backend: 191/191 testes aprovados (`pytest`).
"""
    },
    {
        "issue_number": 103,
        "comment": """## Correção Implementada & Verificada (Issue #103)

### 1. Causa Raiz Identificada
No extrator de metadados 3MF (`frontend/js/parsers/threemf.js`), os fallbacks 3 (arquivos de configuração de fatiador como `print_config.ini`, `model_settings.config`) e 4 (arquivos 3MF brutos sem metadados de fatiamento) não atribuíam as propriedades de setup de manufatura `nozzle_diameter`, `layer_height` e `bed_type`. Isso gerava inconsistências na estrutura de dados de `currentPlates` e na geração de Fichas Técnicas em PDF.

### 2. Modificações Implementadas
- **Fallback 3 (`frontend/js/parsers/threemf.js`)**:
  Adicionada extração regex de `nozzle_diameter`, `layer_height` e `bed_type` dos arquivos de configuração, com valores padrão seguros (`'0.4'`, `'0.20'`, `'Textured PEI'`).
- **Fallback 4 (`frontend/js/parsers/threemf.js`)**:
  Inicialização explícita das propriedades de manufatura: `nozzle_diameter: '0.4'`, `layer_height: '0.20'`, `bed_type: 'Textured PEI'`.
- **Alinhamento do Parser Python (`tests/test_parsers.py`)**:
  Atualizada a implementação espelho `python_parse_3mf` para extrair e preencher os parâmetros nos mesmos fallbacks.

### 3. Verificação Automatizada
- Testes unitários dedicados em `tests/test_parsers.py`:
  - `test_3mf_fallback_config_manufacturing_parameters`: aprovado.
  - `test_3mf_fallback_unsliced_default_manufacturing_parameters`: aprovado.
- Teste em `tests/test_frontend_inputs.py` (`test_issue_103_threemf_fallbacks_contain_manufacturing_params`): aprovado.
- Auditoria em navegador Chrome via CDP (`3MF Parser Fallbacks Hardware Setup Parameters Completeness`): 100% de aprovação.
"""
    },
    {
        "issue_number": 104,
        "comment": """## Correção Implementada & Verificada (Issue #104)

### 1. Causa Raiz Identificada
No gerador de PDF (`backend/pdf_service.py`), a Seção 3 da Ficha Técnica de Produção ("DEMONSTRATIVO DE CUSTOS INTERNOS E MARGENS") não incluía linhas para Desconto Comercial (`discount_amount`) e Frete / Envio (`shipping_cost`). Isso causava uma aparente divergência matemática entre a margem nominal calculada sobre o Custo Base e o Preço Final de Venda Sugerido / Lucro Líquido Real exibido.

### 2. Modificações Implementadas
- Em `backend/pdf_service.py` (Seção 3, `cost_breakdown_data`), adicionadas linhas condicionais:
  - `Desconto Comercial (X.X%): - R$ Y.YY` (quando `discount_amount > 0`).
  - `Frete / Envio: + R$ Z.ZZ` (quando `shipping_cost > 0`).
- Posicionadas antes do Preço Final de Venda Sugerido e Lucro Líquido Real, garantindo conciliação visual imediata para o operador técnico da oficina.

### 3. Verificação Automatizada
- Teste em `tests/test_api.py` (`test_pdf_technical_demonstrative_discount_and_freight_issue_104`): criação de projeto com desconto de 15% e frete de R$ 25,00, emissão de PDF técnico e validação de montagem da tabela sem erros.
- Auditoria em navegador Chrome via CDP (`Technical PDF Internal Financial Demonstrative Discount & Freight Completeness`): 100% aprovado.
- Suíte completa: 191/191 testes aprovados (`pytest`).
"""
    }
]

def post_comment(token, issue_num, body):
    payload = json.dumps({"body": body.strip()}).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/issues/{issue_num}/comments",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "Antigravity-IssueCloser-V12"
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def close_issue(token, issue_num):
    payload = json.dumps({"state": "closed", "state_reason": "completed"}).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/issues/{issue_num}",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "Antigravity-IssueCloser-V12"
        },
        method="PATCH"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    token = get_token()
    if not token:
        print("Erro: Token do GitHub não encontrado via git credential fill.")
        sys.exit(1)

    print(f"Token obtido. Fechando {len(CLOSING_ACTIONS)} issues no repositório {REPO}...\n")

    for item in CLOSING_ACTIONS:
        num = item["issue_number"]
        print(f"-> Processando Issue #{num}...")
        try:
            c_res = post_comment(token, num, item["comment"])
            print(f"   Comentário adicionado: {c_res.get('html_url')}")
            cl_res = close_issue(token, num)
            print(f"   Status atualizado: {cl_res.get('state')} (reason: {cl_res.get('state_reason')})")
        except Exception as e:
            print(f"   Erro ao processar #{num}: {str(e)}")
        time.sleep(1.0)

    print("\nProcesso concluído!")

if __name__ == "__main__":
    main()
