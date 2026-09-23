#!/usr/bin/env bash
# Bash script to synchronize issues to GitHub using gh CLI once remote is configured
set -e

if ! command -v gh &> /dev/null; then
    echo "GitHub CLI (gh) não está instalado. Instale gh e execute 'gh auth login'."
    exit 1
fi

echo "Verificando autenticação no GitHub..."
gh auth status

create_and_close() {
    local title="$1"
    local body="$2"
    local labels="$3"
    local comment="$4"

    echo "Criando issue: $title"
    local issue_url
    issue_url=$(gh issue create --title "$title" --body "$body" --label "$labels")
    echo "Issue criada: $issue_url"
    echo "Fechando issue como resolvida..."
    gh issue close "$issue_url" --comment "$comment"
}

create_and_close \
    "Cadastrar filamento: peso do carretel só aceita valores ímpares (ex: 1001) e rejeita 1000g" \
    "Corrigido step mismatch causado por min=1 e step=50 no input de peso do carretel. Atualizado para step='any' e parseLocaleFloat no frontend/index.html e frontend/js/app.js." \
    "bug,frontend,ux" \
    "Resolvido no commit 86ad9aa e verificado na suíte de testes automatizados."

create_and_close \
    "Cadastrar filamento: preço do carretel só aceita inteiros e bloqueia centavos (ex: 56,50)" \
    "Corrigido step='1' no input de preço. Adicionado suporte a decimais com step='any', conversão de vírgula em tempo real via beforeinput/keydown e suporte a formatação monetária brasileira via parseLocaleFloat." \
    "bug,financial,frontend" \
    "Resolvido no commit 86ad9aa e verificado na suíte de testes automatizados."

create_and_close \
    "Cadastrar impressora: vida útil em horas rejeita valores redondos (5000h)" \
    "Corrigido step mismatch causado por min=1 e step=100 no input printer-lifespan. Atualizado para step='any' e verificado no cálculo de depreciação horária de máquinas." \
    "bug,printers,frontend" \
    "Resolvido no commit 86ad9aa e verificado na suíte de testes automatizados."

echo "Todas as issues foram sincronizadas e marcadas como resolvidas!"
