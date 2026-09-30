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
        "title": "[BUG] Notificações toast exibem '[object Object]' ao ocorrer erro de validação HTTP 422 da API",
        "labels": ["bug", "frontend", "ux"],
        "body": """### Descrição do Problema
Ao submeter formulários que violam regras de validação do backend (ex: alíquota de impostos superior a 99%, desconto comercial inválido, formato de e-mail incorreto ou campos obrigatórios faltantes), o FastAPI retorna uma resposta com status HTTP 422 (*Unprocessable Entity*) contendo um corpo JSON com a chave `detail` estruturada como uma lista de objetos:
```json
{
  "detail": [
    {
      "type": "less_than_equal",
      "loc": ["body", "tax_rate_percent"],
      "msg": "Input should be less than or equal to 99",
      "input": 150,
      "ctx": { "le": 99.0 }
    }
  ]
}
```

No arquivo `frontend/js/api.js`, o método `API.request` trata os erros da seguinte forma:
```javascript
if (!resp.ok) {
    const msg = data && data.detail ? data.detail : `Erro na requisição (${resp.status})`;
    throw new Error(msg);
}
```
Como `data.detail` é uma lista de objetos, a conversão nativa de `new Error(data.detail)` chama o método `.toString()`, resultando na mensagem textual `"[object Object]"`. Quando o bloco `catch` aciona `showToast(err.message, 'error')`, o usuário visualiza na interface uma notificação toast vermelha contendo apenas o texto opaco e incompreensível `[object Object]`, sem qualquer indicação de qual campo foi rejeitado ou como corrigir o problema.

### Passos para Reproduzir
1. Abrir o navegador em `http://localhost:8000` e autenticar-se.
2. Abrir o editor de orçamentos ou executar via console:
   ```javascript
   await API.projects.create({ name: 'Teste', tax_rate_percent: 150 });
   ```
3. Observar a notificação toast exibida no canto da tela:
   - Texto exibido: `[object Object]`

### Solução Proposta
No arquivo `frontend/js/api.js`, tratar adequadamente respostas onde `data.detail` é um array ou objeto:
```javascript
if (!resp.ok) {
    let msg = `Erro na requisição (${resp.status})`;
    if (data && data.detail) {
        if (Array.isArray(data.detail)) {
            msg = data.detail
                .map(d => `${d.loc ? d.loc.slice(-1)[0] + ': ' : ''}${d.msg}`)
                .join('; ');
        } else if (typeof data.detail === 'string') {
            msg = data.detail;
        } else {
            msg = JSON.stringify(data.detail);
        }
    }
    throw new Error(msg);
}
```"""
    },
    {
        "title": "[BUG] Pré-visualização do nome do filamento não atualiza ao selecionar tipo de material pelo dropdown",
        "labels": ["bug", "frontend", "filaments"],
        "body": """### Descrição do Problema
No modal de cadastro e edição de filamento (`#modal-filament`), a caixa de pré-visualização dinâmica (`#filament-preview-text`) deve gerar e exibir o nome padronizado do material no formato:
`Material + Cor + - + Marca` (ex: `PETG Azul Royal - Sunlu`).

Entretanto, o elemento `<select id="filament-material">` no arquivo `frontend/index.html` possui apenas o atributo `oninput="updateFilamentNamePreview()"`. Na especificação HTML5 e na implementação da maioria dos navegadores (Google Chrome, Microsoft Edge, Firefox, Safari), elementos do tipo `<select>` disparam o evento `change` ao ter uma opção selecionada pelo cursor do mouse ou navegação por teclado, enquanto o evento `input` pode não ser disparado ou falhar em mudanças programáticas.

Como consequência, ao abrir o modal e selecionar outro polímero (ex: mudar de `PLA` para `PETG` ou `TPU`), o preview permanece exibindo `PLA ...` até que o usuário foque e digite alguma letra nos campos de marca ou cor.

### Passos para Reproduzir
1. Acessar a tela "Carretéis de Filamento" (`#view-filaments`).
2. Clicar em "Cadastrar Filamento".
3. No campo "Tipo de Material", selecionar "PETG" ou "TPU".
4. Observar a caixa "Nome Gerado (Padrão)": o texto permanece como "PLA Preto - Marca" em vez de atualizar imediatamente para "PETG Preto - Marca".

### Solução Proposta
No arquivo `frontend/index.html`:
Adicionar o atributo `onchange="updateFilamentNamePreview()"` ao elemento `#filament-material`:
```html
<select id="filament-material" oninput="updateFilamentNamePreview()" onchange="updateFilamentNamePreview()" class="...">
```"""
    },
    {
        "title": "[FEAT] Filtro por tipo de material na tela de Filamentos e por status operacional na tela de Impressoras",
        "labels": ["enhancement", "frontend", "ux", "filaments", "printers"],
        "body": """### Descrição da Solicitação
A tela inicial de Filamentos (`#view-filaments`) e de Impressoras (`#view-printers`) dispõem atualmente de um campo de busca por texto livre em tempo real (`#filament-search-input` e `#printer-search-input`).

Contudo, para oficinas e birôs com catálogos volumosos (dezenas de carretéis de filamento e múltiplas máquinas em produção), a seleção visual rápida por categoria é essencial para agilizar o fluxo de trabalho:
1. **Na tela de Filamentos (`#view-filaments`)**:
   - Disponibilizar um seletor/chips de filtro por material (ex: `Todos`, `PLA`, `PETG`, `ABS`, `TPU`, `ASA`, `Resina`, `Outro`).
   - Ao selecionar uma categoria, a grade exibe exclusivamente os carretéis do polímero correspondente, combinando o filtro categórico com o termo digitado na barra de busca.
2. **Na tela de Impressoras (`#view-printers`)**:
   - Disponibilizar um seletor/chips de status operacional (ex: `Todas`, `Ativas`, `Inativas / Manutenção`).

### Solução Proposta
1. **Na interface (`frontend/index.html`)**:
   - Adicionar dropdowns ou botões de chip de filtro ao lado dos inputs de busca nas seções `#view-filaments` e `#view-printers`.
2. **No controlador (`frontend/js/app.js`)**:
   - Atualizar `filterFilaments()` e `renderFilamentsGrid()` para considerar o material selecionado em conjunto com o termo de busca.
   - Atualizar `filterPrinters()` e `renderPrintersGrid()` para filtrar pelo status `is_active` em conjunto com a busca."""
    },
    {
        "title": "[BUG] Cadastro e duplicação de filamento não incluem campo para densidade do material (g/cm³)",
        "labels": ["bug", "frontend", "filaments", "parsers"],
        "body": """### Descrição do Problema
O modelo de dados `Filament` (`backend/models.py`) e os schemas Pydantic (`backend/schemas.py`) possuem a propriedade `density_g_cm3` (padrão 1.24 g/cm³), utilizada para conversões volumétricas de comprimento extrudado (mm/cm³) para massa em gramas na importação de arquivos de fatiadores G-code.

Entretanto:
1. No formulário do modal `#modal-filament` (`frontend/index.html`), não há input para visualizar ou ajustar a densidade do carretel.
2. Na função `handleSaveFilament()` em `frontend/js/app.js`, o campo `density_g_cm3` é omitido do payload enviado à API, forçando sempre o valor padrão de 1.24 g/cm³ (densidade típica do PLA).

Termoplásticos de engenharia comuns em impressão 3D apresentam densidades significativamente distintas:
- ABS: ~1.04 g/cm³ (~16% mais leve que PLA)
- ASA: ~1.07 g/cm³
- TPU: ~1.21 g/cm³
- PETG: ~1.27 g/cm³
- Resina UV: ~1.10 - 1.15 g/cm³

Essa discrepância causa erros no cálculo de peso quando arquivos G-code expressam consumo em volume ou milímetros lineares.

### Solução Proposta
1. **No modal `frontend/index.html`**:
   - Adicionar input numérico `#filament-density` (step="0.01", min="0.5") com valor padrão automático preenchido com base no material selecionado.
2. **No controlador `frontend/js/app.js`**:
   - Ao trocar o material em `#filament-material`, sugerir a densidade de referência do polímero.
   - Incluir `density_g_cm3: parseLocaleFloat(document.getElementById('filament-density')?.value, 1.24)` no payload de criação e atualização em `handleSaveFilament`.
   - Na duplicação de filamento (`openFilamentModal(filament, true)`), herdar a densidade do carretel original."""
    },
    {
        "title": "[FEAT] Formatação automática e máscara para telefones comerciais e chave PIX",
        "labels": ["enhancement", "frontend", "ux"],
        "body": """### Descrição da Solicitação
Nos formulários da aplicação — especificamente o telefone do cliente no editor de orçamento (`#proj-client-phone`) e o telefone/WhatsApp comercial da oficina nas preferências (`#pref-phone`) —, os campos aceitam digitação de texto totalmente livre sem qualquer máscara de formatação ou padronização.

Como esses números são renderizados diretamente no cabeçalho comercial e rodapé das propostas em PDF enviadas aos clientes, preenchimentos sem DDD, sem parênteses ou sem hífen (ex: `11999998888` ou `9999-8888`) prejudicam a apresentação profissional da oficina e dificultam o clique direto para envio de mensagens via WhatsApp pelo cliente.

### Solução Proposta
1. Implementar função de máscara dinâmica no evento `input` em `frontend/js/app.js`:
   - Detectar a quantidade de dígitos numéricos e aplicar automaticamente a formatação brasileira:
     - 10 dígitos: `(XX) XXXX-XXXX` (Telefone Fixo)
     - 11 dígitos: `(XX) XXXXX-XXXX` (Celular / WhatsApp)
2. Adicionar listeners nos inputs `#proj-client-phone` e `#pref-phone`."""
    }
]

def create_issues():
    token = get_token()
    if not token:
        print("ERRO: Token do GitHub não encontrado via git credential.")
        sys.exit(1)

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Splendid-Hypatia-IssueSync/1.0",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Fetch existing issues to avoid duplicates
    req = urllib.request.Request(f"{API_BASE}/issues?state=all&per_page=100", headers=headers)
    with urllib.request.urlopen(req) as resp:
        existing = json.loads(resp.read().decode())
    existing_titles = {i["title"].strip(): i for i in existing}

    created_issues = []
    for item in NEW_ISSUES:
        title = item["title"].strip()
        if title in existing_titles:
            num = existing_titles[title]["number"]
            url = existing_titles[title]["html_url"]
            print(f"Issue já existente: #{num} - {title} ({url})")
            created_issues.append(existing_titles[title])
            continue

        post_data = json.dumps({
            "title": item["title"],
            "body": item["body"],
            "labels": item["labels"]
        }).encode("utf-8")

        create_req = urllib.request.Request(f"{API_BASE}/issues", data=post_data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(create_req) as resp:
                res_json = json.loads(resp.read().decode())
                print(f"✅ Issue #{res_json['number']} criada com sucesso: {res_json['title']}")
                print(f"   URL: {res_json['html_url']}")
                created_issues.append(res_json)
        except urllib.error.HTTPError as e:
            print(f"❌ Erro ao criar issue '{title}': {e.code} {e.reason}")
            print(e.read().decode())

    print(f"\nTotal de {len(created_issues)} issues processadas no repositório {REPO}.")

if __name__ == "__main__":
    create_issues()
