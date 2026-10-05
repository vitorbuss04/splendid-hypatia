import subprocess
import urllib.request
import urllib.error
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

ISSUES_TO_CREATE = [
    {
        "title": "[SECURITY/XSS] Falha de Cross-Site Scripting (XSS) no card de placas do editor de orçamentos por interpolação direta de material e cor do filamento",
        "labels": ["security", "frontend", "bug"],
        "body": """### Descrição do Problema
Na renderização dos cards das placas no editor de orçamentos (`renderPlates` em `frontend/js/app.js`), os dados do filamento selecionado para a placa são interpolados diretamente no HTML do cabeçalho da placa sem sanitização por `escapeHtml()`:

```javascript
${selFil ? `<span class="flex items-center gap-1 text-[10px] text-slate-400 font-normal shrink-0 max-w-[55%] truncate" title="${selFil.material} ${selFil.color || ''}"><span class="w-2 h-2 rounded-full inline-block border border-slate-600 shadow-sm shrink-0" style="background-color: ${selFil.color_hex || '#10b981'};"></span> <span class="truncate">${selFil.material} ${selFil.color || ''}</span></span>` : ''}
```

Além disso, nos elementos `<select>` de seleção de impressora e filamento (linhas 1723-1727 e 1756-1760), os nomes das entidades cadastradas também são injetados diretamente nas tags `<option>`:
```javascript
${state.printers.map(p => `
    <option value="${p.id}" ${plate.printer_id === p.id ? 'selected' : ''}>
        ${p.name} (R$ ${p.machine_hourly_rate.toFixed(2)}/h)
    </option>
`).join('')}
```

```javascript
${state.filaments.map(f => `
    <option value="${f.id}" ${plate.filament_id === f.id ? 'selected' : ''}>
        ${f.name} (R$ ${(Number(f.cost_per_gram) || 0).toFixed(2)}/g)
    </option>
`).join('')}
```

### Impacto
- **Cross-Site Scripting Armazenado (Stored XSS)**: Se um usuário cadastrar um filamento com caracteres como `<b id="xss">...</b>` ou payload `<img src=x onerror=...>` no campo de cor ou material, ao abrir o editor de projetos contendo esse filamento, elementos arbitrários são injetados no DOM e scripts podem ser executados no contexto da sessão.
- **Risco de Acesso a Dados Sensíveis**: Exfiltração potencial do token JWT salvo no `localStorage` (`auth_token`).

### Passos para Reproduzir
1. Acessar "Meus Filamentos" (`#/filaments`) e cadastrar um filamento com cor ou material contendo tags HTML, por exemplo `<b id="xss-plate-test">PLA</b>`.
2. Acessar o Editor de Orçamentos (`#/project-editor`).
3. Associar o filamento criado à placa #1.
4. Inspecionar o elemento `#plates-container` e observar a tag `<b>` renderizada diretamente no DOM em vez de escapada como texto puro.

### Arquivo e Linhas Afetadas
- `frontend/js/app.js`: linhas 1724-1726, 1750 e 1757-1759.

### Solução Proposta
Aplicar `escapeHtml()` nas propriedades de texto do filamento e impressora:
```javascript
${selFil ? `<span class="flex items-center gap-1 text-[10px] text-slate-400 font-normal shrink-0 max-w-[55%] truncate" title="${escapeHtml(selFil.material)} ${escapeHtml(selFil.color || '')}"><span class="w-2 h-2 rounded-full inline-block border border-slate-600 shadow-sm shrink-0" style="background-color: ${escapeHtml(selFil.color_hex || '#10b981')};"></span> <span class="truncate">${escapeHtml(selFil.material)} ${escapeHtml(selFil.color || '')}</span></span>` : ''}
```
E nas opções dos dropdowns:
```javascript
${escapeHtml(p.name)} (R$ ${p.machine_hourly_rate.toFixed(2)}/h)
${escapeHtml(f.name)} (R$ ${(Number(f.cost_per_gram) || 0).toFixed(2)}/g)
```
"""
    },
    {
        "title": "[BUG/CÁLCULO] Divergência entre taxa manual padrão exibida no input da placa (R$ 2,50/h e R$ 0,10/g) e o cálculo da calculadora ao vivo (recalcLiveSummary usa R$ 2,00/h e R$ 0,09/g)",
        "labels": ["bug", "frontend"],
        "body": """### Descrição do Problema
Ao definir uma placa no modo "Personalizada (Manual)" sem selecionar uma impressora ou filamento do catálogo, os inputs visuais exibem como valor padrão / placeholder:
- **Taxa da Impressora**: `R$ 2,50/h` (linha 1733: `value="${plate.custom_printer_hourly_rate ?? 2.50}" placeholder="2.50"`)
- **Custo do Filamento**: `R$ 0,10/g` (linha 1767: `value="${plate.custom_filament_cost_per_g ?? 0.10}" placeholder="0.10"`)
- **Salvamento no Backend**: em `saveCurrentProject` (linhas 2224-2225), o fallback utilizado ao serializar o payload também é `2.50` e `0.10`.

Entretanto, na rotina de cálculo dinâmico da calculadora em tempo real (`recalcLiveSummary` em `frontend/js/app.js`), quando o valor `custom_*` no estado é `null`, o cálculo adota fallbacks hardcoded diferentes:
```javascript
// Linhas 2026-2028:
} else if (plate.custom_filament_cost_per_g != null) {
    costPerGram = parseLocaleFloat(plate.custom_filament_cost_per_g, 0);
} else {
    costPerGram = 0.09; // fallback standard PLA
}

// Linhas 2034-2038:
} else if (plate.custom_printer_hourly_rate != null) {
    machineHourlyRate = parseLocaleFloat(plate.custom_printer_hourly_rate, 0);
} else {
    machineHourlyRate = 2.0; // fallback standard rate
}
```

### Impacto
- **Divergência de Cálculo Visível**: Para uma impressão de 10 horas com 1000g de filamento:
  - Custo esperado pelos inputs exibidos: 10h × R$ 2,50 + 1000g × R$ 0,10 = R$ 125,00.
  - Custo calculado pela calculadora ao vivo no terminal à direita: 10h × R$ 2,00 + 1000g × R$ 0,09 = R$ 110,00 (diferença de R$ 15,00 ou ~12%).
- **Salto Abrupto de Preço ao Salvar**: Ao clicar em "Salvar Projeto", o backend calcula com as taxas persistidas (2.50 e 0.10), fazendo o preço final e as margens divergirem subitamente do que o usuário estava vendo na simulação ao vivo na tela.

### Passos para Reproduzir
1. Abrir um novo orçamento no editor (`#/project-editor`).
2. Adicionar uma placa sem selecionar impressora ou filamento cadastrado (modo manual padrão).
3. Definir tempo de impressão como 10 horas e peso de 1000g.
4. Notar que os campos exibem "2.50" e "0.10".
5. Observar o painel lateral de resumo: o Custo de Máquina exibe `R$ 20,00` (calculado a R$ 2,00/h) em vez de `R$ 25,00`, e o Custo de Material exibe `R$ 90,00` (calculado a R$ 0,09/g) em vez de `R$ 100,00`.

### Arquivo e Linhas Afetadas
- `frontend/js/app.js`: linhas 2027 e 2037 (em `recalcLiveSummary`).

### Solução Proposta
Harmonizar as taxas padrão da calculadora ao vivo com os inputs e com a persistência (`2.50` e `0.10`):
```javascript
// Em recalcLiveSummary:
} else {
    costPerGram = 0.10; // alinhado com fallback visual de 0.10/g
}

...

} else {
    machineHourlyRate = 2.50; // alinhado com fallback visual de 2.50/h
}
```
"""
    },
    {
        "title": "[BUG/DASHBOARD] Gráfico de Estrutura de Custos da Oficina (Chart 3) soma custos e lucros de orçamentos em Rascunho ('draft') e Orçados ('quoted'), distorcendo as despesas reais operacionais",
        "labels": ["bug", "backend", "frontend"],
        "body": """### Descrição do Problema
No endpoint de métricas analíticas `/api/projects/dashboard-stats` (`backend/routes/project_routes.py`), os custos operacionais agregados para o gráfico de Estrutura de Custos & Lucro da Oficina (Chart 3: `cost_breakdown`) são acumulados para qualquer projeto cujo status seja diferente de cancelado:

```python
if st != "cancelled":
    material_cost += float(summary.get("total_material_cost", 0.0) or 0.0)
    machine_energy_cost += float(summary.get("total_machine_cost", 0.0) or 0.0)
    labor_cost += float(summary.get("total_labor_cost", 0.0) or 0.0)
    bom_cost += float(summary.get("total_bom_cost", 0.0) or 0.0)
    overhead_cost += float(summary.get("overhead_cost", 0.0) or 0.0)
    profit_acc += max(0.0, net_profit)
```

Essa lógica inclui todos os projetos com status `draft` (rascunhos experimentais ou testes de viabilidade) e `quoted` (propostas orçadas enviadas mas ainda não aceitas pelo cliente).

### Impacto
- **Contaminação da Estrutura de Custos**: Se uma oficina cadastrar simulações de orçamentos ou rascunhos de grandes volumes (ex: projeto de R$ 50.000 em rascunho), os custos de material, horas de máquina, mão de obra e lucro teórico desse rascunho entram diretamente no gráfico analítico da oficina como se fossem despesas e lucros reais incorridos.
- **Inconsistência Flagrante com os Cards do Dashboard**: Os cards superiores de KPI ("Faturamento Aprovado", "Lucro Líquido Realizado", "Horas de Impressão", "Consumo de Filamento") consideram rigorosamente apenas projetos em `["approved", "in_production", "completed"]`. Já o gráfico logo abaixo exibe valores de custos e lucros centenas de vezes maiores devido aos rascunhos.

### Passos para Reproduzir
1. Registrar uma conta limpa.
2. Criar um projeto com status `draft` com custo de filamento alto (ex: 200h de máquina e 5000g de filamento).
3. Acessar o Dashboard (`#/dashboard`).
4. Observar que o card de Faturamento Aprovado exibe R$ 0,00, enquanto o gráfico de Estrutura de Custos da Oficina (Chart 3) exibe milhares de Reais distribuídos em filamento, energia e mão de obra de um rascunho não aprovado.

### Arquivo e Linhas Afetadas
- `backend/routes/project_routes.py`: linhas 224-231.

### Solução Proposta
No backend, agregar `cost_breakdown` apenas para projetos com status aprovado ou em execução (`st in ["approved", "in_production", "completed"]`), garantindo paridade contábil e coerência com as demais métricas operacionais realizadas:
```python
if st in ["approved", "in_production", "completed"]:
    material_cost += float(summary.get("total_material_cost", 0.0) or 0.0)
    machine_energy_cost += float(summary.get("total_machine_cost", 0.0) or 0.0)
    labor_cost += float(summary.get("total_labor_cost", 0.0) or 0.0)
    bom_cost += float(summary.get("total_bom_cost", 0.0) or 0.0)
    overhead_cost += float(summary.get("overhead_cost", 0.0) or 0.0)
    profit_acc += max(0.0, net_profit)
```
"""
    },
    {
        "title": "[BUG/MÉTRICAS] Contador de \"Orçamentos Ativos\" (active_quotes) omite projetos com status \"aprovado\" (approved), gerando queda inconsistente na métrica durante a transição operacional",
        "labels": ["bug", "frontend", "backend"],
        "body": """### Descrição do Problema
O contador do card "Orçamentos Ativos" no Dashboard mede o volume de propostas em ciclo ativo de atendimento.
No backend (`backend/routes/project_routes.py` linhas 208-210):
```python
if st in ["draft", "quoted", "in_production"]:
    active_quotes += 1
```

E no fallback do frontend (`frontend/js/app.js` linhas 739-741):
```javascript
const activeQuotes = stats ? stats.active_quotes : (state.projects 
    ? state.projects.filter(p => ['draft', 'quoted', 'in_production'].includes(p.status)).length 
    : 0);
```

O status `approved` (Aprovado) foi omitido da lista.

### Impacto
- **Comportamento Inconsistente de Métrica**: No fluxo natural de um pedido:
  1. Criação da proposta (`draft` / `quoted`): o contador de "Orçamentos Ativos" contabiliza 1.
  2. Cliente aceita e status muda para `approved`: o contador **cai em 1** (como se o projeto estivesse finalizado ou cancelado).
  3. Pedido é colocado na fila de impressão (`in_production`): o contador **volta a subir em 1**.
  4. Pedido entregue (`completed`): o contador decresce.
- A exclusão de `approved` cria um "vácuo" ilusório nas métricas operacionais quando o orçamento é aprovado e aguarda a entrada em máquina.

### Passos para Reproduzir
1. Criar um projeto com status `quoted`.
2. Observar o contador "Orçamentos Ativos" marcar 1.
3. Editar o projeto e alterar o status para `approved`.
4. Visualizar o Dashboard: o contador cai para 0, mesmo com o pedido ativo e recém-aprovado.
5. Alterar o status para `in_production`: o contador volta para 1.

### Arquivo e Linhas Afetadas
- `backend/routes/project_routes.py`: linha 208.
- `frontend/js/app.js`: linha 740.

### Solução Proposta
Incluir `'approved'` no conjunto de status de pedidos ativos:
```python
# No backend (project_routes.py):
if st in ["draft", "quoted", "approved", "in_production"]:
    active_quotes += 1
```

```javascript
// No frontend (app.js):
state.projects.filter(p => ['draft', 'quoted', 'approved', 'in_production'].includes(p.status)).length
```
"""
    }
]

def publish():
    token = get_token()
    if not token:
        print("❌ Erro: GitHub token não encontrado via git credential.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "BrowserAuditHunterV6",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }

    print("Verificando issues existentes no GitHub...")
    req = urllib.request.Request(f"{API_BASE}/issues?state=all&per_page=100", headers=headers)
    with urllib.request.urlopen(req) as resp:
        existing = json.loads(resp.read().decode())

    existing_titles = {i["title"].strip(): i for i in existing}
    print(f"Total de issues existentes no repositório: {len(existing_titles)}")

    created_issues = []
    for item in ISSUES_TO_CREATE:
        title = item["title"].strip()
        if title in existing_titles:
            existing_issue = existing_titles[title]
            print(f"⏭️  Issue já existe: #{existing_issue['number']} - {title}")
            created_issues.append(existing_issue)
            continue

        print(f"\nCriando issue no GitHub: {title}...")
        payload = json.dumps({
            "title": item["title"],
            "body": item["body"],
            "labels": item["labels"]
        }).encode("utf-8")

        post_req = urllib.request.Request(f"{API_BASE}/issues", data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(post_req) as resp:
                res_data = json.loads(resp.read().decode())
                print(f"✅ Issue #{res_data['number']} criada com sucesso!")
                print(f"   URL: {res_data['html_url']}")
                created_issues.append(res_data)
        except urllib.error.HTTPError as e:
            print(f"❌ Erro HTTP {e.code} ao criar issue '{title}': {e.reason}")
            print(e.read().decode())

    print(f"\n🎉 Publicação finalizada! {len(created_issues)} issues processadas.")

if __name__ == "__main__":
    publish()
