import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.exceptions import HTTPException as StarletteHTTPException
from redis import asyncio as aioredis
from sqlalchemy import text

from app.adapters.api.dependencies import (
    get_payment_operation,
    get_payment_service,
)

# Configure logging to capture INFO level logs (required for email service logs in Cloud Run)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
# Ensure uvicorn logs are also at INFO level
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown events: verifica conexión a BD y Redis al iniciar."""
    # === STARTUP: Probar conexiones ===
    logger.info("[STARTUP] Iniciando verificación de conexiones...")

    # 1. Probar conexión a base de datos (solo si usamos database)
    if settings.persistence_backend.lower() == "database":
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("[STARTUP] ✅ Conexión a base de datos OK")
        except Exception as e:
            logger.error("[STARTUP] ❌ Error al conectar a la base de datos: %s", str(e), exc_info=True)
    else:
        logger.info("[STARTUP] Modo %s: saltando verificación de BD", settings.persistence_backend)

    # 2. Probar conexión a Redis
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        await redis_client.aclose()
        logger.info("[STARTUP] ✅ Conexión a Redis OK")
    except Exception as e:
        logger.warning("[STARTUP] ⚠️ Redis no disponible: %s (la app puede continuar)", str(e))

    # 3. BDC healthcheck de prueba: ejecución en main thread (bloquea startup, verboso)
    try:
        from app.utils.bdc_healthcheck import run_bdc_healthchecks_main_thread

        await run_bdc_healthchecks_main_thread(count=1, interval_seconds=1.0)
    except Exception as e:
        logger.warning("[STARTUP] No se pudo ejecutar healthchecks BDC de prueba: %s", e)

    logger.info("[STARTUP] Verificación de conexiones completada")
    yield
    # === SHUTDOWN (opcional) ===
    # El engine se cierra automáticamente al terminar el proceso


from app.adapters.api.routes import router as payment_router
from app.api_server.routers.auth import router as auth_router
from app.api_server.routers.kyc import router as kyc_router
from app.api_server.routers.webhook import router as webhook_router
from app.api_server.routers.legal import router as legal_router
from app.api_server.routers.bdc_auth import router as bdc_router
from app.api_server.routers.bank_accounts import router as bank_accounts_router
from app.adapters.db.memory_repository import InMemoryPaymentRepository
from app.adapters.db.memory_transfer_repository import InMemoryTransferRepository
from app.adapters.db.sql_payment_repository import SqlAlchemyPaymentRepository
from app.adapters.db.sql_transfer_repository import SqlAlchemyTransferRepository
from app.adapters.payment.mock_gateway import MockPaymentGateway
from app.core.payments.operation import PaymentOperation
from app.db.session import engine, get_db_session
from app.services.payment_service import PaymentService
from sqlalchemy.ext.asyncio import AsyncSession
from config.settings import settings
from app.auth.security import verify_access_token

app = FastAPI(
    title="Pagoflex Middleware",
    description="Payment Gateway API",
    version="0.1.0",
    lifespan=lifespan,
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict):
        payload = dict(exc.detail)
        payload.setdefault("statusCode", exc.status_code)
        return JSONResponse(status_code=exc.status_code, content=payload)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "statusCode": exc.status_code,
            "message": str(exc.detail),
        },
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "statusCode": 422,
            "message": "Validation error",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "statusCode": 500,
            "message": "Internal server error",
        },
    )

# Security scheme for Swagger UI
security = HTTPBearer(auto_error=False)


def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    if not credentials or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Token Bearer requerido")
    user_id = verify_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token JWT inválido o expirado")
    return user_id


def build_openapi_schema() -> dict:
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    security_schemes = schema.setdefault("components", {}).setdefault("securitySchemes", {})
    security_schemes["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    return schema

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

gateway = MockPaymentGateway()


if settings.persistence_backend.lower() == "memory":
    # Fallback mode for tests or local development without Postgres
    _payment_repository = InMemoryPaymentRepository()
    _transfer_repository = InMemoryTransferRepository()

    def get_payment_service_impl() -> PaymentService:
        return PaymentService(_payment_repository, gateway)

    def get_payment_operation_impl() -> PaymentOperation:
        return PaymentOperation(transfer_repository=_transfer_repository)

else:

    async def get_payment_service_impl(
        session: AsyncSession = Depends(get_db_session),
    ) -> PaymentService:
        repository = SqlAlchemyPaymentRepository(session)
        return PaymentService(repository, gateway)

    async def get_payment_operation_impl(
        session: AsyncSession = Depends(get_db_session),
    ) -> PaymentOperation:
        repository = SqlAlchemyTransferRepository(session)
        return PaymentOperation(transfer_repository=repository)

# Override dependency tokens
app.dependency_overrides[get_payment_service] = get_payment_service_impl
app.dependency_overrides[get_payment_operation] = get_payment_operation_impl

app.include_router(payment_router, prefix="/api/v1")
app.include_router(auth_router)
app.include_router(legal_router)
app.include_router(bdc_router)
app.include_router(kyc_router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/api/v1")
app.include_router(bank_accounts_router, tags=["bank-accounts"])


if settings.DOCS_ENABLED:
    @app.get("/openapi.json", include_in_schema=False)
    async def protected_openapi_json(_: str = Depends(verify_jwt)):
        if app.openapi_schema is None:
            app.openapi_schema = build_openapi_schema()
        return JSONResponse(content=app.openapi_schema)


    @app.get("/docs", include_in_schema=False)
    async def protected_swagger_ui(_: str = Depends(verify_jwt)):
        return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{app.title} - Swagger UI")


    @app.get("/redoc", include_in_schema=False)
    async def protected_redoc(_: str = Depends(verify_jwt)):
        return get_redoc_html(openapi_url="/openapi.json", title=f"{app.title} - ReDoc")

@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/debug/brevo-test")
async def test_brevo_connectivity(_: str = Depends(verify_jwt)):
    """Test if we can reach Brevo API - diagnostic endpoint"""
    try:
        import httpx
        print("[BREVO-TEST] 🔗 Intentando conectar a Brevo...", flush=True)
        async with httpx.AsyncClient(timeout=10.0) as client:
            # This should return 400 or 401, but not connection error
            response = await client.get(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": "test-key"},
            )
            print(f"[BREVO-TEST] ✅ Brevo reachable! Status: {response.status_code}", flush=True)
            return {
                "status": "ok",
                "brevo_reachable": True,
                "code": response.status_code,
                "message": "Successfully connected to Brevo"
            }
    except Exception as e:
        print(f"[BREVO-TEST] ❌ Error: {str(e)}", flush=True)
        return {
            "status": "error",
            "brevo_reachable": False,
            "error": str(e),
            "message": "Cannot reach Brevo API"
        }


@app.get("/health/redis")
async def redis_health():
    """Verifica que Cloud Run pueda conectar a Redis (PING + SET/GET)."""
    try:
        client = aioredis.from_url(settings.REDIS_URL)
        await client.ping()
        await client.set("cloudrun:redis:test", "ok", ex=10)
        value = await client.get("cloudrun:redis:test")
        await client.aclose()
        if value != b"ok":
            raise HTTPException(status_code=503, detail="Redis test read failed")
        return {"status": "ok", "redis": "connected"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis unreachable: {e}")


@app.get("/debug/outbound-ip")
async def get_outbound_ip(_: str = Depends(verify_jwt)):
    """Obtiene la IP de salida de Cloud Run para whitelist del banco"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://api.ipify.org?format=json")
            ip_data = response.json()
            
            # Obtener información adicional
            response2 = await client.get("https://ipinfo.io/json")
            ip_info = response2.json()
            
            return {
                "outbound_ip": ip_data.get("ip"),
                "details": ip_info,
                "note": "Esta es la IP que ve el servidor de destino al recibir peticiones desde Cloud Run"
            }
    except Exception as e:
        return {"error": str(e), "message": "No se pudo obtener la IP de salida"}
