# Caderno de Feedbacks & Melhorias

Abaixo estão registrados os feedbacks de usuários com seu respectivo status de resolução e rastreamento oficial de issues no GitHub.

---

### 1. Cadastrar filamento > peso do carretel só aceita valores ímpares: ex: 1001, e não aceita 1000
- **Status:** [x] **RESOLVIDO / CONCLUÍDO**
- **GitHub Issue:** [#1 - Cadastrar filamento: peso do carretel só aceita ímpares (ex: 1001) e rejeita 1000g](https://github.com/vitorbuss04/splendid-hypatia/issues/1)
- **Causa:** O atributo HTML `step="50"` combinado com `min="1"` no campo `filament-weight` exigia que o valor cumprisse `(valor - 1) % 50 === 0`, fazendo com que 1000 g falhasse na validação nativa do navegador (`stepMismatch`) e apenas valores como 1001 fossem aceitos.
- **Solução Implementada:** Atualizado para `step="any"` em `frontend/index.html` e validação numérica resiliente no frontend e backend. Testado com carretéis de 250g, 500g, 1000g e 1001g.

---

### 2. Cadastrar filamento > Preço do carretel, só aceita valores inteiros, como é dinheiro, deveria aceitar centavos. (ex: 56,50)
- **Status:** [x] **RESOLVIDO / CONCLUÍDO**
- **GitHub Issue:** [#2 - Cadastrar filamento: preço do carretel só aceita inteiros e bloqueia centavos (ex: 56,50)](https://github.com/vitorbuss04/splendid-hypatia/issues/2)
- **Causa:** O atributo HTML `step="1"` bloqueava valores decimais. Além disso, a digitação de vírgula ou colagem no formato monetário brasileiro (`56,50` ou `R$ 56,50`) causava rejeição nativa pelo navegador.
- **Solução Implementada:** 
  1. Atualizado para `step="any"` em `frontend/index.html`.
  2. Implementada função `parseLocaleFloat` para cálculo preciso do custo por grama em centavos (ex: R$ 56,50 / 1000g = R$ 0,0565/g).
  3. Suporte a colagem com símbolos de moeda brasileira via listener de `paste`.
  4. Suporte a separadores decimais brasileiro (vírgula) e internacional (ponto).

---

### 3. Cadastrar impressora: mesmo problema na vida útil em horas.
- **Status:** [x] **RESOLVIDO / CONCLUÍDO**
- **GitHub Issue:** [#3 - Cadastrar impressora: vida útil em horas rejeita valores redondos (5000h)](https://github.com/vitorbuss04/splendid-hypatia/issues/3)
- **Causa:** O campo `printer-lifespan` possuía `step="100"` e `min="1"`. O valor padrão recomendado de 5000h resultava em `(5000 - 1) % 100 = 99 != 0`, causando erro de validação `stepMismatch`.
- **Solução Implementada:** Atualizado para `step="any"` com fallback seguro para 5000h em `app.js` e verificação no cálculo de depreciação horária de máquinas em `backend/engine.py`.

---

### 4. Input numérico decimal: digitação de vírgula apagava o valor no navegador Chrome/Edge
- **Status:** [x] **RESOLVIDO / CONCLUÍDO**
- **GitHub Issue:** [#4 - Input numérico decimal: digitação de vírgula limpa o valor no navegador](https://github.com/vitorbuss04/splendid-hypatia/issues/4)
- **Causa:** Ao atribuir diretamente `target.value += '.'` em um elemento `<input type="number">`, a string terminada em ponto (ex: `"56."`) violava o algoritmo de sanitização de ponto flutuante do HTML5, levando o navegador a resetar o valor para string vazia (`""`).
- **Solução Implementada:** Implementada alternância dinâmica de modo de edição em `frontend/js/app.js`: no foco (`focusin`), o campo transiciona para `type="text"` com `inputMode="decimal"`, permitindo digitação fluida e livre de vírgula e ponto. Na saída (`focusout`) e no envio de formulários (`normalizeNumericInputs`), o valor é parseado com precisão via `parseLocaleFloat` e o tipo é restaurado com segurança para `number`.
