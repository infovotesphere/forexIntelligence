import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import get_settings
from app.core.security import decode_access_token

AUTH_COOKIE_NAME = "fi_access_token"


class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        settings = get_settings()
        path = request.url.path
        api_prefix = settings.api_v1_prefix
        if request.method == "OPTIONS" or not path.startswith(f"{api_prefix}/"):
            return await call_next(request)

        route = path.removeprefix(api_prefix)
        if route in {"/auth/login", "/auth/logout", "/auth/register", "/health"} or route.startswith("/worker/mt5/"):
            return await call_next(request)

        token = request.cookies.get(AUTH_COOKIE_NAME)
        authorization = request.headers.get("authorization", "")
        if token is None and authorization.startswith("Bearer "):
            token = authorization.removeprefix("Bearer ")
        if not token:
            return JSONResponse({"detail": "Authentication required"}, status_code=401)

        try:
            claims = decode_access_token(token)
        except jwt.InvalidTokenError:
            return JSONResponse({"detail": "Invalid or expired session"}, status_code=401)

        subject = claims.get("sub")
        role = claims.get("role")
        if not isinstance(subject, str) or not isinstance(role, str):
            return JSONResponse({"detail": "Invalid or expired session"}, status_code=401)

        administrator_routes = {
            "/accounts/connect",
            "/accounts/disconnect",
            "/engine/start",
            "/engine/stop",
        }
        if route in administrator_routes and request.method != "GET" and role != "administrator":
            return JSONResponse({"detail": "Administrator access required"}, status_code=403)

        request.state.user = {"email": subject, "role": role}
        return await call_next(request)
