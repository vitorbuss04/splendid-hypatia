#!/usr/bin/env python3
"""
GitHub Issues Synchronizer for 3D Print Calc Pro (Splendid Hypatia)
Synchronizes user feedback and bug fixes with GitHub issues via REST API.
"""

import os
import sys
import json
import subprocess
import urllib.request
import urllib.error

REPO = "vitorbuss04/splendid-hypatia"
API_BASE = f"https://api.github.com/repos/{REPO}"

ISSUES_DEF = [
    {
        "number": 1,
        "title": "Cadastrar filamento: peso do carretel só aceita valores ímpares (ex: 1001) e rejeita 1000g",
        "labels": ["bug", "frontend", "ux"],
        "body": """### Descrição do Problema
Ao cadastrar um carretel de filamento, o campo de peso (em gramas) só aceitava valores ímpares como 1001g, rejeitando o valor padrão da indústria (1000g).

### Causa Raiz
O elemento `<input type="number" id="filament-weight">` no arquivo `frontend/index.html` possuía simultaneamente os atributos `min="1"` e `step="50"`. Pela especificação HTML5, o valor válido deve cumprir `(valor - min) % step === 0`. Portanto, `(1000 - 1) % 50 = 49 != 0` (inválido), enquanto `(1001 - 1) % 50 = 0` (válido).

### Solução Implementada
1. Alterado atributo no HTML para `step="any"` e `min="1"`.
2. Implementada validação numérica flexível no frontend (`frontend/js/app.js`) e backend Pydantic (`backend/schemas.py`).
3. Adicionada cobertura de testes automatizados em `tests/test_api.py` e `tests/test_frontend_inputs.py` para pesos comuns (250g, 500g, 1000g, 1001g).""",
        "comment": "Resolvido no commit 86ad9aa e verificado na suíte de testes pytest."
    },
    {
        "number": 2,
        "title": "Cadastrar filamento: preço do carretel só aceita inteiros e bloqueia centavos (ex: 56,50)",
        "labels": ["bug", "financial", "frontend"],
        "body": """### Descrição do Problema
O cadastro do filamento não aceitava valores com centavos (ex: R$ 56,50), forçando o preenchimento de números inteiros. Como se trata de precificação financeira, valores fracionários são fundamentais para o cálculo exato do custo por grama.

### Causa Raiz
O input HTML continha `step="1"` (padrão de `<input type="number">`), bloqueando decimais. Além disso, a inserção com vírgula ou no formato monetário brasileiro `56,50` ou `R$ 56,50` falhava no navegador.

### Solução Implementada
1. No HTML `frontend/index.html`, atualizado `filament-price` para `step="any"`.
2. No JavaScript `frontend/js/app.js`:
   - Implementada função `parseLocaleFloat` com suporte completo a moeda brasileira (`R$ 56,50`, `56,50`, `1.200,50`) e internacional (`56.50`).
   - Adicionado listener global `paste` com parsing monetário.
3. No backend, schema e banco utilizam `float` com precisão adequada para centavos e custo por grama com alta precisão decimal.
4. Coberto por testes unitários e de integração em `tests/test_api.py` e `tests/test_frontend_inputs.py`.""",
        "comment": "Resolvido no commit 86ad9aa e verificado na suíte de testes pytest."
    },
    {
        "number": 3,
        "title": "Cadastrar impressora: vida útil em horas rejeita valores redondos (5000h)",
        "labels": ["bug", "printers", "frontend"],
        "body": """### Descrição do Problema
Ao cadastrar uma impressora 3D, o campo de vida útil estimada em horas rejeitava o valor padrão recomendado de 5000h (e outros valores redondos como 3000h), aceitando apenas valores com step mismatch (ex: 5001h, 3001h).

### Causa Raiz
O campo `<input type="number" id="printer-lifespan">` possuía `step="100"` combinado com `min="1"`. Como `(5000 - 1) % 100 = 99 != 0`, o valor 5000h gerava `stepMismatch`, enquanto valores incomuns como 5001h eram aceitos.

### Solução Implementada
1. Alterado `step="any"` e `min="1"` em `frontend/index.html`.
2. Implementado `parseLocaleFloat` com fallback seguro para `5000` em `handleSavePrinter`.
3. Verificado cálculo de taxa horária de depreciação `acquisition_cost / lifespan_hours` com valores decimais e redondos no motor de custos (`backend/engine.py`).
4. Coberto por testes em `tests/test_api.py` e `tests/test_frontend_inputs.py`.""",
        "comment": "Resolvido no commit 86ad9aa e verificado na suíte de testes pytest."
    },
    {
        "number": 4,
        "title": "Input numérico decimal: digitação de vírgula limpa o valor no navegador",
        "labels": ["bug", "frontend", "ux"],
        "body": """### Descrição do Problema
Ao digitar uma vírgula em campos numéricos (`<input type="number">`), listeners anteriores tentavam concatenar `.` diretamente na propriedade `.value` (`target.value += '.'`). Em navegadores como Google Chrome e Microsoft Edge, atribuir uma string terminada em ponto (como `56.`) a um `input[type="number"]` viola o algoritmo de sanitização do padrão HTML5, resultando na limpeza imediata do campo (`value = ""`).

### Causa Raiz
No padrão HTML5, `input[type="number"].value` não aceita `.` sem dígitos subsequentes. A execução de fallback `target.value += '.'` nos listeners de `beforeinput` e `keydown` limpava o valor digitado pelo usuário.

### Solução Implementada
1. Implementada alternância dinâmica de modo de entrada: no evento `focusin`, o input transiciona para `type="text"` com `inputMode="decimal"`, permitindo digitação fluida de números, vírgula e ponto sem sanitização destrutiva do navegador.
2. No evento `focusout`, o valor é normalizado via `parseLocaleFloat` e o tipo é restaurado com segurança para `number`.
3. Adicionada função `normalizeNumericInputs()` chamada antes do salvamento de projetos, filamentos, impressoras e preferências.
4. Coberto por testes unitários e de navegador real em `tests/test_frontend_inputs.py`.""",
        "comment": "Resolvido e verificado com testes automatizados em headless Chrome e pytest."
    },
    {
        "number": 5,
        "title": "Card de filamento: exibir custo por grama com 2 casas decimais",
        "labels": ["enhancement", "frontend", "ui"],
        "body": """### Descrição da Solicitação
No elemento de destaque do card de filamento (`mt-4 p-3 rounded-lg bg-emerald-950/30 border border-emerald-800/40 text-center`), o custo por grama do filamento deve ser exibido com duas casas decimais em vez de quatro casas decimais.

### Solução Implementada
1. Atualizada a interpolação do card em `frontend/js/app.js` de `f.cost_per_gram.toFixed(4)` para `f.cost_per_gram.toFixed(2)`.
2. Adicionado teste automatizado em `tests/test_frontend_inputs.py` para assegurar conformidade do componente visual.""",
        "comment": "Resolvido e verificado com testes automatizados na suíte pytest."
    },
    {
        "number": 6,
        "title": "Importação de G-Code: extrair tempo estimado de impressão além do peso do filamento",
        "labels": ["bug", "parsers", "frontend"],
        "body": """### Descrição do Problema
Ao importar arquivos `.gcode`, o leitor puxava apenas os gramas do filamento, deixando o tempo estimado de impressão zerado ou falhando na extração de cabeçalhos de diversos fatiadores.

### Causa Raiz
1. A checagem de palavras-chave de tempo em `frontend/js/parsers/gcode.js` era estritamente sensível a maiúsculas/minúsculas (`line.includes('print time')` falhava em `;Print time:` ou `;Estimated printing time:`).
2. Regexes de Cura falhavam quando havia espaços após o ponto-e-vírgula (ex: `; TIME:`).
3. Padrões sem segundos (como `1:30` ou `01:45`) e linhas combinadas de Bambu/OrcaSlicer não eram casados.
4. O leitor analisava apenas 500 linhas finais, perdendo metadados em fatiadores com rodapés de configuração extensos (+800 linhas).

### Solução Implementada
1. Reformulado o extrator em `frontend/js/parsers/gcode.js` para busca normalizada em minúsculas, ampliação de janela para 3000 linhas e fallback dinâmico.
2. Adicionado suporte completo para Cura, PrusaSlicer, SuperSlicer, Bambu Studio, OrcaSlicer, IdeaMaker e Creality Print.
3. Atualizado o espelho de testes `tests/test_parsers.py` com cobertura completa de casos de borda.""",
        "comment": "Resolvido e verificado com 9 testes automatizados em tests/test_parsers.py."
    },
    {
        "number": 7,
        "title": "Inputs das placas: adicionar campos separados para horas e minutos (ex: 1:30)",
        "labels": ["enhancement", "frontend", "ux"],
        "body": """### Descrição da Solicitação
Nos inputs quantitativos das placas na calculadora, adicionar um campo específico para minutos além de apenas horas, viabilizando preenchimento intuitivo como `1:30` em vez de apenas `1` ou decimais complexos.

### Solução Implementada
1. Decomposto o input de tempo em `frontend/js/app.js` em dois campos numéricos agrupados: Horas (`plate-time-h-${idx}`) e Minutos (`plate-time-m-${idx}`).
2. Implementada função reativa `updatePlateTime(idx)` que converte `h + m/60` para horas decimais em tempo real.
3. Importações de 3MF e G-Code decompõem automaticamente o tempo lido em horas e minutos no formulário.
4. Adicionado teste de validação em `tests/test_frontend_inputs.py`.""",
        "comment": "Resolvido e validado com testes automatizados."
    },
    {
        "number": 8,
        "title": "Cadastro de filamento: gerar nome padronizado (Material + Cor + - + Marca) e seletor visual de cor",
        "labels": ["enhancement", "frontend", "database"],
        "body": """### Descrição da Solicitação
Ao cadastrar um novo filamento:
1. Remover o campo manual de nome do filamento.
2. O nome do filamento deve seguir automaticamente o padrão: `Material + Cor + - + Marca` (ex: `PLA Preto - 3D Prime`).
3. Adicionar seletor visual de cor (`<input type="color">`), exibindo a cor escolhida tanto no card de filamento quanto no seletor de filamentos da calculadora.

### Solução Implementada
1. No banco de dados e schemas (`backend/models.py`, `backend/schemas.py`), adicionada a coluna `color_hex` com migração automática no SQLite.
2. No modal `frontend/index.html`, removido o input de nome livre, adicionado `<input type="color" id="filament-color-hex">` e preview dinâmico do nome gerado.
3. Em `frontend/js/app.js`, geração automática do nome padronizado no salvamento e inclusão de badges/swatches coloridos no card de filamento e no dropdown de placas da calculadora.
4. Coberto por testes em `tests/test_api.py` e `tests/test_frontend_inputs.py`.""",
        "comment": "Resolvido e verificado com testes automatizados na API e no frontend."
    },
    {
        "number": 9,
        "title": "Exportação de PDF: exibir apenas o nome do material na coluna de filamento (ex: PLA, TPU)",
        "labels": ["enhancement", "pdf", "reporting"],
        "body": """### Descrição da Solicitação
Nas propostas e orçamentos em PDF (tanto para o cliente quanto na ficha técnica de produção), a coluna de insumo/filamento deve exibir exclusivamente o nome do material (ex: `PLA`, `TPU`, `PETG`), em vez da descrição completa do carretel.

### Solução Implementada
1. No motor de cálculo (`backend/engine.py`), incluído o atributo `filament_material` na estrutura resumida das placas.
2. No gerador de relatórios (`backend/pdf_service.py`), alterado o cabeçalho da coluna para `Material` e exibição exclusiva da nomenclatura técnica do polímero.
3. Coberto por testes unitários e de integração em `tests/test_api.py`.""",
        "comment": "Resolvido e testado na geração dos PDFs via ReportLab."
    },
    {
        "number": 10,
        "title": "Orçamento: campo para prazo de entrega em dias úteis após aprovação no rodapé",
        "labels": ["enhancement", "pdf", "financial"],
        "body": """### Descrição da Solicitação
Adicionar um campo para número de dias úteis para entrega a partir da data de aprovação, conferindo ao usuário controle direto sobre a informação de prazo exibida no rodapé do orçamento em PDF.

### Solução Implementada
1. Adicionada coluna `delivery_days` ao modelo `Project` em `backend/models.py`, schemas Pydantic e migração do banco SQLite.
2. Adicionado campo `proj-delivery-days` no formulário do projeto em `frontend/index.html` e controle no `frontend/js/app.js`.
3. Atualizada a seção de condições comerciais em `backend/pdf_service.py` para injetar o prazo informado (ou cálculo automático de segurança).
4. Coberto por testes em `tests/test_api.py` e `tests/test_frontend_inputs.py`.""",
        "comment": "Resolvido e validado com testes automatizados."
    },
    {
        "number": 11,
        "title": "Exportação de Orçamento: visualização em nova guia com opção de download",
        "labels": ["enhancement", "frontend", "pdf", "ux"],
        "body": """### Descrição da Solicitação
Ao invés de efetuar o download forçado e imediato do orçamento ao clicar, o sistema deve apresentar uma página de visualização em uma nova guia do navegador, acompanhada de opção de download e impressão.

### Solução Implementada
1. Criada a página dedicada `frontend/preview.html` com visualizador PDF em tela cheia, barra de ferramentas escura, e botões de `Baixar PDF` e `Imprimir`.
2. Adicionada rota dedicada `/preview` em `app.py` e suporte a `disposition=inline` e autenticação via query param `token` no endpoint `backend/routes/project_routes.py`.
3. Atualizados os métodos `API.pdf.preview()` e `exportCurrentPdf()` em `frontend/js/app.js` e botões da interface em `frontend/index.html`.
4. Coberto por testes em `tests/test_api.py` e `tests/test_frontend_inputs.py`.""",
        "comment": "Resolvido e testado com suíte de testes."
    },
    {
        "number": 12,
        "title": "[BUG] Edição de orçamento reseta campo Impostos / Taxas para 6% quando definido como 0%",
        "labels": ["bug", "frontend", "financial", "ux"],
        "body": """### Descrição do Problema
Ao editar um orçamento salvo com alíquota de impostos de 0%, o campo "Impostos / Taxas (%)" no formulário de edição voltava indevidamente para o valor padrão de 6%, recalculando os valores comerciais de forma equivocada.

### Causa Raiz
No arquivo `frontend/js/app.js`, a função `editProject` utilizava o operador lógico OR (`||`) para carregar o valor no formulário:
`document.getElementById('proj-tax').value = proj.tax_rate_percent || 6;`
Como `0` é avaliado como falso em JavaScript (`0 || 6 === 6`), a alíquota zero era sempre substituída por 6. O mesmo ocorria nas preferências (`populateSettingsForm`) e na inicialização (`initNewProject`).

### Solução Implementada
1. No arquivo `frontend/js/app.js`:
   - Substituído `||` pelo operador de coalescência nula (`??`) em `editProject`:
     `proj.tax_rate_percent ?? 6`, `proj.profit_margin_percent ?? 30`, `proj.cad_hourly_rate ?? 50`, `proj.post_process_hourly_rate ?? 30`, etc.
   - Atualizados `initNewProject`, `populateSettingsForm`, `openPrinterModal` e `createDefaultPlate` para preservar valores `0`.
   - Ajustado fallback em `recalcLiveSummary()` para `0%`.
2. No backend (`backend/engine.py` e `backend/routes/project_routes.py`):
   - Função de extração de atributos protegida contra `None` vs `0.0`.
   - Preservação do campo `delivery_days` na duplicação de projetos.
3. Adicionados testes automatizados:
   - `tests/test_api.py`: `test_project_zero_tax_rate_and_preservation`
   - `tests/test_frontend_inputs.py`: `test_edit_project_preserves_zero_tax_rate_and_nullish_coalescing` (incluindo teste com navegador Chrome headless real).""",
        "comment": "Resolvido com substituição por operador nullish coalescing (??) no frontend e engine protegida no backend. Verificado com 45 testes automatizados no pytest e navegador headless Chrome."
    },
    {
        "number": 13,
        "title": "[FEAT] Mudar a posição do botão \"Nova Placa\" para a parte de baixo",
        "labels": ["enhancement", "frontend", "ux"],
        "body": """### Descrição da Solicitação
Na calculadora de orçamentos, o botão "Nova Placa" encontrava-se posicionado no cabeçalho superior da seção "Placas Impressas", enquanto as novas placas criadas eram adicionadas no final da lista. Quando um projeto continha múltiplas placas, o usuário era obrigado a rolar até o topo da tela para clicar no botão e depois descer até o rodapé para editar a placa adicionada.

### Solução Implementada
1. No arquivo `frontend/index.html`:
   - Removido o botão de adição do topo do card de "Placas Impressas".
   - Inserido botão proeminente `#btn-add-plate-bottom` imediatamente abaixo do container de placas (`#plates-container`), com largura total e estilo tracejado integrado.
2. No arquivo `frontend/js/app.js`:
   - Na função `addNewPlateRow()`, adicionada rolagem suave automática (`scrollIntoView`) para a nova placa adicionada.
3. Coberto por testes em `tests/test_frontend_inputs.py` (`test_nova_placa_button_at_bottom`).""",
        "comment": "Resolvido e verificado com testes automatizados: botão reposicionado abaixo do container de placas com rolagem automática suave."
    },
    {
        "number": 14,
        "title": "[FEAT] Suporte à leitura e importação de arquivos .gcode.3mf",
        "labels": ["enhancement", "parsers", "frontend"],
        "body": """### Descrição da Solicitação
Fatiadores modernos como Bambu Studio e OrcaSlicer frequentemente exportam arquivos fatiados com a extensão composta `.gcode.3mf`. A plataforma aceitava apenas `.3mf` ou `.gcode`, impedindo a seleção ou importação direta desse formato comum.

### Solução Implementada
1. No arquivo `frontend/index.html`:
   - Atualizados os atributos de upload para `accept=\".3mf,.gcode,.gcode.3mf\"` no dropzone híbrido e cards de placas.
   - Atualizada a identidade visual e textos informativos do dropzone.
2. No arquivo `frontend/js/parsers/threemf.js`:
   - Implementado suporte a pacotes ZIP contendo arquivos G-code embutidos (`Metadata/plate_*.gcode`), extraindo metadados de impressão (tempo estimado, massa de filamento e polímero).
   - Adicionado fallback resiliente para decodificação como texto caso o arquivo contenha código G-code puro.
3. No arquivo `frontend/js/app.js`:
   - Atualizados `handleSlicerFile` e `handleSinglePlateFile` para processar e reconhecer `.gcode.3mf`.
4. Coberto por testes automatizados em `tests/test_parsers.py` e `tests/test_frontend_inputs.py`.""",
        "comment": "Resolvido e verificado com testes automatizados: suporte completo a .gcode.3mf com leitura de metadados e G-code embutido."
    }
]

def get_github_token():
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        p = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            text=True,
            capture_output=True
        )
        for line in p.stdout.splitlines():
            if line.startswith("password="):
                return line[9:]
    except Exception as e:
        print(f"Warning: could not get credentials via git credential helper: {e}")
    return None

def api_request(url, method="GET", data=None, token=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Splendid-Hypatia-IssueSync/1.0"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def sync():
    token = get_github_token()
    if not token:
        print("ERRO: Token do GitHub não encontrado. Configure GITHUB_TOKEN ou autentique via git credential.")
        sys.exit(1)

    print(f"Sincronizando issues com o repositório {REPO}...")

    # Fetch existing issues (up to 100)
    try:
        existing_issues = api_request(f"{API_BASE}/issues?state=all&per_page=100", token=token)
    except urllib.error.HTTPError as e:
        print(f"Erro ao listar issues: {e.code} {e.reason}")
        print(e.read().decode("utf-8"))
        sys.exit(1)

    existing_by_num = {i["number"]: i for i in existing_issues}
    existing_by_title = {i["title"].strip(): i for i in existing_issues}

    for item in ISSUES_DEF:
        num = item.get("number")
        existing = existing_by_num.get(num) or existing_by_title.get(item["title"].strip())
        if existing:
            target_num = existing["number"]
            # Update issue
            print(f"Atualizando Issue #{target_num}: {item['title']}...")
            patch_data = {
                "title": item["title"],
                "body": item["body"],
                "labels": item["labels"],
                "state": "closed",
                "state_reason": "completed"
            }
            updated = api_request(f"{API_BASE}/issues/{target_num}", method="PATCH", data=patch_data, token=token)
            print(f"  -> Issue #{target_num} atualizada e fechada como resolvida: {updated['html_url']}")

            # Check if resolution comment already exists
            try:
                comments = api_request(f"{API_BASE}/issues/{target_num}/comments", token=token)
                has_comment = any("Resolvido" in (c.get("body") or "") for c in comments)
            except Exception:
                has_comment = False

            if not has_comment:
                comment_data = {
                    "body": f"✅ **Resolvido**: {item['comment']}"
                }
                api_request(f"{API_BASE}/issues/{target_num}/comments", method="POST", data=comment_data, token=token)
                print(f"  -> Comentário de resolução publicado na Issue #{target_num}!")
        else:
            # Create issue
            print(f"Criando Issue: {item['title']}...")
            post_data = {
                "title": item["title"],
                "body": item["body"],
                "labels": item["labels"]
            }
            created = api_request(f"{API_BASE}/issues", method="POST", data=post_data, token=token)
            created_num = created["number"]
            print(f"  -> Issue #{created_num} criada: {created['html_url']}")

            # Close issue as completed
            close_data = {
                "state": "closed",
                "state_reason": "completed"
            }
            api_request(f"{API_BASE}/issues/{created_num}", method="PATCH", data=close_data, token=token)

            # Add comment
            comment_data = {
                "body": f"✅ **Resolvido**: {item['comment']}"
            }
            api_request(f"{API_BASE}/issues/{created_num}/comments", method="POST", data=comment_data, token=token)
            print(f"  -> Issue #{created_num} fechada como resolvida com sucesso!")

    print(f"\nTodas as {len(ISSUES_DEF)} issues foram sincronizadas e marcadas como resolvidas no GitHub!")

if __name__ == "__main__":
    sync()
