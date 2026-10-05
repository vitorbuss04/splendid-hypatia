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
        "title": "[SECURITY/PRIVACY] Logout não limpa estado em memória (state) e mantém dados de projetos, orçamentos e clientes acessíveis no navegador",
        "labels": ["security", "frontend", "privacy"],
        "body": """### Descrição do Problema
Na rotina de autenticação do frontend (`frontend/js/app.js`), o evento de logout é tratado da seguinte forma:
```javascript
window.addEventListener('auth:logout', () => {
    state.user = null;
    if (typeof window !== 'undefined' && window.location && typeof window.location.hash === 'string') {
        window.location.hash = '#/dashboard';
    }
    document.getElementById('auth-modal').classList.remove('hidden');
});
```

Ao acionar `API.auth.logout()` ou o botão "Sair da conta" na barra lateral:
1. O token JWT é removido do `localStorage`.
2. Apenas `state.user` é definido como `null`.
3. Os arrays de dados em memória `state.projects`, `state.printers`, `state.filaments`, `state.dashboardStats`, `state.currentProject`, `state.currentPlates` e `state.currentBOM` **permanecem intactos na memória JavaScript da página**.
4. O DOM dos componentes (tabela de projetos recentes, listagem de orçamentos, números de faturamento do dashboard) permanece renderizado atrás do overlay do modal de login.

### Impacto
- **Vazamento de Dados Sensíveis**: Qualquer usuário com acesso físico posterior ao mesmo navegador ou via console de desenvolvedor (`window.state.projects`) consegue inspecionar toda a carteira de orçamentos, dados de contato de clientes (nomes, e-mails, telefones), margens de lucro e faturamento do usuário anterior.
- **Contaminação de Sessão**: Se outro usuário realizar login na mesma aba, ou caso o token expire e o modal de reautenticação seja exibido, dados do usuário anterior podem piscar na tela ou ser misturados até que `loadAllData()` sobrescreva os objetos.

### Passos para Reproduzir
1. Autenticar no sistema com uma conta que contenha orçamentos cadastrados.
2. Clicar no botão de logout na barra lateral (ou executar `API.auth.logout()`).
3. O modal de autenticação é exibido.
4. Abrir o DevTools (F12 -> Console) e digitar `state.projects` ou inspecionar o DOM atrás do modal.
5. Observar que a lista completa de orçamentos e clientes continua disponível.

### Arquivo e Linhas Afetadas
- `frontend/js/app.js`: linhas 3215-3221 (no listener `auth:logout`) e no listener `auth:unauthorized`.

### Solução Proposta
No evento `auth:logout` e `auth:unauthorized`, limpar completamente o estado global e os elementos visuais sensíveis do DOM:
```javascript
window.addEventListener('auth:logout', () => {
    state.user = null;
    state.projects = [];
    state.printers = [];
    state.filaments = [];
    state.currentProject = null;
    state.currentPlates = [];
    state.currentBOM = [];
    state.dashboardStats = null;
    
    // Limpar tabelas e resumos renderizados no DOM
    const projContainer = document.getElementById('projects-table-container');
    if (projContainer) projContainer.innerHTML = '';
    const recentTable = document.querySelector('#view-dashboard table tbody');
    if (recentTable) recentTable.innerHTML = '';
    
    if (typeof destroyDashboardCharts === 'function') {
        destroyDashboardCharts();
    }
    
    if (typeof window !== 'undefined' && window.location && typeof window.location.hash === 'string') {
        window.location.hash = '#/dashboard';
    }
    document.getElementById('auth-modal').classList.remove('hidden');
});
```"""
    },
    {
        "title": "[BUG/DATA-LOSS] updatePlateTime zera silenciosamente o tempo de impressão (print_time_hours = 0) ao salvar projeto se inputs não estiverem no DOM",
        "labels": ["bug", "frontend", "data-integrity"],
        "body": """### Descrição do Problema
No editor de orçamentos (`frontend/js/app.js`), a função `updatePlateTime(idx)` lê os inputs de horas e minutos de uma placa:
```javascript
function updatePlateTime(idx) {
    const hElem = document.getElementById(`plate-time-h-${idx}`);
    const mElem = document.getElementById(`plate-time-m-${idx}`);
    const h = Math.max(0, parseInt(hElem?.value, 10) || 0);
    const m = Math.max(0, parseInt(mElem?.value, 10) || 0);
    state.currentPlates[idx].print_time_hours = Number((h + (m / 60)).toFixed(4));
    recalcLiveSummary();
}
```

E no início da função `saveCurrentProject()`:
```javascript
async function saveCurrentProject(navigateBack = true) {
    normalizeNumericInputs();
    if (state.currentPlates) {
        state.currentPlates.forEach((_, idx) => updatePlateTime(idx));
    }
    // ...
```

Se `saveCurrentProject()` for invocado em um contexto onde os elementos `plate-time-h-${idx}` não estejam presentes no DOM (por exemplo, ao salvar antes da renderização completa dos cards, durante transições de tela, importações em segundo plano ou chamadas programáticas como `exportCurrentPdf()`), `hElem` e `mElem` retornam `null`.
A expressão `parseInt(null?.value, 10)` avalia como `NaN`, que com o fallback `|| 0` resulta em `h = 0` e `m = 0`.
Consequentemente, `state.currentPlates[idx].print_time_hours` é **zerado para 0.0**.

### Impacto
- **Perda de Dados e Distorção Financeira**: Placas que já continham tempos de impressão calculados (ex: 4.5 horas) têm seu tempo zerado para 0 horas ao salvar, zerando o custo de máquina (`total_machine_cost = 0`) e reduzindo drasticamente o preço sugerido do orçamento para o cliente.

### Passos para Reproduzir
1. Configurar uma placa com tempo de 5h 30m no editor de projetos.
2. Invocar `updatePlateTime(idx)` para um índice cujos elementos não estejam visíveis no DOM.
3. Observar que `state.currentPlates[idx].print_time_hours` é sobrescrito para `0`.

### Arquivo e Linhas Afetadas
- `frontend/js/app.js`: linhas 1495-1502.

### Solução Proposta
Adicionar verificação de existência dos elementos antes de sobrescrever a propriedade no modelo:
```javascript
function updatePlateTime(idx) {
    const hElem = document.getElementById(`plate-time-h-${idx}`);
    const mElem = document.getElementById(`plate-time-m-${idx}`);
    if (!hElem && !mElem) {
        return; // Preserva o print_time_hours já existente se os inputs não existirem no DOM
    }
    const h = Math.max(0, parseInt(hElem?.value, 10) || 0);
    const m = Math.max(0, parseInt(mElem?.value, 10) || 0);
    state.currentPlates[idx].print_time_hours = Number((h + (m / 60)).toFixed(4));
    recalcLiveSummary();
}
```"""
    },
    {
        "title": "[SECURITY/XSS] Falha de Cross-Site Scripting (XSS) no container de notificações Toast por inserção direta via innerHTML",
        "labels": ["security", "frontend", "vulnerability"],
        "body": """### Descrição do Problema
Na função `showToast(message, type)` em `frontend/js/app.js`:
```javascript
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    // ...
    const toast = document.createElement('div');
    toast.className = `p-3 rounded-lg border shadow-lg text-xs font-semibold flex items-center gap-2 pointer-events-auto transition-all transform duration-300 translate-y-2 opacity-0 ${colors[type] || colors.info}`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);
```

A variável `message` é injetada diretamente via `innerHTML` sem passar por `escapeHtml(message)`.
No fluxo do sistema, `showToast` recebe strings contendo entradas do usuário e nomes de arquivos:
- `showToast(\`Erro ao ler "${file.name || 'arquivo'}": ${err.message}\`, 'error')`
- `showToast(\`Processando metadados de ${fileList[0].name}...\`, 'info')`
- `showToast(err.message, 'error')` (onde mensagens de erro da API podem refletir campos de input enviados).

### Impacto
- Se um usuário fizer upload ou arrastar um arquivo de fatiador com nome contendo tags HTML (ex: `<img src=x onerror=alert(1)>.3mf` ou `<svg onload=fetch(...)>.gcode`), o código HTML/JavaScript é executado arbitrariamente no contexto da sessão da aplicação.

### Passos para Reproduzir
1. Arrastar para a dropzone de arquivos um arquivo com nome `<img src=x onerror=console.log("XSS_TRIGGERED")>.3mf`.
2. O toast dispara: `Processando metadados de <img src=x onerror=...`.
3. O payload é executado no navegador.

### Arquivo e Linhas Afetadas
- `frontend/js/app.js`: linhas 372-385.

### Solução Proposta
Em `frontend/js/app.js`, utilizar `escapeHtml` ou construir os nós com `textContent`:
```javascript
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const colors = {
        success: 'bg-emerald-600 text-white border-emerald-500',
        error: 'bg-red-600 text-white border-red-500',
        info: 'bg-blue-600 text-white border-blue-500',
    };

    const toast = document.createElement('div');
    toast.className = `p-3 rounded-lg border shadow-lg text-xs font-semibold flex items-center gap-2 pointer-events-auto transition-all transform duration-300 translate-y-2 opacity-0 ${colors[type] || colors.info}`;
    
    const textSpan = document.createElement('span');
    textSpan.textContent = String(message);
    toast.appendChild(textSpan);
    
    container.appendChild(toast);
    // ...
```"""
    },
    {
        "title": "[BUG/VALIDATION] Placas e itens de BOM aceitam nomes vazios no salvamento gerando registros em branco na proposta e no PDF",
        "labels": ["bug", "frontend", "backend", "validation"],
        "body": """### Descrição do Problema
Na calculadora de orçamentos (`frontend/js/app.js`), o usuário pode apagar o texto dos inputs de nome de placa (`state.currentPlates[idx].name`) ou de item de insumo/BOM (`state.currentBOM[idx].name`).
Ao clicar em "Salvar Orçamento":
```javascript
plates: state.currentPlates.map(p => ({
    name: p.name,
    // ...
})),
bom_items: state.currentBOM.map(b => ({
    name: b.name,
    // ...
}))
```
O payload envia `name: ""` para o backend.
No backend (`backend/schemas.py`), os modelos `PlateBase` e `BOMItemBase` possuem:
```python
class PlateBase(BaseModel):
    name: str = "Placa 1"

class BOMItemBase(BaseModel):
    name: str
```
O Pydantic aceita a string vazia `""` como válida, persistindo registros com nome vazio no banco SQLite.

### Impacto
- Na proposta comercial e na ficha técnica geradas em PDF (`backend/pdf_service.py`), a tabela de itens impressos exibe linhas em branco (`<b></b>`) e os componentes de montagem aparecem sem identificação.
- Prejudica a legibilidade e a apresentação profissional das propostas geradas para clientes.

### Passos para Reproduzir
1. Abrir um orçamento no editor.
2. Apagar o nome da placa e de um item BOM, deixando os campos em branco.
3. Salvar o orçamento.
4. Visualizar a proposta comercial em PDF: a primeira coluna de peças impressas aparece vazia.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 2045-2065.
- `backend/schemas.py`: linhas 138 (`PlateBase`) e 179 (`BOMItemBase`).

### Solução Proposta
1. No frontend (`frontend/js/app.js`), aplicar fallback automático ao montar o payload:
```javascript
name: (p.name || '').trim() || `Placa ${idx + 1}`,
```
e para itens BOM:
```javascript
name: (b.name || '').trim() || `Insumo ${idx + 1}`,
```
2. No backend (`backend/schemas.py`), adicionar validação `Field(..., min_length=1)` para `name` em `PlateBase` e `BOMItemBase`.
"""
    },
    {
        "title": "[BUG/DASHBOARD] Projetos com status 'cancelado' (cancelled) continuam exibidos no ranking de Top Projetos e distorcem métricas operacionais",
        "labels": ["bug", "backend", "dashboard", "metrics"],
        "body": """### Descrição do Problema
No endpoint de estatísticas do painel (`backend/routes/project_routes.py`, função `get_dashboard_stats`), na linha 253:
```python
project_items.append(schemas.TopProjectItem(
    id=proj.id,
    name=proj.name,
    client_name=proj.client_name,
    status=proj.status,
    final_price=round(final_price, 2),
    net_profit=round(net_profit, 2),
    print_hours=round(hours, 2),
))
```
E na linha 288:
```python
top_projects = sorted(project_items, key=lambda x: x.final_price, reverse=True)[:5]
```

Todos os projetos do usuário são inseridos em `project_items` sem filtrar o status `st`.
Se um orçamento com valor elevado for cancelado pelo cliente (status `cancelled`), ele continuará sendo ordenado e exibido no ranking dos Top 5 Projetos no Dashboard.

Além disso, no mesmo loop (linhas 224-229):
```python
material_cost += float(summary.get("total_material_cost", 0.0) or 0.0)
machine_energy_cost += float(summary.get("total_machine_cost", 0.0) or 0.0)
labor_cost += float(summary.get("total_labor_cost", 0.0) or 0.0)
bom_cost += float(summary.get("total_bom_cost", 0.0) or 0.0)
overhead_cost += float(summary.get("overhead_cost", 0.0) or 0.0)
profit_acc += max(0.0, net_profit)
```
Os custos operacionais continuam sendo somados ao `cost_breakdown` mesmo para projetos com status `cancelled` que nunca foram fabricados.

### Impacto
- Um projeto cancelado de R$ 5.000,00 aparecerá como o "Maior Projeto da Oficina" no gráfico de barras do dashboard, e seus insumos inflarão a estrutura de custos operacionais da oficina.

### Passos para Reproduzir
1. Criar um projeto com valor de R$ 10.000,00 e alterar seu status para "Cancelado" (`cancelled`).
2. Criar outro projeto aprovado de R$ 500,00.
3. Consultar o Dashboard (`GET /api/projects/dashboard-stats`): o projeto cancelado ocupa o 1º lugar na lista de `top_projects`.

### Arquivo e Linhas Afetadas
- `backend/routes/project_routes.py`: linhas 224-229 e 253-261.

### Solução Proposta
Em `backend/routes/project_routes.py`, restringir a inclusão em `project_items` e no somatório de custos operacionais apenas para projetos não cancelados (`if st != "cancelled":`):
```python
if st != "cancelled":
    material_cost += float(summary.get("total_material_cost", 0.0) or 0.0)
    machine_energy_cost += float(summary.get("total_machine_cost", 0.0) or 0.0)
    labor_cost += float(summary.get("total_labor_cost", 0.0) or 0.0)
    bom_cost += float(summary.get("total_bom_cost", 0.0) or 0.0)
    overhead_cost += float(summary.get("overhead_cost", 0.0) or 0.0)
    profit_acc += max(0.0, net_profit)

    project_items.append(schemas.TopProjectItem(
        id=proj.id,
        name=proj.name,
        client_name=proj.client_name,
        status=proj.status,
        final_price=round(final_price, 2),
        net_profit=round(net_profit, 2),
        print_hours=round(hours, 2),
    ))
```"""
    },
    {
        "title": "[FEAT/UX] Adicionar ação de duplicação para componentes e insumos adicionais (BOM) na calculadora de orçamentos",
        "labels": ["enhancement", "frontend", "ux"],
        "body": """### Descrição do Problema
Na calculadora e editor de orçamentos (`frontend/js/app.js`), existe o recurso de duplicação rápida para placas de impressão 3D através da função `duplicatePlateRow(idx)` e do botão com ícone de cópia.
Filamentos e orçamentos inteiros também contam com ações rápidas de duplicação.

No entanto, para a seção de insumos e montagem (**BOM - Bill of Materials**), existem apenas botões para adicionar um insumo padrão (`addNewBomRow()`) e remover (`removeBomRow(index)`).
Em projetos de fabricação digital é extremamente comum cadastrar múltiplos parafusos (ex: M3x8, M3x12, M3x16, M3x20), insertos roscados, ímãs ou arruelas com custos unitários idênticos ou categorias repetidas. A ausência de um botão "Duplicar Insumo" força o usuário a recriar o item do zero, selecionar novamente a categoria no dropdown e redigitar o custo unitário.

### Solução Proposta
1. Implementar a função `duplicateBomRow(idx)` em `frontend/js/app.js`:
```javascript
function duplicateBomRow(idx) {
    const orig = state.currentBOM[idx];
    if (!orig) return;
    const cloned = JSON.parse(JSON.stringify(orig));
    delete cloned.id;
    cloned.name = `${orig.name || 'Insumo'} (Cópia)`;
    state.currentBOM.splice(idx + 1, 0, cloned);
    renderBOM();
    recalcLiveSummary();
    showToast('Insumo duplicado com sucesso!', 'success');
}
window.duplicateBomRow = duplicateBomRow;
```
2. Na função `renderBOM()`, incluir o botão de duplicação com ícone `copy` na coluna de ações ao lado do botão de exclusão:
```html
<div class="sm:col-span-1 flex justify-center items-center gap-1 pt-1 sm:pt-0">
    <button type="button" onclick="duplicateBomRow(${idx})" class="p-1.5 text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 rounded-md transition-all" title="Duplicar Insumo">
        <i data-lucide="copy" class="w-3.5 h-3.5"></i>
    </button>
    <button type="button" onclick="removeBomRow(${idx})" class="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-md transition-all" title="Remover Insumo">
        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
    </button>
</div>
```"""
    }
]

def publish():
    token = get_token()
    if not token:
        print("❌ Erro: Token do GitHub não encontrado.")
        sys.exit(1)

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Splendid-Hypatia-IssuePublisher",
        "Content-Type": "application/json"
    }

    print(f"Buscando issues existentes no repositório {REPO}...")
    req = urllib.request.Request(f"{API_BASE}/issues?state=all&per_page=100", headers=headers)
    with urllib.request.urlopen(req) as resp:
        existing = json.loads(resp.read().decode())

    existing_titles = {i["title"].strip(): i for i in existing}
    print(f"Total de issues já existentes no repositório: {len(existing_titles)}")

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

    print(f"\n🎉 Publicação finalizada! {len(created_issues)} issues processadas no repositório {REPO}.")

if __name__ == "__main__":
    publish()
