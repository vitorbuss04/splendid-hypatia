import subprocess
import urllib.request
import json
import sys

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

RESOLUTIONS = {
    28: {
        "comment": """### ✅ Resolução - Issue #28

**Causa Raiz**:
O frontend calculava as etapas comerciais intermediárias (`suggestedPrice`, `discountAmount`, `subtotalAfterDiscount`, `taxAmount`, `netRevenue`, `netProfit`, `finalPriceToClient`) acumulando floats sem truncamento ou arredondamento para 2 casas decimais, enquanto o backend (`backend/engine.py`) arredonda a cada etapa com `round(..., 2)`. Em combinações fracionárias de margem, imposto e desconto, isso produzia uma discrepância visual de R$ 0,01 entre a interface em tempo real e a proposta final salva/impressa.

**Correção Implementada**:
- No arquivo `frontend/js/app.js` (função `recalcLiveSummary`):
  - Todas as etapas comerciais foram alinhadas para arredondamento a 2 casas decimais com `Math.round(val * 100) / 100`.
  - As somas de custos base por placa foram mantidas contínuas para preservação de precisão cumulativa.

**Verificação**:
- Teste empírico em `tests/test_recalc_live_summary_empirical.js` (19/19 passaram).
- Teste unitário em `tests/test_frontend_inputs.py::test_recalc_live_summary_commercial_rounding_precision` passou com paridade exata aos valores da engine.
- Auditoria E2E via CDP no navegador sem divergências.""",
    },
    29: {
        "comment": """### ✅ Resolução - Issue #29

**Causa Raiz**:
A renderização dinâmica de `p.name` e `p.client_name` nas tabelas de projetos recentes (`renderRecentProjects`) e listagem geral de projetos (`renderProjectsTable`) interpolava strings diretamente nos templates HTML sem sanitização de entidades (`<`, `>`, `&`, `"`, `'`), abrindo brecha para Stored XSS e quebra de layout quando nomes de peças continham caracteres especiais como `<V2>` ou tags de script.

**Correção Implementada**:
- Implementada a função utilitária `escapeHtml(str)` em `frontend/js/app.js`.
- Aplicada a sanitização a:
  - `p.name` e `p.client_name` em `renderRecentProjects()`
  - `p.name` e `p.client_name` em `renderProjectsTable()`
  - Mensagem de filtro de busca vazio no catálogo de projetos

**Verificação**:
- Teste unitário em `tests/test_frontend_inputs.py::test_escape_html_xss_protection_in_projects` validando escape estrito de tags `<script>` e `<V2>`.
- Auditoria de segurança via navegador validando ausência de execução de scripts arbitrários.""",
    },
    30: {
        "comment": """### ✅ Resolução - Issue #30

**Causa Raiz**:
Ao importar um arquivo G-Code individual para uma placa (`handleSinglePlateFile` em `frontend/js/app.js`), o parser de G-Code não extrai purge tower (já que G-Code padrão não contém metadados de torre de purga multicolor). Se a placa continha previamente dados de um projeto 3MF com purge tower, o valor de `purge_weight_g` permanecia no objeto de estado da placa, inflando o custo de filamento e o preço final indevidamente.

**Correção Implementada**:
- No manipulador de arquivo `.gcode` em `handleSinglePlateFile()` (`frontend/js/app.js`):
  - Adicionado reset explícito: `state.currentPlates[plateIdx].purge_weight_g = 0;`.

**Verificação**:
- Teste unitário em `tests/test_frontend_inputs.py::test_gcode_import_resets_residual_purge_weight` confirmando zeramento imediato da purga residual ao importar G-code em placa pré-populada com 3MF.""",
    },
    31: {
        "comment": """### ✅ Resolução - Issue #31

**Causa Raiz**:
A função `formatPhoneInput()` em `frontend/js/app.js` formatava apenas com base nos primeiros 10 ou 11 dígitos. Ao colar ou digitar números com o código de país DDI (`+55` ou `55`), o prefixo 55 era tratado erroneamente como código de área (DDD 55 - Santa Maria/RS), empurrando os dígitos reais do telefone e truncando os últimos dígitos.

**Correção Implementada**:
- Em `frontend/js/app.js` (`formatPhoneInput`):
  - Adicionada detecção e remoção automática do prefixo DDI `55` quando a contagem total de dígitos for 12 ou 13 dígitos:
  ```javascript
  if ((v.length === 12 || v.length === 13) && v.startsWith('55')) {
      v = v.slice(2);
  }
  ```

**Verificação**:
- Testes unitários cobrindo números colados com `+55 (11) 98765-4321` e `5547999887766` passando 100% em `tests/test_frontend_inputs.py::test_phone_formatting_handles_ddi_prefix`.""",
    },
    32: {
        "comment": """### ✅ Resolução - Issue #32

**Causa Raiz**:
Nas funções `duplicateProject()` e `deleteProject()` em `frontend/js/app.js`, após a chamada à API de mutação e re-carregamento dos dados com `loadAllData()`, apenas `renderProjectsTable()` era invocada. Caso a ação fosse disparada a partir do Dashboard ou caso o usuário retornasse ao Dashboard, os cards e a tabela de projetos recentes permaneciam com o estado desatualizado em cache até um refresh manual da página (F5).

**Correção Implementada**:
- Em `frontend/js/app.js`:
  - Adicionada invocação a `renderRecentProjects()` em `duplicateProject()` e `deleteProject()`.
  - Adicionada checagem: `if (state.activeView === 'dashboard') { renderDashboard(); }` para re-renderizar métricas e gráficos imediatamente.

**Verificação**:
- Teste unitário em `tests/test_frontend_inputs.py::test_duplicate_and_delete_project_refreshes_dashboard` validando a atualização do dashboard e projetos recentes em ambas as operações.""",
    },
    33: {
        "comment": """### ✅ Resolução - Issue #33

**Causa Raiz**:
Nas rotas de criação e atualização de projetos e placas (`backend/routes/project_routes.py`), os campos `printer_id` e `filament_id` de cada placa eram atribuídos sem validação de tenant (`user_id`). Um usuário autenticado podia enviar um payload JSON referenciando `printer_id` ou `filament_id` de outro usuário, visualizando indiretamente custos de insumos de concorrentes ou violando o isolamento de dados.

**Correção Implementada**:
- Implementada a função de sanitização de chaves estrangeiras `sanitize_plate_foreign_keys(plate_dict, user_id, db)` em `backend/routes/project_routes.py`:
  - Valida se `printer_id` e `filament_id` pertencem ao `user_id` autenticado.
  - Caso pertençam a outro usuário ou não existam, reseta o ID com segurança para `None` e utiliza as taxas horárias e de material padrão do sistema para o cálculo.
- Sanitização aplicada uniformemente em:
  - `create_project`
  - `update_project`
  - `duplicate_project`
  - `add_plate`
  - `update_plate`

**Verificação**:
- Teste de integração de segurança em `tests/test_api.py::test_plate_cross_tenant_idor_prevention` validando a mitigação completa da injeção de IDOR.""",
    },
    34: {
        "comment": """### ✅ Resolução - Issue #34

**Causa Raiz**:
Ao salvar ou atualizar um projeto que continha placas referenciando uma impressora ou filamento que foi posteriormente excluído pelo usuário, a foreign key `printer_id` ou `filament_id` tentava ser persistida ou consultada contra o banco relacional, disparando `IntegrityError` / `HTTP 500 Internal Server Error`.

**Correção Implementada**:
- A função `sanitize_plate_foreign_keys` em `backend/routes/project_routes.py` verifica a existência da entidade no banco de dados. Caso o ID aponte para um registro que já não existe mais (excluído), o ID é sanitizado para `None` e o projeto é salvo com sucesso com os valores de fallback sem levantar exceção de integridade referencial.

**Verificação**:
- Teste de integração em `tests/test_api.py::test_project_update_with_deleted_printer_or_filament_no_crash` passando com sucesso (retorno 200 OK sem crash 500).""",
    },
    35: {
        "comment": """### ✅ Resolução - Issue #35

**Causa Raiz**:
Ao remover todas as placas no Editor de Orçamentos (`removePlateRow`), o container `#plates-container` ficava em branco sem nenhum feedback visual explicativo ou botão direto para adicionar nova placa, deixando o usuário sem ação óbvia e permitindo salvar orçamentos vazios sem aviso.

**Correção Implementada**:
- Em `frontend/js/app.js`:
  - Na função `renderPlates()`, caso `currentPlates.length === 0`, renderiza um estado vazio moderno com ícone, mensagem orientadora e botão de ação direta "Adicionar Placa".
  - Na função `saveCurrentProject()`, caso o orçamento possua 0 placas e 0 insumos adicionais, emite um toast de aviso orientador (`warning`): *"Orçamento salvo sem placas ou insumos configurados."*

**Verificação**:
- Teste unitário em `tests/test_frontend_inputs.py::test_render_plates_empty_state_and_warning` validando a exibição do estado visual vazio e o disparo do alerta orientador.""",
    },
}

def main():
    token = get_token()
    if not token:
        print("Erro: Token do GitHub não encontrado.")
        sys.exit(1)

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "splendid-hypatia-bot",
        "Content-Type": "application/json"
    }

    for issue_num, data in RESOLUTIONS.items():
        print(f"\nResolvendo Issue #{issue_num}...")
        
        # 1. Post resolution comment
        comment_url = f"{API_BASE}/issues/{issue_num}/comments"
        req_comment = urllib.request.Request(
            comment_url,
            data=json.dumps({"body": data["comment"]}).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        try:
            with urllib.request.urlopen(req_comment) as resp:
                print(f"  ✓ Comentário adicionado com sucesso na issue #{issue_num}")
        except Exception as e:
            print(f"  ✗ Erro ao adicionar comentário na issue #{issue_num}: {e}")

        # 2. Close issue
        patch_url = f"{API_BASE}/issues/{issue_num}"
        patch_data = json.dumps({"state": "closed", "state_reason": "completed"}).encode("utf-8")
        req_close = urllib.request.Request(
            patch_url,
            data=patch_data,
            headers=headers,
            method="PATCH"
        )
        try:
            with urllib.request.urlopen(req_close) as resp:
                print(f"  ✓ Issue #{issue_num} fechada com sucesso (state=closed)!")
        except Exception as e:
            print(f"  ✗ Erro ao fechar issue #{issue_num}: {e}")

if __name__ == "__main__":
    main()
