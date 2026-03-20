#!/bin/bash

# ============================================================================
# Script de Despliegue Automatizado - Pagoflex Gateway
# ============================================================================
# Este script automatiza el proceso de build, push y deploy a GCP Cloud Run
# Verifica autenticación y ejecuta los pasos necesarios
# ============================================================================

set -e  # Salir si algún comando falla

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
REQUIRED_EMAIL="gcloud@pagoflex.com.ar"
PROJECT_ID="pagoflex-middleware"
IMAGE_NAME="us-central1-docker.pkg.dev/pagoflex-middleware/pagoflex-middleware/pagoflex:latest"
SERVICE_NAME="pagoflex-middleware-api"
REGION="us-central1"

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

print_header() {
    echo -e "\n${BLUE}===============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===============================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}→ $1${NC}"
}

# ============================================================================
# VERIFICACIONES PREVIAS
# ============================================================================

check_gcloud_installed() {
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI no está instalado"
        echo "Instala gcloud desde: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    print_success "gcloud CLI instalado"
}

check_docker_installed() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker no está instalado"
        echo "Instala Docker desde: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_success "Docker instalado"
}

check_dockerfile_exists() {
    if [ ! -f "Dockerfile" ]; then
        print_error "Dockerfile no encontrado en el directorio actual"
        echo "Directorio actual: $(pwd)"
        echo "Por favor ejecuta este script desde el directorio gateway_p/"
        exit 1
    fi
    print_success "Dockerfile encontrado"
}

# ============================================================================
# AUTENTICACIÓN GCP
# ============================================================================

check_gcloud_auth() {
    print_header "VERIFICANDO AUTENTICACIÓN GCP"
    
    # Verificar si hay una cuenta activa
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null)
    
    if [ -z "$ACTIVE_ACCOUNT" ]; then
        print_warning "No hay ninguna cuenta activa"
        return 1
    fi
    
    if [ "$ACTIVE_ACCOUNT" != "$REQUIRED_EMAIL" ]; then
        print_warning "Cuenta activa: $ACTIVE_ACCOUNT"
        print_warning "Se requiere: $REQUIRED_EMAIL"
        return 1
    fi
    
    print_success "Autenticado como: $ACTIVE_ACCOUNT"
    
    # Verificar el proyecto activo
    ACTIVE_PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [ "$ACTIVE_PROJECT" != "$PROJECT_ID" ]; then
        print_info "Configurando proyecto: $PROJECT_ID"
        gcloud config set project "$PROJECT_ID"
    fi
    print_success "Proyecto configurado: $PROJECT_ID"
    
    return 0
}

perform_gcloud_login() {
    print_header "AUTENTICACIÓN REQUERIDA"
    
    print_info "Iniciando login de gcloud..."
    echo "Se abrirá el navegador, logueate con: $REQUIRED_EMAIL"
    sleep 2
    
    if gcloud auth login; then
        print_success "Login principal completado"
    else
        print_error "Error en el login principal"
        exit 1
    fi
    
    print_info "Configurando credenciales de aplicación..."
    echo "Se abrirá el navegador nuevamente, usa la misma cuenta"
    sleep 2
    
    if gcloud auth application-default login; then
        print_success "Credenciales de aplicación configuradas"
    else
        print_error "Error al configurar credenciales de aplicación"
        exit 1
    fi
    
    # Configurar proyecto
    gcloud config set project "$PROJECT_ID"
    print_success "Proyecto configurado: $PROJECT_ID"
}

# ============================================================================
# PROCESO DE DESPLIEGUE
# ============================================================================

build_image() {
    print_header "PASO 1: BUILD - Construyendo imagen Docker"
    
    print_info "Imagen: $IMAGE_NAME"
    print_info "Plataforma: linux/amd64"
    
    if docker build --platform linux/amd64 -t "$IMAGE_NAME" .; then
        print_success "Imagen construida exitosamente"
    else
        print_error "Error al construir la imagen"
        exit 1
    fi
}

push_image() {
    print_header "PASO 2: PUSH - Subiendo imagen a GCP"
    
    print_info "Destino: Container Registry GCP"
    
    if docker push "$IMAGE_NAME"; then
        print_success "Imagen subida exitosamente"
    else
        print_error "Error al subir la imagen"
        exit 1
    fi
}

deploy_service() {
    print_header "PASO 3: DEPLOY - Actualizando servicio en Cloud Run"
    
    print_info "Servicio: $SERVICE_NAME"
    print_info "Región: $REGION"
    
    if gcloud run services update "$SERVICE_NAME" \
        --image "$IMAGE_NAME" \
        --region "$REGION"; then
        print_success "Servicio actualizado exitosamente"
    else
        print_error "Error al actualizar el servicio"
        exit 1
    fi
}

get_service_url() {
    print_header "INFORMACIÓN DEL SERVICIO"
    
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region "$REGION" \
        --format='value(status.url)' 2>/dev/null)
    
    if [ -n "$SERVICE_URL" ]; then
        echo -e "${GREEN}✓ Servicio activo en:${NC}"
        echo -e "  ${BLUE}$SERVICE_URL${NC}"
        echo -e "\n${GREEN}✓ Documentación Swagger:${NC}"
        echo -e "  ${BLUE}$SERVICE_URL/docs${NC}"
    fi
}

verify_service_health() {
    print_header "VERIFICACIÓN DE SALUD DEL SERVICIO"
    
    print_info "Comprobando endpoint /health..."
    
    HEALTH_URL="https://pagoflex-middleware-api-470611393827.us-central1.run.app/health"
    
    # Hacer el request y capturar status code y respuesta
    HTTP_CODE=$(curl -s -o /tmp/health_response.txt -w "%{http_code}" "$HEALTH_URL")
    RESPONSE=$(cat /tmp/health_response.txt 2>/dev/null)
    
    echo -e "\n${BLUE}Respuesta del servicio:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$RESPONSE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ "$HTTP_CODE" -eq 200 ]; then
        print_success "Servicio respondiendo correctamente (HTTP $HTTP_CODE)"
    else
        print_warning "Servicio respondió con HTTP $HTTP_CODE"
    fi
    
    # Limpiar archivo temporal
    rm -f /tmp/health_response.txt
}

# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================

main() {
    clear
    print_header "🚀 DESPLIEGUE PAGOFLEX GATEWAY - GCP CLOUD RUN"
    
    echo "Este script automatiza el proceso de despliegue:"
    echo "  1. Verificación de autenticación"
    echo "  2. Build de imagen Docker"
    echo "  3. Push a Container Registry"
    echo "  4. Deploy a Cloud Run"
    echo ""
    
    # Verificaciones previas
    print_header "VERIFICACIONES PREVIAS"
    check_gcloud_installed
    check_docker_installed
    check_dockerfile_exists
    
    # Verificar autenticación
    if ! check_gcloud_auth; then
        print_warning "Autenticación requerida"
        read -p "¿Deseas continuar con el login? (s/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            perform_gcloud_login
        else
            print_error "Autenticación cancelada"
            exit 1
        fi
    fi
    
    # Confirmar inicio del despliegue
    echo ""
    print_warning "Estás a punto de desplegar a PRODUCCIÓN"
    read -p "¿Continuar con el despliegue? (s/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        print_info "Despliegue cancelado"
        exit 0
    fi
    
    # Ejecutar proceso de despliegue
    START_TIME=$(date +%s)
    
    build_image
    push_image
    deploy_service
    
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    # Resumen final
    print_header "✅ DESPLIEGUE COMPLETADO"
    echo -e "${GREEN}Tiempo total: ${DURATION} segundos${NC}\n"
    
    get_service_url
    
    # Verificar salud del servicio
    verify_service_health
    
    echo ""
    print_success "¡Despliegue exitoso!"
    echo ""
}

# Ejecutar script principal
main "$@"
