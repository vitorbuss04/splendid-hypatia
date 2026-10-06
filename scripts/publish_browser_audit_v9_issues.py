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
        "title": "[BUG/OPERACIONAL] Duplicação de Projeto descarta parâmetros de manufatura das placas (nozzle_diameter, bed_type, layer_height) resetando para os padrões",
        "labels": ["bug", "backend"],
        "body": """### Descrição do Problema
No endpoint `POST /api/projects/{project_id}/duplicate` (`backend/routes/project_routes.py`), ao clonar um projeto existente, o sistema itera sobre as placas originais (`orig.plates`) para instanciar novas entidades `models.Plate`.

Entretanto, as colunas de parâmetros operacionais de manufatura introduzidas no modelo de placas (`nozzle_diameter`, `bed_type` e `layer_height`) são completamente omitidas do construtor:

```python
# backend/routes/project_routes.py (linhas 448-463):
c_plate = models.Plate(
    project_id=cloned.id,
    name=pl.name,
    printer_id=cleaned_pl["printer_id"],
    filament_id=cleaned_pl["filament_id"],
    custom_printer_hourly_rate=cleaned_pl["custom_printer_hourly_rate"],
    custom_filament_cost_per_g=cleaned_pl["custom_filament_cost_per_g"],
    print_time_hours=pl.print_time_hours,
    part_weight_g=pl.part_weight_g,
    purge_weight_g=pl.purge_weight_g,
    failure_margin_percent=pl.failure_margin_percent,
    quantity=pl.quantity,
    slicer_filament_profile=pl.slicer_filament_profile,
    notes=pl.notes,
    # <-- FALTAM: nozzle_diameter, bed_type, layer_height
)
```

Como resultado, todas as placas do projeto duplicado voltam a assumir os valores default de coluna do banco (`nozzle_diameter='0.4'`, `bed_type='Textured PEI'`, `layer_height='0.20'`).

### Impacto
- **Perda Silenciosa de Especificações de Produção**: Se uma peça foi orçada para impressão com bico 0.6mm ou 0.8mm (ex: peças estruturais volumosas), mesa lisa Smooth PEI ou camada fina 0.12mm, a duplicação do projeto reseta todos esses valores sem alertar o operador.
- **Risco de Falha na Oficina**: Ao enviar o projeto duplicado para produção ou emitir a Ficha Técnica, a equipe de manufatura receberá instruções incorretas de diâmetro de bico e altura de camada.

### Passos para Reproduzir
1. Criar um projeto com uma placa configurada com bico `0.6`, mesa `Smooth PEI` e camada `0.12`.
2. Salvar o projeto e clicar no botão "Duplicar" na tabela de orçamentos (`#/projects`) ou via API `POST /api/projects/{id}/duplicate`.
3. Abrir o projeto duplicado: constatar que o setup de manufatura foi resetado para `0.4`, `Textured PEI` e `0.20`.

### Arquivos e Linhas Afetadas
- `backend/routes/project_routes.py`: linhas 448-463.

### Solução Proposta
Incluir os campos no construtor de `models.Plate` em `duplicate_project`:
```python
c_plate = models.Plate(
    ...
    nozzle_diameter=pl.nozzle_diameter,
    bed_type=pl.bed_type,
    layer_height=pl.layer_height,
    ...
)
```
"""
    },
    {
        "title": "[BUG/ENGINE] calculate_plate_cost omite nozzle_diameter, bed_type e layer_height nos detalhes da placa fazendo a Ficha Técnica de Produção exibir dados hardcoded",
        "labels": ["bug", "backend"],
        "body": """### Descrição do Problema
Na engine de cálculo de custos (`backend/engine.py`), a função `calculate_plate_cost` calcula métricas financeiras e operacionais de cada placa e retorna um dicionário contendo o detalhamento da placa.

No entanto, o retorno de `calculate_plate_cost` omite os parâmetros de manufatura configurados na placa:
```python
# backend/engine.py (linhas 120-145):
return {
    "plate_id": get_attr(plate, "id", None),
    "name": name,
    "quantity": quantity,
    "printer_name": printer_name,
    "filament_name": filament_name,
    "filament_material": filament_material,
    "cost_per_gram": round(cost_per_gram, 4),
    "machine_hourly_rate": round(machine_hourly_rate, 4),
    ...
    # <-- FALTAM: nozzle_diameter, bed_type, layer_height
}
```

Posteriormente, no gerador de relatórios e PDF (`backend/pdf_service.py:441-448`), a Ficha Técnica de Produção (`doc_type="technical"`) tenta ler esses dados a partir de `plates_details`:
```python
nozzle = html.escape(str(p.get('nozzle_diameter') or '0.4'))
bed = html.escape(str(p.get('bed_type') or 'Textured PEI'))
layer = html.escape(str(p.get('layer_height') or '0.20'))
```
Como `plates_details` provém de `calculate_plate_cost`, `p.get('nozzle_diameter')`, `p.get('bed_type')` e `p.get('layer_height')` retornam invariavelmente `None`. O PDF sempre exibe os valores de fallback `'0.4'`, `'Textured PEI'` e `'0.20'`, ignorando completamente o que o usuário configurou na placa.

### Impacto
- **Ficha Técnica de Produção Descalibrada**: A Ficha Técnica (Checklist do Operador) é o documento oficial levado ao chão de fábrica para guiar a preparação de impressoras e fatiadores. Ela exibe parâmetros incorretos independentemente do que foi configurado no sistema.

### Passos para Reproduzir
1. Configurar um projeto com bico `0.8` mm, mesa de vidro `SuperPlate Glass` e camada `0.28` mm.
2. Clicar em "Ficha Técnica de Produção" (`preview.html?project_id=...&type=technical`).
3. Observar a coluna "Setup Fab.": o documento imprime `0.4mm / 0.20mm (Textured PEI)`.

### Arquivos e Linhas Afetadas
- `backend/engine.py`: linhas 120-145 (`calculate_plate_cost`).
- `backend/pdf_service.py`: linhas 441-448.

### Solução Proposta
Em `backend/engine.py`, extrair e incluir os parâmetros de setup no dicionário retornado por `calculate_plate_cost`:
```python
nozzle_diameter = str(get_attr(plate, "nozzle_diameter", "0.4") or "0.4")
bed_type = str(get_attr(plate, "bed_type", "Textured PEI") or "Textured PEI")
layer_height = str(get_attr(plate, "layer_height", "0.20") or "0.20")
...
return {
    ...
    "nozzle_diameter": nozzle_diameter,
    "bed_type": bed_type,
    "layer_height": layer_height,
    ...
}
```
"""
    },
    {
        "title": "[UX/BUG] Criação de Novo Orçamento (openNewProject) zera Condições de Pagamento e Garantia em vez de carregar os padrões das preferências da oficina",
        "labels": ["bug", "frontend", "ux"],
        "body": """### Descrição do Problema
O sistema disponibiliza nas Configurações da Oficina (`#/settings`) os campos `default_payment_terms` ("Condições de Pagamento Padrão") e `default_warranty_terms` ("Termo de Garantia Padrão").

Entretanto, na função `openNewProject()` em `frontend/js/app.js`, enquanto as taxas de CAD, pós-processamento, margem de lucro e impostos são corretamente pré-populadas a partir de `state.user`, os campos de condições comerciais são forçados para string vazia:

```javascript
// frontend/js/app.js (linhas 1512-1513):
document.getElementById('proj-payment-terms').value = '';
document.getElementById('proj-warranty-terms').value = '';
```

Isso faz com que o formulário do editor apresente os campos em branco toda vez que um novo orçamento é aberto.

### Impacto
- **Inconsistência de Experiência e Retrabalho**: O usuário é obrigado a digitar ou colar manualmente suas condições comerciais toda vez que inicia uma proposta, contrariando o propósito das preferências salvas.
- **Risco de Proposta Sem Termos**: Se o usuário não redigitar os termos no editor, o formulário salva strings vazias ou nulas no banco de dados.

### Passos para Reproduzir
1. Acessar Configurações (`#/settings`) e preencher:
   - Condições de Pagamento: `50% entrada e 50% na entrega via PIX`
   - Termo de Garantia: `90 dias de garantia legal contra delaminação`
2. Salvar as preferências.
3. Clicar em "Criar Novo Orçamento" no menu ou dashboard.
4. Rolar até a seção "Condições Comerciais": os campos estão vazios.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 1512-1513.

### Solução Proposta
Em `frontend/js/app.js`:
```javascript
document.getElementById('proj-payment-terms').value = u.default_payment_terms || '';
document.getElementById('proj-warranty-terms').value = u.default_warranty_terms || '';
```
"""
    },
    {
        "title": "[UX/BUG] Exclusão de projeto não limpa state.currentProject em cache permitindo tentativa de salvamento de registro inexistente com erro HTTP 404",
        "labels": ["bug", "frontend", "ux"],
        "body": """### Descrição do Problema
Ao excluir um orçamento na interface através da função `deleteProject(id)` (`frontend/js/app.js:2329-2343`), o sistema invoca a API `DELETE /api/projects/{id}` e atualiza as listagens:

```javascript
async function deleteProject(id) {
    if (!confirm('Deseja realmente excluir este orçamento?')) return;
    try {
        await API.projects.delete(id);
        showToast('Projeto excluído com sucesso.', 'success');
        await loadAllData();
        renderProjectsTable();
        renderRecentProjects();
        if (state.activeView === 'dashboard') {
            renderDashboard();
        }
    } catch (err) {
        showToast(err.message, 'error');
    }
}
```

No entanto, se o projeto excluído estiver atualmente carregado na sessão do editor (`state.currentProject && state.currentProject.id === id`), a variável `state.currentProject` NÃO é limpa (`null`).

Se o usuário estiver no editor ou navegar para `#/project-editor` e clicar em "Salvar Orçamento", a função `saveCurrentProject()` detecta `state.currentProject.id` e tenta executar um `PUT /api/projects/{id}`, resultando em erro HTTP 404 ("Projeto não encontrado.").

### Impacto
- **Desincronização de Estado em Memória (SPA)**: Permite que a interface fique em estado inconsistente após uma deleção.
- **Erro Inesperado para o Usuário**: Exibe notificação de erro 404 ao salvar em vez de redirecionar ou inicializar um novo projeto limpo.

### Passos para Reproduzir
1. Abrir um projeto existente para edição (`#/project-editor?id=...`).
2. Voltar à lista de projetos (`#/projects`) e excluir esse mesmo projeto na tabela.
3. Alternar de volta para o editor de orçamentos e clicar em "Salvar Orçamento".
4. Observar a requisição falhando com status 404.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 2329-2343 (`deleteProject`).

### Solução Proposta
Em `deleteProject(id)`:
```javascript
if (state.currentProject && state.currentProject.id === id) {
    state.currentProject = null;
    if (state.activeView === 'project-editor') {
        openNewProject();
    }
}
```
"""
    },
    {
        "title": "[UX/FEAT] Card de Filamento na listagem da oficina omite a exibição da densidade do material (g/cm³)",
        "labels": ["enhancement", "frontend", "ux"],
        "body": """### Descrição do Problema
O cadastro e edição de filamentos permite registrar a densidade volumétrica do polímero em `density_g_cm3` (ex: 1.24 g/cm³ para PLA, 1.27 g/cm³ para PETG, 1.04 g/cm³ para ABS, 1.21 g/cm³ para TPU).

Contudo, na renderização do grid de filamentos (`renderFilamentsGrid` em `frontend/js/app.js:3228-3230`):
```javascript
<div class="pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex justify-between">
    <span>Carretel: ${f.spool_weight_g} g</span>
    <span>Preço: ${formatCurrency(f.spool_price)}</span>
</div>
```
A densidade do material não é exibida em nenhuma parte do card, impedindo a visualização rápida da especificação física do polímero cadastrado.

### Impacto
- **Falta de Visibilidade de Dados Cadastrados**: O usuário não consegue inspecionar a densidade dos filamentos na listagem sem abrir o modal de edição para cada um.

### Passos para Reproduzir
1. Cadastrar um filamento com densidade personalizada (ex: ABS com 1.04 g/cm³).
2. Visualizar o catálogo em `#/filaments`.
3. Notar que o card não exibe a densidade.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 3228-3230.

### Solução Proposta
Adicionar a informação de densidade no rodapé ou cabeçalho do card de filamentos:
```javascript
<span>Densidade: ${f.density_g_cm3 ? f.density_g_cm3.toFixed(2) : '1.24'} g/cm³</span>
```
"""
    },
    {
        "title": "[UX/BUG] Ação de duplicar filamento zera o campo de cor forçando preenchimento manual obrigatório",
        "labels": ["bug", "frontend", "ux"],
        "body": """### Descrição do Problema
Na tela de Filamentos (`#/filaments`), ao clicar no botão "Duplicar" em um carretel, a função `openFilamentModal(filament, true)` é chamada.

Na linha 2991 de `frontend/js/app.js`:
```javascript
} else if (filament && isDuplicate) {
    title.textContent = 'Cadastrar Filamento (Duplicar)';
    document.getElementById('filament-id').value = '';
    document.getElementById('filament-material').value = filament.material || 'PLA';
    document.getElementById('filament-brand').value = filament.brand || '';
    document.getElementById('filament-color').value = ''; // <-- Zera a cor
```
O campo de cor é forçado para string vazia (`''`). Em contrapartida, `handleSaveFilament(e)` possui uma validação estrita:
```javascript
const color = document.getElementById('filament-color').value.trim();
if (!color) {
    showToast('Informe a cor do filamento.', 'error');
    document.getElementById('filament-color')?.focus();
    return;
}
```
Como consequência, se o operador desejar duplicar um carretel existente mantendo a cor (ou apenas registrar um segundo carretel do mesmo lote), a ação é bloqueada com erro, exigindo redigitação manual.

Enquanto isso, a duplicação de impressoras (`duplicatePrinter`) cria diretamente a cópia (`${orig.name} (Cópia)`) sem atrito.

### Impacto
- **Atrito Operacional Desnecessário**: Força o usuário a digitar novamente a cor mesmo quando apenas desejava duplicar o carretel existente.

### Passos para Reproduzir
1. Na tela de Filamentos, clicar no ícone de cópia em qualquer filamento (ex: "Preto").
2. No modal aberto, tentar clicar em "Salvar Filamento".
3. O sistema exibe o toast de erro "Informe a cor do filamento." e bloqueia o salvamento.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linha 2991.

### Solução Proposta
Pré-preencher a cor existente ou sufixar com "(Cópia)" caso o usuário não altere:
```javascript
document.getElementById('filament-color').value = filament.color ? `${filament.color} (Cópia)` : '';
```
"""
    },
    {
        "title": "[UX/BUG] Formulário de impressora não valida nome obrigatório no frontend antes de submeter requisição à API",
        "labels": ["bug", "frontend", "ux"],
        "body": """### Descrição do Problema
No formulário de filamentos (`handleSaveFilament`) e no salvamento de projetos (`saveCurrentProject`), o frontend valida campos obrigatórios (marca, cor, título) antes de disparar a requisição de rede, fornecendo feedback instantâneo e focando o input inválido.

Porém, na função `handleSavePrinter` (`frontend/js/app.js:2728-2745`):
```javascript
async function handleSavePrinter(e) {
    e.preventDefault();
    normalizeNumericInputs();
    const id = document.getElementById('printer-id').value;
    const payload = {
        name: document.getElementById('printer-name').value.trim(),
        ...
    };
    ...
    try {
        if (id) {
            await API.printers.update(id, payload);
        } else {
            await API.printers.create(payload);
        }
    ...
```
Não existe verificação prévia de `if (!payload.name)`. O formulário envia uma requisição POST/PUT com string vazia para a API, dependendo do erro HTTP 422 de validação do Pydantic para exibir toast de erro.

### Impacto
- **Tráfego de Rede Desnecessário**: Dispara requisições que sabidamente falharão.
- **Inconsistência de Feedback**: Filamentos e orçamentos focam o campo faltante imediatamente no cliente; impressoras disparam requisição remota.

### Passos para Reproduzir
1. Abrir o modal "Cadastrar Impressora".
2. Deixar o campo "Nome / Identificação" em branco e clicar em "Salvar Impressora".
3. Uma chamada de rede `POST /api/printers` é disparada retornando 422.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 2728-2745 (`handleSavePrinter`).

### Solução Proposta
Adicionar validação prévia no frontend:
```javascript
const name = document.getElementById('printer-name').value.trim();
if (!name) {
    showToast('Informe o nome ou identificação da impressora.', 'error');
    document.getElementById('printer-name')?.focus();
    return;
}
```
"""
    },
    {
        "title": "[FEAT/SLICER] Extração de diâmetro do bico (nozzle_diameter) e altura de camada (layer_height) na importação de arquivos 3MF e G-Code",
        "labels": ["enhancement", "frontend"],
        "body": """### Descrição do Problema
Os fatiadores modernos (Bambu Studio, OrcaSlicer, PrusaSlicer e Cura) exportam parâmetros de fatiamento no arquivo:
- **3MF (Bambu Studio / OrcaSlicer)**: No nó XML `Metadata/slice_info.xml`, cada placa contém `<metadata key="nozzle_diameter" value="0.4"/>` e informações de altura de camada `<metadata key="layer_height" value="0.20"/>`.
- **G-Code (Prusa / Bambu / Orca / Cura)**: Comentários como `; nozzle_diameter = 0.4`, `; layer_height = 0.20` ou `;Layer height: 0.2`.

No entanto, as funções de extração `parseGcodeMetadata` (`frontend/js/parsers/gcode.js`) e `parse3mfMetadata` (`frontend/js/parsers/threemf.js`) ignoram esses parâmetros, fixando valores hardcoded `'0.4'` e `'0.20'` nas placas importadas.

### Impacto
- **Setup Manual Redundante**: Se um arquivo foi fatiado para bico 0.6mm ou camada 0.12mm (alta resolução), o operador precisa reconfigurar manualmente o bico e a camada na placa importada toda vez, sob risco de esquecer e enviar a Ficha Técnica com bico 0.4mm padrão.

### Passos para Reproduzir
1. Fatiar um arquivo com bico 0.6mm e altura de camada 0.15mm no Bambu Studio ou OrcaSlicer.
2. Importar o arquivo `.3mf` ou `.gcode` na calculadora de orçamentos.
3. Observar que a placa importada registra bico `0.4` e camada `0.20`.

### Arquivos e Linhas Afetadas
- `frontend/js/parsers/gcode.js`: linhas 29-277.
- `frontend/js/parsers/threemf.js`: linhas 130-245.

### Solução Proposta
Adicionar a leitura das chaves `nozzle_diameter` e `layer_height` no XML do 3MF e nas linhas de comentário do G-Code, repassando-as nos metadados retornados da placa.
"""
    },
    {
        "title": "[BUG/DASHBOARD] Métrica de Filamento Consumido (total_filament_kg) desconsidera a taxa de perda/falha (failure_margin_percent) divergindo do Custo de Material apurado",
        "labels": ["bug", "backend"],
        "body": """### Descrição do Problema
No endpoint `/api/projects/dashboard-stats` (`backend/routes/project_routes.py`), o cálculo do total de filamento consumido em projetos realizados (`total_filament_kg`) soma o peso bruto das placas (`total_filament_weight_g`):

```python
# backend/routes/project_routes.py (linhas 204-215):
weight = float(summary.get("total_filament_weight_g", 0.0) or 0.0)
...
if st in ["approved", "in_production", "completed"]:
    total_filament_g += weight
...
total_filament_kg = round(total_filament_g / 1000.0, 2)
```

Por outro lado, o custo de material calculado pela engine (`total_material_cost`) leva em conta o peso efetivo consumido (`total_effective_filament_weight_g`), que inclui a margem de falha/perda de impressão (`failure_factor = 1.0 + failure_margin_percent / 100.0`):

```python
# backend/engine.py (linhas 75-78):
unit_raw_weight = part_weight_g + purge_weight_g
failure_factor = 1.0 + (failure_margin_percent / 100.0)
unit_effective_weight = unit_raw_weight * failure_factor
unit_material_cost = unit_effective_weight * cost_per_gram
```

Dessa forma, enquanto o custo contábil de material reflete o consumo real de carretéis (peça + perdas), o medidor de consumo em quilogramas no Dashboard exibe apenas o peso limpo, gerando uma divergência matemática perceptível no cálculo de estoque e custo médio por kg.

### Impacto
- **Distorção no Planejamento de Estoque**: Para oficinas com volume de produção elevado e margem de perda configurada (ex: 10% a 15%), o dashboard subestima a quantidade real de filamento retirada do estoque físico.

### Passos para Reproduzir
1. Criar e aprovar um projeto com 1000g de peça e margem de perda de 10% (100g de perda calculada no custo).
2. Consultar o dashboard: a métrica exibe `Filamento: 1.00 kg` em vez de `1.10 kg`, embora o custo de material computado seja referente a 1.10 kg.

### Arquivos e Linhas Afetadas
- `backend/routes/project_routes.py`: linhas 204 e 215.

### Solução Proposta
Permitir que o dashboard calcule o consumo total considerando o peso efetivo (`total_effective_filament_weight_g`):
```python
weight = float(summary.get("total_effective_filament_weight_g", summary.get("total_filament_weight_g", 0.0)) or 0.0)
```
"""
    }
]

def publish():
    token = get_token()
    if not token:
        print("❌ Token do GitHub não encontrado via git credential!")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "BrowserBugHunterV9"
    }

    # Fetch existing issues to avoid duplication
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
