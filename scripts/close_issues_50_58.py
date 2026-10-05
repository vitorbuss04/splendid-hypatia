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
    50: {
        "comment": """### ✅ Resolução - Issue #50

**Causa Raiz**:
Na visualização de impressoras (`renderPrintersGrid` em `frontend/js/app.js`), os campos `p.name`, `p.model` e o termo de pesquisa `${term}` na mensagem de busca vazia eram interpolados diretamente no template HTML sem escape de entidades, permitindo injeção de tags HTML/scripts arbitrários (XSS).

**Correção Implementada**:
- Adicionado helper de escape `esc = (typeof escapeHtml === 'function') ? escapeHtml : ...` em `renderPrintersGrid`.
- Aplicado escape em `p.name`, `p.model`, `${esc(term)}` e no rótulo de status filtrado `${esc(statusLabel)}`.

**Verificação**:
- Teste automatizado `test_issue_50_printers_grid_xss_protection` em `tests/test_frontend_inputs.py` validando bloqueio de injeção em nomes, modelos e filtros de busca.
- 167/167 testes passando.""",
    },
    51: {
        "comment": """### ✅ Resolução - Issue #51

**Causa Raiz**:
No catálogo de filamentos (`renderFilamentsGrid` em `frontend/js/app.js`), os campos `f.name`, `f.brand`, `f.color`, `f.material`, `f.color_hex` e o termo de pesquisa `${term}` eram interpolados sem sanitização em strings HTML, permitindo execução de Stored XSS e Reflected XSS.

**Correção Implementada**:
- Adicionado helper de escape em `renderFilamentsGrid`.
- Sanitizados `f.name`, `f.brand`, `f.color`, `f.material`, `f.color_hex`, `${esc(term)}` e `${esc(material)}` no card e nos filtros de pesquisa.

**Verificação**:
- Teste automatizado `test_issue_51_filaments_grid_xss_protection` em `tests/test_frontend_inputs.py`.
- 167/167 testes passando.""",
    },
    52: {
        "comment": """### ✅ Resolução - Issue #52

**Causa Raiz**:
No editor de placas (`renderPlates` em `frontend/js/app.js`), os inputs de taxa horária da máquina (`custom_printer_hourly_rate`) e custo por grama do filamento (`custom_filament_cost_per_g`) eram condicionados apenas a `!p.printer_id` e `!p.filament_id`. Se uma placa possuía um ID de impressora ou filamento que havia sido excluído do banco (órfão), o select exibia "Selecionar..." mas os inputs numéricos manuais permaneciam ocultos com `hidden`, impedindo o usuário de visualizar ou editar os custos manuais da placa.

**Correção Implementada**:
- Criadas flags `hasValidPrinter = !!(p.printer_id && state.printers.some(pr => pr.id === p.printer_id))` e `hasValidFilament = !!(p.filament_id && state.filaments.some(fi => fi.id === p.filament_id))`.
- Os inputs de taxa manual de impressora e filamento agora são exibidos quando `!hasValidPrinter` e `!hasValidFilament`, permitindo edição transparente mesmo para entidades órfãs.

**Verificação**:
- Teste automatizado `test_issue_52_and_55_plate_card_orphans_and_xss` em `tests/test_frontend_inputs.py`.
- 167/167 testes passando.""",
    },
    53: {
        "comment": """### ✅ Resolução - Issue #53

**Causa Raiz**:
No cálculo estatístico do dashboard (`backend/routes/project_routes.py` - rota `get_dashboard_stats`), a timeline financeira mensal (Gráfico 2) somava a receita (`revenue`) e lucro líquido apenas para projetos realizados (`approved`, `in_production`, `completed`), mas somava `base_cost` incondicionalmente para todos os projetos não cancelados, incluindo `draft` e `quoted`. Isso inflacionava artificialmente os custos mensais realizados e distorcia o balanço financeiro da oficina.

**Correção Implementada**:
- No loop de projetos em `get_dashboard_stats`, `monthly_data[month_key]["base_cost"]` passou a ser acumulado exclusivamente quando `st in ["approved", "in_production", "completed"]`, alinhando perfeitamente receita, custo e lucro realizado.

**Verificação**:
- Teste de regressão `test_issue_53_and_57_dashboard_stats_excludes_draft_and_quoted_from_timeline_and_breakdown` em `tests/test_api.py`.
- 167/167 testes passando.""",
    },
    54: {
        "comment": """### ✅ Resolução - Issue #54

**Causa Raiz**:
A calculadora em tempo real (`recalcLiveSummary` em `frontend/js/app.js`) e a rotina de salvamento (`saveCurrentProject`) não tratavam nem limitavam valores numéricos negativos nos campos de margem de lucro, desconto, imposto, frete e quantidade de placas. Valores negativos geravam anomalias como textos com sinal duplicado (`- -R$ 15,00`), margens negativas distorcendo o cálculo e respostas HTTP 422 ao salvar projetos com quantidade de placas menor que 1.

**Correção Implementada**:
- Em `recalcLiveSummary`:
  - `plate.quantity` é agora truncado com `Math.max(1, parseInt(...) || 1)`.
  - Margem, imposto, frete, desconto e custos horários foram limitados com `Math.max(0, ...)`, com `tax` e `discount` limitados ao teto de 99% e 100%.
- Em `saveCurrentProject`:
  - Aplicado `Math.max(0, ...)` e `Math.max(1, ...)` nos payloads enviados ao backend.

**Verificação**:
- Teste automatizado `test_issue_54_and_56_recalc_live_summary` em `tests/test_frontend_inputs.py`.
- 167/167 testes passando.""",
    },
    55: {
        "comment": """### ✅ Resolução - Issue #55

**Causa Raiz**:
No cabeçalho do card de placa e nos selects de filamento do editor (`renderPlates` em `frontend/js/app.js`), `selFil.material`, `selFil.color`, `selFil.color_hex`, `p.name` e as opções de materiais e filamentos eram renderizados diretamente sem sanitização, abrindo vulnerabilidade de XSS ao renderizar carretéis ou perfis com tags HTML.

**Correção Implementada**:
- Adicionado helper `esc` seguro com fallback em `renderPlates`.
- Sanitizados `p.name`, `cleanFilamentProfileName()`, `selFil.material`, `selFil.color`, `selFil.color_hex` e nomes de filamentos em opções de `<select>`.

**Verificação**:
- Teste automatizado `test_issue_52_and_55_plate_card_orphans_and_xss` em `tests/test_frontend_inputs.py`.
- 167/167 testes passando.""",
    },
    56: {
        "comment": """### ✅ Resolução - Issue #56

**Causa Raiz**:
Existia divergência entre os valores de taxa padrão de fallback para entidades não configuradas ou órfãs: o live summary utilizava `2.00/h` e `0.09/g` em certas ramificações `else`, enquanto a interface visual, os schemas e os fallbacks de salvamento utilizavam `2.50/h` e `0.10/g`.

**Correção Implementada**:
- Em `backend/routes/project_routes.py`: `sanitize_plate_foreign_keys` padronizado para usar `2.50` (máquina) e `0.10` (filamento).
- Em `frontend/js/app.js`: no `recalcLiveSummary`, o fallback geral quando não há impressora cadastrada foi alinhado para `2.50`, e para filamento para `0.10`.

**Verificação**:
- Teste unitário `test_issue_56_orphaned_foreign_key_fallbacks_2_50_and_0_10` em `tests/test_api.py`.
- Teste frontend `test_issue_54_and_56_recalc_live_summary` em `tests/test_frontend_inputs.py`.
- 167/167 testes passando.""",
    },
    57: {
        "comment": """### ✅ Resolução - Issue #57

**Causa Raiz**:
O gráfico de distribuição de custos (Gráfico 3 / Cost Breakdown) em `get_dashboard_stats` (`backend/routes/project_routes.py`) somava `material_cost`, `machine_energy_cost`, `labor_cost` e `overhead_cost` para todos os projetos com status diferente de `cancelled`, incluindo projetos em rascunho (`draft`) e orçados (`quoted`). Isso inflacionava os custos operacionais realizados com orçamentos que ainda não foram aprovados ou produzidos.

**Correção Implementada**:
- A acumulação de `material_cost`, `machine_energy_cost`, `labor_cost`, `bom_cost` e `overhead_cost` em `get_dashboard_stats` foi restrita para projetos com status `approved`, `in_production` e `completed`.

**Verificação**:
- Teste unitário `test_issue_53_and_57_dashboard_stats_excludes_draft_and_quoted_from_timeline_and_breakdown` em `tests/test_api.py`.
- 167/167 testes passando.""",
    },
    58: {
        "comment": """### ✅ Resolução - Issue #58

**Causa Raiz**:
O contador de orçamentos ativos (`active_quotes`) na API (`get_dashboard_stats` em `backend/routes/project_routes.py`) e no fallback do frontend (`renderDashboard` em `frontend/js/app.js`) filtrava apenas projetos com status `draft`, `quoted` e `in_production`, deixando de fora projetos com status `approved` (orçamentos formalmente aprovados pelo cliente aguardando fila de produção).

**Correção Implementada**:
- Atualizado o filtro em `backend/routes/project_routes.py`:
  `if st in ["draft", "quoted", "approved", "in_production"]: active_quotes += 1`.
- Atualizado o filtro de fallback em `frontend/js/app.js`:
  `['draft', 'quoted', 'approved', 'in_production'].includes(p.status)`.

**Verificação**:
- Teste unitário `test_issue_58_active_quotes_includes_approved_projects` em `tests/test_api.py`.
- Atualizado e verificado `test_m2_adversarial.py::test_dashboard_rendering_1_5_and_10_plus_projects`.
- 167/167 testes passando.""",
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
