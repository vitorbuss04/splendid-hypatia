# PowerShell script to synchronize issues to GitHub using gh CLI once remote is configured
param(
    [string]$Repo = ""
)

Write-Host "Verificando GitHub CLI (gh)..." -ForegroundColor Cyan

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "GitHub CLI (gh) não está instalado no sistema. Instale via 'winget install GitHub.cli' e autentique via 'gh auth login'." -ForegroundColor Red
    exit 1
}

$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "gh não está autenticado. Execute 'gh auth login' antes de prosseguir." -ForegroundColor Yellow
    exit 1
}

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
        Body = "Corrigido step='1' no input de preço. Adicionado suporte a decimais com step='any', conversão de vírgula em tempo real via beforeinput/keydown e suporte a formatação monetária brasileira via parseLocaleFloat."
        Labels = "bug,financial,frontend"
        CloseComment = "Resolvido no commit 86ad9aa e verificado na suíte de testes automatizados."
    },
    @{
        Title = "Cadastrar impressora: vida útil em horas rejeita valores redondos (5000h)"
        Body = "Corrigido step mismatch causado por min=1 e step=100 no input printer-lifespan. Atualizado para step='any' e verificado no cálculo de depreciação horária de máquinas."
        Labels = "bug,printers,frontend"
        CloseComment = "Resolvido no commit 86ad9aa e verificado na suíte de testes automatizados."
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
