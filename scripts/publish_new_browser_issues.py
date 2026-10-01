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
        "title": "[BUG/CRASH] Falha HTTP 500 ao gerar ou visualizar PDF comercial e técnico com caracteres especiais (<, >, &) no título, cliente, placas, notas ou insumos",
        "labels": ["bug", "backend", "pdf-generation"],
        "body": """### Descrição do Problema
No serviço de geração de PDFs (`backend/pdf_service.py`), a biblioteca ReportLab utiliza a classe `Paragraph`, que analisa o texto fornecido como se fosse marcação XML (`<b>`, `<i>`, etc.).

Quando campos do orçamento contêm caracteres especiais usuais na área técnica e maker como:
- Símbolos `<` ou `>` (ex: `Gabinete <V2> Inox`, `Placa <A> Base`, `Tolerância < 0.2mm`, `Parafuso M3x10 <Inox>`)
- Símbolos `&` (ex: `Alpha & Omega Eng`, `M&M Prototipagem`, `Corte & Gravação`)

A chamada `doc.build(story)` quebra com uma exceção não tratada:
`ValueError: paragraph text '<para><b>Placa <A> Base</b></para>' caused exception Parse error: saw </b> instead of expected </a>` (ou erro XML análogo com `&`).

Como consequência, as rotas `GET /api/projects/{id}/pdf?type=client` e `GET /api/projects/{id}/pdf?type=technical` retornam **HTTP 500 (Internal Server Error)**.

### Impacto
No frontend, ao clicar em "Visualizar Orçamento" ou "Ficha Técnica", o modal/aba `preview.html` tenta carregar o PDF inline e falha com o erro:
`Erro ao carregar documento: Servidor respondeu com status 500: Internal Server Error`.
O usuário fica totalmente impossibilitado de emitir propostas ou fichas técnicas para qualquer projeto que possua tais caracteres.

### Passos para Reproduzir
1. Criar um orçamento com o nome `Suporte <V2> Náutico` e cliente `Alpha & Omega Eng`.
2. Adicionar uma placa chamada `Base Inferior <A>`.
3. Adicionar notas: `Tolerância < 0.2mm & sem rebarbas`.
4. Salvar o projeto e clicar no botão de visualizar PDF (ou acessar `/api/projects/{id}/pdf?type=client`).
5. Observar o crash HTTP 500 com `ValueError: paragraph text ... caused exception Parse error`.

### Arquivos e Linhas Afetadas
- `backend/pdf_service.py`: linhas 167-173, 199-204, 247-248, 438-440, 472-473, 526-527.
Atualmente, apenas `payment_terms`, `warranty_terms` e `pix_info` utilizam `html.escape()`. Os demais campos (`project_title`, `client_name`, `client_email`, `client_phone`, `company_name`, `contact_text`, `p.name`, `b.name`, `b.category`, `b.notes`, `notes_txt`) são interpolados sem escape.

### Solução Proposta
Em `backend/pdf_service.py`, aplicar `html.escape()` em todas as variáveis textuais antes de inseri-las em instâncias de `Paragraph`:
```python
safe_company = html.escape(str(company_name))
safe_contact = html.escape(str(contact_text))
safe_title = html.escape(str(project_title))
safe_client = html.escape(str(client_name))
safe_email = html.escape(str(client_email))
safe_phone = html.escape(str(client_phone))
safe_plate_name = html.escape(str(p.get('name', 'Placa')))
safe_bom_name = html.escape(str(b.get('name', 'Item')))
safe_notes = html.escape(str(notes_txt))
```"""
    },
    {
        "title": "[BUG/CÁLCULO] Dupla contagem do custo de energia elétrica em machine_energy_cost no resumo do Dashboard",
        "labels": ["bug", "backend", "calculation-engine", "dashboard"],
        "body": """### Descrição do Problema
No endpoint de estatísticas do painel (`backend/routes/project_routes.py`, função `get_dashboard_stats`), na linha 225:
```python
machine_energy_cost += float(summary.get("total_machine_cost", 0.0) or 0.0) + float(summary.get("total_energy_cost", 0.0) or 0.0)
```

No entanto, no motor de cálculo oficial (`backend/engine.py`, função `calculate_printer_hourly_rate` e `calculate_plate_cost`):
```python
depreciation_per_hour = (acquisition_cost / lifespan_hours) if lifespan_hours > 0 else 0.0
energy_cost_per_hour = (avg_power_watts / 1000.0) * energy_rate_kwh
total_hourly_rate = depreciation_per_hour + maintenance_cost_per_hour + energy_cost_per_hour

unit_machine_cost = print_time_hours * machine_hourly_rate
total_machine_cost = unit_machine_cost * quantity
total_energy_cost = (print_time_hours * machine_rate_details["energy_cost_per_hour"]) * quantity
```
A taxa horária da máquina (`machine_hourly_rate`) **já inclui** o custo de energia (`energy_cost_per_hour`). Logo, `total_machine_cost` já contempla integralmente o valor de `total_energy_cost`.

### Impacto
Ao somar `total_machine_cost + total_energy_cost`, o custo de energia elétrica da impressora é contabilizado **duas vezes**.
Isso faz com que o campo `machine_energy_cost` retornado em `schemas.CostBreakdownTotals` fique inflado, e a soma das partes do custo exceda o custo base real (`base_cost`) dos projetos da oficina.

### Passos para Reproduzir
1. Cadastrar uma impressora com potência de 350W e energia R$ 0,95/kWh.
2. Criar um projeto com 10 horas de impressão na referida máquina.
3. Consultar `GET /api/projects/dashboard-stats`.
4. Comparar a soma de `cost_breakdown` com o somatório dos custos base dos projetos: a energia elétrica das impressoras aparece duplicada em `machine_energy_cost`.

### Solução Proposta
Em `backend/routes/project_routes.py`, linha 225, utilizar apenas `total_machine_cost` (ou separar adequadamente depreciação/manutenção e energia se desejado):
```python
machine_energy_cost += float(summary.get("total_machine_cost", 0.0) or 0.0)
```"""
    },
    {
        "title": "[BUG/DASHBOARD] Custos indiretos (Overhead) omitidos do gráfico de Estrutura de Custos da Oficina (Chart 3)",
        "labels": ["bug", "frontend", "dashboard", "ui"],
        "body": """### Descrição do Problema
O backend calcula com precisão e retorna em `schemas.CostBreakdownTotals` o somatório de custos indiretos de operação:
```python
overhead_cost=round(overhead_cost, 2)
```

No entanto, no frontend (`frontend/js/app.js`, função `renderDashboardCharts`, linhas 933-950), o gráfico de rosca "Estrutura de Custos & Lucro da Oficina" (`chart-cost-breakdown`) monta os vetores de dados e legendas da seguinte forma:
```javascript
const cbValues = cb ? [
    cb.material_cost || 0,
    cb.machine_energy_cost || 0,
    cb.labor_cost || 0,
    cb.bom_cost || 0,
    cb.net_profit || 0
] : [0, 0, 0, 0, 0];

const cbLabels = ['Filamento', 'Máquina & Energia', 'Mão de Obra', 'Insumos BOM', 'Lucro Líquido'];
```
O campo `cb.overhead_cost` foi completamente esquecido na montagem de `cbValues` e `cbLabels`.

### Impacto
Quando uma oficina 3D aloca custos indiretos nos orçamentos (como aluguel, internet, licença de fatiador/CAD ou custos fixos de embalagem), esses valores não aparecem na visualização de composição de custos do painel, gerando um gráfico financeiro incompleto.

### Passos para Reproduzir
1. Criar um orçamento preenchendo o campo "Overhead / Indiretos" com R$ 50,00.
2. Salvar o projeto e acessar o Dashboard (`#/dashboard`).
3. Analisar o gráfico de rosca "Estrutura de Custos & Lucro".
4. Notar que o valor de Overhead não compõe nenhuma fatia do gráfico.

### Solução Proposta
No arquivo `frontend/js/app.js`, incluir `cb.overhead_cost` em `cbValues`, `cbLabels` e na paleta `cbColors`:
```javascript
const cbValues = cb ? [
    cb.material_cost || 0,
    cb.machine_energy_cost || 0,
    cb.labor_cost || 0,
    cb.bom_cost || 0,
    cb.overhead_cost || 0,
    cb.net_profit || 0
] : [0, 0, 0, 0, 0, 0];

const cbLabels = ['Filamento', 'Máquina & Energia', 'Mão de Obra', 'Insumos BOM', 'Custos Indiretos (Overhead)', 'Lucro Líquido'];
const cbColors = ['#8b5cf6', '#3b82f6', '#f59e0b', '#64748b', '#ec4899', '#10b981'];
```"""
    },
    {
        "title": "[BUG/MÉTRICAS] Projetos com status 'cancelado' (cancelled) somados indevidamente no faturamento e lucro do gráfico temporal (Chart 2)",
        "labels": ["bug", "backend", "dashboard", "metrics"],
        "body": """### Descrição do Problema
No endpoint `GET /api/projects/dashboard-stats` (`backend/routes/project_routes.py`, linhas 247-251), ao acumular o histórico mensal em `monthly_data`:
```python
monthly_data[month_key]["revenue"] = round(monthly_data[month_key]["revenue"] + final_price, 2)
monthly_data[month_key]["base_cost"] = round(monthly_data[month_key]["base_cost"] + base_cost, 2)
monthly_data[month_key]["net_profit"] = round(monthly_data[month_key]["net_profit"] + net_profit, 2)
monthly_data[month_key]["print_hours"] = round(monthly_data[month_key]["print_hours"] + hours, 2)
monthly_data[month_key]["projects_count"] += 1
```

O laço itera sobre todos os projetos do usuário sem verificar o `proj.status`. Enquanto os cards de KPI (`total_revenue_approved`, `total_net_profit`) filtram estritamente os status aprovados/concluídos (`st in ["approved", "in_production", "completed"]`), o gráfico temporal de barras ("Faturamento & Lucratividade Temporal") soma orçamentos cancelados (`status == 'cancelled'`).

### Impacto
Um orçamento descartado ou recusado pelo cliente de R$ 5.000,00 entra no gráfico do mês como receita faturada e lucro auferido, distorcendo a análise de desempenho real da oficina.

### Passos para Reproduzir
1. Criar um projeto com valor final de R$ 1.000,00 e alterar o status para `Cancelado`.
2. Acessar o Dashboard (`#/dashboard`).
3. Observar o gráfico "Faturamento & Lucratividade Temporal" (Chart 2): a barra de faturamento e a linha de lucro líquido daquele mês aumentam em R$ 1.000,00, embora o projeto tenha sido cancelado.

### Solução Proposta
Em `backend/routes/project_routes.py`, ignorar projetos com `proj.status == 'cancelled'` ao agregar valores em `monthly_data`, ou somar em `revenue` apenas projetos com status de proposta aprovada/concluída:
```python
if st != "cancelled":
    # Contabilizar no histórico temporal apenas propostas válidas
    monthly_data[month_key]["revenue"] = round(monthly_data[month_key]["revenue"] + (final_price if st in ["approved", "in_production", "completed"] else 0.0), 2)
    ...
```"""
    },
    {
        "title": "[UX/FEAT] Ausência de campo para visualização e edição manual de peso de purga (purge_weight_g) no card da placa",
        "labels": ["enhancement", "frontend", "ux", "3d-printing"],
        "body": """### Descrição do Problema
O sistema conta com suporte completo a peso de purga em seu backend e parsers:
- Modelo no banco: `Plate.purge_weight_g` (`backend/models.py`)
- Motor de cálculo: `unit_raw_weight = part_weight_g + purge_weight_g` (`backend/engine.py`)
- Extrator 3MF: extração automática de purga e torre de transição de arquivos do Bambu Studio / OrcaSlicer (`frontend/js/parsers/threemf.js`)

Entretanto, na interface do usuário (`frontend/js/app.js`, função `renderPlates()`, linhas 1629-1664), o grid da placa exibe apenas:
- Tempo (horas e minutos)
- Filamento usado (g)
- Falha (%)
- Qtd Cópias

**Não existe nenhum campo de entrada para `purge_weight_g` no card da placa.**

### Impacto
1. Usuários que configuram impressões manuais multicoloridas (AMS / MMU / Toolchanger) não conseguem lançar o peso de purga descartado na torre de purga ou poço de descarte, subestimando o filamento consumido e o preço final.
2. Ao importar um arquivo `.3mf` que possui torre de purga, o usuário não tem como visualizar nem calibrar/editar os gramas de purga calculados pelo fatiador.

### Solução Proposta
No arquivo `frontend/js/app.js` (`renderPlates()`), adicionar a coluna de entrada para peso de purga:
```html
<div class="col-span-1 plate-field-col">
    <div class="plate-label-slot flex items-start justify-between gap-1 mb-1">
        <label class="text-[10px] font-medium text-slate-400 leading-tight">Purga (g)</label>
    </div>
    <input type="number" step="any" min="0" value="${plate.purge_weight_g || 0}" 
           oninput="state.currentPlates[${idx}].purge_weight_g = parseLocaleFloat(this.value, 0); recalcLiveSummary();" 
           class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white font-numeric focus:outline-none focus:border-blue-500" 
           placeholder="0">
</div>
```"""
    },
    {
        "title": "[UX/BUG] Botão 'Imprimir' na tela de pré-visualização (preview.html) dispara download do arquivo em vez da caixa de diálogo de impressão",
        "labels": ["bug", "frontend", "preview", "ux"],
        "body": """### Descrição do Problema
No visualizador de propostas comerciais (`frontend/preview.html`), a função `triggerPrint()` (linhas 245-254) executa:
```javascript
function triggerPrint() {
    const frame = document.getElementById('pdf-frame');
    if (frame && frame.contentWindow) {
        try {
            frame.contentWindow.print();
        } catch (e) {
            triggerDownload();
        }
    }
}
```

O iframe `#pdf-frame` recebe um `Blob URL` contendo dados binários `application/pdf`. Em navegadores modernos baseados em Chromium (Google Chrome, Microsoft Edge, Brave) e Firefox, carregar um PDF em iframe ativa o plugin embutido de PDF viewer do navegador. O acesso a `frame.contentWindow.print()` em um documento com plugin lança uma exceção de restrição de segurança do DOM ou `TypeError: print is not a function`.

O bloco `catch (e)` imediatamente redireciona para `triggerDownload()`.

### Impacto
O usuário clica no botão "Imprimir", mas a caixa de impressão da impressora física/virtual nunca se abre; em vez disso, o navegador faz o download do arquivo PDF para a pasta Downloads, tornando o botão "Imprimir" uma duplicata redundante do botão "Baixar PDF".

### Solução Proposta
Em `frontend/preview.html`, utilizar uma abordagem compatível para acionar a impressão:
1. Criar uma janela pop-up dedicada com a URL do PDF blob e invocar o método `print()` após o carregamento; ou
2. Utilizar `print()` direto caso o navegador suporte ou fornecer aviso/atalho de instrução claro (como o atalho de impressão nativo do leitor embutido)."""
    },
    {
        "title": "[UX/BUG] Importação individual de arquivo 3MF multi-placas substitui a placa alvo e descarta silenciosamente as demais placas do fatiamento",
        "labels": ["bug", "frontend", "slicer-import", "ux"],
        "body": """### Descrição do Problema
No Editor de Orçamentos, ao utilizar o botão individual "Importar 3MF/Gcode" presente no cabeçalho de uma placa (`frontend/js/app.js`, função `handleSinglePlateFile`, linhas 2368-2394), o código executa:
```javascript
const plates = await parse3mfMetadata(file);
if (plates.length > 0) {
    if (cleanName) {
        state.currentPlates[plateIdx].name = cleanName;
    }
    state.currentPlates[plateIdx].print_time_hours = plates[0].print_time_hours;
    state.currentPlates[plateIdx].part_weight_g = plates[0].part_weight_g;
    state.currentPlates[plateIdx].purge_weight_g = plates[0].purge_weight_g;
    state.currentPlates[plateIdx].slicer_filament_profile = cleanFilamentProfileName(plates[0].slicer_filament_profile, file.name) || null;
    ...
```

Se o usuário carregar um arquivo `.3mf` contendo um projeto completo de fatiador composto por 3 ou mais placas (comum no Bambu Studio e OrcaSlicer), o sistema aproveita apenas `plates[0]`. As demais placas (`plates[1]`, `plates[2]`, etc.) são **descartadas silenciosamente**, sem aviso nem opção de aproveitamento.

Em contrapartida, no dropzone principal (`handleSlicerFiles`), todas as placas do lote são adicionadas ao projeto.

### Impacto
Perda de dados de fatiamento: o usuário seleciona seu arquivo 3MF na placa acreditando que todo o projeto fatiado foi importado, mas as placas adicionais deixam de ser orçadas.

### Solução Proposta
Em `handleSinglePlateFile`:
Se `plates.length > 1`:
1. Atualizar a placa atual com `plates[0]`;
2. Inserir automaticamente as placas adicionais (`plates.slice(1)`) logo após o índice atual em `state.currentPlates`;
3. Exibir uma notificação explicativa: `Placa atualizada e ${plates.length - 1} nova(s) placa(s) adicionada(s) a partir do arquivo 3MF`.
4. Chamar `renderPlates()` e `recalcLiveSummary()`."""
    },
    {
        "title": "[FEAT/UX] Ordenação interativa por colunas (Nome, Cliente, Valor Final, Tempo, Status) na tabela de Orçamentos",
        "labels": ["enhancement", "frontend", "ux"],
        "body": """### Descrição do Problema
Na listagem geral de orçamentos (`frontend/js/app.js`, função `renderProjectsTable`), os projetos são renderizados sempre na ordem padrão de retorno da API (`id DESC`).

Os cabeçalhos da tabela:
- Projeto & Referência
- Cliente
- Placas
- Tempo Total
- Custo Base
- Preço de Venda
- Status

São elementos estáticos `<th>` sem interação de clique, sem estado de ordenação e sem indicadores visuais de ordenação (ascendente / descendente).

### Impacto
Oficinas com dezenas ou centenas de orçamentos cadastrados não conseguem ordenar a listagem para:
- Visualizar rapidamente os orçamentos de maior valor financeiro (Ticket Alto);
- Identificar trabalhos com maior tempo de impressão para planejar fila de máquinas;
- Agrupar pedidos por ordem alfabética de cliente.

### Solução Proposta
1. Adicionar variáveis de controle no estado global:
```javascript
state.projectSortField = 'id';
state.projectSortAsc = false;
```
2. Adicionar função `setProjectSort(field)` acionada pelo clique nos `<th>`.
3. Ordenar a lista `items` antes de renderizar as linhas da tabela.
4. Adicionar ícones de ordenação (Lucide `arrow-up-down`, `arrow-up`, `arrow-down`) nos cabeçalhos clicáveis."""
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

    # Fetch existing issues to avoid duplicating
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
