"""Structured logging setup.

Every log line includes the current request's correlation ID (see
app.middleware.request_context.request_id_var). In deployed environments, `configure_logging`
also attaches an Azure Application Insights log handler when
`APPLICATIONINSIGHTS_CONNECTION_STRING` is set.
"""

import logging
import sys

from app.core.config import get_settings
from app.middleware.request_context import request_id_var

settings = get_settings()


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | request_id=%(request_id)s | %(name)s | %(message)s"
        )
    )
    handler.addFilter(RequestIdFilter())

    root.handlers.clear()
    root.addHandler(handler)

    if settings.applicationinsights_connection_string:
        try:
            from opencensus.ext.azure.log_exporter import AzureLogHandler

            azure_handler = AzureLogHandler(
                connection_string=settings.applicationinsights_connection_string
            )
            azure_handler.addFilter(RequestIdFilter())
            root.addHandler(azure_handler)
        except Exception:  # pragma: no cover - best-effort telemetry wiring
            logging.getLogger(__name__).warning(
                "Application Insights connection string set but exporter could not be initialized.",
                exc_info=True,
            )

    # Quiet noisy third-party loggers by default.
    logging.getLogger("uvicorn.access").setLevel(
        logging.WARNING if not settings.debug else logging.INFO
    )
