# =============================================================================
# Terraform Variables Example
# =============================================================================
# Copy this file to terraform.tfvars and fill in your values
# NEVER commit terraform.tfvars to version control!
# =============================================================================

# Google Cloud Project
project_id   = "pagoflex-middleware-dev"
project_name = "pagoflex-middleware-dev"
region       = "us-central1"

# Database credentials
db_user     = "pagoflex"
db_password = "dev-gl0Ud.pgFlX.2712!!"

# Redis credentials
redis_password = "dev-gl0Ud.pgFlX.2712!!"

# Cloud Run image: usar imagen pública para el primer deploy (dev no puede pull del proyecto prod).
# Luego: build & push al Artifact Registry de dev y poner aquí esa URL.
api_image = "gcr.io/cloudrun/hello"

# Set to true to allow public access to the API
allow_unauthenticated = true
# false: la política de la org bloquea allUsers. Para acceso público usá la consola (Seguridad → Permite el acceso público).
enable_public_invoker_iam = false

# Service account Cloud Run: sufijo corto (account_id max 30 caracteres)
cloudrun_sa_suffix = "run"