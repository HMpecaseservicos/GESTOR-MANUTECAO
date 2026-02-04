# Instalacao do Fly CLI e Deploy - Windows PowerShell
# =====================================================

Write-Host "`n=================================================" -ForegroundColor Cyan
Write-Host "   FLY.IO - INSTALACAO E DEPLOY ETAPA 0" -ForegroundColor Cyan
Write-Host "=================================================`n" -ForegroundColor Cyan

# 1. Instalar Fly CLI
Write-Host "1 INSTALANDO FLY CLI..." -ForegroundColor Yellow
try {
    iwr https://fly.io/install.ps1 -useb | iex
    Write-Host "Fly CLI instalado com sucesso!`n" -ForegroundColor Green
    
    # Adicionar ao PATH da sessao atual
    $env:Path = "$env:USERPROFILE\.fly\bin;" + $env:Path
    
} catch {
    Write-Host "Erro ao instalar Fly CLI: $_" -ForegroundColor Red
    exit 1
}

# 2. Verificar instalacao
Write-Host "2 VERIFICANDO INSTALACAO..." -ForegroundColor Yellow
try {
    $version = fly version
    Write-Host "Fly CLI versao: $version`n" -ForegroundColor Green
} catch {
    Write-Host "Reinicie o PowerShell e execute: fly auth login" -ForegroundColor Yellow
    exit 0
}

# 3. Login no Fly.io
Write-Host "3 FAZENDO LOGIN NO FLY.IO..." -ForegroundColor Yellow
Write-Host "   Uma janela do navegador sera aberta para login.`n" -ForegroundColor Cyan
fly auth login

# 4. Criar app (se nao existir)
Write-Host "`n4 CRIANDO APP NO FLY.IO..." -ForegroundColor Yellow
$appName = "gestor-frota-hibrido"

try {
    fly apps create $appName --org personal 2>$null
    Write-Host "App '$appName' criado com sucesso!" -ForegroundColor Green
} catch {
    Write-Host "App '$appName' ja existe ou erro ao criar." -ForegroundColor Cyan
}

# 5. Criar cluster PostgreSQL
Write-Host "`n5 CRIANDO CLUSTER POSTGRESQL..." -ForegroundColor Yellow
$dbName = "gestor-frota-db"

Write-Host "   Criando cluster '$dbName' na regiao gru (Sao Paulo)..." -ForegroundColor Cyan
fly postgres create --name $dbName --region gru --initial-cluster-size 1 --vm-size shared-cpu-1x --volume-size 1

# 6. Anexar banco ao app
Write-Host "`n6 ANEXANDO BANCO AO APP..." -ForegroundColor Yellow
fly postgres attach $dbName --app $appName

# 7. Configurar secrets
Write-Host "`n7 CONFIGURANDO SECRETS..." -ForegroundColor Yellow

# Gerar SECRET_KEY
$secretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | ForEach-Object {[char]$_})
fly secrets set SECRET_KEY="$secretKey" --app $appName

Write-Host "SECRET_KEY configurada!" -ForegroundColor Green

# 8. Fazer deploy
Write-Host "`n8 FAZENDO DEPLOY DA APLICACAO..." -ForegroundColor Yellow
Write-Host "   Isso pode levar alguns minutos...`n" -ForegroundColor Cyan
fly deploy

# 9. Verificar status
Write-Host "`n9 VERIFICANDO STATUS..." -ForegroundColor Yellow
fly status --app $appName

# 10. Executar migracoes
Write-Host "`n10 EXECUTANDO MIGRACOES NO FLY..." -ForegroundColor Yellow
Write-Host "   Acessando console SSH...`n" -ForegroundColor Cyan

fly ssh console --app $appName -C "cd /app && python run_migrations.py"

# 11. Verificar health
Write-Host "`nVALIDANDO HEALTH CHECK..." -ForegroundColor Yellow
$url = "https://$appName.fly.dev/health"
Write-Host "   Testando: $url`n" -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri $url
    Write-Host "Health check OK:" -ForegroundColor Green
    $response | ConvertTo-Json
} catch {
    Write-Host "Erro ao acessar health check: $_" -ForegroundColor Yellow
}

# Finalizacao
Write-Host "`n=================================================" -ForegroundColor Cyan
Write-Host "   DEPLOY CONCLUIDO!" -ForegroundColor Green
Write-Host "=================================================`n" -ForegroundColor Cyan

Write-Host "Proximos passos:" -ForegroundColor Yellow
Write-Host "   1. Verificar logs: fly logs --app $appName" -ForegroundColor White
Write-Host "   2. Acessar console: fly ssh console --app $appName" -ForegroundColor White
Write-Host "   3. Ver status: fly status --app $appName" -ForegroundColor White
Write-Host "   4. Abrir app: fly open --app $appName" -ForegroundColor White
Write-Host ""
