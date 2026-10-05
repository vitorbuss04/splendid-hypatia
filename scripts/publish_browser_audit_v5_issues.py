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
        "title": "[SECURITY/XSS] Falha de Cross-Site Scripting (XSS) no grid de impressoras por interpolação direta de nome e modelo sem escapeHtml",
        "labels": ["security", "frontend", "bug"],
        "body": """### Descrição do Problema
Na renderização dos cards da listagem de impressoras (`renderPrintersGrid` em `frontend/js/app.js`), os campos `p.name` e `p.model` são concatenados diretamente via template string no `innerHTML` do elemento `#printers-grid`:

```javascript
<h4 class="font-bold text-white text-base">${p.name}</h4>
<p class="text-xs text-slate-400">${p.model || 'FDM'}</p>
```

Além disso, na mensagem de estado vazio do filtro de busca por impressoras (linhas 2788-2790), o termo digitado pelo usuário (`term`) também é interpolado sem sanitização:
```javascript
term ? `busca "<strong class="text-white">${term}</strong>"` : ''
```

Diferente da tabela de projetos (`renderProjectsTable`) onde a sanitização com `escapeHtml()` foi implementada, na tela de impressoras o conteúdo é injetado diretamente no DOM sem tratamento.

### Impacto
- **Cross-Site Scripting Armazenado (Stored XSS)**: Se um usuário cadastrar uma impressora com payload malicioso (ex: `<img src=x onerror=...>` ou tags `<script>`), o script é executado no contexto da sessão de qualquer usuário visualizando o catálogo de impressoras.
- **Cross-Site Scripting Refletido no Filtro (DOM XSS)**: A digitação de payload no campo `#printer-search-input` pode forçar a injeção de elementos arbitrários quando nenhum resultado é retornado.
- **Risco de Roubo de Sessão**: O token JWT (`auth_token`) mantido no `localStorage` pode ser exfiltrado por scripts maliciosos.

### Passos para Reproduzir
1. Acessar a tela "Minhas Impressoras" (`#/printers`).
2. Clicar em "+ Cadastrar Impressora".
3. No campo "Nome / Identificação", preencher `<img src=x onerror="alert('XSS Printer')">`.
4. Salvar a impressora.
5. Observar a execução do script ou injeção da tag HTML no DOM.
6. Digitar `<b id="test">xss</b>` no campo de busca de impressoras até cair no estado vazio e inspecionar o DOM.

### Arquivo e Linhas Afetadas
- `frontend/js/app.js`: linhas 2788-2790 e 2812-2813.

### Solução Proposta
Envolver as variáveis `p.name`, `p.model` e `term` na função `escapeHtml()`:
```javascript
<h4 class="font-bold text-white text-base">${escapeHtml(p.name)}</h4>
<p class="text-xs text-slate-400">${escapeHtml(p.model || 'FDM')}</p>
```
E no filtro:
```javascript
term ? `busca "<strong class="text-white">${escapeHtml(term)}</strong>"` : ''
```
"""
    },
    {
        "title": "[SECURITY/XSS] Falha de Cross-Site Scripting (XSS) no grid de filamentos por interpolação direta de nome, marca e cor sem escapeHtml",
        "labels": ["security", "frontend", "bug"],
        "body": """### Descrição do Problema
Na renderização dos cards da listagem de filamentos (`renderFilamentsGrid` em `frontend/js/app.js`), os campos `f.name`, `f.brand` e `f.color` são concatenados diretamente via template string no `innerHTML` do elemento `#filaments-grid`:

```javascript
<h4 class="font-bold text-white text-sm">${f.name}</h4>
...
<span>${f.brand || 'Genérico'} • ${f.color || 'Cor padrão'}</span>
```

Da mesma forma, no estado vazio do filtro de filamentos (linhas 3078-3082), os termos de busca `term` e o filtro de material `material` são concatenados sem sanitização:
```javascript
const filterDesc = [
    term ? `busca "<strong class="text-white">${term}</strong>"` : '',
    material ? `material "<strong class="text-white">${material}</strong>"` : ''
].filter(Boolean).join(' e ');
```

### Impacto
- **Stored XSS**: Filamentos cadastrados com caracteres especiais ou vetores de ataque HTML têm suas tags renderizadas diretamente no navegador.
- **Quebra de Layout / Defacement**: Nomes com tags HTML ou aspas não tratadas corrompem a estrutura flex/grid do catálogo.
- **Risco de Comprometimento de Credenciais**: Execução indevida de JavaScript no mesmo domínio da aplicação e acesso ao `localStorage` contendo o JWT do usuário.

### Passos para Reproduzir
1. Acessar a tela "Meus Filamentos" (`#/filaments`).
2. Abrir o modal de criação de filamento.
3. Inserir `<b id="fil-xss">Teste</b>` no campo de marca ou cor.
4. Salvar o filamento e observar que o texto é interpretado como tag HTML rica no grid de filamentos.
5. No input `#filament-search-input`, digitar `<img src=x onerror="alert('fil xss')">` e acionar o filtro sem correspondências.

### Arquivo e Linhas Afetadas
- `frontend/js/app.js`: linhas 3078-3082 e 3111-3115.

### Solução Proposta
Aplicar `escapeHtml()` nas propriedades renderizadas:
```javascript
<h4 class="font-bold text-white text-sm">${escapeHtml(f.name)}</h4>
...
<span>${escapeHtml(f.brand || 'Genérico')} • ${escapeHtml(f.color || 'Cor padrão')}</span>
```
E nas mensagens de busca:
```javascript
term ? `busca "<strong class="text-white">${escapeHtml(term)}</strong>"` : '',
material ? `material "<strong class="text-white">${escapeHtml(material)}</strong>"` : ''
```
"""
    },
    {
        "title": "[UX/BUG] Inputs de taxa horária e custo de filamento manual ficam ocultos quando placa referencia ID de impressora ou filamento inexistente/excluído",
        "labels": ["frontend", "ux", "bug"],
        "body": """### Descrição do Problema
No editor de placas do projeto (`renderPlates` em `frontend/js/app.js`), o usuário pode selecionar uma impressora cadastrada ou optar por "Personalizada (Manual)":

```javascript
<select onchange="updatePlatePrinter(${idx}, this.value)" class="w-full ...">
    <option value="">Personalizada (Manual)</option>
    ${state.printers.map(p => `
        <option value="${p.id}" ${plate.printer_id === p.id ? 'selected' : ''}>
            ${p.name} (R$ ${p.machine_hourly_rate.toFixed(2)}/h)
        </option>
    `).join('')}
</select>
${!plate.printer_id ? `
    <div class="mt-1.5 flex items-center gap-1.5 bg-slate-800/60 p-1.5 rounded-lg border border-slate-700/60">
        <span class="text-[10px] text-amber-400 font-medium">Taxa manual:</span>
        <span class="text-[10px] text-slate-400">R$</span>
        <input type="number" step="any" min="0" value="${plate.custom_printer_hourly_rate ?? 2.50}" ...>
    </div>
` : ''}
```

O mesmo padrão é utilizado para o seletor de filamento (`${!plate.filament_id ? ... : ''}`).

Quando uma impressora ou filamento que estava associado a um orçamento é **excluído** do sistema (ou se o projeto for carregado com IDs órfãos):
1. O elemento `<select>` procura uma `<option value="${p.id}">` correspondente ao ID. Como o ID não existe em `state.printers`, nenhuma opção é marcada com `selected`.
2. Por padrão de navegadores HTML, o `<select>` passa a exibir a primeira opção disponível: **"Personalizada (Manual)"**.
3. No entanto, `plate.printer_id` no objeto JavaScript ainda contém o valor inteiro antigo (ex: `15`).
4. Como `plate.printer_id` é avaliado como truthy (`!15 === false`), o bloco `${!plate.printer_id ? ... : ''}` **não é renderizado**.
5. O mesmo comportamento ocorre com o filamento (`plate.filament_id`).

### Impacto
- **Bloqueio de Interface / UX Confusa**: O usuário vê o campo selecionado como "Personalizada (Manual)", mas não existe nenhum campo de input para digitar a taxa horária manual ou custo por grama manual.
- **Cálculo Silencioso com Taxa Oculta**: A calculadora aplica taxas em segundo plano sem que o usuário consiga ver ou alterar o valor no card da placa.

### Passos para Reproduzir
1. Cadastrar uma impressora e criar um orçamento vinculando uma placa a essa impressora.
2. Salvar o orçamento.
3. Ir na tela de impressoras e excluir a impressora.
4. Abrir o orçamento para edição.
5. Observar o card da placa: o dropdown exibe "Personalizada (Manual)", porém a caixa "Taxa manual: R$ [input] /h" está invisível.

### Arquivo e Linhas Afetadas
- `frontend/js/app.js`: linhas 1729 e 1763.

### Solução Proposta
Verificar se o ID existe na lista ativa de impressoras/filamentos:
```javascript
const hasValidPrinter = plate.printer_id && state.printers.some(p => p.id === plate.printer_id);
const hasValidFilament = plate.filament_id && state.filaments.some(f => f.id === plate.filament_id);
```
E condicionar a renderização dos inputs manuais a `!hasValidPrinter` e `!hasValidFilament`.
"""
    },
    {
        "title": "[BUG/MÉTRICAS] Gráfico temporal de Faturamento e Lucratividade (Chart 2) soma Custo Base de orçamentos em Rascunho ('draft') e Orçados ('quoted'), distorcendo o balanço mensal",
        "labels": ["backend", "metrics", "bug"],
        "body": """### Descrição do Problema
No endpoint de estatísticas do painel (`get_dashboard_stats` em `backend/routes/project_routes.py`), os dados mensais para o gráfico de Faturamento & Lucratividade Temporal (Chart 2) são acumulados da seguinte forma:

```python
monthly_data[month_key]["revenue"] = round(monthly_data[month_key]["revenue"] + (final_price if st in ["approved", "in_production", "completed"] else 0.0), 2)
monthly_data[month_key]["base_cost"] = round(monthly_data[month_key]["base_cost"] + base_cost, 2)
monthly_data[month_key]["net_profit"] = round(monthly_data[month_key]["net_profit"] + (net_profit if st in ["approved", "in_production", "completed"] else 0.0), 2)
```

Observe que:
- `revenue` (Faturamento) é somado **apenas** quando o status é `approved`, `in_production` ou `completed`.
- `net_profit` (Lucro Líquido) é somado **apenas** quando o status é `approved`, `in_production` ou `completed`.
- Porém, `base_cost` (Custo Base) é somado **incondicionalmente** para todos os projetos que não são `cancelled`, incluindo orçamentos em `draft` (Rascunho) e `quoted` (Aguardando resposta do cliente).

### Impacto
- **Distorção Contábil Crítica**: Se um usuário simular ou cadastrar 5 orçamentos em rascunho com alto consumo de material para teste, o custo base desses rascunhos é somado no mês atual, enquanto a receita correspondente permanece 0.
- **Gráfico Ilógico**: O gráfico exibe barras com Custo Base muito superior ao Faturamento (aparentando prejuízo operacional massivo), ao mesmo tempo em que a linha de Lucro Líquido permanece positiva (porque vem apenas dos projetos aprovados). Exemplo capturado em auditoria: Faturamento R$ 208,83, Custo Base R$ 2.671,00 e Lucro Líquido R$ 45,30 no mesmo mês.

### Passos para Reproduzir
1. Criar um projeto aprovado com Faturamento de R$ 200,00 e Custo Base de R$ 100,00.
2. Criar 3 orçamentos em status `draft` (rascunho) totalizando R$ 3.000,00 de custo base.
3. Acessar o Dashboard e visualizar o "Gráfico 2: Faturamento & Lucratividade Temporal".
4. Observar que a barra de Custo Base reflete R$ 3.100,00, a barra de Faturamento reflete apenas R$ 200,00 e a linha de Lucro Líquido indica R$ 100,00.

### Arquivo e Linhas Afetadas
- `backend/routes/project_routes.py`: linha 249.

### Solução Proposta
Somar o `base_cost` no gráfico temporal apenas para os projetos cujas receitas e lucros foram realizados (`approved`, `in_production`, `completed`):
```python
is_realized = st in ["approved", "in_production", "completed"]
monthly_data[month_key]["revenue"] = round(monthly_data[month_key]["revenue"] + (final_price if is_realized else 0.0), 2)
monthly_data[month_key]["base_cost"] = round(monthly_data[month_key]["base_cost"] + (base_cost if is_realized else 0.0), 2)
monthly_data[month_key]["net_profit"] = round(monthly_data[month_key]["net_profit"] + (net_profit if is_realized else 0.0), 2)
```
"""
    },
    {
        "title": "[BUG/CÁLCULO] Calculadora em tempo real (recalcLiveSummary) não limita valores negativos em descontos, margens, taxas e quantidade de placas gerando inconsistências visuais e erro HTTP 422",
        "labels": ["frontend", "bug"],
        "body": """### Descrição do Problema
Na rotina de cálculo em tempo real do frontend (`recalcLiveSummary` em `frontend/js/app.js`), os campos numéricos são lidos sem a garantia de limite mínimo `Math.max(0, ...)`:

```javascript
const marginPercent = parseLocaleFloat(document.getElementById('proj-margin')?.value, 30);
const taxPercent = Math.min(99, parseLocaleFloat(document.getElementById('proj-tax')?.value, 0));
const discountPercent = Math.min(100, parseLocaleFloat(document.getElementById('proj-discount')?.value, 0));
const shippingCost = parseLocaleFloat(document.getElementById('proj-shipping')?.value, 0);
```

E no cálculo de placas:
```javascript
const qty = plate.quantity || 1;
```
Se o usuário digitar um valor negativo ou o input contiver `-2`:
1. `discountPercent` aceita `-20`, calculando um desconto negativo (que aumenta o preço final de venda).
2. A exibição do desconto na linha `#live-discount-amount` renderiza `- -R$ 10,00` (sinal de menos duplo).
3. Se `plate.quantity` for digitado como negativo (ex: `-1`), `qty` torna-se negativo e inverte as horas, peso e custo da placa.
4. Ao clicar em "Salvar Projeto", o backend rejeita com HTTP 422 Unprocessable Entity (`quantity: ge=1`, `discount_percent: ge=0`, etc.), enquanto o frontend no terminal exibia valores calculados divergentes.

No backend (`backend/engine.py` linhas 254-257), os limites são rigorosamente tratados com `max(0.0, ...)`:
```python
profit_margin_percent = max(0.0, _get_val("profit_margin_percent", 30.0))
tax_rate_percent = max(0.0, min(99.0, _get_val("tax_rate_percent", 6.0)))
discount_percent = max(0.0, min(100.0, _get_val("discount_percent", 0.0)))
shipping_cost = max(0.0, _get_val("shipping_cost", 0.0))
```

### Impacto
- **Divergência entre Frontend e Backend**: A simulação ao vivo na tela exibe valores inconsistentes com o que será persistido pelo servidor.
- **Falha de Validação**: O usuário recebe erro 422 ao tentar salvar sem entender o motivo de o cálculo visual ter permitido a entrada.
- **Glitches de UI**: Exibição de duplo sinal negativo (`- -R$`) no resumo financeiro.

### Passos para Reproduzir
1. Abrir um orçamento no editor (`#/project-editor`).
2. Digitar `-15` no campo "Desconto Comercial (%)".
3. Observar a linha "Desconto Comercial" no terminal à direita exibir `- -R$ XX,XX` e o preço final aumentar.
4. Digitar `-2` na quantidade de cópias da placa e observar os custos e horas ficarem negativos.

### Arquivo e Linhas Afetadas
- `frontend/js/app.js`: linhas 2040 e 2093-2096.

### Solução Proposta
Aplicar limites inferiores nos valores lidos em `recalcLiveSummary`:
```javascript
const qty = Math.max(1, parseInt(plate.quantity, 10) || 1);
const marginPercent = Math.max(0, parseLocaleFloat(document.getElementById('proj-margin')?.value, 30));
const taxPercent = Math.max(0, Math.min(99, parseLocaleFloat(document.getElementById('proj-tax')?.value, 0)));
const discountPercent = Math.max(0, Math.min(100, parseLocaleFloat(document.getElementById('proj-discount')?.value, 0)));
const shippingCost = Math.max(0, parseLocaleFloat(document.getElementById('proj-shipping')?.value, 0));
```
"""
    }
]

def publish():
    token = get_token()
    if not token:
        print("❌ Git token não encontrado via git credential fill!")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "BrowserAuditHunterV5",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }

    # Fetch existing issues to avoid duplicating
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
