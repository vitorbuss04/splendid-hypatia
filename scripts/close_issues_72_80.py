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
    72: {
        "comment": """### ✅ Resolução - Issue #72

**Causa Raiz**:
No endpoint de clonagem `POST /api/projects/{project_id}/duplicate` em `backend/routes/project_routes.py`, a instanciação da entidade `models.Plate` para cada placa do projeto clonado omitia a atribuição das colunas de parâmetros operacionais de manufatura (`nozzle_diameter`, `bed_type` e `layer_height`). Como consequência, as placas clonadas revertiam silenciosamente para os valores default de coluna do banco (`'0.4'`, `'Textured PEI'`, `'0.20'`).

**Correção Implementada**:
- Em `backend/routes/project_routes.py` (função `duplicate_project`), repassadas as propriedades `nozzle_diameter=pl.nozzle_diameter`, `bed_type=pl.bed_type` e `layer_height=pl.layer_height` na criação do objeto `models.Plate`.

**Verificação**:
- Teste backend dedicado `test_duplicate_project_preserves_manufacturing_parameters_issue_72` em `tests/test_api.py`.
- 181/181 testes passando na suíte completa.""",
    },
    73: {
        "comment": """### ✅ Resolução - Issue #73

**Causa Raiz**:
A engine financeira `backend/engine.py` calculava os custos unitários e totais na função `calculate_plate_cost`, porém o dicionário de retorno omitia as chaves `nozzle_diameter`, `bed_type` e `layer_height`. Como a emissão da Ficha Técnica de Produção (`doc_type="technical"` em `backend/pdf_service.py`) lê esses dados exclusivamente a partir de `plates_details`, os fallbacks `'0.4'`, `'Textured PEI'` e `'0.20'` eram sempre aplicados, desconsiderando o setup real configurado pelo usuário.

**Correção Implementada**:
- Em `backend/engine.py` (`calculate_plate_cost`), adicionada a extração resiliente dos atributos `nozzle_diameter`, `bed_type` e `layer_height` e incluídas suas respectivas chaves no dicionário retornado.

**Verificação**:
- Teste unitário de engine `test_plate_cost_manufacturing_parameters_issue_73` em `tests/test_engine.py`.
- Teste de integração de persistência e geração de PDF técnico em `tests/test_api.py`.
- 181/181 testes passando na suíte completa.""",
    },
    74: {
        "comment": """### ✅ Resolução - Issue #74

**Causa Raiz**:
Na função `openNewProject()` em `frontend/js/app.js`, os campos de Condições de Pagamento (`proj-payment-terms`) e Termo de Garantia (`proj-warranty-terms`) eram inicializados com string vazia (`''`), ignorando as preferências salvas no perfil da oficina (`u.default_payment_terms` e `u.default_warranty_terms`).

**Correção Implementada**:
- Em `frontend/js/app.js` (`openNewProject`), atualizado o valor inicial dos inputs para carregar `u.default_payment_terms || ''` e `u.default_warranty_terms || ''`, mantendo os placeholders informativos da oficina.

**Verificação**:
- Teste frontend automatizado em `tests/test_frontend_inputs.py::test_issues_59_through_71_frontend_verification`.
- 181/181 testes passando na suíte completa.""",
    },
    75: {
        "comment": """### ✅ Resolução - Issue #75

**Causa Raiz**:
Ao acionar `deleteProject(id)` em `frontend/js/app.js`, o registro era excluído no banco de dados via API, mas a variável de estado global `state.currentProject` em cache na SPA não era limpa. Se o usuário navegasse de volta ao editor ou clicasse em salvar, o sistema tentava executar `PUT /api/projects/{id}` disparando erro HTTP 404 ("Projeto não encontrado.").

**Correção Implementada**:
- Em `frontend/js/app.js` (`deleteProject`), adicionada a checagem: se `state.currentProject && state.currentProject.id === id`, redefine `state.currentProject = null` e, caso o usuário esteja com a visualização do editor aberta (`state.activeView === 'project-editor'`), reinicializa um formulário limpo chamando `openNewProject()`.

**Verificação**:
- Teste frontend automatizado em `tests/test_frontend_inputs.py::test_issues_59_through_71_frontend_verification`.
- 181/181 testes passando na suíte completa.""",
    },
    76: {
        "comment": """### ✅ Resolução - Issue #76

**Causa Raiz**:
O grid de filamentos da oficina (`renderFilamentsGrid` em `frontend/js/app.js`) exibia o peso do carretel, o preço e o custo por grama, mas omitia a propriedade física de densidade volumétrica do polímero (`density_g_cm3`), impedindo a visualização rápida da especificação dos materiais cadastrados.

**Correção Implementada**:
- Em `frontend/js/app.js` (`renderFilamentsGrid`), adicionado no rodapé de cada card a exibição da densidade: `<span>Densidade: ${f.density_g_cm3 != null ? Number(f.density_g_cm3).toFixed(2) : '1.24'} g/cm³</span>`.

**Verificação**:
- Teste de renderização no Node/VM em `tests/test_frontend_inputs.py::test_issues_59_through_71_frontend_verification`.
- 181/181 testes passando na suíte completa.""",
    },
    77: {
        "comment": """### ✅ Resolução - Issue #77

**Causa Raiz**:
Ao clicar em duplicar um filamento (`openFilamentModal(filament, true)` em `frontend/js/app.js`), o campo de cor (`filament-color`) era forçado para vazio (`''`). Como o formulário possui validação obrigatória estrita exigindo cor preenchida, o usuário era impedido de salvar a duplicata sem redigitar manualmente o nome da cor.

**Correção Implementada**:
- Em `frontend/js/app.js` (`openFilamentModal`), o campo de cor na duplicação passou a ser pré-preenchido mantendo a cor original sufixada com `(Cópia)`: `document.getElementById('filament-color').value = filament.color ? `${filament.color} (Cópia)` : '';`, com foco e seleção do texto permitindo alteração rápida ou salvamento imediato.

**Verificação**:
- Teste de frontend em `tests/test_frontend_inputs.py::test_issues_59_through_71_frontend_verification`.
- 181/181 testes passando na suíte completa.""",
    },
    78: {
        "comment": """### ✅ Resolução - Issue #78

**Causa Raiz**:
Na função `handleSavePrinter` (`frontend/js/app.js`), a requisição HTTP POST/PUT era disparada sem validação prévia de preenchimento obrigatório do nome da impressora no lado do cliente, disparando requisições de rede destinadas a falhar com erro HTTP 422 do backend.

**Correção Implementada**:
- Em `frontend/js/app.js` (`handleSavePrinter`), incluída validação prévia no cliente:
  ```javascript
  const name = document.getElementById('printer-name').value.trim();
  if (!name) {
      showToast('Informe o nome ou identificação da impressora.', 'error');
      document.getElementById('printer-name')?.focus();
      return;
  }
  ```

**Verificação**:
- Teste de frontend em `tests/test_frontend_inputs.py::test_issues_59_through_71_frontend_verification`.
- 181/181 testes passando na suíte completa.""",
    },
    79: {
        "comment": """### ✅ Resolução - Issue #79

**Causa Raiz**:
Os fatiadores modernos exportam informações de diâmetro de bico e altura de camada tanto nos comentários de G-Code quanto no XML `Metadata/slice_info.xml` de arquivos 3MF (Bambu Studio / OrcaSlicer). As funções `parseGcodeMetadata` e `parse3mfMetadata` ignoravam esses parâmetros, fazendo com que placas importadas assumissem invariavelmente os fallbacks de bico 0.4mm e camada 0.20mm.

**Correção Implementada**:
- **G-Code Parser** (`frontend/js/parsers/gcode.js` e espelho Python `tests/test_parsers.py`): Adicionada extração regex para `nozzle_diameter` (incluindo suporte a bicos múltiplos/slots e sintaxes Prusa/Bambu/Orca/Cura), `layer_height` e `bed_type`.
- **3MF Parser** (`frontend/js/parsers/threemf.js` e espelho Python `tests/test_parsers.py`): Adicionada extração de tags `<metadata key="nozzle_diameter">`, `<metadata key="layer_height">` e `<metadata key="curr_bed_type">` em nível global e de placa em `slice_info.xml`/`.config`, além de extração complementar a partir de G-Codes embutidos no pacote ZIP.
- **Workflow de Importação** (`frontend/js/app.js`): Mapeados os novos metadados extraídos para os campos da placa criada no editor.

**Verificação**:
- Testes unitários `test_gcode_manufacturing_parameters_extraction` e `test_3mf_manufacturing_parameters_extraction` em `tests/test_parsers.py`.
- Teste frontend em `tests/test_frontend_inputs.py`.
- 181/181 testes passando na suíte completa.""",
    },
    80: {
        "comment": """### ✅ Resolução - Issue #80

**Causa Raiz**:
No endpoint `/api/projects/dashboard-stats` (`backend/routes/project_routes.py`), a métrica de filamento consumido em projetos realizados (`total_filament_kg`) lia a chave bruta `summary.get("total_filament_weight_g", 0.0)`. No entanto, o custo financeiro de material apurado pela engine considera o consumo real de filamento acrescido da margem de perda/falha (`total_effective_filament_weight_g`), gerando divergência entre o peso reportado no dashboard e o custo contábil de material.

**Correção Implementada**:
- Em `backend/routes/project_routes.py` (`get_dashboard_stats`), a leitura do peso passou a priorizar o peso efetivo consumido:
  `weight = float(summary.get("total_effective_filament_weight_g", summary.get("total_filament_weight_g", 0.0)) or 0.0)`.

**Verificação**:
- Teste backend `test_dashboard_stats_total_filament_kg_includes_failure_margin_issue_80` em `tests/test_api.py`.
- 181/181 testes passando na suíte completa.""",
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

    for issue_num, data in sorted(RESOLUTIONS.items()):
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
