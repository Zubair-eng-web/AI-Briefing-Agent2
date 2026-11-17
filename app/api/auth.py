"""Account endpoints: register, login, current user, per-user interests."""
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core import ratelimit, users
from app.core.ratelimit import client_ip
from app.core.config import settings
from app.core.personalize import personalize_stories
from app.core.storage import get_recent_stories
from app.core.tokens import create_token, verify_token

router = APIRouter(tags=["accounts"])


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class UserInterests(BaseModel):
    interests: str = Field(default="", max_length=1000)


def _secret() -> str:
    if not settings.auth_secret:
        raise HTTPException(status_code=503, detail="Accounts band hain: AUTH_SECRET set nahi hai")
    return settings.auth_secret


def _throttle(request: Request, email: str | None = None) -> None:
    """Bruteforce rokne ke liye: IP aur (login par) email, dono par limit."""
    limit, window = settings.auth_rate_limit, settings.auth_rate_window_seconds
    keys = [f"auth-ip:{client_ip(request, settings.trust_proxy_headers)}"]
    if email:
        keys.append(f"auth-email:{email[:254]}")
    for key in keys:
        wait = ratelimit.hit(key, limit, window)
        if wait:
            raise HTTPException(
                status_code=429,
                detail="Bohat zyada koshishein. Thori der baad dobara try karein",
                headers={"Retry-After": str(int(wait) + 1)},
            )


def _issue(user: dict) -> dict:
    token = create_token(user["id"], _secret(), settings.auth_token_hours * 3600)
    return {"access_token": token, "token_type": "bearer", "user": user}


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    secret = _secret()
    scheme, _, token = (authorization or "").partition(" ")
    user_id = verify_token(token.strip(), secret) if scheme.lower() == "bearer" else None
    user = users.get_user(user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="Login chahiye ya token expire ho gaya")
    return user


@router.post("/auth/register", status_code=201)
def register(req: Credentials, request: Request):
    _secret()
    _throttle(request)
    email = users.normalize_email(req.email)
    if not users.is_valid_email(email):
        raise HTTPException(status_code=400, detail="Email sahi nahi hai")
    try:
        user = users.create_user(email, req.password)
    except users.UserExistsError:
        raise HTTPException(status_code=409, detail="Ye email pehle se registered hai")
    return _issue(user)


@router.post("/auth/login")
def login(req: Credentials, request: Request):
    _secret()
    _throttle(request, users.normalize_email(req.email))
    user = users.authenticate(req.email, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Email ya password ghalat hai")
    return _issue(user)


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user


@router.put("/me/interests")
def update_my_interests(req: UserInterests, user: dict = Depends(get_current_user)):
    saved = users.set_user_interests(user["id"], req.interests)
    return {"interests": saved or []}


@router.get("/me/feed")
def my_feed(limit: int = Query(20, ge=1, le=100), user: dict = Depends(get_current_user)):
    """Recent stories re-ranked for this user's interests."""
    ranked = personalize_stories(get_recent_stories(limit=100), user["interests"])[:limit]
    return {"interests": user["interests"], "count": len(ranked), "stories": ranked}


class Delivery(BaseModel):
    digest_enabled: bool


@router.get("/me/delivery")
def my_delivery(user: dict = Depends(get_current_user)):
    return {"email": user["email"], "digest_enabled": users.get_digest_enabled(user["id"])}


@router.put("/me/delivery")
def update_my_delivery(req: Delivery, user: dict = Depends(get_current_user)):
    users.set_digest_enabled(user["id"], req.digest_enabled)
    return {"email": user["email"], "digest_enabled": users.get_digest_enabled(user["id"])}
