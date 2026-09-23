# GitHub Issues Tracker & Changelog

Este arquivo centraliza o rastreamento de issues do repositório **3D Print Calc Pro** conforme os feedbacks de usuários e melhorias contínuas.

Todas as issues abaixo foram sincronizadas diretamente com o repositório remoto [`vitorbuss04/splendid-hypatia`](https://github.com/vitorbuss04/splendid-hypatia/issues).

---

## Índice de Issues

| ID | Título | Tipo | Status | Link Remoto | Testes Automatizados |
|---|---|---|---|---|---|
| [#1](#issue-1-validação-de-peso-do-carretel-de-filamento-rejeita-valores-pares-e-padrões-como-1000g) | Cadastrar filamento: peso do carretel só aceita ímpares (ex: 1001) e rejeita 1000g | Bug / UX | **FECHADA (Resolvida)** | [GitHub #1](https://github.com/vitorbuss04/splendid-hypatia/issues/1) | `tests/test_frontend_inputs.py`, `tests/test_api.py` |
| [#2](#issue-2-preço-do-carretel-de-filamento-não-aceita-centavos-ex-r-5650) | Cadastrar filamento: preço do carretel só aceita inteiros e bloqueia centavos | Bug / Financeiro | **FECHADA (Resolvida)** | [GitHub #2](https://github.com/vitorbuss04/splendid-hypatia/issues/2) | `tests/test_frontend_inputs.py`, `tests/test_api.py` |
| [#3](#issue-3-vida-útil-da-impressora-em-horas-rejeita-5000h-por-validação-de-step) | Cadastrar impressora: vida útil em horas rejeita valores redondos (5000h) | Bug / UX | **FECHADA (Resolvida)** | [GitHub #3](https://github.com/vitorbuss04/splendid-hypatia/issues/3) | `tests/test_frontend_inputs.py`, `tests/test_api.py` |
| [#4](#issue-4-input-numérico-decimal-digitação-de-vírgula-limpa-o-valor-no-navegador) | Input numérico decimal: digitação de vírgula limpa o valor no navegador | Bug / UX / Frontend | **FECHADA (Resolvida)** | [GitHub #4](https://github.com/vitorbuss04/splendid-hypatia/issues/4) | `tests/test_frontend_inputs.py` |
| [#5](#issue-5-card-de-filamento-exibir-custo-por-grama-com-2-casas-decimais) | Card de filamento: exibir custo por grama com 2 casas decimais | Melhoria / UI | **FECHADA (Resolvida)** | [GitHub #5](https://github.com/vitorbuss04/splendid-hypatia/issues/5) | `tests/test_frontend_inputs.py` |
| [#6](#issue-6-importação-de-g-code-extrair-tempo-estimado-de-impressão-além-do-peso) | Importação de G-Code: extrair tempo estimado de impressão além do peso | Bug / Parsers | **FECHADA (Resolvida)** | [GitHub #6](https://github.com/vitorbuss04/splendid-hypatia/issues/6) | `tests/test_parsers.py` |
| [#7](#issue-7-inputs-das-placas-adicionar-campos-separados-para-horas-e-minutos) | Inputs das placas: adicionar campos separados para horas e minutos (ex: 1:30) | Melhoria / UX | **FECHADA (Resolvida)** | [GitHub #7](https://github.com/vitorbuss04/splendid-hypatia/issues/7) | `tests/test_frontend_inputs.py` |
| [#8](#issue-8-cadastro-de-filamento-gerar-nome-padronizado-e-seletor-visual-de-cor) | Cadastro de filamento: gerar nome padronizado e seletor visual de cor | Melhoria / Frontend | **FECHADA (Resolvida)** | [GitHub #8](https://github.com/vitorbuss04/splendid-hypatia/issues/8) | `tests/test_api.py`, `tests/test_frontend_inputs.py` |
| [#9](#issue-9-exportação-de-pdf-exibir-apenas-o-nome-do-material-na-coluna-de-filamento) | Exportação de PDF: exibir apenas o nome do material na coluna de filamento | Melhoria / Relatórios | **FECHADA (Resolvida)** | [GitHub #9](https://github.com/vitorbuss04/splendid-hypatia/issues/9) | `tests/test_api.py` |
| [#10](#issue-10-orçamento-campo-para-prazo-de-entrega-em-dias-úteis-após-aprovação-no-rodapé) | Orçamento: campo para prazo de entrega em dias úteis no rodapé | Melhoria / Backend | **FECHADA (Resolvida)** | [GitHub #10](https://github.com/vitorbuss04/splendid-hypatia/issues/10) | `tests/test_api.py` |
| [#11](#issue-11-exportação-de-orçamento-visualização-em-nova-guia-com-opção-de-download) | Exportação de Orçamento: visualização em nova guia com opção de download | Melhoria / Frontend | **FECHADA (Resolvida)** | [GitHub #11](https://github.com/vitorbuss04/splendid-hypatia/issues/11) | `tests/test_api.py`, `tests/test_frontend_inputs.py` |

---

## Detalhamento das Issues

### Issue #1: Validação de peso do carretel de filamento rejeita valores pares e padrões como 1000g
- **Status:** `CLOSED` (Resolvido)
- **Link Remoto:** https://github.com/vitorbuss04/splendid-hypatia/issues/1
- **Labels:** `bug`, `frontend`, `ux`
- **Origem:** Feedback de usuário em `anotacoes/feedbacks.md` (*"Cadastrar filamento > peso do carretel só aceita valores impares: ex: 1001, e não aceita 1000"*)
- **Comportamento Anterior:** Ao tentar cadastrar ou salvar um filamento com carretel padrão de 1000g, o navegador disparava erro de validação nativo (`stepMismatch`), impedindo a submissão. Valores como 1001g passavam normalmente.
- **Causa Raiz:** O elemento `<input type="number" id="filament-weight">` no arquivo `frontend/index.html` possuía simultaneamente os atributos `min="1"` e `step="50"`. Pela especificação HTML5, o valor válido deve satisfazer `(valor - min) % step === 0`. Portanto, `(1000 - 1) % 50 = 49 != 0` (inválido), enquanto `(1001 - 1) % 50 = 0` (válido).
- **Correção Implementada:**
  1. Alterado atributo no HTML para `step="any"` e `min="1"`.
  2. Implementado `parseLocaleFloat` no frontend para parsing resiliente no formulário de filamentos.
  3. Validado que o backend Pydantic (`backend/schemas.py`) aceita qualquer float positivo (`spool_weight_g: float = Field(1000.0, gt=0)`).
- **Verificação:** Coberto pelo teste unitário `test_html_numeric_inputs_step_attributes` em `tests/test_frontend_inputs.py` e testes de API em `tests/test_api.py`.

---

### Issue #2: Preço do carretel de filamento não aceita centavos (ex: R$ 56,50)
- **Status:** `CLOSED` (Resolvido)
- **Link Remoto:** https://github.com/vitorbuss04/splendid-hypatia/issues/2
- **Labels:** `bug`, `financial`, `frontend`, `backend`
- **Origem:** Feedback de usuário em `anotacoes/feedbacks.md` (*"Cadastrar filamento > Preço do carretel, só aceita valores inteiros, como é dinheiro, deveria aceitar centavos. (ex: 56,50)"*)
- **Comportamento Anterior:** O campo de preço do filamento recusava valores com casas decimais (centavos), exigindo números inteiros. Além disso, se o usuário digitasse vírgula ou colasse `56,50` ou `R$ 56,50`, o campo ficava inválido ou zerado.
- **Causa Raiz:** O input HTML continha `step="1"`, limitando a entrada a inteiros. Além disso, navegadores em desktop bloqueiam o caractere de vírgula em inputs `type="number"` sem tratamento explícito de eventos.
- **Correção Implementada:**
  1. No HTML `frontend/index.html`, atualizado `filament-price` para `step="any"`.
  2. No JavaScript `frontend/js/app.js`:
     - Implementada a função `parseLocaleFloat` para lidar com separadores de milhar e centavos no padrão brasileiro (`R$ 56,50`, `56,50`, `1.200,50`) e internacional (`56.50`).
     - Adicionado listener global `paste` com suporte à colagem de valores monetários brasileiros.
  3. No backend, schema e banco utilizam `float` com precisão adequada para centavos e custo por grama com 3 a 4 casas decimais.
- **Verificação:** Testes de validação de input em `tests/test_frontend_inputs.py` e cálculo de custo por grama em `tests/test_api.py`.

---

### Issue #3: Vida útil da impressora em horas rejeita 5000h por validação de step
- **Status:** `CLOSED` (Resolvido)
- **Link Remoto:** https://github.com/vitorbuss04/splendid-hypatia/issues/3
- **Labels:** `bug`, `printers`, `frontend`
- **Origem:** Feedback de usuário em `anotacoes/feedbacks.md` (*"Cadastrar impressora: mesmo problema na vida útil em horas."*)
- **Comportamento Anterior:** Ao cadastrar uma impressora com a vida útil padrão de mercado de 5000 horas, o formulário apresentava erro de validação nativo e não permitia salvar.
- **Causa Raiz:** O campo `<input type="number" id="printer-lifespan">` possuía `step="100"` combinado com `min="1"`. Como `(5000 - 1) % 100 = 99 != 0`, o valor 5000h gerava `stepMismatch`, enquanto valores incomuns como 5001h eram aceitos.
- **Correção Implementada:**
  1. Alterado `step="any"` e `min="1"` em `frontend/index.html`.
  2. Implementado `parseLocaleFloat` com fallback seguro para `5000` em `handleSavePrinter`.
  3. Verificado cálculo de taxa horária de depreciação `acquisition_cost / lifespan_hours` com valores decimais e redondos.
- **Verificação:** Coberto em `tests/test_frontend_inputs.py` e `tests/test_api.py`.

---

### Issue #4: Input numérico decimal: digitação de vírgula limpa o valor no navegador
- **Status:** `CLOSED` (Resolvido)
- **Link Remoto:** https://github.com/vitorbuss04/splendid-hypatia/issues/4
- **Labels:** `bug`, `frontend`, `ux`
- **Origem:** Análise de testes de navegadores reais Chrome/Edge em `frontend/js/app.js`
- **Comportamento Anterior:** Ao digitar vírgula num campo de preço ou numérico, o listener anterior concatenava ponto ao `.value` (`target.value += '.'`). Em navegadores como Chrome e Edge, atribuir uma string como `"56."` a um `input[type="number"]` viola a validação nativa de ponto flutuante do HTML5 e o navegador resetava o campo inteiro para string vazia (`""`).
- **Causa Raiz:** Padrão HTML5 de sanitização de `type="number"` descarta strings com ponto sem dígitos posteriores.
- **Correção Implementada:**
  1. Implementada alternância dinâmica de modo de edição em `frontend/js/app.js`: no foco (`focusin`), o campo transiciona para `type="text"` com `inputMode="decimal"`, permitindo digitação fluida e livre de vírgula e ponto.
  2. Na saída (`focusout`) e no envio de formulários (`normalizeNumericInputs`), o valor é parseado com precisão via `parseLocaleFloat` e o tipo é restaurado com segurança para `number`.
- **Verificação:** Testes automatizados em `tests/test_frontend_inputs.py` incluindo teste real em navegador headless.

---

### Issue #5: Card de filamento: exibir custo por grama com 2 casas decimais
- **Status:** `CLOSED` (Resolvido)
- **Link Remoto:** https://github.com/vitorbuss04/splendid-hypatia/issues/5
- **Labels:** `enhancement`, `frontend`, `ui`
- **Origem:** Feedback de usuário em `anotacoes/feedbacks.md` (*"em 'mt-4 p-3 rounded-lg bg-emerald-950/30 border border-emerald-800/40 text-center', deixar o custo por grama do filamento com duas casas decimais."*)
- **Comportamento Anterior:** O card exibia o custo por grama com 4 casas decimais (ex: R$ 0,0899/g).
- **Causa Raiz:** Uso de `toFixed(4)` na interpolação do card em `frontend/js/app.js`.
- **Correção Implementada:** Atualizada interpolação para `(Number(f.cost_per_gram) || 0).toFixed(2)` e coberto em `tests/test_frontend_inputs.py`.

---

### Issue #6: Importação de G-Code: extrair tempo estimado de impressão além do peso do filamento
- **Status:** `CLOSED` (Resolvido)
- **Link Remoto:** https://github.com/vitorbuss04/splendid-hypatia/issues/6
- **Labels:** `bug`, `parsers`, `frontend`
- **Origem:** Feedback de usuário em `anotacoes/feedbacks.md` (*"Ao importar gcode, ele puxa apenas os gramas do filamento. deveria puxar também o tempo de impressão."*)
- **Comportamento Anterior:** Arquivos G-Code tinham apenas gramas extraídos; o tempo ficava zerado ou era mal interpretado em diversos fatiadores.
- **Causa Raiz:** Falta de suporte a tags em minúsculas/maiúsculas, regexes rígidas, clobbering de normal mode por silent mode no PrusaSlicer, e interpretação indevida de diâmetro de bico em milímetros (`0.4mm`) como minutos.
- **Correção Implementada:**
  1. Parser `frontend/js/parsers/gcode.js` e espelho `tests/test_parsers.py` reformulados com priorização explícita de tempo (`normal mode` vs `silent mode`).
  2. Proteção contra falsos positivos com `(?!m)` para ignorar milímetros.
  3. Suporte completo a Cura, PrusaSlicer, Bambu Studio, OrcaSlicer, Creality Print e IdeaMaker.
  4. Extração de tipo de material para Cura (`MATERIAL:PLA`) e Prusa (`filament_type = PLA`).
- **Verificação:** 13 testes unitários dedicados em `tests/test_parsers.py`.

---

### Issue #7: Inputs das placas: adicionar campos separados para horas e minutos (ex: 1:30)
- **Status:** `CLOSED` (Resolvido)
- **Link Remoto:** https://github.com/vitorbuss04/splendid-hypatia/issues/7
- **Labels:** `enhancement`, `frontend`, `ux`
- **Origem:** Feedback de usuário em `anotacoes/feedbacks.md` (*"nos imputs das placas, adicionar um campo para minutos, além de somente horas. Ex: 1:30, em vez de somente 1."*)
- **Comportamento Anterior:** O tempo de impressão aceitava apenas um único campo de horas.
- **Correção Implementada:**
  1. No formulário de placas em `frontend/js/app.js`, criado par de inputs `plate-time-h-${idx}` e `plate-time-m-${idx}`.
  2. Implementada função `updatePlateTime(idx)` com recálculo instantâneo sem perda de foco do cursor.
  3. Sincronização automática na submissão de projeto em `saveCurrentProject`.
- **Verificação:** Coberto em `tests/test_frontend_inputs.py`.

---

### Issue #8: Cadastro de filamento: gerar nome padronizado e seletor visual de cor
- **Status:** `CLOSED` (Resolvido)
- **Link Remoto:** https://github.com/vitorbuss04/splendid-hypatia/issues/8
- **Labels:** `enhancement`, `frontend`, `database`
- **Origem:** Feedback de usuário em `anotacoes/feedbacks.md` (*"Ao cadastrar um novo filamento, quero o seguinte: remover o campo do nome do filamento, em vez disso, quero que o nome do filamento seja esse padrão: 'Material + Cor + - + Marca'... adicionar um input color..."*)
- **Correção Implementada:**
  1. Campo manual de nome removido no modal de filamento.
  2. Adicionado `<input type="color" id="filament-color-hex">` com prévia em tempo real do nome gerado (`Material Cor - Marca`).
  3. Adicionada coluna `color_hex` em `models.Filament` e schemas Pydantic com migração dinâmica SQLite.
  4. Adicionado swatch de cor visual nos cards e indicador de cor nos dropdowns de seleção na calculadora.
- **Verificação:** Coberto em `tests/test_api.py` e `tests/test_frontend_inputs.py`.

---

### Issue #9: Exportação de PDF: exibir apenas o nome do material na coluna de filamento
- **Status:** `CLOSED` (Resolvido)
- **Link Remoto:** https://github.com/vitorbuss04/splendid-hypatia/issues/9
- **Labels:** `enhancement`, `reports`, `backend`
- **Origem:** Feedback de usuário em `anotacoes/feedbacks.md` (*"Nos pdfs, a coluna do material / filamento deve aparecer apenas o nome do material, ex: PLA, TPU."*)
- **Comportamento Anterior:** O PDF exibia o nome comercial completo do filamento (ex: "PLA Preto - 3D Prime") ou "Filamento Técnico".
- **Correção Implementada:**
  1. Criada função `extract_clean_material(p)` em `backend/pdf_service.py` que sanitiza notas de polímero e extrai materiais puros (PLA, PETG, TPU, ABS, Resina).
  2. Aplicado nos relatórios de proposta comercial (cliente) e ficha técnica de produção.
- **Verificação:** Coberto em `tests/test_api.py`.

---

### Issue #10: Orçamento: campo para prazo de entrega em dias úteis no rodapé
- **Status:** `CLOSED` (Resolvido)
- **Link Remoto:** https://github.com/vitorbuss04/splendid-hypatia/issues/10
- **Labels:** `enhancement`, `backend`, `frontend`
- **Origem:** Feedback de usuário em `anotacoes/feedbacks.md` (*"Adicionar campo para número de dias para entrega a partir da aprovação para ter o controle sobra a informação que aparece no rodapé do orçamento."*)
- **Correção Implementada:**
  1. Adicionado campo `delivery_days` em `models.Project`, `schemas.ProjectBase` e `frontend/index.html` (`#proj-delivery-days`).
  2. Migração automática do banco SQLite em `backend/database.py`.
  3. No rodapé do PDF, formatação gramatical correta: "1 dia útil" para 1 dia e "N dias úteis" para múltiplos dias.
- **Verificação:** Coberto em `tests/test_api.py`.

---

### Issue #11: Exportação de Orçamento: visualização em nova guia com opção de download
- **Status:** `CLOSED` (Resolvido)
- **Link Remoto:** https://github.com/vitorbuss04/splendid-hypatia/issues/11
- **Labels:** `enhancement`, `frontend`, `reports`
- **Origem:** Feedback de usuário em `anotacoes/feedbacks.md` (*"Ao invés de fazer o download do orçamento sempre que clicar, mostrar uma página de visualização em uma nova guia com opção de download"*)
- **Correção Implementada:**
  1. Criada página `frontend/preview.html` com cabeçalho de ações (download do arquivo e impressão) e visualizador de documento PDF integrado.
  2. Implementada rota `/preview` e suporte a Content-Disposition inline no backend.
  3. Atualizado `API.pdf.preview()` para abrir a nova guia passando o token de autenticação de forma resiliente.
  4. Botões de exportação salvam alterações do editor antes de abrir a visualização.
- **Verificação:** Coberto em `tests/test_api.py` e `tests/test_frontend_inputs.py`.

---

## Como Sincronizar Novamente com GitHub

Para ressincronizar ou rodar a qualquer momento:

```bash
# Via Python (utiliza as credenciais já configuradas no Git Credential Manager ou GITHUB_TOKEN)
python scripts/sync_github_issues.py

# Ou via PowerShell (se o CLI gh estiver instalado)
.\.github\sync_issues.ps1

# Ou via Bash / Shell Linux
./.github/sync_issues.sh
```
