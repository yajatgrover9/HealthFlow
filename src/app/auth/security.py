from fastapi import Header, HTTPException, status

from src.app.core.config import settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> str:
    if not settings.APP_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key is not configured",
        )

    if x_api_key != settings.APP_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    return x_api_key
