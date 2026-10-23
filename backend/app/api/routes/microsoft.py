"""Sign in with Microsoft. Only active when SHAREPOINT_ENABLED is true.

While the registered redirect URI is a page outside the application (Postman's
for now), the user pastes the address it shows. When it points to
`/api/v1/login/microsoft/callback`, Microsoft posts the result to the API and
the browser receives a one-time ticket instead.
"""

from datetime import timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app import microsoft_auth
from app.api.deps import CurrentUser, SessionDep
from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.microsoft_models import (
    LoginMethods,
    MicrosoftLoginComplete,
    MicrosoftLoginStart,
    MicrosoftTicket,
)
from app.models import Message, Token, User

router = APIRouter(prefix="/login", tags=["login"])


def session_token(user: User) -> Token:
    return Token(
        access_token=security.create_access_token(
            user.id,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
    )


def require_microsoft() -> None:
    if not settings.SHAREPOINT_ENABLED:
        raise HTTPException(404, "El inicio de sesión con Microsoft no está activo.")


@router.get("/methods", response_model=LoginMethods)
def login_methods() -> LoginMethods:
    """How to sign in, and which source the file pickers browse."""
    return LoginMethods(
        password=not settings.SHAREPOINT_ENABLED,
        microsoft=settings.SHAREPOINT_ENABLED,
        microsoft_paste=settings.SHAREPOINT_ENABLED
        and not settings.microsoft_redirect_handled,
        sharepoint=settings.SHAREPOINT_ENABLED,
        source_name=settings.ASSETS_SOURCE_NAME,
    )


@router.post("/microsoft/start", response_model=MicrosoftLoginStart)
def start_microsoft_login(session: SessionDep) -> MicrosoftLoginStart:
    require_microsoft()
    return MicrosoftLoginStart(auth_uri=microsoft_auth.start(session))


@router.post("/microsoft/complete", response_model=Token)
def complete_microsoft_login(
    session: SessionDep, body: MicrosoftLoginComplete
) -> Token:
    """Finish a sign-in from the address of the page Microsoft redirected to."""
    require_microsoft()
    try:
        response = microsoft_auth.pasted_response(body.response_url)
        return session_token(microsoft_auth.complete(session, response))
    except microsoft_auth.LoginError as error:
        raise HTTPException(400, error.message)


def finish_callback(response: dict[str, str]) -> dict[str, str]:
    with Session(engine) as session:
        try:
            user = microsoft_auth.complete(session, response)
            return {"microsoft": microsoft_auth.issue_ticket(session, user)}
        except microsoft_auth.LoginError as error:
            return {"microsoft_error": error.message}


@router.post("/microsoft/callback", include_in_schema=False)
async def microsoft_callback(request: Request) -> RedirectResponse:
    """Microsoft posts the authorization response here (response_mode=form_post)."""
    require_microsoft()
    form = await request.form()
    response = {key: str(value) for key, value in form.items()}
    query = await run_in_threadpool(finish_callback, response)
    return RedirectResponse(
        f"{settings.FRONTEND_HOST}/login?{urlencode(query)}", status_code=303
    )


@router.post("/microsoft/ticket", response_model=Token)
def redeem_microsoft_ticket(session: SessionDep, body: MicrosoftTicket) -> Token:
    require_microsoft()
    try:
        return session_token(microsoft_auth.redeem_ticket(session, body.ticket))
    except microsoft_auth.LoginError as error:
        raise HTTPException(400, error.message)


@router.post("/microsoft/logout", response_model=Message)
def microsoft_logout(session: SessionDep, current_user: CurrentUser) -> Message:
    """Forget this user's Microsoft tokens; the next access signs in again."""
    microsoft_auth.sign_out(session, current_user.id)
    return Message(message="Sesión de Microsoft cerrada")
