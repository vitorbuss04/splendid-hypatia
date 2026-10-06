import subprocess
import urllib.request
import urllib.error
import json
import sys
import time

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
        "title": "[BUG/CÁLCULO] Divergência de fallback entre o resumo em tempo real e o salvamento quando campos de Taxa CAD, Pós-processamento e Margem são esvaziados",
        "labels": ["bug", "frontend"],
        "body": """### Descrição do Problema
Na calculadora de orçamentos (`frontend/js/app.js`), existe uma divergência de valores default/fallback entre o cálculo em tempo real (`recalcLiveSummary`) e o salvamento do formulário (`saveCurrentProject`).

Quando o operador apaga o conteúdo dos campos de taxa horária de modelagem CAD (`proj-cad-rate`), pós-processamento manual (`proj-post-rate`) ou margem de lucro (`proj-margin`), o comportamento é divergente:

1. **No Resumo em Tempo Real (`recalcLiveSummary`, linhas 2099-2113)**:
```javascript
const cadRate = Math.max(0, parseLocaleFloat(document.getElementById('proj-cad-rate')?.value, 50));
const postRate = Math.max(0, parseLocaleFloat(document.getElementById('proj-post-rate')?.value, 30));
const marginPercent = Math.max(0, parseLocaleFloat(document.getElementById('proj-margin')?.value, 30));
```
A interface utiliza os fallbacks padrão da oficina (50, 30 e 30%) e exibe o resumo financeiro com esses valores calculados (ex: R$ 130 de mão de obra para 2h CAD e 1h Pós).

2. **No Salvamento do Projeto (`saveCurrentProject`, linhas 2228-2232)**:
```javascript
cad_hourly_rate: Math.max(0, parseLocaleFloat(document.getElementById('proj-cad-rate').value, 0)),
post_process_hourly_rate: Math.max(0, parseLocaleFloat(document.getElementById('proj-post-rate').value, 0)),
profit_margin_percent: Math.max(0, parseLocaleFloat(document.getElementById('proj-margin').value, 0)),
```
A função de salvamento passa fallback `0` para `parseLocaleFloat`, gravando `cad_hourly_rate = 0`, `post_process_hourly_rate = 0` e `profit_margin_percent = 0` no banco de dados.

### Impacto
- **Discrepância Financeira Silenciosa**: O operador vê um valor final e margem na tela durante a edição, mas ao salvar o projeto ou emitir o PDF, o backend recalcula os custos usando taxa 0 e margem 0, reduzindo drasticamente o preço de venda e o faturamento apurado.
- **Prejuízo Comercial**: Orçamentos podem ser aprovados com preço abaixo do custo real de produção.

### Passos para Reproduzir
1. Abrir um Novo Orçamento (`openNewProject()`).
2. Adicionar 2 horas de CAD (`proj-cad-hours = 2`).
3. Apagar o conteúdo do campo Taxa CAD (`proj-cad-rate = ''`).
4. Observar que o painel lateral exibe R$ 100,00 de Mão de Obra (fallback 50).
5. Salvar o projeto e reabri-lo: o custo de mão de obra e a taxa CAD foram salvos como R$ 0,00.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 2228-2232 (`saveCurrentProject`).

### Solução Proposta
Alinhar os fallbacks de `saveCurrentProject` com as preferências do usuário logado (`state.user`) ou valores de referência da aplicação:
```javascript
cad_hourly_rate: Math.max(0, parseLocaleFloat(document.getElementById('proj-cad-rate').value, state.user?.default_cad_rate ?? 50)),
post_process_hourly_rate: Math.max(0, parseLocaleFloat(document.getElementById('proj-post-rate').value, state.user?.default_post_rate ?? 30)),
profit_margin_percent: Math.max(0, parseLocaleFloat(document.getElementById('proj-margin').value, state.user?.default_profit_margin ?? 30)),
```
"""
    },
    {
        "title": "[UX/FEAT] Modal de impressora não exibe pré-visualização em tempo real da tarifa horária resultante (R$/h) durante a edição dos parâmetros",
        "labels": ["enhancement", "ux"],
        "body": """### Descrição do Problema
No modal de cadastro e edição de impressoras (`#modal-printer` em `frontend/index.html`), o operador insere os parâmetros contábeis e elétricos da máquina:
- Custo de Aquisição (R$)
- Vida Útil Estimada (horas)
- Potência Média (W)
- Reserva de Manutenção (R$/h)
- Tarifa de Energia Elétrica (R$/kWh)

No entanto, o modal não disponibiliza nenhum card ou indicador em tempo real mostrando o valor da Tarifa Horária da Máquina ($T_{\\text{máquina}} = D_{\\text{hora}} + \\text{Manutenção} + E_{\\text{hora}}$) resultante.

### Impacto
- **Falta de Feedback Operacional**: O usuário é obrigado a salvar o registro e procurar a impressora no grid para descobrir qual tarifa horária foi calculada pelo sistema.
- **Risco de Configuração Incorreta**: Erros de digitação (ex: colocar 1500W em vez de 150W ou esquecer um zero na vida útil) passam despercebidos durante o preenchimento, pois a taxa calculada não é visível antes da gravação.

### Passos para Reproduzir
1. Acessar a tela de Impressoras (`#/printers`).
2. Clicar em "+ Cadastrar Impressora" ou "Editar" em uma impressora existente.
3. Alterar os valores de Custo de Aquisição, Potência ou Tarifa de Energia.
4. Constatar que nenhum elemento do modal exibe o valor calculado da tarifa horária.

### Arquivos e Linhas Afetadas
- `frontend/index.html`: linhas 1327-1388 (estrutura do `#modal-printer`).
- `frontend/js/app.js`: linhas 2691-2760 (`openPrinterModal` e listeners de input).

### Solução Proposta
1. Adicionar um card de destaque dinâmico no modal de impressora (similar ao `#filament-name-preview-box` do filamento):
```html
<div class="p-3 bg-blue-950/40 border border-blue-800/40 rounded-xl text-center">
    <span class="text-[10px] uppercase font-semibold text-blue-300">Tarifa Horária Estimada</span>
    <div id="printer-rate-preview" class="text-xl font-black text-blue-400 mt-0.5">R$ 2,50/h</div>
</div>
```
2. Adicionar função `updatePrinterRatePreview()` chamada no evento `input` de todos os campos numéricos do modal.
"""
    },
    {
        "title": "[UX/BUG] Seletores de impressora e filamento no card da placa formatam tarifas com ponto decimal americano (ex: R$ 2.50/h e R$ 0.18/g) em vez de formatCurrency (R$ 2,50/h e R$ 0,18/g)",
        "labels": ["bug", "ux"],
        "body": """### Descrição do Problema
Na renderização dos cards de placas de impressão (`renderPlates` em `frontend/js/app.js`), os elementos `<select>` de seleção de Impressora e Filamento interpolam suas opções com formatação numérica fixa `.toFixed(2)`:

```javascript
// frontend/js/app.js linha 1730:
<option value="${p.id}" ${plate.printer_id === p.id ? 'selected' : ''}>
    ${esc(p.name)} (R$ ${p.machine_hourly_rate.toFixed(2)}/h)
</option>

// frontend/js/app.js linha 1763:
<option value="${f.id}" ${plate.filament_id === f.id ? 'selected' : ''}>
    ${esc(f.name)} (R$ ${(Number(f.cost_per_gram) || 0).toFixed(2)}/g)
</option>
```

Da mesma forma, no card de filamento do catálogo (`renderFilamentsGrid`, linha 3223):
```javascript
R$ ${f.cost_per_gram != null ? f.cost_per_gram.toFixed(2) : '0.00'}<span class="text-xs font-normal text-slate-400">/g</span>
```

### Impacto
- **Inconsistência Visual e Padrão Monetário**: Enquanto todo o sistema utiliza `formatCurrency()` (gerando `R$ 2,50/h` e `R$ 0,18/g` no padrão brasileiro pt-BR com vírgula), esses seletores exibem `R$ 2.50/h` e `R$ 0.18/g` com ponto decimal americano.

### Passos para Reproduzir
1. Abrir a tela de Orçamentos e editar ou criar um projeto (`#/project-editor`).
2. Abrir o dropdown de Impressoras ou Filamentos no card de uma placa.
3. Verificar a notação monetária nas opções: exibem ponto decimal em vez de vírgula.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 1730, 1763 e 3223.

### Solução Proposta
Substituir a concatenação `.toFixed(2)` pela função utilitária `formatCurrency`:
```javascript
// Linha 1730:
${esc(p.name)} (${formatCurrency(p.machine_hourly_rate)}/h)

// Linha 1763:
${esc(f.name)} (${formatCurrency(f.cost_per_gram)}/g)

// Linha 3223:
${formatCurrency(f.cost_per_gram || 0)}<span class="text-xs font-normal text-slate-400">/g</span>
```
"""
    },
    {
        "title": "[UX/FEAT] Ausência de campo de especificações/observações (notes) na linha de insumos (BOM) da calculadora de orçamentos",
        "labels": ["enhancement", "ux"],
        "body": """### Descrição do Problema
No modelo de dados relacional (`models.BOMItem` em `backend/models.py`) e nos schemas da API (`schemas.BOMItemBase` em `backend/schemas.py`), cada insumo possui a coluna `notes` (`notes: Optional[str] = None`) para armazenar especificações técnicas (ex: rosca métrica, tamanho do inserto, código de fornecedor, link de compra ou instruções de montagem).

Além disso, a função de persistência `saveCurrentProject` (`frontend/js/app.js`, linha 2271) mapeia `notes: b.notes`.

Porém, a interface do usuário em `renderBOM` (`frontend/js/app.js`, linhas 1963-2013) omite completamente a coluna ou campo para edição de `notes`.

### Impacto
- **Impossibilidade de Registrar Especificações Técnicas**: O operador não tem onde anotar o link de compra, fornecedor ou detalhes de montagem de itens adicionais (como parafusos, imãs, rolamentos ou placas eletrônicas).
- **Subutilização da Ficha Técnica**: Na Ficha Técnica de Produção em PDF, os insumos poderiam listar essas especificações para auxiliar o operador na bancada de montagem.

### Passos para Reproduzir
1. Abrir o Editor de Orçamentos (`#/project-editor`).
2. Rolar até a seção "Componentes & Acessórios Adicionais (BOM)".
3. Clicar em "Adicionar Insumo": apenas Descrição, Categoria, Quantidade e Custo Unitário são editáveis; não há campo para observações ou especificações.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 1950-2015 (`renderBOM`).
- `frontend/index.html`: tabela de insumos BOM.

### Solução Proposta
Incluir um campo secundário ou linha colapsável/tooltip de observações em cada item de BOM:
```html
<input type="text" value="${esc(item.notes || '')}" oninput="state.currentBOM[${idx}].notes = this.value" placeholder="Obs / Fornecedor / Link..." class="...">
```
"""
    },
    {
        "title": "[UX/BUG] Ação de logout na barra lateral encerra a sessão imediatamente sem confirmação do usuário causando risco de perda de dados",
        "labels": ["bug", "ux"],
        "body": """### Descrição do Problema
Na barra lateral da aplicação (`frontend/index.html`, linha 233), o botão de logout dispara diretamente `API.auth.logout()`:

```html
<button onclick="API.auth.logout()" title="Sair da conta" class="sidebar-logout-btn ...">
    <i data-lucide="log-out" class="w-4 h-4"></i>
</button>
```

Ao ser clicado, `API.auth.logout()` limpa o token do `localStorage`, remove o usuário em memória, despacha o evento `auth:logout` e abre o modal de autenticação.

### Impacto
- **Perda de Dados em Edição**: Se o operador clicar no ícone de logout acidentalmente (que fica posicionado logo abaixo do menu de navegação e perfil), todo o orçamento em edição, placas fatiadas e insumos não salvos são destruídos instantaneamente sem qualquer confirmação ou oportunidade de cancelamento.

### Passos para Reproduzir
1. Fazer login no sistema e abrir um orçamento com múltiplas placas e insumos.
2. Clicar no ícone de saída (porta com seta) no canto inferior esquerdo da barra lateral.
3. A sessão é encerrada imediatamente sem modal ou mensagem de confirmação.

### Arquivos e Linhas Afetadas
- `frontend/index.html`: linha 233 (`sidebar-logout-btn`).
- `frontend/js/app.js` e `frontend/js/api.js`: fluxo de encerramento de sessão.

### Solução Proposta
Implementar confirmação antes de deslogar:
```javascript
function handleLogout() {
    if (confirm('Deseja realmente sair da sua conta? Certifique-se de salvar suas alterações.')) {
        API.auth.logout();
    }
}
window.handleLogout = handleLogout;
```
E atualizar o botão no HTML: `onclick="handleLogout()"`.
"""
    },
    {
        "title": "[UX/BUG] Formulário de filamento não valida valores estritamente positivos para peso do carretel e densidade no frontend antes de submeter requisição à API",
        "labels": ["bug", "ux"],
        "body": """### Descrição do Problema
No modal de cadastro de filamento (`handleSaveFilament` em `frontend/js/app.js`), o código valida apenas a presença de marca e cor:

```javascript
// frontend/js/app.js linhas 3041-3052:
const brand = document.getElementById('filament-brand').value.trim();
if (!brand) { ... }
const color = document.getElementById('filament-color').value.trim();
if (!color) { ... }
```

Não há validação no cliente para:
- `spool_weight_g`: que deve ser estritamente maior que 0 (`gt=0` no schema Pydantic).
- `density_g_cm3`: que deve ser estritamente maior que 0 (`gt=0` no schema Pydantic).
- `spool_price`: que deve ser não-negativo (`ge=0`).

Se o usuário digitar `0` no peso do carretel (ou valor negativo), o payload é enviado para a API e rejeitado com erro HTTP 422 (`Input should be greater than 0`).

### Impacto
- **Experiência de Usuário Ruim (UX)**: A mensagem de erro exibida no Toast é a resposta crua da validação da API em vez de um aviso amigável com foco automático no campo inválido.
- **Risco de Divisão por Zero**: No cliente, `cost_per_gram = spool_price / spool_weight_g` gera `Infinity` se o peso for zero.

### Passos para Reproduzir
1. Acessar o catálogo de Filamentos (`#/filaments`) e clicar em "+ Cadastrar Filamento".
2. Preencher Marca e Cor normalmente.
3. Definir "Peso do Carretel" como `0` ou `-100`.
4. Clicar em "Salvar Filamento": a API retorna erro HTTP 422.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 3036-3065 (`handleSaveFilament`).

### Solução Proposta
Adicionar validações no frontend antes da chamada à API:
```javascript
const weight = parseLocaleFloat(document.getElementById('filament-weight').value, 1000);
if (weight <= 0) {
    showToast('O peso do carretel deve ser maior que zero.', 'error');
    document.getElementById('filament-weight')?.focus();
    return;
}
const density = parseLocaleFloat(document.getElementById('filament-density')?.value, 1.24);
if (density <= 0) {
    showToast('A densidade do material deve ser maior que zero.', 'error');
    document.getElementById('filament-density')?.focus();
    return;
}
```
"""
    },
    {
        "title": "[BUG/PARSER] Leitor de G-Code zera o tempo de impressão (print_time_hours = 0) para peças de calibração ou testes rápidos devido a arredondamento prematuro toFixed(2)",
        "labels": ["bug", "frontend"],
        "body": """### Descrição do Problema
No leitor de arquivos G-Code (`frontend/js/parsers/gcode.js`), a função `parseGcodeMetadata` calcula o tempo de impressão em horas a partir dos segundos extraídos do comentário (ex: `;TIME:15` ou `;TIME_ELAPSED:15`):

```javascript
// frontend/js/parsers/gcode.js linhas 267-270:
const printTimeHours = printTimeSeconds > 0 ? (printTimeSeconds / 3600) : 0;

return {
    print_time_hours: parseFloat(printTimeHours.toFixed(2)),
    part_weight_g: parseFloat(filamentGrams.toFixed(2)),
    ...
};
```

Quando um arquivo G-Code é gerado para testes rápidos de calibração (como cubo de teste miniatura, torre de temperatura de poucos layers, calibração de retração ou scripts de teste) com duração inferior a 18 segundos, o tempo em horas é inferior a 0.005h (ex: 15s / 3600 = 0.00416h).

Ao aplicar `.toFixed(2)`, o valor `0.00416` é truncado para `0.00`, e o retorno é `print_time_hours: 0.0`.

### Impacto
- **Tempo e Custo de Máquina Zerados**: Ao importar esse arquivo G-Code para uma placa, a placa assume `print_time_hours = 0`, resultando em custo de máquina nulo (R$ 0,00) no orçamento.
- **Divergência com o Parser 3MF**: O extrator `threemf.js` preserva o valor contínuo `(predictionSeconds / 3600)` sem arredondamento prematuro em 2 casas.

### Passos para Reproduzir
1. Criar um arquivo `.gcode` contendo `;TIME:15` e `;Filament used: 1.5g`.
2. Importar o arquivo para uma placa no Editor de Orçamentos (`handleSinglePlateFile`).
3. Verificar que o filamento é importado com 1.5g, mas o tempo de impressão é definido como `0h 0m` (`print_time_hours = 0`).

### Arquivos e Linhas Afetadas
- `frontend/js/parsers/gcode.js`: linha 270.

### Solução Proposta
Preservar pelo menos 4 casas decimais ou evitar arredondamento prematuro no objeto retornado pelo parser:
```javascript
print_time_hours: parseFloat(printTimeHours.toFixed(4)),
```
Garantindo que mesmo impressões de poucos segundos resultem em frações válidas de hora (ex: 15s = 0.0042h).
"""
    }
]

def main():
    token = get_token()
    if not token:
        print("Erro: Token do GitHub não encontrado via git credential fill!")
        sys.exit(1)

    print(f"Token obtido com sucesso. Criando {len(ISSUES_TO_CREATE)} issues no repositório {REPO}...")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "BrowserAuditV10Publisher"
    }

    created = []
    for idx, iss in enumerate(ISSUES_TO_CREATE, 1):
        print(f"[{idx}/{len(ISSUES_TO_CREATE)}] Criando issue: {iss['title']}...")
        payload = {
            "title": iss["title"],
            "body": iss["body"],
            "labels": iss.get("labels", ["bug"])
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{API_BASE}/issues",
            data=data,
            headers=headers,
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                created.append(res)
                print(f" -> Sucesso! Issue #{res['number']} criada: {res['html_url']}")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            print(f" -> Erro HTTP {e.code}: {err_body}")
        except Exception as e:
            print(f" -> Erro inesperado: {e}")

        time.sleep(1.0)

    print(f"\nTotal de issues criadas com sucesso: {len(created)}/{len(ISSUES_TO_CREATE)}")

if __name__ == "__main__":
    main()
