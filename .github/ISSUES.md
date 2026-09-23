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
