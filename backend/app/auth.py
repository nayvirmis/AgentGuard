from dataclasses import dataclass

import httpx
import jwt
from fastapi import Header, HTTPException, status

from .config import get_settings


@dataclass(frozen=True)
class CurrentUser:
    id: str
    authenticated: bool


async def current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    settings = get_settings()
    if settings.auth_mode == "development":
        return CurrentUser(settings.demo_user_id, True)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    if not settings.clerk_jwks_url:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Clerk authentication is not configured"
        )

    token = authorization.removeprefix("Bearer ").strip()
    async with httpx.AsyncClient(timeout=5) as client:
        keys = (await client.get(settings.clerk_jwks_url)).json()
    header = jwt.get_unverified_header(token)
    key = next((item for item in keys["keys"] if item["kid"] == header["kid"]), None)
    if not key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown signing key")
    payload = jwt.decode(
        token,
        jwt.PyJWK.from_dict(key).key,
        algorithms=[header["alg"]],
        issuer=settings.clerk_issuer,
        options={"verify_aud": False},
    )
    return CurrentUser(payload["sub"], True)


async def optional_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if authorization:
        return await current_user(authorization)
    return CurrentUser("public-demo", False)
