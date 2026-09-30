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

NEW_ISSUES = [
    {
        "title": "[BUG] Divergência de arredondamento comercial (1 centavo) entre o resumo dinâmico do Frontend e o cálculo oficial da Engine no Backend",
        "labels": ["bug", "frontend", "calculation-engine"],
        "body": """### Descrição do Problema
No cálculo financeiro de orçamentos, o backend calcula e arredonda a duas casas decimais cada etapa comercial (`backend/engine.py`):
```python
suggested_price = round((base_cost * (1.0 + (profit_margin_percent / 100.0))) / tax_divisor, 2)
discount_amount = round(suggested_price * (discount_percent / 100.0), 2)
subtotal_after_discount = round(suggested_price - discount_amount, 2)
tax_amount = round(subtotal_after_discount * (tax_rate_percent / 100.0), 2)
net_revenue = round(subtotal_after_discount - tax_amount, 2)
net_profit = round(net_revenue - base_cost, 2)
final_price_to_client = round(subtotal_after_discount + shipping_cost, 2)
```

No entanto, no frontend (`frontend/js/app.js`, função `recalcLiveSummary()`, linhas 1891-1901), as variáveis `suggestedPrice`, `discountAmount`, `subtotalAfterDiscount`, `taxAmount`, `netRevenue` e `finalPriceToClient` são mantidas com números de ponto flutuante contínuos sem arredondamento intermediário para centavos.

Como consequência, em orçamentos reais com margens ou impostos fracionários (ex: 40% margem, 6% imposto, 5% desconto), o frontend exibe na tela um valor com diferença de R$ 0,01 em relação ao valor gravado no banco e emitido no PDF da proposta comercial.

### Passos para Reproduzir
1. Abrir o navegador em `http://localhost:8000/#/project-editor` e criar um novo orçamento.
2. Adicionar uma placa: 3.5h de impressão, 120g de filamento (PLA a R$ 0,135/g), taxa horária R$ 2,44/h, 10% falha.
3. Adicionar 1 insumo BOM no valor de R$ 9,00.
4. Definir 1.0h CAD a R$ 80,00/h, margem de 40%, impostos de 6%, desconto de 5% e frete de R$ 25,00.
5. Observar os valores exibidos no card flutuante em tempo real no Frontend:
   - **Preço Sugerido**: `R$ 171,79`
   - **Preço Final**: `R$ 188,20`
   - **Lucro Líquido**: `R$ 38,06`
6. Salvar o orçamento e consultar o retorno da API (`GET /api/projects/{id}/summary`) ou o PDF:
   - **Preço Sugerido**: `R$ 171,80` (+R$ 0,01)
   - **Preço Final**: `R$ 188,21` (+R$ 0,01)
   - **Lucro Líquido**: `R$ 38,07` (+R$ 0,01)

### Solução Proposta
No arquivo `frontend/js/app.js`, alinhar a função `recalcLiveSummary()` para arredondar a 2 casas decimais em cada etapa matemática comercial:
```javascript
const suggestedPrice = baseCost > 0 
    ? Math.round(((baseCost * (1.0 + (marginPercent / 100.0))) / taxDivisor) * 100) / 100 
    : 0;

const discountAmount = Math.round(suggestedPrice * (discountPercent / 100.0) * 100) / 100;
const subtotalAfterDiscount = Math.round((suggestedPrice - discountAmount) * 100) / 100;
const taxAmount = Math.round(subtotalAfterDiscount * (taxPercent / 100.0) * 100) / 100;
const netRevenue = Math.round((subtotalAfterDiscount - taxAmount) * 100) / 100;
const netProfit = Math.round((netRevenue - baseCost) * 100) / 100;
const finalPriceToClient = Math.round((subtotalAfterDiscount + shippingCost) * 100) / 100;
```"""
    },
    {
        "title": "[SECURITY] Falta de sanitização contra XSS e quebra de layout na listagem de projetos e projetos recentes",
        "labels": ["bug", "security", "frontend", "ux"],
        "body": """### Descrição do Problema
No arquivo `frontend/js/app.js`, nas funções `renderProjectsTable()` (linhas 1236 e 1245) e `renderRecentProjects()` (linhas 1107 e 1111), os valores de `p.name` (nome do projeto) e `p.client_name` (nome do cliente) são interpolados diretamente na estrutura HTML sem qualquer sanitização ou escape de entidades HTML:
```javascript
// renderProjectsTable:
<p class="font-bold text-white group-hover:text-blue-400 transition-colors truncate">${p.name}</p>
<span class="truncate">${p.client_name}</span>

// renderRecentProjects:
<span class="font-semibold text-white group-hover:text-blue-400 transition-colors">${p.name}</span>
<span class="truncate">${p.client_name}</span>
```

### Impacto
1. **Quebra Visual**: Nomes técnicos comuns no meio industrial e maker como `Gabinete <V2> Inox` ou `Cliente <Empresa & Cia>` fazem com que o navegador interprete `<V2>` como uma tag HTML customizada não finalizada. Isso faz a tag desaparecer da tela ou corrompe toda a tabela de orçamentos.
2. **Segurança (Stored XSS)**: Se um usuário mal-intencionado ou um cliente que preenche um formulário externo injetar tags como `<img src=x onerror=...>` ou `<svg onload=...>`, o script executa diretamente na sessão do usuário no navegador.

### Passos para Reproduzir
1. Criar um projeto com o nome `Suporte <V2> Náutico` e cliente `Alpha <Corp> & Tech`.
2. Navegar para a tela \"Orçamentos\" (`#view-projects`) ou para o Dashboard.
3. Observar que o texto `<V2>` e `<Corp>` são suprimidos da visualização porque foram convertidos em elementos DOM inválidos no `innerHTML`.

### Solução Proposta
Criar uma função utilitária `escapeHtml` no frontend:
```javascript
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
```
E utilizar `escapeHtml(p.name)` e `escapeHtml(p.client_name)` em todas as renderizações de tabelas e cartões."""
    },
    {
        "title": "[BUG] Importação de G-Code individual para placa não reseta peso de purga residual de importações 3MF anteriores",
        "labels": ["bug", "parsers", "frontend"],
        "body": """### Descrição do Problema
No arquivo `frontend/js/app.js`, a função `handleSinglePlateFile(e, plateIdx)` permite ao usuário carregar arquivos `.3mf`, `.gcode.3mf` ou `.gcode` para preencher os dados técnicos de uma placa existente.

Ao importar arquivos `.3mf` contendo torre de purga (comum em arquivos do Bambu Studio ou OrcaSlicer com AMS), a propriedade `state.currentPlates[plateIdx].purge_weight_g` é preenchida:
```javascript
state.currentPlates[plateIdx].part_weight_g = plates[0].part_weight_g;
state.currentPlates[plateIdx].purge_weight_g = plates[0].purge_weight_g;
```

Porém, se o usuário substituir essa placa importando em seguida um arquivo `.gcode` convencional (peça em cor única fatiada no Cura ou PrusaSlicer):
```javascript
state.currentPlates[plateIdx].print_time_hours = meta.print_time_hours;
state.currentPlates[plateIdx].part_weight_g = meta.part_weight_g;
// purge_weight_g NÃO É RESETADO!
```

### Impacto
O peso de purga do arquivo 3MF anterior permanece no estado da placa em memória (`state.currentPlates[plateIdx].purge_weight_g`). Na função `recalcLiveSummary()`:
```javascript
const rawWeight = (plate.part_weight_g || 0) + (plate.purge_weight_g || 0);
```
O cálculo soma indevidamente os gramas de purga antigos ao peso da nova peça de G-code, inflando o custo de material e superestimando o valor final apresentado ao cliente sem que o usuário perceba.

### Passos para Reproduzir
1. Abrir o editor de orçamentos.
2. Na placa 1, clicar em \"Importar 3MF/Gcode\" e carregar um arquivo `.3mf` multimaterial que tenha torre de purga (ex: 35g).
3. Na mesma placa, clicar novamente em \"Importar 3MF/Gcode\" e selecionar um arquivo `.gcode` de peça única de 50g.
4. Inspecionar o peso total exibido no resumo: o sistema calcula 85g (50g do G-code + 35g de purga residual fantasma).

### Solução Proposta
No arquivo `frontend/js/app.js`, dentro de `handleSinglePlateFile`, adicionar explicitamente `purge_weight_g: 0` no bloco do G-Code:
```javascript
state.currentPlates[plateIdx].print_time_hours = meta.print_time_hours;
state.currentPlates[plateIdx].part_weight_g = meta.part_weight_g;
state.currentPlates[plateIdx].purge_weight_g = 0;
```"""
    },
    {
        "title": "[BUG] Formatação de telefone corrompe DDD e trunca dígitos ao colar números com código DDI internacional (+55 ou 55)",
        "labels": ["bug", "frontend", "ux"],
        "body": """### Descrição do Problema
No arquivo `frontend/js/app.js`, a função `formatPhoneInput(value)` aplica máscara brasileira em tempo real nos campos `#proj-client-phone` e `#pref-phone`:
```javascript
function formatPhoneInput(value) {
    if (!value) return '';
    const digits = String(value).replace(/\D/g, '').slice(0, 11);
    if (digits.length <= 2) {
        return digits.length > 0 ? `(${digits}` : '';
    }
    if (digits.length <= 6) {
        return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
    }
    if (digits.length <= 10) {
        return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
    }
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7, 11)}`;
}
```

No dia a dia comercial, números copiados de conversas do WhatsApp, contatos do smartphone ou vCards frequentemente vêm acompanhados do código do país DDI `+55` ou `55` (ex: `+55 11 98888-7777` ou `5511988887777`, com 12 ou 13 dígitos).

Ao aplicar `.slice(0, 11)` diretamente sobre os dígitos brutos, a função captura `55119888877`, tratando o DDI `55` como se fosse o DDD (código de área), e corta os dois últimos dígitos reais (`77`) do telefone. O resultado exibido e gravado torna-se `(55) 11988-8877`.

### Passos para Reproduzir
1. Abrir a tela de Orçamento ou Preferências.
2. Colar no campo \"Telefone / WhatsApp Comercial\": `+55 11 98888-7777`.
3. Observar o campo formatado: `(55) 11988-8877`.
4. Os dígitos finais foram perdidos e o DDD 55 é inválido.

### Solução Proposta
No arquivo `frontend/js/app.js`, higienizar o prefixo `55` quando a quantidade total de dígitos for 12 ou 13:
```javascript
function formatPhoneInput(value) {
    if (!value) return '';
    let digits = String(value).replace(/\D/g, '');
    if ((digits.length === 12 || digits.length === 13) && digits.startsWith('55')) {
        digits = digits.slice(2);
    }
    digits = digits.slice(0, 11);
    if (digits.length <= 2) {
        return digits.length > 0 ? `(${digits}` : '';
    }
    if (digits.length <= 6) {
        return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
    }
    if (digits.length <= 10) {
        return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
    }
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7, 11)}`;
}
```"""
    },
    {
        "title": "[BUG] Duplicação ou exclusão de orçamentos a partir do Dashboard não atualiza a tabela de projetos recentes",
        "labels": ["bug", "frontend", "dashboard", "ux"],
        "body": """### Descrição do Problema
No painel principal do Dashboard (`#view-dashboard`), a seção \"Orçamentos Recentes\" (`#dashboard-recent-projects`) exibe a lista dos 5 orçamentos mais recentes com botões de ação para editar, duplicar, gerar PDF e excluir.

Ao clicar no botão de duplicação (`duplicateProject(p.id)`) ou exclusão (`deleteProject(p.id)`), as funções correspondentes em `frontend/js/app.js` executam:
```javascript
async function duplicateProject(id) {
    try {
        await API.projects.duplicate(id);
        showToast('Projeto duplicado com sucesso!', 'success');
        await loadAllData();
        renderProjectsTable(); // Atualiza apenas a tela de Projetos!
    } catch (err) {
        showToast(err.message, 'error');
    }
}
```

### Impacto
Quando a ação é disparada a partir do Dashboard, o toast informa o sucesso da operação, porém a tabela do Dashboard permanece inalterada (o projeto duplicado não aparece, ou o projeto excluído continua visível). O usuário precisa navegar para outra tela ou dar F5 para visualizar a alteração no Dashboard.

### Passos para Reproduzir
1. Acessar o Dashboard (`#/dashboard`).
2. Localizar um projeto na tabela \"Orçamentos Recentes\".
3. Clicar no botão de ícone de cópia para duplicar o projeto.
4. Notar a notificação de sucesso verde, mas a tabela de projetos recentes permanece estática sem o novo projeto duplicado.

### Solução Proposta
Em `duplicateProject(id)` e `deleteProject(id)` em `frontend/js/app.js`, renderizar o dashboard caso o usuário esteja nele ou atualizar ambas as visualizações:
```javascript
await loadAllData();
renderProjectsTable();
if (state.activeView === 'dashboard') {
    renderDashboard();
    renderRecentProjects();
}
```"""
    },
    {
        "title": "[SECURITY/IDOR] Vulnerabilidade de autorização permite associar placas a impressoras e filamentos de outros usuários",
        "labels": ["bug", "security", "backend"],
        "body": """### Descrição do Problema
Nos endpoints de criação e edição individual de placas de impressão (`backend/routes/project_routes.py`):
- `POST /api/projects/{project_id}/plates` (linhas 460-461)
- `PUT /api/projects/{project_id}/plates/{plate_id}` (linhas 490-491)

A busca das entidades relacionadas `Printer` e `Filament` para o cálculo do detalhamento de custo (`calculate_plate_cost`) é realizada filtrando apenas pela chave primária, sem validar o `user_id`:
```python
printer = db.query(models.Printer).filter(models.Printer.id == plate.printer_id).first() if plate.printer_id else None
filament = db.query(models.Filament).filter(models.Filament.id == plate.filament_id).first() if plate.filament_id else None
```

### Impacto (Insecure Direct Object Reference - IDOR)
Um usuário autenticado pode criar ou editar uma placa enviando o `printer_id` ou `filament_id` pertencente a qualquer outro usuário ou oficina cadastrada no banco PostgreSQL multi-inquilino.

Na resposta JSON da API, o campo `cost_breakdown` é enriquecido contendo:
- `printer_name`: Nome da máquina da outra oficina.
- `machine_hourly_rate`: Taxa horária da máquina configurada pelo concorrente.
- `filament_name` e `filament_material`: Marca, cor e tipo de material do outro usuário.
- `cost_per_gram`: Custo por grama pago pelo outro usuário.

Isso configura vazamento indevido de dados comerciais confidenciais entre contas.

### Solução Proposta
Nos endpoints de placas em `backend/routes/project_routes.py`, filtrar obrigatoriamente pelo `current_user.id`:
```python
printer = db.query(models.Printer).filter(
    models.Printer.id == plate.printer_id,
    models.Printer.user_id == current_user.id
).first() if plate.printer_id else None

filament = db.query(models.Filament).filter(
    models.Filament.id == plate.filament_id,
    models.Filament.user_id == current_user.id
).first() if plate.filament_id else None
```"""
    },
    {
        "title": "[BUG] Crash HTTP 500 no backend ao salvar ou atualizar projeto referenciando impressora ou filamento excluído",
        "labels": ["bug", "backend"],
        "body": """### Descrição do Problema
No endpoint de atualização de orçamentos (`PUT /api/projects/{project_id}` em `backend/routes/project_routes.py`), ao salvar um projeto com placas:
```python
if proj_update.plates is not None:
    project.plates.clear()
    for p_data in proj_update.plates:
        plate = models.Plate(
            project_id=project.id,
            **p_data.model_dump()
        )
        db.add(plate)

db.commit()
```

Se o usuário tiver excluído uma impressora ou filamento na tela de cadastros e em seguida salvar um orçamento que ainda continha aquele `printer_id` ou `filament_id` selecionado, a execução do `db.commit()` dispara uma exceção `sqlalchemy.exc.IntegrityError` de violação de chave estrangeira (`plates_printer_id_fkey`).

Como não há bloco `try...except` ou validação prévia de existência das chaves estrangeiras, o FastAPI retorna um erro 500 não tratado (*Internal Server Error*), impedindo o usuário de salvar seu trabalho e gerando uma notificação toast de erro no frontend.

### Passos para Reproduzir
1. Criar uma impressora chamada \"Impressora Teste\".
2. Criar um orçamento e selecionar a \"Impressora Teste\" na Placa 1.
3. Abrir a tela de impressoras e excluir a \"Impressora Teste\".
4. Retornar ao orçamento e clicar em \"Salvar Orçamento\".
5. O backend responde com status HTTP 500 e erro de chave estrangeira no log.

### Solução Proposta
No backend (`backend/routes/project_routes.py`), antes de associar os IDs de impressora e filamento à nova placa:
1. Validar se o `printer_id` e `filament_id` existem no banco para o `current_user.id`.
2. Caso o registro não exista mais (tenha sido excluído), atribuir `None` ao campo e definir a taxa horária manual de fallback (`custom_printer_hourly_rate` ou `custom_filament_cost_per_g`), evitando o crash de chave estrangeira e preservando o salvamento íntegro do orçamento."""
    },
    {
        "title": "[UX/FEAT] Ausência de estado vazio visual e aviso explicativo ao remover todas as placas no Editor de Orçamentos",
        "labels": ["enhancement", "frontend", "ux"],
        "body": """### Descrição da Solicitação
No editor de orçamentos (`#view-project-editor`), cada placa de impressão possui um botão de exclusão com ícone de lixeira (`removePlateRow(idx)`).

Quando o usuário exclui todas as placas da lista, a função `renderPlates()` (`frontend/js/app.js`) executa `container.innerHTML = state.currentPlates.map(...).join('')`, resultando em uma string vazia `""`.

Diferente da seção de componentes (BOM), que renderiza um card pontilhado com ícone, mensagem amigável e botão para adicionar o primeiro insumo, a área de placas torna-se um espaço em branco invisível, sem qualquer indicação de que o orçamento está sem peças para fatiamento ou instrução de como adicionar uma nova placa.

Além disso, o usuário pode clicar em \"Salvar Orçamento\" e submeter um orçamento vazio sem placas.

### Solução Proposta
1. **Em `renderPlates()` (`frontend/js/app.js`)**:
   Quando `state.currentPlates.length === 0`, renderizar um card de Empty State com visual padronizado:
   ```html
   <div class="p-8 rounded-xl bg-slate-900/40 border border-dashed border-slate-800/80 text-center flex flex-col items-center justify-center space-y-3">
       <div class="w-12 h-12 rounded-2xl bg-blue-600/10 text-blue-400 border border-blue-500/20 flex items-center justify-center">
           <i data-lucide="layers" class="w-6 h-6"></i>
       </div>
       <p class="text-sm font-semibold text-white">Nenhuma placa de impressão configurada</p>
       <p class="text-xs text-slate-400 max-w-sm">Adicione arquivos 3MF/G-code ou configure placas manualmente para calcular o tempo de máquina e filamento.</p>
       <button type="button" onclick="addNewPlateRow()" class="py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-md shadow-blue-600/20">
           <i data-lucide="plus" class="w-4 h-4"></i> Adicionar Placa
       </button>
   </div>
   ```
2. **Em `saveCurrentProject()`**:
   Emitir aviso caso o usuário tente salvar um orçamento com 0 placas e 0 insumos BOM, evitando propostas zeradas."""
    }
]

def publish_issues():
    token = get_token()
    if not token:
        print("❌ Erro: Token do GitHub não encontrado via Git Credential Manager.")
        sys.exit(1)

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Splendid-Hypatia-BugHunter",
        "Content-Type": "application/json"
    }

    # Fetch existing issues to avoid duplicating
    print(f"Obtendo issues existentes de {REPO}...")
    req = urllib.request.Request(f"{API_BASE}/issues?state=all&per_page=100", headers=headers)
    with urllib.request.urlopen(req) as resp:
        existing = json.loads(resp.read().decode())

    existing_titles = {i["title"].strip(): i for i in existing}
    print(f"Total de issues existentes no repositório: {len(existing_titles)}")

    created = []
    for item in NEW_ISSUES:
        title = item["title"].strip()
        if title in existing_titles:
            existing_issue = existing_titles[title]
            print(f"⏭️  Issue já existe: #{existing_issue['number']} - {title}")
            created.append(existing_issue)
            continue

        print(f"\nCriando issue: {title}...")
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
                created.append(res_data)
        except urllib.error.HTTPError as e:
            print(f"❌ Erro HTTP {e.code} ao criar issue '{title}': {e.reason}")
            print(e.read().decode())

    print(f"\n🎉 Processamento concluído! Total de {len(created)} issues cadastradas/verificadas.")

if __name__ == "__main__":
    publish_issues()
