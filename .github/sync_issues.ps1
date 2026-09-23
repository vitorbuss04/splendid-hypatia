# PowerShell script to synchronize issues to GitHub using Python REST API or gh CLI
param(
    [string]$Repo = "vitorbuss04/splendid-hypatia"
)

Write-Host "Iniciando sincronização de issues com o GitHub..." -ForegroundColor Cyan

# 1. Se Python estiver disponível, roda o sincronizador direto via API REST autenticada
if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "Executando sincronização via Python REST API..." -ForegroundColor Green
    python scripts/sync_github_issues.py
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Sincronização concluída com sucesso via Python!" -ForegroundColor Green
        exit 0
    }
}

# 2. Fallback para gh CLI se instalado
if (Get-Command gh -ErrorAction SilentlyContinue) {
    Write-Host "Executando sincronização via GitHub CLI (gh)..." -ForegroundColor Green
    
    $repoArg = @()
    if ($Repo -ne "") {
        $repoArg = @("--repo", $Repo)
    }

    $issues = @(
        @{
            Title = "Cadastrar filamento: peso do carretel só aceita valores ímpares (ex: 1001) e rejeita 1000g"
            Body = "Corrigido step mismatch causado por min=1 e step=50 no input de peso do carretel. Atualizado para step='any' e parseLocaleFloat no frontend/index.html e frontend/js/app.js."
            Labels = "bug,frontend,ux"
            CloseComment = "Resolvido no commit 86ad9aa e verificado na suíte de testes automatizados."
        },
        @{
            Title = "Cadastrar filamento: preço do carretel só aceita inteiros e bloqueia centavos (ex: 56,50)"
            Body = "Corrigido step='1' no input de preço. Adicionado suporte a decimais com step='any', suporte a formatação monetária brasileira e internacional via parseLocaleFloat."
            Labels = "bug,financial,frontend"
            CloseComment = "Resolvido no commit 86ad9aa e verificado na suíte de testes automatizados."
        },
        @{
            Title = "Cadastrar impressora: vida útil em horas rejeita valores redondos (5000h)"
            Body = "Corrigido step mismatch causado por min=1 e step=100 no input printer-lifespan. Atualizado para step='any' e verificado no cálculo de depreciação horária de máquinas."
            Labels = "bug,printers,frontend"
            CloseComment = "Resolvido no commit 86ad9aa e verificado na suíte de testes automatizados."
        },
        @{
            Title = "Input numérico decimal: digitação de vírgula limpa o valor no navegador"
            Body = "Corrigido comportamento no Chrome/Edge onde atribuir trailing dot ao .value resetava o input. Implementado toggle para type=text e inputMode=decimal no foco."
            Labels = "bug,frontend,ux"
            CloseComment = "Resolvido e verificado com testes automatizados em headless Chrome e pytest."
        }
    )

    foreach ($issue in $issues) {
        Write-Host "Criando issue: $($issue.Title)..." -ForegroundColor Green
        $url = gh issue create @repoArg --title $issue.Title --body $issue.Body --label $issue.Labels
        if ($url) {
            Write-Host "Issue criada: $url" -ForegroundColor DarkGreen
            Write-Host "Fechando issue como resolvida..." -ForegroundColor Yellow
            gh issue close @repoArg $url --comment $issue.CloseComment
        }
    }

    Write-Host "Todas as issues foram sincronizadas e marcadas como resolvidas com sucesso!" -ForegroundColor Green
    exit 0
}

Write-Host "Não foi possível sincronizar: instale Python ou GitHub CLI (gh)." -ForegroundColor Red
exit 1
