"""Request-ID correlation middleware.

Every request gets a correlation ID (from the inbound `X-Request-ID` header if the caller
supplied one, otherwise a freshly generated UUID). It is echoed back on the response, attached to
`request.state.request_id` for use in logs/audit/errors, and pushed into Application Insights
telemetry via the `request_id` custom dimension in production.
"""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"

# Readable from app.core.logging_config's logging filter without threading request objects
# through every function signature.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_var.set(request_id)

        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)

        response.headers[REQUEST_ID_HEADER] = request_id
        return response
