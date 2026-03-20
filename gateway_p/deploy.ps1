# ============================================================================
# Script de Despliegue Automatizado - Pagoflex Gateway (PowerShell)
# ============================================================================
# Este script automatiza el proceso de build, push y deploy a GCP Cloud Run
# Verifica autenticación y ejecuta los pasos necesarios
# ============================================================================

$ErrorActionPreference = "Stop"

# Configuración
$REQUIRED_EMAIL = "gcloud@pagoflex.com.ar"
$PROJECT_ID = "pagoflex-middleware"
$IMAGE_NAME = "us-central1-docker.pkg.dev/pagoflex-middleware/pagoflex-middleware/pagoflex:latest"
$SERVICE_NAME = "pagoflex-middleware-api"
$REGION = "us-central1"

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

function Print-Header {
    param([string]$Message)
    Write-Host "`n===============================================" -ForegroundColor Blue
    Write-Host $Message -ForegroundColor Blue
    Write-Host "===============================================`n" -ForegroundColor Blue
}

function Print-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Print-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Print-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Print-Info {
    param([string]$Message)
    Write-Host "→ $Message" -ForegroundColor Cyan
}

# ============================================================================
# VERIFICACIONES PREVIAS
# ============================================================================

function Check-GcloudInstalled {
    if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
        Print-Error "gcloud CLI no está instalado"
        Write-Host "Instala gcloud desde: https://cloud.google.com/sdk/docs/install"
        exit 1
    }
    Print-Success "gcloud CLI instalado"
}

function Check-DockerInstalled {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Print-Error "Docker no está instalado"
        Write-Host "Instala Docker desde: https://docs.docker.com/get-docker/"
        exit 1
    }
    Print-Success "Docker instalado"
}

function Check-DockerfileExists {
    if (-not (Test-Path "Dockerfile")) {
        Print-Error "Dockerfile no encontrado en el directorio actual"
        Write-Host "Directorio actual: $(Get-Location)"
        Write-Host "Por favor ejecuta este script desde el directorio gateway_p/"
        exit 1
    }
    Print-Success "Dockerfile encontrado"
}

# ============================================================================
# AUTENTICACIÓN GCP
# ============================================================================

function Check-GcloudAuth {
    Print-Header "VERIFICANDO AUTENTICACIÓN GCP"
    
    # Verificar si hay una cuenta activa
    $activeAccount = gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null
    
    if (-not $activeAccount) {
        Print-Warning "No hay ninguna cuenta activa"
        return $false
    }
    
    if ($activeAccount -ne $REQUIRED_EMAIL) {
        Print-Warning "Cuenta activa: $activeAccount"
        Print-Warning "Se requiere: $REQUIRED_EMAIL"
        return $false
    }
    
    Print-Success "Autenticado como: $activeAccount"
    
    # Verificar el proyecto activo
    $activeProject = gcloud config get-value project 2>$null
    if ($activeProject -ne $PROJECT_ID) {
        Print-Info "Configurando proyecto: $PROJECT_ID"
        gcloud config set project $PROJECT_ID
    }
    Print-Success "Proyecto configurado: $PROJECT_ID"
    
    return $true
}

function Perform-GcloudLogin {
    Print-Header "AUTENTICACIÓN REQUERIDA"
    
    Print-Info "Iniciando login de gcloud..."
    Write-Host "Se abrirá el navegador, logueate con: $REQUIRED_EMAIL"
    Start-Sleep -Seconds 2
    
    try {
        gcloud auth login
        Print-Success "Login principal completado"
    }
    catch {
        Print-Error "Error en el login principal"
        exit 1
    }
    
    Print-Info "Configurando credenciales de aplicación..."
    Write-Host "Se abrirá el navegador nuevamente, usa la misma cuenta"
    Start-Sleep -Seconds 2
    
    try {
        gcloud auth application-default login
        Print-Success "Credenciales de aplicación configuradas"
    }
    catch {
        Print-Error "Error al configurar credenciales de aplicación"
        exit 1
    }
    
    # Configurar proyecto
    gcloud config set project $PROJECT_ID
    Print-Success "Proyecto configurado: $PROJECT_ID"
}

# ============================================================================
# PROCESO DE DESPLIEGUE
# ============================================================================

function Build-Image {
    Print-Header "PASO 1: BUILD - Construyendo imagen Docker"
    
    Print-Info "Imagen: $IMAGE_NAME"
    Print-Info "Plataforma: linux/amd64"
    
    try {
        docker build --platform linux/amd64 -t $IMAGE_NAME .
        Print-Success "Imagen construida exitosamente"
    }
    catch {
        Print-Error "Error al construir la imagen"
        exit 1
    }
}

function Push-Image {
    Print-Header "PASO 2: PUSH - Subiendo imagen a GCP"
    
    Print-Info "Destino: Container Registry GCP"
    
    try {
        docker push $IMAGE_NAME
        Print-Success "Imagen subida exitosamente"
    }
    catch {
        Print-Error "Error al subir la imagen"
        exit 1
    }
}

function Deploy-Service {
    Print-Header "PASO 3: DEPLOY - Actualizando servicio en Cloud Run"
    
    Print-Info "Servicio: $SERVICE_NAME"
    Print-Info "Región: $REGION"
    
    try {
        gcloud run services update $SERVICE_NAME `
            --image $IMAGE_NAME `
            --region $REGION
        Print-Success "Servicio actualizado exitosamente"
    }
    catch {
        Print-Error "Error al actualizar el servicio"
        exit 1
    }
}

function Get-ServiceUrl {
    Print-Header "INFORMACIÓN DEL SERVICIO"
    
    $serviceUrl = gcloud run services describe $SERVICE_NAME `
        --region $REGION `
        --format='value(status.url)' 2>$null
    
    if ($serviceUrl) {
        Write-Host "✓ Servicio activo en:" -ForegroundColor Green
        Write-Host "  $serviceUrl" -ForegroundColor Blue
        Write-Host "`n✓ Documentación Swagger:" -ForegroundColor Green
        Write-Host "  $serviceUrl/docs" -ForegroundColor Blue
    }
}

function Verify-ServiceHealth {
    Print-Header "VERIFICACIÓN DE SALUD DEL SERVICIO"
    
    Print-Info "Comprobando endpoint /health..."
    
    $healthUrl = "https://pagoflex-middleware-api-470611393827.us-central1.run.app/health"
    
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -Method Get -UseBasicParsing
        
        Write-Host "`nRespuesta del servicio:" -ForegroundColor Blue
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        Write-Host $response.Content
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if ($response.StatusCode -eq 200) {
            Print-Success "Servicio respondiendo correctamente (HTTP $($response.StatusCode))"
        }
        else {
            Print-Warning "Servicio respondió con HTTP $($response.StatusCode)"
        }
    }
    catch {
        Print-Warning "No se pudo verificar el servicio: $_"
    }
}

# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================

function Main {
    Clear-Host
    Print-Header "🚀 DESPLIEGUE PAGOFLEX GATEWAY - GCP CLOUD RUN"
    
    Write-Host "Este script automatiza el proceso de despliegue:"
    Write-Host "  1. Verificación de autenticación"
    Write-Host "  2. Build de imagen Docker"
    Write-Host "  3. Push a Container Registry"
    Write-Host "  4. Deploy a Cloud Run"
    Write-Host ""
    
    # Verificaciones previas
    Print-Header "VERIFICACIONES PREVIAS"
    Check-GcloudInstalled
    Check-DockerInstalled
    Check-DockerfileExists
    
    # Verificar autenticación
    if (-not (Check-GcloudAuth)) {
        Print-Warning "Autenticación requerida"
        $response = Read-Host "¿Deseas continuar con el login? (s/n)"
        if ($response -match '^[Ss]$') {
            Perform-GcloudLogin
        }
        else {
            Print-Error "Autenticación cancelada"
            exit 1
        }
    }
    
    # Confirmar inicio del despliegue
    Write-Host ""
    Print-Warning "Estás a punto de desplegar a PRODUCCIÓN"
    $response = Read-Host "¿Continuar con el despliegue? (s/n)"
    if ($response -notmatch '^[Ss]$') {
        Print-Info "Despliegue cancelado"
        exit 0
    }
    
    # Ejecutar proceso de despliegue
    $startTime = Get-Date
    
    Build-Image
    Push-Image
    Deploy-Service
    
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    
    # Resumen final
    Print-Header "✅ DESPLIEGUE COMPLETADO"
    Write-Host "Tiempo total: $duration segundos" -ForegroundColor Green
    Write-Host ""
    
    Get-ServiceUrl
    
    # Verificar salud del servicio
    Verify-ServiceHealth
    
    Write-Host ""
    Print-Success "¡Despliegue exitoso!"
    Write-Host ""
}

# Ejecutar script principal
Main
