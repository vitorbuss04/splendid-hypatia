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
        "issue_number": 109,
        "comment": """## Correção Implementada & Verificada (Issue #109)

### 1. Causa Raiz Identificada
Na função `findBestMatchingFilament` (`frontend/js/app.js`), o fallback final retornava `filaments[0]` mesmo quando nenhum dos critérios de perfil, marca, cor ou material coincidia. Se o usuário importasse um arquivo 3MF ou G-Code com filamentos técnicos (ex: TPU, Nylon, ABS) não cadastrados no estoque, o sistema forçava o primeiro filamento (ex: PLA), precificando e calculando densidade erroneamente. Além disso, em `handleSinglePlateFile`, faltava o bloco `else` para desassociar filamentos pré-existentes quando nenhum filamento correspondente era encontrado.

### 2. Modificações Implementadas
- **Retorno Estrito em `findBestMatchingFilament` (`frontend/js/app.js`)**:
  Alterado o fallback para retornar explicitamente `null` quando não houver qualquer correspondência válida no estoque.
- **Tratamento de Fallback em `handleSinglePlateFile` (`frontend/js/app.js`)**:
  Adicionado bloco `else` tanto no processamento de 3MF quanto de G-Code, definindo `plate.filament_id = null` e atribuindo custo manual padrão (`custom_filament_cost_per_g = 0.10`), mantendo a integridade de cálculo da oficina e compatibilidade com `handleSlicerFiles`.

### 3. Verificação Automatizada
- Teste Node/JS `test_issue_109_find_best_matching_filament_returns_null_when_unmatched` em `tests/test_frontend_inputs.py`.
- 199/199 testes aprovados na suíte de testes (`pytest`).
"""
    },
    {
        "issue_number": 110,
        "comment": """## Correção Implementada & Verificada (Issue #110)

### 1. Causa Raiz Identificada
Apesar do campo `plate.notes` estar presente no modelo de dados (`Plate` em `backend/models.py`) e nos endpoints da API, ele não possuía campo de entrada na interface do editor de orçamentos (`renderPlates()` em `frontend/js/app.js`), e era completamente omitido na tabela de parâmetros operacionais da Ficha Técnica de Produção em PDF (`backend/pdf_service.py`).

### 2. Modificações Implementadas
- **Input no Card da Placa (`frontend/js/app.js`)**:
  Adicionado campo estilizado de entrada de texto "Observações / Instruções de Impressão" em `renderPlates()`, com data-binding reativo bidirecional para `state.currentPlates[idx].notes`.
- **Exibição na Ficha Técnica de Produção em PDF (`backend/pdf_service.py`)**:
  Na coluna de especificações de manufatura da tabela de placas, incluída a exibição sanitizada com `html.escape` das anotações operacionais da placa (`Obs: ...`).

### 3. Verificação Automatizada
- Teste unitário e de PDF `test_issue_110_pdf_technical_renders_plate_notes` em `tests/test_api.py`.
- Teste de frontend `test_issue_110_plate_notes_input_in_render_plates` em `tests/test_frontend_inputs.py`.
- 199/199 testes aprovados na suíte de testes (`pytest`).
"""
    },
    {
        "issue_number": 111,
        "comment": """## Correção Implementada & Verificada (Issue #111)

### 1. Causa Raiz Identificada
O endpoint `POST /api/projects/{id}/duplicate` em `backend/routes/project_routes.py` omitia o parâmetro `status_code=status.HTTP_201_CREATED`, retornando `HTTP 200 OK`. Isso divergia do padrão REST adotado nos endpoints de duplicação de impressoras (`POST /api/printers/{id}/duplicate`) e filamentos (`POST /api/filaments/{id}/duplicate`), que retornam `HTTP 201 Created`.

### 2. Modificações Implementadas
- **Padronização RESTful em `backend/routes/project_routes.py`**:
  Declarado explicitamente `status_code=status.HTTP_201_CREATED` no decorator de rota `@router.post("/{project_id}/duplicate")`.
- **Alinhamento da Suíte de Testes**:
  Atualizadas as asserções de clonagem de projetos em `tests/test_api.py` para validar `201 Created`.

### 3. Verificação Automatizada
- Teste de contrato `test_issue_111_duplicate_project_status_code_201_created` em `tests/test_api.py`.
- 199/199 testes aprovados na suíte de testes (`pytest`).
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
