# Load environment variables
import os

from dotenv import load_dotenv

load_dotenv()

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from open_notebook.utils.logger_config import setup_logging

setup_logging()

# Monkey-patch ChatOpenAI to preserve DeepSeek reasoning_content across turns
import api.deepseek_reasoning_patch  # noqa: E402

api.deepseek_reasoning_patch.apply()

from api.auth import PasswordAuthMiddleware
from api.routers import (
    audit_log,
    auth,
    chat,
    config,
    context,
    credentials,
    embedding,
    embedding_rebuild,
    episode_profiles,
    insights,
    languages,
    models,
    notebooks,
    notes,
    podcasts,
    search,
    settings,
    share_grants,
    source_chat,
    sources,
    speaker_profiles,
    teams,
    transformations,
    users,
    workspaces,
)
from api.routers import commands as commands_router
from open_notebook.database.async_migrate import AsyncMigrationManager
from open_notebook.database.repository import close_database_pool, initialize_database_pool
from open_notebook.exceptions import (
    AuthenticationError,
    ConfigurationError,
    ExternalServiceError,
    InvalidInputError,
    NetworkError,
    NotFoundError,
    OpenNotebookError,
    RateLimitError,
)
from open_notebook.utils.encryption import get_secret_from_env

# Import commands to register them in the API process
try:
    logger.info("Commands imported in API process")
except Exception as e:
    logger.error(f"Failed to import commands in API process: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for the FastAPI application.
    Runs database migrations automatically on startup.
    """
    # Startup: Security checks
    logger.info("Starting API initialization...")
    database_pool_started = False

    # Security check: Encryption key
    if not get_secret_from_env("OPEN_NOTEBOOK_ENCRYPTION_KEY"):
        logger.warning(
            "OPEN_NOTEBOOK_ENCRYPTION_KEY not set. "
            "API key encryption will fail until this is configured. "
            "Set OPEN_NOTEBOOK_ENCRYPTION_KEY to any secret string."
        )

    try:
        # Pre-warm the process-local SurrealDB connection pool before migrations.
        await initialize_database_pool()
        database_pool_started = True

        # Run database migrations
        try:
            migration_manager = AsyncMigrationManager()
            current_version = await migration_manager.get_current_version()
            logger.info(f"Current database version: {current_version}")

            if await migration_manager.needs_migration():
                logger.warning("Database migrations are pending. Running migrations...")
                await migration_manager.run_migration_up()
                new_version = await migration_manager.get_current_version()
                logger.success(
                    f"Migrations completed successfully. Database is now at version {new_version}"
                )
            else:
                logger.info(
                    "Database is already at the latest version. No migrations needed."
                )
        except Exception as e:
            logger.error(f"CRITICAL: Database migration failed: {str(e)}")
            logger.exception(e)
            # Fail fast - don't start the API with an outdated database schema
            raise RuntimeError(f"Failed to run database migrations: {str(e)}") from e

        # Run podcast profile data migration (legacy strings -> Model registry)
        try:
            from open_notebook.podcasts.migration import migrate_podcast_profiles

            await migrate_podcast_profiles()
        except Exception as e:
            logger.warning(f"Podcast profile migration encountered errors: {e}")
            # Non-fatal: profiles can be migrated manually via UI

        logger.success("API initialization completed successfully")

        # Yield control to the application
        yield
    finally:
        if database_pool_started:
            await close_database_pool()

        # Shutdown: cleanup if needed
        logger.info("API shutdown complete")


app = FastAPI(
    title="Open Notebook API",
    description="API for Open Notebook - Research Assistant",
    lifespan=lifespan,
)


def _cors_origins_from_env() -> list[str]:
    import os

    raw_origins = os.getenv("OPEN_NOTEBOOK_CORS_ORIGINS", "*")
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return origins or ["*"]


def _cors_response_origin(request: Request) -> str:
    allowed_origins = _cors_origins_from_env()
    request_origin = request.headers.get("origin")
    if "*" in allowed_origins:
        return request_origin or "*"
    if request_origin and request_origin in allowed_origins:
        return request_origin
    return allowed_origins[0]

# Add password authentication middleware first
# Exclude /api/auth/status and /api/config from authentication
app.add_middleware(
    PasswordAuthMiddleware,
    excluded_paths=[
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/auth/status",
        "/api/config",
        "/api/notebooks/public",
        "/api/sources/public",
    ],
)

# Add CORS middleware last (so it processes first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins_from_env(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom exception handler to ensure CORS headers are included in error responses
# This helps when errors occur before the CORS middleware can process them
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Custom exception handler that ensures CORS headers are included in error responses.
    This is particularly important for 413 (Payload Too Large) errors during file uploads.

    Note: If a reverse proxy (nginx, traefik) returns 413 before the request reaches
    FastAPI, this handler won't be called. In that case, configure your reverse proxy
    to add CORS headers to error responses.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            **(exc.headers or {}),
            "Access-Control-Allow-Origin": _cors_response_origin(request),
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


def _cors_headers(request: Request) -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": _cors_response_origin(request),
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }


@app.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
        headers=_cors_headers(request),
    )


@app.exception_handler(InvalidInputError)
async def invalid_input_error_handler(request: Request, exc: InvalidInputError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
        headers=_cors_headers(request),
    )


@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc)},
        headers=_cors_headers(request),
    )


@app.exception_handler(RateLimitError)
async def rate_limit_error_handler(request: Request, exc: RateLimitError):
    return JSONResponse(
        status_code=429,
        content={"detail": str(exc)},
        headers=_cors_headers(request),
    )


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(request: Request, exc: ConfigurationError):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
        headers=_cors_headers(request),
    )


@app.exception_handler(NetworkError)
async def network_error_handler(request: Request, exc: NetworkError):
    return JSONResponse(
        status_code=502,
        content={"detail": str(exc)},
        headers=_cors_headers(request),
    )


@app.exception_handler(ExternalServiceError)
async def external_service_error_handler(request: Request, exc: ExternalServiceError):
    return JSONResponse(
        status_code=502,
        content={"detail": str(exc)},
        headers=_cors_headers(request),
    )


@app.exception_handler(OpenNotebookError)
async def open_notebook_error_handler(request: Request, exc: OpenNotebookError):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers=_cors_headers(request),
    )


# Include routers
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(workspaces.router, prefix="/api", tags=["workspaces"])
app.include_router(teams.router, prefix="/api", tags=["teams"])
app.include_router(share_grants.router, prefix="/api", tags=["share-grants"])
app.include_router(audit_log.router, prefix="/api", tags=["audit-log"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(notebooks.router, prefix="/api", tags=["notebooks"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(models.router, prefix="/api", tags=["models"])
app.include_router(transformations.router, prefix="/api", tags=["transformations"])
app.include_router(notes.router, prefix="/api", tags=["notes"])
app.include_router(embedding.router, prefix="/api", tags=["embedding"])
app.include_router(
    embedding_rebuild.router, prefix="/api/embeddings", tags=["embeddings"]
)
app.include_router(settings.router, prefix="/api", tags=["settings"])
app.include_router(context.router, prefix="/api", tags=["context"])
app.include_router(sources.router, prefix="/api", tags=["sources"])
app.include_router(insights.router, prefix="/api", tags=["insights"])
app.include_router(commands_router.router, prefix="/api", tags=["commands"])
app.include_router(podcasts.router, prefix="/api", tags=["podcasts"])
app.include_router(episode_profiles.router, prefix="/api", tags=["episode-profiles"])
app.include_router(speaker_profiles.router, prefix="/api", tags=["speaker-profiles"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(source_chat.router, prefix="/api", tags=["source-chat"])
app.include_router(credentials.router, prefix="/api", tags=["credentials"])
app.include_router(languages.router, prefix="/api", tags=["languages"])


@app.get("/")
async def root():
    return {"message": "Open Notebook API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
