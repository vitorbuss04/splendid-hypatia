# Caderno de Feedbacks & Melhorias

Abaixo estão registrados os feedbacks de usuários com seu respectivo status de resolução e rastreamento de issues do GitHub.

---

### 1. Cadastrar filamento > peso do carretel só aceita valores ímpares: ex: 1001, e não aceita 1000
- **Status:** [x] **RESOLVIDO / CONCLUÍDO**
- **GitHub Issue:** [#1 - Cadastrar filamento: peso do carretel só aceita ímpares (.github/ISSUES.md)](../.github/ISSUES.md#issue-1-validação-de-peso-do-carretel-de-filamento-rejeita-valores-pares-e-padrões-como-1000g)
- **Causa:** O atributo HTML `step="50"` combinado com `min="1"` no campo `filament-weight` exigia que o valor cumprisse `(valor - 1) % 50 === 0`, fazendo com que 1000 g falhasse na validação nativa do navegador e apenas valores como 1001 fossem aceitos.
- **Solução Implementada:** Atualizado para `step="any"` em `frontend/index.html` e validação numérica resiliente no frontend e backend. Testado com carretéis de 1000g, 500g, 250g e 1001g.

---

### 2. Cadastrar filamento > Preço do carretel, só aceita valores inteiros, como é dinheiro, deveria aceitar centavos. (ex: 56,50)
- **Status:** [x] **RESOLVIDO / CONCLUÍDO**
- **GitHub Issue:** [#2 - Cadastrar filamento: preço do carretel só aceita inteiros e bloqueia centavos (.github/ISSUES.md)](../.github/ISSUES.md#issue-2-preço-do-carretel-de-filamento-não-aceita-centavos-ex-r-5650)
- **Causa:** O atributo HTML `step="1"` bloqueava valores decimais. Além disso, a digitação de vírgula ou colagem no formato monetário brasileiro (`56,50` ou `R$ 56,50`) causava rejeição nativa pelo navegador.
- **Solução Implementada:** 
  1. Atualizado para `step="any"` em `frontend/index.html`.
  2. Implementado listeners `beforeinput` e `keydown` para converter a tecla vírgula em ponto em tempo real.
  3. Suporte a colagem com símbolos de moeda via listener de `paste`.
  4. Função `parseLocaleFloat` para cálculo preciso do custo por grama em centavos (ex: R$ 56,50 / 1000g = R$ 0,0565/g).

---

### 3. Cadastrar impressora: mesmo problema na vida útil em horas.
- **Status:** [x] **RESOLVIDO / CONCLUÍDO**
- **GitHub Issue:** [#3 - Cadastrar impressora: vida útil em horas rejeita valores redondos (.github/ISSUES.md)](../.github/ISSUES.md#issue-3-vida-útil-da-impressora-em-horas-rejeita-5000h-por-validação-de-step)
- **Causa:** O campo `printer-lifespan` possuía `step="100"` e `min="1"`. O valor padrão recomendado de 5000h resultava em `(5000 - 1) % 100 = 99 != 0`, causando erro de validação `stepMismatch`.
- **Solução Implementada:** Atualizado para `step="any"` com fallback seguro para 5000h em `app.js` e verificação no cálculo de depreciação horária de máquinas.
