import logging
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api_server.routers import payments, kyc, webhook, auth, legal, bdc_auth, bank_accounts
from config.settings import settings
from app.auth.security import verify_access_token

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

app = FastAPI(
    title="Pagoflex Modular Platform",
    version="2.0.0",
    openapi_url=None,  # Desactiva el endpoint público
    docs_url=None,
    redoc_url=None
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

def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if not credentials or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Token Bearer requerido")
    user_id = verify_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token JWT inválido o expirado")
    return user_id

# Ejemplo de endpoint protegido
@app.get("/protected", tags=["auth"], summary="Endpoint protegido", description="Solo accesible con Bearer JWT", response_model=dict, security=[{"bearerAuth": []}])
async def protected_endpoint(user_id: str = Depends(verify_jwt)):
    return {"message": f"Acceso autorizado para usuario {user_id}"}


def build_openapi_schema() -> dict:
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    security_schemes = openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    security_schemes["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT"
    }
    return openapi_schema

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "api_server"}

# Include Routers
app.include_router(auth.router)
app.include_router(legal.router)
app.include_router(bank_accounts.router)
app.include_router(bdc_auth.router)
app.include_router(payments.router, prefix="/payments", tags=["payments"])
app.include_router(kyc.router, prefix="/kyc")
app.include_router(webhook.router, prefix="/api/v1", tags=["webhooks"])

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
