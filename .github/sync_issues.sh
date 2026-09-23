#!/usr/bin/env bash
# Bash script to synchronize issues to GitHub using Python REST API or gh CLI

set -e

REPO="vitorbuss04/splendid-hypatia"

echo "Iniciando sincronização de issues com o GitHub..."

# 1. Se Python estiver disponível, roda o sincronizador direto via API REST autenticada
if command -v python3 &>/dev/null || command -v python &>/dev/null; then
    PY_CMD=$(command -v python3 || command -v python)
    echo "Executando sincronização via Python REST API..."
    "$PY_CMD" scripts/sync_github_issues.py
    echo "Sincronização concluída com sucesso via Python!"
    exit 0
fi

# 2. Fallback para gh CLI se instalado
if command -v gh &>/dev/null; then
    echo "Executando sincronização via GitHub CLI (gh)..."
    
    create_and_close() {
        local title="$1"
        local body="$2"
        local labels="$3"
        local comment="$4"

        echo "Criando issue: $title"
        local issue_url
        issue_url=$(gh issue create --repo "$REPO" --title "$title" --body "$body" --label "$labels")
        echo "Issue criada: $issue_url"
        echo "Fechando issue como resolvida..."
        gh issue close --repo "$REPO" "$issue_url" --comment "$comment"
    }

    create_and_close \
        "Cadastrar filamento: peso do carretel só aceita valores ímpares (ex: 1001) e rejeita 1000g" \
        "Corrigido step mismatch causado por min=1 e step=50 no input de peso do carretel. Atualizado para step='any' e parseLocaleFloat no frontend/index.html e frontend/js/app.js." \
        "bug,frontend,ux" \
        "Resolvido no commit 86ad9aa e verificado na suíte de testes automatizados."

    create_and_close \
        "Cadastrar filamento: preço do carretel só aceita inteiros e bloqueia centavos (ex: 56,50)" \
        "Corrigido step='1' no input de preço. Adicionado suporte a decimais com step='any', suporte a formatação monetária brasileira e internacional via parseLocaleFloat." \
        "bug,financial,frontend" \
        "Resolvido no commit 86ad9aa e verificado na suíte de testes automatizados."

    create_and_close \
        "Cadastrar impressora: vida útil em horas rejeita valores redondos (5000h)" \
        "Corrigido step mismatch causado por min=1 e step=100 no input printer-lifespan. Atualizado para step='any' e verificado no cálculo de depreciação horária de máquinas." \
        "bug,printers,frontend" \
        "Resolvido no commit 86ad9aa e verificado na suíte de testes automatizados."

    create_and_close \
        "Input numérico decimal: digitação de vírgula limpa o valor no navegador" \
        "Corrigido comportamento no Chrome/Edge onde atribuir trailing dot ao .value resetava o input. Implementado toggle para type=text e inputMode=decimal no foco." \
        "bug,frontend,ux" \
        "Resolvido e verificado com testes automatizados em headless Chrome e pytest."

    echo "Todas as issues foram sincronizadas e marcadas como resolvidas com sucesso!"
    exit 0
fi

echo "Não foi possível sincronizar: instale Python ou GitHub CLI (gh)." >&2
exit 1
