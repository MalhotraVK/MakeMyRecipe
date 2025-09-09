"""Main FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import settings
from ..core.logging import get_logger, setup_logging
from .middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from .routes import chat, websocket

# Set up logging
setup_logging()
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="An LLM-based chat application for recipe recommendations",
        debug=settings.api_debug,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(chat.router)
    app.include_router(websocket.router)

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "app_name": settings.app_name,
            "version": settings.app_version,
        }

    # Root endpoint
    @app.get("/")
    async def root() -> dict:
        """Root endpoint."""
        return {
            "message": f"Welcome to {settings.app_name}!",
            "version": settings.app_version,
            "docs": "/docs",
            "redoc": "/redoc",
            "websocket": "/ws/chat/{user_id}",
        }

    logger.info(f"Created {settings.app_name} v{settings.app_version}")
    return app


# Create the app instance
app = create_app()


def main() -> None:
    """Main entry point for running the application."""
    import uvicorn

    logger.info(f"Starting {settings.app_name} server...")
    uvicorn.run(
        "makemyrecipe.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
