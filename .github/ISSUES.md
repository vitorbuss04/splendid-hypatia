# GitHub Issues Tracker & Changelog

Este arquivo centraliza o rastreamento de issues do repositório **3D Print Calc Pro** conforme os feedbacks de usuários e melhorias contínuas.

---

## Índice de Issues

| ID | Título | Tipo | Status | Resolução | Testes Automatizados |
|---|---|---|---|---|---|
| [#1](#issue-1-validação-de-peso-do-carretel-de-filamento-rejeita-valores-pares-e-padrões-como-1000g) | Cadastrar filamento: peso do carretel só aceita ímpares (ex: 1001) e rejeita 1000g | Bug / UX | **FECHADA (Resolvida)** | `step="any"` + validação no app.js | `tests/test_frontend_inputs.py`, `tests/test_api.py` |
| [#2](#issue-2-preço-do-carretel-de-filamento-não-aceita-centavos-ex-r-5650) | Cadastrar filamento: preço do carretel só aceita inteiros e bloqueia centavos | Bug / Financeiro | **FECHADA (Resolvida)** | `step="any"` + suporte a vírgula/moeda BR + `parseLocaleFloat` | `tests/test_frontend_inputs.py`, `tests/test_api.py` |
| [#3](#issue-3-vida-útil-da-impressora-em-horas-rejeita-5000h-por-validação-de-step) | Cadastrar impressora: vida útil em horas rejeita valores redondos (5000h) | Bug / UX | **FECHADA (Resolvida)** | `step="any"` + validação de horas no frontend/backend | `tests/test_frontend_inputs.py`, `tests/test_api.py` |

---

## Detalhamento das Issues

### Issue #1: Validação de peso do carretel de filamento rejeita valores pares e padrões como 1000g
- **Status:** `CLOSED` (Resolvido)
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
- **Labels:** `bug`, `financial`, `frontend`, `backend`
- **Origem:** Feedback de usuário em `anotacoes/feedbacks.md` (*"Cadastrar filamento > Preço do carretel, só aceita valores inteiros, como é dinheiro, deveria aceitar centavos. (ex: 56,50)"*)
- **Comportamento Anterior:** O campo de preço do filamento recusava valores com casas decimais (centavos), exigindo números inteiros. Além disso, se o usuário digitasse vírgula ou colasse `56,50` ou `R$ 56,50`, o campo ficava inválido ou zerado.
- **Causa Raiz:** O input HTML continha `step="1"`, limitando a entrada a inteiros. Além disso, navegadores em desktop bloqueiam o caractere de vírgula em inputs `type="number"` sem tratamento explícito de eventos.
- **Correção Implementada:**
  1. No HTML `frontend/index.html`, atualizado `filament-price` para `step="any"`.
  2. No JavaScript `frontend/js/app.js`:
     - Adicionado listener global `beforeinput` e `keydown` para converter automaticamente tecla de vírgula (`,`) em ponto decimal (`.`) sem quebrar a validação nativa.
     - Adicionado listener global `paste` com suporte à colagem de valores monetários brasileiros (ex: `R$ 56,50` ou `1.250,90`).
     - Função `parseLocaleFloat` para lidar com separadores de milhar e centavos no padrão brasileiro.
  3. No backend, schema e banco utilizam `float` com precisão adequada para centavos e custo por grama com 3 a 4 casas decimais.
- **Verificação:** Testes de validação de input em `tests/test_frontend_inputs.py` e cálculo de custo por grama em `tests/test_api.py`.

---

### Issue #3: Vida útil da impressora em horas rejeita 5000h por validação de step
- **Status:** `CLOSED` (Resolvido)
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

## Comandos para Sincronização com GitHub (Quando o Remote for Conectado)

Caso o repositório seja associado a uma conta GitHub e o GitHub CLI (`gh`) seja autenticado, execute os comandos abaixo ou execute `.github/sync_issues.ps1` (Windows) / `.github/sync_issues.sh` (Linux/macOS):

```bash
# 1. Autenticar no GitHub (se ainda não autenticado)
gh auth login

# 2. Criar Issue #1 e fechá-la como resolvida
gh issue create \
  --title "Cadastrar filamento: peso do carretel só aceita valores ímpares (ex: 1001) e rejeita 1000g" \
  --body "Corrigido step mismatch causado por min=1 e step=50 no input de peso do carretel. Atualizado para step='any' e parseLocaleFloat." \
  --label "bug,frontend,ux"
gh issue close 1 --comment "Resolvido no commit 86ad9aa e verificado na suíte de testes automatizados."

# 3. Criar Issue #2 e fechá-la como resolvida
gh issue create \
  --title "Cadastrar filamento: preço do carretel só aceita inteiros e bloqueia centavos (ex: 56,50)" \
  --body "Corrigido step='1' no input de preço. Adicionado suporte a decimais com step='any', conversão de vírgula em tempo real e tratamento de moeda brasileira." \
  --label "bug,financial,frontend"
gh issue close 2 --comment "Resolvido no commit 86ad9aa e verificado na suíte de testes automatizados."

# 4. Criar Issue #3 e fechá-la como resolvida
gh issue create \
  --title "Cadastrar impressora: vida útil em horas rejeita valores redondos (5000h)" \
  --body "Corrigido step mismatch causado por min=1 e step=100 no input printer-lifespan. Atualizado para step='any' e verificado no cálculo de depreciação horária." \
  --label "bug,printers,frontend"
gh issue close 3 --comment "Resolvido no commit 86ad9aa e verificado na suíte de testes automatizados."
```
