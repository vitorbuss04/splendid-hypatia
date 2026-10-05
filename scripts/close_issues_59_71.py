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
    59: {
        "comment": """### ✅ Resolução - Issue #59

**Causa Raiz**:
Em `frontend/js/app.js` (`renderFilamentsGrid`), o valor de `f.color_hex` era interpolado diretamente sem sanitização nos atributos de estilo `style="background-color: ${f.color_hex}..."` dos previews dos cards de filamento. Além disso, os esquemas do backend aceitavam strings arbitrárias sem validação de padrão hexadecimal.

**Correção Implementada**:
- **Backend**: Em `backend/schemas.py`, adicionada validação de regex pattern `^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3}|[A-Fa-f0-9]{8})$` em `FilamentBase`, `FilamentUpdate` e `FilamentDuplicate`.
- **Frontend**: Em `frontend/js/app.js`, adicionada sanitização defensiva via regex (`safeHex = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3}|[A-Fa-f0-9]{8})$/.test(f.color_hex || '') ? f.color_hex : '#10b981'`) antes de qualquer interpolação em atributos CSS `style=""`.

**Verificação**:
- Teste backend `test_issue_59_color_hex_pattern_validation` em `tests/test_api.py`.
- Teste frontend em `tests/test_frontend_inputs.py::test_issues_59_through_71_frontend_verification`.
- 176/176 testes passando com sucesso.""",
    },
    60: {
        "comment": """### ✅ Resolução - Issue #60

**Causa Raiz**:
Nas tabelas de projetos recentes e listagem geral (`renderRecentProjects` e `renderProjectsTable`), a classe de badge `badge-${p.status}` e o texto de status formatado eram interpolados no template sem escape de entidades HTML, expondo o front-end a injeções caso valores não sanitizados fossem salvos no banco.

**Correção Implementada**:
- **Backend**: Em `backend/schemas.py`, adicionado padrão restritivo de validação regex `^(draft|quoted|approved|in_production|completed|cancelled)$` nos campos `status` de `ProjectBase` e `ProjectUpdate`.
- **Frontend**: Em `frontend/js/app.js`, aplicado `escapeHtml(p.status || 'draft')` e `escapeHtml(formatStatus(p.status))` em todas as renderizações de badge de projeto.

**Verificação**:
- Teste backend `test_issue_60_project_status_pattern_validation` em `tests/test_api.py`.
- Teste frontend em `tests/test_frontend_inputs.py::test_issues_59_through_71_frontend_verification`.
- 176/176 testes passando com sucesso.""",
    },
    61: {
        "comment": """### ✅ Resolução - Issue #61

**Causa Raiz**:
Os schemas Pydantic de Impressoras, Filamentos e Projetos permitiam strings contendo exclusivamente espaços em branco (`"   "`) ou caracteres de quebra de linha/tabulação, criando entidades anônimas no banco de dados.

**Correção Implementada**:
- Em `backend/schemas.py`, adicionado `Field(..., min_length=1)` e `@field_validator("name")` com método `validate_name_not_blank` em `PrinterBase`, `PrinterUpdate`, `FilamentBase`, `FilamentUpdate`, `ProjectBase` e `ProjectUpdate`, rejeitando valores vazios ou contendo apenas espaços e realizando `.strip()` no retorno.

**Verificação**:
- Teste backend `test_issue_61_empty_whitespace_name_rejected` em `tests/test_api.py` cobrindo impressoras, filamentos e projetos.
- 176/176 testes passando com sucesso.""",
    },
    62: {
        "comment": """### ✅ Resolução - Issue #62

**Causa Raiz**:
No endpoint `/api/projects/dashboard-stats`, a lista de projetos do ranking Top Projetos (`project_items`) acumulava projetos com status `draft` e `quoted` indistintamente, distorcendo o faturamento realizado no gráfico 4.

**Correção Implementada**:
- Em `backend/routes/project_routes.py`, a inclusão em `project_items.append(...)` foi condicionada estritamente à flag `if is_realized:`, onde `is_realized = st in ["approved", "in_production", "completed"]`.

**Verificação**:
- Teste backend `test_issue_62_and_71_dashboard_stats_realized_projects_filtering` em `tests/test_api.py`.
- 176/176 testes passando com sucesso.""",
    },
    63: {
        "comment": """### ✅ Resolução - Issue #63

**Causa Raiz**:
No modal de cadastro/edição de impressoras, não existia controle para o campo `is_active`. Como consequência, impressoras não podiam ser marcadas como inativas/em manutenção e o filtro `printer-status-filter` da barra de ferramentas não tinha efeito funcional.

**Correção Implementada**:
- **Interface**: Adicionado `<select id="printer-active">` em `#form-printer` em `frontend/index.html`.
- **Controle**: Em `frontend/js/app.js`, `openPrinterModal` popula o select de acordo com `printer.is_active` e `handleSavePrinter` envia `payload.is_active = activeEl.value !== 'false'`.
- **Visualização**: Cards de impressoras agora exibem badge de status 'Ativa' ou 'Inativa'.

**Verificação**:
- Teste frontend em `tests/test_frontend_inputs.py::test_issues_59_through_71_frontend_verification`.
- 176/176 testes passando com sucesso.""",
    },
    64: {
        "comment": """### ✅ Resolução - Issue #64

**Causa Raiz**:
Faltava a funcionalidade de duplicar impressoras cadastradas tanto no backend quanto no frontend, exigindo digitação manual de todos os parâmetros operacionais (depreciação, potência, manutenção, tarifas) para máquinas semelhantes.

**Correção Implementada**:
- **Backend**: Criado endpoint `POST /api/printers/{printer_id}/duplicate` em `backend/routes/printer_routes.py`, clonando todas as especificações operacionais com sufixo `(Cópia)`.
- **API Client**: Adicionado método `duplicate: (id) => API.request(...)` em `frontend/js/api.js`.
- **Frontend**: Adicionado botão de duplicar em cada card de impressora e exposta função global `duplicatePrinter(id)` em `frontend/js/app.js`.

**Verificação**:
- Teste backend `test_issue_64_printer_duplication_endpoint` em `tests/test_api.py`.
- Teste frontend em `tests/test_frontend_inputs.py::test_issues_59_through_71_frontend_verification`.
- 176/176 testes passando com sucesso.""",
    },
    65: {
        "comment": """### ✅ Resolução - Issue #65

**Causa Raiz**:
Os schemas `PlateBase` e `PlateUpdate` não impunham restrição de valor mínimo não-negativo nos campos manuais `custom_printer_hourly_rate` e `custom_filament_cost_per_g`.

**Correção Implementada**:
- Em `backend/schemas.py`, configurado `Field(None, ge=0)` para `custom_printer_hourly_rate` e `custom_filament_cost_per_g` em ambos os schemas, rejeitando requisições com taxas ou custos negativos (HTTP 422).

**Verificação**:
- Teste backend `test_issue_65_plate_negative_custom_rates_rejected` em `tests/test_api.py`.
- 176/176 testes passando com sucesso.""",
    },
    66: {
        "comment": """### ✅ Resolução - Issue #66

**Causa Raiz**:
No parser 3MF (`frontend/js/parsers/threemf.js`), a variável `purgeGrams` era calculada via atributos de flush/purge dos filamentos, mas ao montar o objeto da placa em `plates.push(...)`, o campo `purge_weight_g` estava fixo como `0.0`.

**Correção Implementada**:
- Em `frontend/js/parsers/threemf.js`, definido `purge_weight_g: parseFloat(purgeGrams.toFixed(2))` e recalculado `part_weight_g` para refletir o peso líquido da peça (`totalWeight = weightGrams - purgeGrams` quando aplicável).

**Verificação**:
- Teste frontend em `tests/test_frontend_inputs.py::test_issues_59_through_71_frontend_verification`.
- 176/176 testes passando com sucesso.""",
    },
    67: {
        "comment": """### ✅ Resolução - Issue #67

**Causa Raiz**:
No motor de cálculo de custos (`calculate_plate_cost` em `backend/engine.py`), caso a placa não tivesse impressora ou filamento vinculado (`printer_id=None`, `filament_id=None`) e as taxas manuais não estivessem explicitadas, as tarifas eram zeradas (`0.0`), resultando em orçamento com custo zero de material e máquina.

**Correção Implementada**:
- Em `backend/engine.py`, atualizados os fallbacks do motor: se `filament` e taxa manual forem nulos, adota `0.10` R$/g (equivalente a R$ 100/kg padrão); se `printer` e taxa manual forem nulos, adota `2.50` R$/h padrão da oficina.

**Verificação**:
- Teste backend `test_issue_67_engine_plate_cost_fallback_when_printer_and_filament_none` em `tests/test_api.py`.
- 176/176 testes passando com sucesso.""",
    },
    68: {
        "comment": """### ✅ Resolução - Issue #68

**Causa Raiz**:
Ao limpar o campo de prazo de entrega (`#proj-delivery-days`) no editor de projeto e salvar, a função `saveCurrentProject` aplicava `parseInt(...) || 3`, forçando o valor 3 no payload mesmo quando o usuário intencionalmente desejava prazo nulo/em aberto. Além disso, ao abrir um projeto com prazo nulo, o editor restaurava 3.

**Correção Implementada**:
- Em `frontend/js/app.js`, `saveCurrentProject` verifica se o input está vazio e retorna `null` para `delivery_days`.
- Na função de carregamento do editor (`openProject`), definido `document.getElementById('proj-delivery-days').value = proj.delivery_days != null ? proj.delivery_days : ''`.

**Verificação**:
- Teste frontend em `tests/test_frontend_inputs.py::test_issues_59_through_71_frontend_verification`.
- 176/176 testes passando com sucesso.""",
    },
    69: {
        "comment": """### ✅ Resolução - Issue #69

**Causa Raiz**:
Não existia controle de status operacional (`is_active`) na interface de filamentos, impossibilitando desativar ou arquivar carretéis esgotados sem excluí-los do histórico.

**Correção Implementada**:
- **Interface**: Adicionado `<select id="filament-active">` em `#form-filament` e `<select id="filament-status-filter">` na toolbar de filamentos em `frontend/index.html`.
- **Controle**: Em `frontend/js/app.js`, `openFilamentModal` carrega o status, `handleSaveFilament` persiste `is_active` e `filterFilaments` suporta filtro por ativas/inativas.
- **Visualização**: Adicionado badge de status 'Ativo' ou 'Inativo' em cada card de filamento.

**Verificação**:
- Teste frontend em `tests/test_frontend_inputs.py::test_issues_59_through_71_frontend_verification`.
- 176/176 testes passando com sucesso.""",
    },
    70: {
        "comment": """### ✅ Resolução - Issue #70

**Causa Raiz**:
Faltavam parâmetros de fabricação física por placa (`nozzle_diameter`, `bed_type`, `layer_height`), essenciais para a ordem de produção técnica da oficina de impressão 3D.

**Correção Implementada**:
- **Banco de Dados**: Adicionadas colunas `nozzle_diameter`, `bed_type` e `layer_height` no modelo `Plate` em `backend/models.py`.
- **Schemas**: Adicionados campos opcionais em `PlateBase` e `PlateUpdate` em `backend/schemas.py`.
- **PDF Técnico**: Atualizada a tabela de parâmetros operacionais de produção em `backend/pdf_service.py` com coluna dedicada de setup de fabricação (Bico / Camada / Mesa).
- **Frontend**: Campos de setup de fabricação adicionados ao card de placa em `renderPlates`, inicializados em `createDefaultPlate` e persistidos em `saveCurrentProject`.

**Verificação**:
- Teste backend `test_issue_70_plate_manufacturing_parameters_and_technical_pdf` em `tests/test_api.py`.
- Teste frontend em `tests/test_frontend_inputs.py::test_issues_59_through_71_frontend_verification`.
- 176/176 testes passando com sucesso.""",
    },
    71: {
        "comment": """### ✅ Resolução - Issue #71

**Causa Raiz**:
No cálculo da timeline mensal do dashboard (`backend/routes/project_routes.py`), as horas de impressão (`print_hours`) eram acumuladas independentemente do status do projeto, somando horas de projetos em rascunho (`draft`) e orçados (`quoted`) na capacidade produtiva mensal realizada.

**Correção Implementada**:
- Em `backend/routes/project_routes.py`, a acumulação mensal de horas foi ajustada para: `monthly_data[month_key]["print_hours"] = round(monthly_data[month_key]["print_hours"] + (hours if is_realized else 0.0), 2)`, computando apenas projetos aprovados, em produção ou concluídos.

**Verificação**:
- Teste backend `test_issue_62_and_71_dashboard_stats_realized_projects_filtering` em `tests/test_api.py`.
- 176/176 testes passando com sucesso.""",
    }
}

def main():
    token = get_token()
    if not token:
        print("Erro: token do GitHub não encontrado.")
        sys.exit(1)

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "splendid-hypatia-resolver"
    }

    for issue_num, data in RESOLUTIONS.items():
        print(f"Processando Issue #{issue_num}...")
        # 1. Post comment
        comment_url = f"{API_BASE}/issues/{issue_num}/comments"
        comment_payload = json.dumps({"body": data["comment"]}).encode("utf-8")
        req = urllib.request.Request(comment_url, data=comment_payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as resp:
                print(f"  Comentário adicionado na Issue #{issue_num} (HTTP {resp.status})")
        except Exception as e:
            print(f"  Erro ao comentar na Issue #{issue_num}: {e}")

        # 2. Close issue
        issue_url = f"{API_BASE}/issues/{issue_num}"
        close_payload = json.dumps({"state": "closed", "state_reason": "completed"}).encode("utf-8")
        req = urllib.request.Request(issue_url, data=close_payload, headers=headers, method="PATCH")
        try:
            with urllib.request.urlopen(req) as resp:
                print(f"  Issue #{issue_num} fechada com sucesso! (HTTP {resp.status})")
        except Exception as e:
            print(f"  Erro ao fechar Issue #{issue_num}: {e}")

if __name__ == "__main__":
    main()
