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
        "title": "[BUG/SLICER] Importação de arquivos 3MF descarta o peso de purga/flush (purge_weight_g = 0) na leitura de metadados do fatiador",
        "labels": ["bug", "frontend"],
        "body": """### Descrição do Problema
Na importação de arquivos `.3mf` e `.gcode.3mf` fatiados (especialmente projetos multicoloridos/AMS do Bambu Studio ou OrcaSlicer), o extrator de metadados `parse3mfMetadata` em `frontend/js/parsers/threemf.js` inspeciona os nós XML `<metadata key="flush_weight" ...>` e `<filament flush_g="..." purge_g="...">`, acumulando corretamente o peso de purga e torre de transição na variável local `purgeGrams`:

```javascript
// Linhas 138-140 e 198-200 em frontend/js/parsers/threemf.js:
if (key === "flush_weight" || key === "purge_weight" || key === "waste_weight") {
    purgeGrams = parseFloat(val) || 0;
}
...
const flushG = parseFloat(f.getAttribute("flush_g") || f.getAttribute("purge_g") || "0") || 0;
if (flushG > 0 && purgeGrams === 0) {
    purgeGrams += flushG;
}
```

No entanto, no momento de montar o objeto da placa resultante (linha 235), o campo `purge_weight_g` é fixado com o valor literal `0.0`:

```javascript
// Linhas 230-236:
plates.push({
    name: finalName,
    plate_index: index,
    print_time_hours: parseFloat(printTimeHours.toFixed(2)),
    part_weight_g: parseFloat(totalWeight.toFixed(2)),
    purge_weight_g: 0.0, // <-- BUG: hardcoded para 0.0, descartando purgeGrams
    filament_type: filamentType,
    ...
});
```

### Impacto
- **Subprecificação Severa em Impressões Multicolor**: Em impressões FDM multicoloridas (Bambu Lab AMS / Prusa MMU), o peso de purga gerado em torres de transição e descargas de bico pode exceder 30% a 70% do filamento total consumido.
- **Distorção no Cálculo de Custo de Material**: Como `totalFilamentGrams` soma apenas o peso líquido da peça (`used_g`) e `purge_weight_g` é zerado para `0.0`, o sistema calcula o orçamento ignorando completamente o filamento desperdiçado no processo, gerando prejuízo financeiro para o operador da oficina.

### Passos para Reproduzir
1. Fatiar um modelo multicolor no Bambu Studio ou OrcaSlicer gerando um arquivo `.3mf` com troca de cores (ex: 50g peça + 35g flush/torre).
2. Na calculadora de orçamentos (`#/project-editor`), arrastar o arquivo `.3mf` para a área de importação.
3. Observar o card da placa gerada: o campo "Purga (g)" exibe `0` em vez de `35.0g`.

### Arquivos e Linhas Afetadas
- `frontend/js/parsers/threemf.js`: linha 235.

### Solução Proposta
Em `frontend/js/parsers/threemf.js`, atribuir o valor acumulado em `purgeGrams`:
```javascript
purge_weight_g: parseFloat(purgeGrams.toFixed(2)),
```
E garantir que `totalWeight` reflita o peso líquido da peça quando `totalFilamentGrams` estiver disponível.
"""
    },
    {
        "title": "[BUG/CÁLCULO] Divergência de custos entre Frontend e Engine quando placa não possui impressora ou filamento associado (Backend zera os custos da placa)",
        "labels": ["bug", "backend"],
        "body": """### Descrição do Problema
Quando uma placa é salva ou criada sem um ID de impressora (`printer_id = null`, `custom_printer_hourly_rate = null`) ou sem um ID de filamento (`filament_id = null`, `custom_filament_cost_per_g = null`):

1. **No Frontend (`recalcLiveSummary` em `frontend/js/app.js:2029-2041`)**:
A calculadora em tempo real adota taxas padrão de fallback:
- Custo por grama de filamento: `R$ 0,10/g`
- Taxa horária de máquina: `R$ 2,50/h`

2. **No Backend (`calculate_plate_cost` em `backend/engine.py:59-105`)**:
A engine oficial define o custo padrão como `0.0` se `custom_filament_cost_per_g` ou `custom_printer_hourly_rate` forem nulos:
```python
# backend/engine.py (linhas 59-74):
cost_per_gram = 0.0
...
if filament is not None:
    ...
else:
    custom_g = get_attr(plate, "custom_filament_cost_per_g", None)
    if custom_g is not None:
        cost_per_gram = max(0.0, float(custom_g or 0.0))
# Se custom_g for None, cost_per_gram permanece 0.0!

# backend/engine.py (linhas 88-105):
if printer is not None:
    ...
else:
    custom_hr = get_attr(plate, "custom_printer_hourly_rate", None)
    if custom_hr is not None:
        rate = max(0.0, float(custom_hr or 0.0))
        machine_rate_details["machine_hourly_rate"] = rate
# Se custom_hr for None, machine_hourly_rate permanece 0.0!
```

### Impacto
- **Divergência Financeira Drástica**: Um orçamento que exibia na interface do editor um custo base de R$ 35,00 (10 horas @ R$ 2,50/h + 100g @ R$ 0,10/g), ao ser salvo e recarregado ou exportado em PDF, tem seus custos recalculados pela engine do backend como R$ 0,00.
- **Inconsistência na Proposta Comercial**: O PDF gerado exibe valores em branco ou zerados para o tempo de máquina e filamento da placa.

### Passos para Reproduzir
1. Criar um projeto via API com uma placa contendo `print_time_hours: 10`, `part_weight_g: 100`, `printer_id: null` e `filament_id: null`.
2. Consultar o resumo do projeto via `GET /api/projects/{id}` ou `/api/projects/{id}/summary`.
3. Constatar que `total_material_cost` e `total_machine_cost` retornam `0.0`, enquanto a tela do frontend calculava com as taxas padrão da oficina.

### Arquivos e Linhas Afetadas
- `backend/engine.py`: linhas 59-74 e 88-105.
- `backend/routes/project_routes.py`: linhas 24-48 (`sanitize_plate_foreign_keys`).

### Solução Proposta
Em `backend/engine.py`, quando `filament` e `printer` forem nulos e nenhuma taxa customizada tiver sido fornecida, aplicar os fallbacks oficiais (alinhados com a interface):
```python
if filament is not None:
    ...
else:
    custom_g = get_attr(plate, "custom_filament_cost_per_g", None)
    cost_per_gram = max(0.0, float(custom_g)) if custom_g is not None else 0.10

if printer is not None:
    ...
else:
    custom_hr = get_attr(plate, "custom_printer_hourly_rate", None)
    machine_rate_details["machine_hourly_rate"] = max(0.0, float(custom_hr)) if custom_hr is not None else 2.50
```
"""
    },
    {
        "title": "[UX/BUG] Limpeza do campo Prazo de Entrega (proj-delivery-days) força valor fixo de 3 dias no salvamento impedindo estimativa dinâmica por horas de impressão",
        "labels": ["bug", "frontend", "ux"],
        "body": """### Descrição do Problema
O serviço de geração de PDF (`backend/pdf_service.py:383-386`) conta com uma lógica inteligente para calcular dinamicamente o prazo de entrega com base nas horas totais de impressão quando `delivery_days` é `None` (não informado):

```python
if delivery_days is None or delivery_days < 0:
    calc_days = max(1, int(summary.get('total_print_time_hours', 1) / 8) + 1)
    unit_days = "dia útil" if calc_days == 1 else "dias úteis"
    delivery_phrase = f"Estimado em até {calc_days} {unit_days} após aprovação."
```

Entretanto, na rotina de salvamento do frontend (`saveCurrentProject` em `frontend/js/app.js:2219`), se o usuário apagar o campo de prazo de entrega para deixar o cálculo automático agir, a expressão força o fallback para `3`:

```javascript
// frontend/js/app.js linha 2219:
delivery_days: (() => { 
    const d = parseInt(document.getElementById('proj-delivery-days')?.value, 10); 
    return isNaN(d) || d < 0 ? 3 : d; 
})(),
```

### Impacto
- Usuários que desejam que o orçamento calcule o prazo proporcionalmente ao tamanho do projeto (ex: projetos de 80h que levariam 11 dias úteis) têm seu campo forçado para 3 dias úteis ao salvar.
- Impossibilidade de salvar um projeto com `delivery_days: null` a partir da interface do usuário.

### Passos para Reproduzir
1. Abrir um orçamento no editor (`#/project-editor`).
2. Limpar o campo "Prazo de Entrega (dias úteis)", deixando-o vazio.
3. Clicar em "Salvar Orçamento".
4. Reabrir o projeto ou inspecionar a requisição de rede: o campo foi salvo com `delivery_days: 3` em vez de `null`.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linha 2219.

### Solução Proposta
Permitir que o valor vazio seja salvo como `null`:
```javascript
delivery_days: (() => {
    const raw = document.getElementById('proj-delivery-days')?.value?.trim();
    if (!raw) return null;
    const d = parseInt(raw, 10);
    return isNaN(d) || d < 0 ? null : d;
})(),
```
"""
    },
    {
        "title": "[UX/FEAT] Ausência de controle de status operacional (is_active) no cadastro, edição e listagem de filamentos",
        "labels": ["enhancement", "frontend", "ux"],
        "body": """### Descrição do Problema
O modelo `models.Filament` em `backend/models.py:76` e os schemas `FilamentBase` e `FilamentUpdate` em `backend/schemas.py:104, 119` possuem a propriedade `is_active: bool = True`.

Contudo, na camada de interface do usuário (`frontend/js/app.js` e `frontend/index.html`):
1. O modal de cadastro e edição de filamento (`modal-filament`) não possui nenhum campo de alternância (checkbox/switch) para `is_active`.
2. A função `handleSaveFilament` não inclui `is_active` no payload enviado para as rotas `POST` e `PUT /api/filaments`.
3. Os cards na tela "Meus Filamentos" (`renderFilamentsGrid`) não exibem indicador de status e não há filtro para filamentos inativos/esgotados.

### Impacto
- **Carretéis Esgotados Poluem Seletores**: Quando um filamento acaba ou é descontinuado pelo fabricante, o usuário é obrigado a excluí-lo (podendo quebrar referências históricas) ou mantê-lo visível para sempre no seletor de filamentos de todos os orçamentos.
- **Inconsistência de Funcionalidade**: As impressoras contam com suporte ao campo `is_active`, mas os filamentos não possuem essa capacidade na UI.

### Passos para Reproduzir
1. Acessar a tela de filamentos (`#/filaments`).
2. Clicar em "Cadastrar Filamento" ou em "Editar" em qualquer filamento existente.
3. Observar a ausência de campo para desativar ou marcar o carretel como esgotado/inativo.

### Arquivos e Linhas Afetadas
- `frontend/index.html`: container do modal `#modal-filament`.
- `frontend/js/app.js`: linhas 2914-3022 (`openFilamentModal`, `handleSaveFilament`, `renderFilamentsGrid`).

### Solução Proposta
1. Incluir checkbox `is_active` em `#modal-filament` em `frontend/index.html`.
2. Em `openFilamentModal`, carregar o estado atual (`filament.is_active ?? true`).
3. Em `handleSaveFilament`, incluir `is_active` no payload para `API.filaments.create` e `API.filaments.update`.
4. Exibir badge visual discreto ("Inativo / Esgotado") nos cards de filamentos com `is_active === false`.
"""
    },
    {
        "title": "[FEAT/UX] Ausência de parâmetros de manufatura (Diâmetro do Bico, Tipo de Mesa e Altura de Camada) no modelo de placas e na Ficha Técnica de Produção",
        "labels": ["enhancement", "frontend", "backend"],
        "body": """### Descrição do Problema
Em `frontend/js/app.js`, a função `createDefaultPlate` inicializa propriedades de setup físico da placa:
```javascript
// frontend/js/app.js linhas 1585-1587:
nozzle_diameter: '0.4',
bed_type: 'Textured PEI',
layer_height: '0.20',
```

E em `renderPlates` (linhas 1685-1687):
```javascript
const nozzle = plate.nozzle_diameter || '0.4';
const bed = plate.bed_type || 'Textured PEI';
const layer = plate.layer_height || '0.20';
```

Entretanto:
1. Nenhuma dessas variáveis é renderizada em campos de entrada ou exibição no card da placa no editor.
2. Na função `saveCurrentProject` (linhas 2223-2240), essas propriedades não são repassadas no payload para o backend.
3. No backend (`models.Plate` em `backend/models.py` e `PlateBase` em `backend/schemas.py`), as colunas correspondentes não existem.
4. Na Ficha Técnica de Produção (`pdf_service.py`), a tabela de parâmetros operacionais omite essas informações essenciais para a fabricação.

### Impacto
- Em oficinas de manufatura aditiva, o operador precisa saber exatamente qual diâmetro de bico (ex: 0.2mm para miniaturas, 0.4mm padrão, 0.6mm/0.8mm para peças resistentes) e qual tipo de chapa de impressão (PEI texturizado, PEI liso, Vidro, Engenharia) deve ser utilizada.
- O código frontend preparou o suporte inicial a esses parâmetros, mas a funcionalidade não foi concluída.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 1585-1587, 1685-1687, 2223-2240.
- `backend/models.py`: classe `Plate` (linhas 121-146).
- `backend/schemas.py`: `PlateBase` e `PlateUpdate` (linhas 137-185).
- `backend/pdf_service.py`: tabela técnica de produção (linhas 426-465).

### Solução Proposta
1. Adicionar colunas `nozzle_diameter`, `bed_type` e `layer_height` no modelo `Plate` e schemas Pydantic.
2. Renderizar seletores/inputs correspondentes dentro do agrupamento "Configuração de Hardware & Setup" no card da placa em `renderPlates`.
3. Persistir os valores em `saveCurrentProject`.
4. Incluir as colunas "Bico", "Mesa" e "Camada" na tabela da Ficha Técnica de Produção do PDF.
"""
    },
    {
        "title": "[BUG/DASHBOARD] Gráfico temporal de Faturamento (Chart 2) soma horas de impressão de orçamentos em Rascunho ('draft') e Orçados ('quoted')",
        "labels": ["bug", "backend"],
        "body": """### Descrição do Problema
No endpoint `/api/projects/dashboard-stats` (`backend/routes/project_routes.py`), a geração do histórico mensal (`monthly_timeline`) isola corretamente o faturamento, custo e lucro de orçamentos não realizados através da flag `is_realized = st in ["approved", "in_production", "completed"]`:

```python
# backend/routes/project_routes.py linhas 249-254:
is_realized = st in ["approved", "in_production", "completed"]
monthly_data[month_key]["revenue"] = round(monthly_data[month_key]["revenue"] + (final_price if is_realized else 0.0), 2)
monthly_data[month_key]["base_cost"] = round(monthly_data[month_key]["base_cost"] + (base_cost if is_realized else 0.0), 2)
monthly_data[month_key]["net_profit"] = round(monthly_data[month_key]["net_profit"] + (net_profit if is_realized else 0.0), 2)
monthly_data[month_key]["print_hours"] = round(monthly_data[month_key]["print_hours"] + hours, 2)
```

Observe que `monthly_data[month_key]["print_hours"]` adiciona as horas de impressão (`hours`) incondicionalmente para qualquer status diferente de `cancelled` (incluindo `draft` e `quoted`).

Enquanto isso, o card de KPI global `total_print_hours` (linha 214) restringe rigorosamente o cálculo para status realizados:
```python
if st in ["approved", "in_production", "completed"]:
    total_print_hours += hours
```

### Impacto
- **Divergência de Métricas no Dashboard**: O total de horas acumulado no gráfico temporal do mês é muito maior do que as horas reais exibidas no card principal de KPIs.
- Orçamentos especulativos em rascunho com 500 horas de impressão inflacionam o gráfico mensal de horas trabalhadas da oficina.

### Passos para Reproduzir
1. Criar um projeto com status `draft` contendo 50 horas de impressão.
2. Acessar o Dashboard (`#/dashboard`).
3. O KPI de horas exibe `0.0 h`, mas o histórico mensal do mês corrente registra `50.0 h` de impressão.

### Arquivos e Linhas Afetadas
- `backend/routes/project_routes.py`: linha 253.

### Solução Proposta
Na linha 253 de `backend/routes/project_routes.py`, condicionar a soma de horas à realização do orçamento:
```python
monthly_data[month_key]["print_hours"] = round(
    monthly_data[month_key]["print_hours"] + (hours if is_realized else 0.0), 2
)
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
        "User-Agent": "BrowserBugHunterV8"
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
