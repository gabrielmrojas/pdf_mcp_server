from __future__ import annotations

from typing import Any

from .config import settings
from .utils.logger import get_logger

logger = get_logger(__name__)


def build_app() -> Any:
    try:
        from fastmcp import FastMCP  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "fastmcp is not installed. Please install dependencies first."
        ) from exc

    app = FastMCP(settings.server_name, version=settings.server_version)

    # Register tools
    from .tools import utilities, text_extraction, pdf_manipulation, conversion, uploads
    from .services.file_manager import cleanup_expired

    utilities.register(app)
    text_extraction.register(app)
    pdf_manipulation.register(app)
    conversion.register(app)
    uploads.register(app)

    # Clean up expired files on startup
    try:
        cleanup_expired()
    except Exception as exc:  # noqa: BLE001
        logger.error("cleanup_expired at startup failed: %s", exc)

    return app


def run() -> None:
    app = build_app()
    # Avoid printing; delegate to the framework. Support multiple API variants.
    if hasattr(app, "run_stdio"):
        app.run_stdio()
    elif hasattr(app, "run"):
        app.run()
    else:  # pragma: no cover
        logger.error("FastMCP app has no run or run_stdio method")
        raise SystemExit("Unsupported FastMCP version: missing run entrypoint")


if __name__ == "__main__":  # pragma: no cover
    run()
