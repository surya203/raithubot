import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import advisory, alerts, chat, crops, environment, health, knowledge, weather
from app.config import get_settings
from app.errors import AppError
from app.utils.logging import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    llm = settings.llm_config()
    logger.info(
        "AgriSense AI ready provider=%s model=%s database=%s embeddings=%s",
        llm.provider or "unset",
        llm.model or "unset",
        settings.database_configured,
        llm.embeddings_configured,
    )
    yield


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(
        title="AgriSense AI",
        summary="Internal agricultural advisory API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def require_internal_token(request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        token = get_settings().internal_api_token.strip()
        path = request.url.path
        if token and path.startswith("/api") and path != "/api/health":
            provided = request.headers.get("x-internal-token", "")
            if not hmac.compare_digest(provided.encode(), token.encode()):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "A valid internal token is required."},
                )
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def handle_app_error(_request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.get("/")
    def root():
        return {"name": "AgriSense AI", "docs": "/docs"}

    app.include_router(health.router, prefix="/api")
    app.include_router(weather.router, prefix="/api")
    app.include_router(crops.router, prefix="/api")
    app.include_router(environment.router, prefix="/api")
    app.include_router(advisory.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(alerts.router, prefix="/api")
    app.include_router(knowledge.router, prefix="/api")
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
