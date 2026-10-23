"""Sign in with Microsoft Entra ID and obtain Microsoft Graph tokens per user.

OpenID Connect over the OAuth 2.0 authorization code flow with PKCE, through MSAL
Python as a confidential client: Microsoft's recommended pattern for a web app
that signs users in and calls Graph. The backend redeems the code, so Microsoft
tokens never reach the browser; the browser keeps the application's own token.

Each user has one MSAL token cache, encrypted in the database. Graph calls use
`acquire_token_silent_with_error`, which renews the access token with the refresh
token until Microsoft requires an interactive sign-in again.
"""

import hashlib
import json
import secrets
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import msal
import requests
from sqlalchemy import delete
from sqlmodel import Session, col, func, select

from app.core.config import settings
from app.core.db import engine
from app.core.security import decrypt_text, encrypt_text
from app.microsoft_models import MicrosoftAccount, MicrosoftLogin
from app.models import User, get_datetime_utc
from app.source_types import SourceError

FLOW_TTL = timedelta(minutes=15)
TICKET_TTL = timedelta(minutes=2)
# MSAL metadata responses (authority discovery); they contain no tokens.
_HTTP_CACHE: dict[Any, Any] = {}
_TOKENS: dict[uuid.UUID, tuple[str, float]] = {}
_LOCK = threading.Lock()


class LoginError(Exception):
    def __init__(self, message: str):
        self.message = message


def scopes() -> list[str]:
    # MSAL adds openid, profile and offline_access (refresh token) itself.
    return settings.MICROSOFT_SCOPES.split()


def application(
    cache: msal.SerializableTokenCache | None = None,
) -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        settings.MICROSOFT_CLIENT_ID,
        client_credential=settings.MICROSOFT_CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}",
        token_cache=cache,
        http_cache=_HTTP_CACHE,
    )


def expired(created_at: datetime, ttl: timedelta) -> bool:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at < get_datetime_utc() - ttl


def start(session: Session) -> str:
    """Create a one-time flow (state, nonce, PKCE verifier) and return its URL."""
    session.execute(
        delete(MicrosoftLogin).where(
            col(MicrosoftLogin.created_at) < get_datetime_utc() - FLOW_TTL
        )
    )
    handled = settings.microsoft_redirect_handled
    flow = application().initiate_auth_code_flow(
        scopes(),
        redirect_uri=settings.MICROSOFT_REDIRECT_URI,
        prompt=None if handled else "select_account",
        # form_post keeps the code out of URLs when Microsoft returns to the API.
        # A page outside the app (Postman's, while testing) only receives a query.
        response_mode="form_post" if handled else "query",
    )
    session.add(MicrosoftLogin(key=flow["state"], flow=encrypt_text(json.dumps(flow))))
    session.commit()
    return str(flow["auth_uri"])


def pasted_response(url: str) -> dict[str, str]:
    """The query of the page Microsoft redirected to, pasted back by the user."""
    parts = urlsplit(url.strip())
    expected = urlsplit(settings.MICROSOFT_REDIRECT_URI or "")
    if (parts.scheme, parts.netloc, parts.path) != (
        expected.scheme,
        expected.netloc,
        expected.path,
    ):
        raise LoginError(
            "Pega la dirección completa de la página a la que te ha llevado Microsoft."
        )
    return dict(parse_qsl(parts.query))


def complete(session: Session, response: dict[str, str]) -> User:
    """Validate state and nonce, redeem the code and bind the account to a user."""
    state = response.get("state", "")
    row = session.get(MicrosoftLogin, state) if state else None
    if row is None or row.flow is None or expired(row.created_at, FLOW_TTL):
        raise LoginError("El inicio de sesión ha caducado. Vuelve a empezar.")
    flow = decrypt_text(row.flow)
    session.delete(row)  # One attempt per flow, whatever the outcome.
    session.commit()
    if flow is None:
        raise LoginError("El inicio de sesión ha caducado. Vuelve a empezar.")
    if response.get("error"):
        raise LoginError(
            response.get("error_description")
            or "Microsoft no ha completado el inicio de sesión."
        )
    cache = msal.SerializableTokenCache()
    try:
        result = application(cache).acquire_token_by_auth_code_flow(
            json.loads(flow), response
        )
    except ValueError:
        raise LoginError(
            "La respuesta de Microsoft no corresponde a este inicio de sesión."
        )
    except requests.RequestException:
        raise LoginError("No se puede conectar con Microsoft. Vuelve a intentarlo.")
    if "error" in result:
        raise LoginError(
            result.get("error_description") or "Microsoft ha rechazado el acceso."
        )
    claims = result.get("id_token_claims") or {}
    if claims.get("tid") != settings.MICROSOFT_TENANT_ID or not claims.get("oid"):
        raise LoginError("Esta cuenta no pertenece a la organización configurada.")
    username = str(claims.get("preferred_username") or claims.get("email") or "")
    account = session.exec(
        select(MicrosoftAccount).where(MicrosoftAccount.object_id == claims["oid"])
    ).first()
    user = (
        session.get(User, account.user_id)
        if account
        else session.exec(
            select(User).where(func.lower(User.email) == username.lower())
        ).first()
    )
    if user is None or not user.is_active:
        raise LoginError(
            f"La cuenta {username} no tiene acceso a la aplicación. "
            "Pide el alta al administrador."
        )
    account = account or session.get(MicrosoftAccount, user.id)
    if account is None:
        account = MicrosoftAccount(
            user_id=user.id, object_id="", tenant_id="", username="", token_cache=""
        )
    account.object_id = str(claims["oid"])
    account.tenant_id = str(claims["tid"])
    account.username = username[:255]
    account.token_cache = encrypt_text(cache.serialize())
    account.updated_at = get_datetime_utc()
    session.add(account)
    session.commit()
    forget(user.id)
    return user


def issue_ticket(session: Session, user: User) -> str:
    """A one-time, two-minute ticket the browser exchanges for the session token."""
    ticket = secrets.token_urlsafe(32)
    session.add(
        MicrosoftLogin(key=hashlib.sha256(ticket.encode()).hexdigest(), user_id=user.id)
    )
    session.commit()
    return ticket


def redeem_ticket(session: Session, ticket: str) -> User:
    row = session.get(MicrosoftLogin, hashlib.sha256(ticket.encode()).hexdigest())
    user = session.get(User, row.user_id) if row and row.user_id else None
    if row is not None:
        session.delete(row)
        session.commit()
    if (
        row is None
        or user is None
        or not user.is_active
        or expired(row.created_at, TICKET_TTL)
    ):
        raise LoginError("El inicio de sesión ha caducado. Vuelve a empezar.")
    return user


def sign_out(session: Session, user_id: uuid.UUID) -> None:
    account = session.get(MicrosoftAccount, user_id)
    if account is not None:
        session.delete(account)
        session.commit()
    forget(user_id)


def forget(user_id: uuid.UUID) -> None:
    with _LOCK:
        _TOKENS.pop(user_id, None)


def session_expired() -> SourceError:
    # 401 ends the application session too: the user signs in with Microsoft again.
    return SourceError(
        "unavailable",
        "Tu sesión de Microsoft ha caducado. Vuelve a iniciar sesión.",
        401,
    )


def access_token(user_id: uuid.UUID) -> str:
    """A Graph access token for this user, renewed silently while possible."""
    now = time.time()
    with _LOCK:
        cached = _TOKENS.get(user_id)
    if cached and cached[1] > now + 300:
        return cached[0]
    with Session(engine) as session:
        account = session.get(MicrosoftAccount, user_id)
        serialized = decrypt_text(account.token_cache) if account else None
        if account is None or serialized is None:
            raise session_expired()
        cache = msal.SerializableTokenCache()
        cache.deserialize(serialized)
        app = application(cache)
        try:
            accounts = app.get_accounts()
            result = (
                app.acquire_token_silent_with_error(scopes(), accounts[0])
                if accounts
                else None
            )
        except requests.RequestException:
            raise SourceError("unavailable", "No se puede conectar con Microsoft.", 503)
        if not result or "access_token" not in result:
            raise session_expired()
        if cache.has_state_changed:
            account.token_cache = encrypt_text(cache.serialize())
            account.updated_at = get_datetime_utc()
            session.add(account)
            session.commit()
    token = str(result["access_token"])
    with _LOCK:
        _TOKENS[user_id] = (token, now + float(result.get("expires_in") or 0))
    return token
