"""FastAPI Main Application Entry Point.

Configures:
- Application lifespan management and configuration validation.
- Standardized CORS middleware.
- Global exception handlers for unified error schemas.
- API route registration.
- Optional static file serving fallback for local development.
"""

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.chat import router as chat_router
from app.config import get_settings, validate_startup_config

# Configure standard application logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("qa_chatbot")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Perform application startup validation and graceful shutdown."""
    settings = get_settings()
    logger.info("Initializing Q&A Chatbot Backend (v0.1.0)...")
    validate_startup_config(settings)
    yield
    logger.info("Shutting down Q&A Chatbot Backend.")


def create_app() -> FastAPI:
    """Application factory for FastAPI instance."""
    settings = get_settings()

    app = FastAPI(
        title="Q&A Chatbot API",
        description="Modular Q&A Chatbot powered by LangChain and Groq API",
        version="0.1.0",
        docs_url="/docs" if settings.APP_ENV != "production" else None,
        redoc_url="/redoc" if settings.APP_ENV != "production" else None,
        lifespan=lifespan,
    )

    # --------------------------------------------------------------------------
    # CORS Configuration
    # --------------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # --------------------------------------------------------------------------
    # Global Exception Handlers (Standardized JSON Error Payloads)
    # --------------------------------------------------------------------------
    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        error_name = {
            400: "BAD_REQUEST",
            404: "NOT_FOUND",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMIT_EXCEEDED",
            500: "INTERNAL_SERVER_ERROR",
            502: "PROVIDER_ERROR",
            503: "SERVICE_UNAVAILABLE",
            504: "GATEWAY_TIMEOUT",
        }.get(exc.status_code, "ERROR")

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": error_name,
                "detail": exc.detail,
                "code": f"HTTP_{exc.status_code}",
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Simplify validation error messages for client readability
        errors = exc.errors()
        error_details = []
        for err in errors:
            loc = " -> ".join(str(item) for item in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            error_details.append(f"{loc}: {msg}")

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "VALIDATION_ERROR",
                "detail": "; ".join(error_details) if error_details else "Invalid request payload.",
                "code": "HTTP_422",
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled server exception processing request to %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "detail": "An unexpected error occurred. Please contact the system administrator.",
                "code": "HTTP_500",
            },
        )

    # --------------------------------------------------------------------------
    # API Routers
    # --------------------------------------------------------------------------
    app.include_router(chat_router)

    # --------------------------------------------------------------------------
    # Frontend Static File Serving Strategy (Fallback for Non-Docker Development)
    # --------------------------------------------------------------------------
    # Check potential frontend directories relative to backend execution path
    possible_frontend_paths = [
        Path(__file__).resolve().parent.parent.parent / "frontend",  # qa-chatbot/frontend
        Path.cwd() / "frontend",
    ]
    frontend_dir = next((p for p in possible_frontend_paths if p.is_dir()), None)

    if frontend_dir and (frontend_dir / "index.html").exists():
        logger.info("Found frontend assets at %s. Mounting static file routes.", frontend_dir)
        # Mount css and js directories if present
        css_path = frontend_dir / "css"
        if css_path.is_dir():
            app.mount("/css", StaticFiles(directory=str(css_path)), name="css")
        js_path = frontend_dir / "js"
        if js_path.is_dir():
            app.mount("/js", StaticFiles(directory=str(js_path)), name="js")

        @app.get("/", include_in_schema=False)
        async def serve_index() -> FileResponse:
            return FileResponse(frontend_dir / "index.html")

    return app


# Root application instance used by Uvicorn
app = create_app()
