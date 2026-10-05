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
        "title": "[SECURITY/XSS] Falha de Cross-Site Scripting (XSS) no Grid de Filamentos por interpolação direta de color_hex no atributo style sem escapeHtml",
        "labels": ["security", "frontend", "bug"],
        "body": """### Descrição do Problema
Na renderização dos cards de filamentos no Grid de Filamentos (`renderFilamentsGrid` em `frontend/js/app.js`), os valores de `f.color_hex` são interpolados diretamente nos atributos `style` do elemento `<div>` e `<span>` sem sanitização por `esc()` ou `escapeHtml()`:

```javascript
// Linhas 3112-3113:
<div class="w-10 h-10 rounded-xl border border-slate-700/60 flex items-center justify-center relative shadow-sm" style="background-color: ${f.color_hex || '#10b981'}22;">
    <span class="w-4 h-4 rounded-full border border-white/30 shadow-sm" style="background-color: ${f.color_hex || '#10b981'};"></span>
</div>
```

Embora na linha 3123 `esc(f.color_hex)` tenha sido aplicado na cor do marcador de texto, as linhas 3112 e 3113 não utilizam `esc()`. Além disso, no backend (`backend/schemas.py`), os schemas `FilamentBase` e `FilamentUpdate` não possuem validação de padrão regex para cores em formato hexadecimal (`#RRGGBB`).

### Impacto
- **Cross-Site Scripting Armazenado (Stored XSS)**: Se um usuário cadastrar um filamento com o campo `color_hex` contendo quebra de atributo (ex: `"><img src=x onerror=...`), ao acessar a tela "Meus Filamentos" (`#/filaments`), o navegador quebra a tag e executa scripts arbitrários no contexto da aplicação.
- **Risco de Segurança**: Exfiltração do token JWT da sessão (`auth_token`) e acesso não autorizado a orçamentos e dados de clientes.

### Passos para Reproduzir
1. Criar um filamento via API ou formulário com payload de cor:
   `"color_hex": "\"><img src=x onerror=alert(document.domain)>"`
2. Acessar a tela "Meus Filamentos" (`#/filaments`).
3. Inspecionar o DOM e constatar a injeção do elemento e a execução do script.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 3112-3113.
- `backend/schemas.py`: linhas 100 e 115 (`FilamentBase` e `FilamentUpdate`).

### Solução Proposta
1. Em `frontend/js/app.js`, sanitizar a interpolação com `esc()`:
```javascript
style="background-color: ${esc(f.color_hex || '#10b981')}22;"
style="background-color: ${esc(f.color_hex || '#10b981')};"
```
2. Em `backend/schemas.py`, adicionar validação de padrão regex de cor hexadecimal:
```python
color_hex: Optional[str] = Field("#10b981", pattern=r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3}|[A-Fa-f0-9]{8})$")
```
"""
    },
    {
        "title": "[SECURITY/XSS] Falha de Cross-Site Scripting (XSS) e ausência de validação de status de projeto nas listagens de orçamentos",
        "labels": ["security", "frontend", "backend", "bug"],
        "body": """### Descrição do Problema
Nas rotinas de renderização dos orçamentos recentes no Dashboard (`renderRecentProjects`, linha 1180) e na tabela completa de projetos (`renderProjectsTable`, linha 1411) em `frontend/js/app.js`, o status do projeto é interpolado diretamente sem escapeHtml:

```javascript
// Linhas 1180-1182 e 1411-1413:
<span class="badge-${p.status}">
    ${formatStatus(p.status)}
</span>
```

A função `formatStatus(status)` mapeia os status conhecidos (`draft`, `quoted`, `approved`, etc.), mas possui um fallback que retorna a string bruta recebida:
```javascript
function formatStatus(status) {
    const map = { ... };
    return map[status] || status;
}
```

No backend (`backend/schemas.py`), `ProjectBase` define `status: str = "draft"` e `ProjectUpdate` define `status: Optional[str] = None` sem qualquer restrição dos valores válidos (`draft`, `quoted`, `approved`, `in_production`, `completed`, `cancelled`).

### Impacto
- **Stored XSS**: Ao cadastrar ou atualizar um projeto com `status` contendo tags HTML ou scripts (ex: `<img src=x onerror=...>` ou `<svg onload=...>`), a API armazena a string no banco de dados. Ao navegar pelo Dashboard ou tela de Projetos, o payload é injetado diretamente no DOM via `innerHTML`, executando scripts na sessão do usuário.

### Passos para Reproduzir
1. Criar um projeto via API com `status`:
   `{"name": "Projeto Teste", "status": "<img src=x onerror=alert(1)>"}`
2. Acessar o Dashboard (`#/dashboard`) ou Projetos (`#/projects`).
3. O script injetado é acionado no navegador.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 1180-1182, 1205-1215 e 1411-1413.
- `backend/schemas.py`: linhas 238 e 262 (`ProjectBase` e `ProjectUpdate`).

### Solução Proposta
1. Em `backend/schemas.py`, adicionar validação estrita com enum ou regex para os status permitidos:
```python
status: str = Field("draft", pattern=r"^(draft|quoted|approved|in_production|completed|cancelled)$")
```
2. Em `frontend/js/app.js`, aplicar `escapeHtml()` no valor formatado e na classe do badge:
```javascript
<span class="badge-${escapeHtml(p.status)}">
    ${escapeHtml(formatStatus(p.status))}
</span>
```
"""
    },
    {
        "title": "[BUG/VALIDATION] API aceita criação e atualização de projetos com nome vazio ou contendo apenas espaços em branco",
        "labels": ["bug", "backend", "validation"],
        "body": """### Descrição do Problema
Na issue #47 foi implementado o validador `validate_name_not_blank` em `PlateBase` e `BOMItemBase` para impedir registros vazios. Contudo, em `ProjectBase` e `ProjectUpdate` (`backend/schemas.py`), o campo `name` é definido como:

```python
class ProjectBase(BaseModel):
    name: str  # Sem restrição min_length ou validator

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
```

O mesmo ocorre em `PrinterBase` e `FilamentBase`, que não possuem validação para rejeitar nomes em branco ou compostos exclusivamente por espaços (`"   "`).

### Impacto
- Projetos podem ser criados ou atualizados via API com `name: "   "`.
- O registro é salvo no banco de dados com sucesso (HTTP 201 Created).
- Na listagem de projetos, o card exibe `#0001` sem título legível.
- Na geração de proposta comercial ou técnica em PDF (`backend/pdf_service.py`), o nome do arquivo cai no fallback `orcamento_projeto_X.pdf` e o título do projeto é impresso em branco.

### Passos para Reproduzir
1. Enviar requisição `POST /api/projects` com payload:
   `{"name": "   ", "plates": [{"name": "P1", "print_time_hours": 1, "part_weight_g": 10}]}`
2. A API retorna HTTP 201 Created em vez de HTTP 422 Unprocessable Entity.

### Arquivos e Linhas Afetadas
- `backend/schemas.py`: linhas 59, 73, 96, 111, 234 e 258 (`PrinterBase`, `PrinterUpdate`, `FilamentBase`, `FilamentUpdate`, `ProjectBase`, `ProjectUpdate`).

### Solução Proposta
Adicionar o validador `@field_validator("name")` em `ProjectBase` e `ProjectUpdate` (e nos schemas de impressora e filamento):
```python
@field_validator("name")
@classmethod
def validate_name_not_blank(cls, v: Optional[str]) -> Optional[str]:
    if v is not None and not v.strip():
        raise ValueError("O nome não pode ser vazio ou conter apenas espaços em branco.")
    return v.strip() if v else v
```
"""
    },
    {
        "title": "[BUG/DASHBOARD] Gráfico de Top Projetos (Chart 4) exibe orçamentos em Rascunho ('draft') e Orçados ('quoted') como Faturamento realizado",
        "labels": ["bug", "metrics", "dashboard"],
        "body": """### Descrição do Problema
Na rota de estatísticas do Dashboard (`get_dashboard_stats` em `backend/routes/project_routes.py`), os projetos são selecionados para compor o ranking `top_projects` (Chart 4) usando apenas a condição:

```python
// Linha 232:
if st != "cancelled":
    ...
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

Em seguida, a lista é ordenada pelo preço final e truncada nos top 5 (linha 290).

Enquanto as métricas oficiais de faturamento (`total_revenue_approved`), lucro líquido (`total_net_profit`), o gráfico temporal (Chart 2) e a estrutura de custos (Chart 3) filtram estritamente projetos confirmados (`approved`, `in_production`, `completed`), o ranking de Top Projetos inclui orçamentos em Rascunho (`draft`) e Orçados (`quoted`).

### Impacto
- No Chart 4 da interface, os eixos e tooltips estão rotulados como **Faturamento** e **Lucro Líquido**.
- Se o usuário cadastrar um orçamento em rascunho de alto valor (ex: R$ 50.000 ou R$ 99.000), ele assume a primeira posição do ranking do Dashboard, exibindo um faturamento comercial fictício que jamais foi aprovado ou faturado.

### Passos para Reproduzir
1. Criar um projeto com status `draft` no valor de R$ 99.000.
2. Criar um projeto com status `approved` no valor de R$ 300.
3. Acessar o Dashboard e inspecionar o Chart 4 ("Top Projetos por Faturamento & Lucro"). O rascunho aparece em 1º lugar com R$ 99.000 de "Faturamento".

### Arquivos e Linhas Afetadas
- `backend/routes/project_routes.py`: linhas 256-264 e 290.

### Solução Proposta
Filtrar os projetos adicionados a `project_items` para incluir apenas projetos com status realizado (`st in ["approved", "in_production", "completed"]`):
```python
if is_realized:
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
"""
    },
    {
        "title": "[UX/BUG] Filtro de status de impressoras ('Inativas / Manutenção') inoperante por ausência de campo is_active no modal e no salvamento",
        "labels": ["bug", "ux", "frontend"],
        "body": """### Descrição do Problema
Na interface de gerenciamento de impressoras (`frontend/index.html`), existe o dropdown de filtro por status operacional:
```html
<select id="printer-status-filter" onchange="filterPrinters()">
    <option value="all">Todas as Impressoras</option>
    <option value="active">Operacionais / Ativas</option>
    <option value="inactive">Inativas / Manutenção</option>
</select>
```

Em `frontend/js/app.js`, a função `renderPrintersGrid` filtra por `p.is_active !== false` e `p.is_active === false`. No backend, o modelo `Printer` e o schema `PrinterBase` suportam `is_active: bool = True`.

Contudo:
1. O formulário `#form-printer` no modal de cadastro/edição não possui nenhum input ou checkbox para `is_active`.
2. A função `openPrinterModal()` não carrega o estado de `is_active`.
3. A função `handleSavePrinter()` não inclui `is_active` no payload enviado para a API.
4. O card da impressora em `renderPrintersGrid` não exibe nenhum indicador visual do status operacional da máquina.

### Impacto
O usuário não consegue marcar nenhuma impressora como inativa ou em manutenção através da interface do sistema. Consequentemente, o filtro "Inativas / Manutenção" nunca exibe nenhum resultado e torna-se inoperante.

### Passos para Reproduzir
1. Acessar a tela "Minhas Impressoras" (`#/printers`).
2. Abrir o modal de edição de qualquer impressora cadastrada.
3. Constatar que não existe opção de marcar a impressora como inativa/em manutenção.
4. Selecionar "Inativas / Manutenção" no filtro superior: nenhuma impressora pode ser visualizada.

### Arquivos e Linhas Afetadas
- `frontend/index.html`: linhas 1322-1376 (`#form-printer`).
- `frontend/js/app.js`: linhas 2673-2715 (`openPrinterModal` e `handleSavePrinter`) e linhas 2813-2865 (`renderPrintersGrid`).

### Solução Proposta
1. Adicionar campo select ou switch para status operacional no modal `#form-printer`:
   - "Operacional / Ativa" (`is_active: true`)
   - "Em Manutenção / Inativa" (`is_active: false`)
2. Carregar e enviar `is_active` em `openPrinterModal` e `handleSavePrinter`.
3. Exibir badge visual de status no card da impressora em `renderPrintersGrid`.
"""
    },
    {
        "title": "[FEAT/UX] Ausência de funcionalidade de duplicação para impressoras no catálogo da oficina",
        "labels": ["enhancement", "ux", "frontend", "backend"],
        "body": """### Descrição do Problema
O sistema já conta com opções de duplicação para filamentos (`duplicateFilament` e endpoint `/api/filaments/{id}/duplicate`), placas de impressão (`duplicatePlateRow`), insumos de BOM (`duplicateBomRow`) e orçamentos (`duplicateProject`).

No entanto, no gerenciamento de impressoras 3D não existe a ação de duplicação, nem no backend nem na interface do usuário.

### Impacto
Em oficinas e fazendas de impressão 3D (print farms), é padrão possuir múltiplos equipamentos do mesmo modelo (ex: 4 unidades de Bambu Lab P1S, 3 unidades de Ender 3 V3, etc.) que compartilham os mesmos custos de aquisição, potência (Watts), reserva de manutenção por hora e vida útil. A ausência do botão "Duplicar" obriga o usuário a preencher manualmente todos os campos técnicos e financeiros para cada impressora adicional.

### Solução Proposta
1. Implementar o endpoint `POST /api/printers/{id}/duplicate` em `backend/routes/printer_routes.py`, clonando as especificações da máquina com sufixo `(Cópia)`.
2. Adicionar o método `duplicate: (id) => API.request(...)` em `frontend/js/api.js`.
3. Adicionar o botão de duplicar (`<button onclick="duplicatePrinter(${p.id})">`) com ícone `copy` no cabeçalho do card de impressora em `renderPrintersGrid`.
4. Implementar a função `duplicatePrinter(id)` em `frontend/js/app.js`.
"""
    },
    {
        "title": "[BUG/VALIDATION] Falta de validação de valores não-negativos para taxas personalizadas de impressora e filamento (custom_printer_hourly_rate e custom_filament_cost_per_g) na placa",
        "labels": ["bug", "validation", "backend"],
        "body": """### Descrição do Problema
Nos schemas `PlateBase` e `PlateUpdate` (`backend/schemas.py`), os campos `custom_printer_hourly_rate` e `custom_filament_cost_per_g` são declarados como:

```python
class PlateBase(BaseModel):
    ...
    custom_printer_hourly_rate: Optional[float] = None
    custom_filament_cost_per_g: Optional[float] = None

class PlateUpdate(BaseModel):
    ...
    custom_printer_hourly_rate: Optional[float] = None
    custom_filament_cost_per_g: Optional[float] = None
```

Ao contrário dos demais campos de precificação e custos do sistema (`acquisition_cost`, `spool_price`, `unit_cost`, `cad_hourly_rate`, `post_process_hourly_rate`, que utilizam `Field(..., ge=0)`), esses dois campos não possuem restrição de valor mínimo `ge=0`.

### Impacto
Valores negativos enviados pela API (como `custom_printer_hourly_rate: -15.0` ou `custom_filament_cost_per_g: -0.5`) são aceitos com sucesso pela validação do Pydantic e gravados na tabela `plates`, permitindo a persistência de taxas manuais inválidas no banco de dados.

### Passos para Reproduzir
1. Enviar requisição `POST /api/projects` com placa contendo taxas manuais negativas:
   `"custom_printer_hourly_rate": -15.0, "custom_filament_cost_per_g": -0.5`
2. A requisição responde HTTP 201 Created com sucesso em vez de HTTP 422.

### Arquivos e Linhas Afetadas
- `backend/schemas.py`: linhas 141-142 e 165-166.

### Solução Proposta
Adicionar `Field(None, ge=0)` para ambos os campos em `PlateBase` e `PlateUpdate`:
```python
custom_printer_hourly_rate: Optional[float] = Field(None, ge=0)
custom_filament_cost_per_g: Optional[float] = Field(None, ge=0)
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
        "User-Agent": "BrowserBugHunterV7"
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
