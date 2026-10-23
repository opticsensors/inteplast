"""Microsoft sign-in state: one encrypted token cache per user and pending logins."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Text
from sqlmodel import Field, SQLModel

from app.models import get_datetime_utc


class MicrosoftAccount(SQLModel, table=True):
    """The Entra ID account bound to an application user, with its MSAL cache."""

    user_id: uuid.UUID = Field(
        primary_key=True, foreign_key="user.id", ondelete="CASCADE"
    )
    object_id: str = Field(max_length=64, unique=True)
    tenant_id: str = Field(max_length=64)
    username: str = Field(max_length=255)
    # Fernet-encrypted MSAL SerializableTokenCache (refresh and access tokens).
    token_cache: str = Field(sa_type=Text)
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class MicrosoftLogin(SQLModel, table=True):
    """A started authorization (PKCE verifier and nonce) or a one-time login ticket.

    Keyed by the OAuth `state`, or by the SHA-256 of a ticket once Microsoft has
    returned to the API. Rows expire after a few minutes and are used once.
    """

    key: str = Field(primary_key=True, max_length=128)
    flow: str | None = Field(default=None, sa_type=Text)
    user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="CASCADE"
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class LoginMethods(SQLModel):
    password: bool
    microsoft: bool
    # Microsoft returns to a page outside this application (for now Postman's):
    # the user pastes that address back.
    microsoft_paste: bool
    sharepoint: bool
    source_name: str


class MicrosoftLoginStart(SQLModel):
    auth_uri: str


class MicrosoftLoginComplete(SQLModel):
    response_url: str = Field(min_length=1, max_length=8192)


class MicrosoftTicket(SQLModel):
    ticket: str = Field(min_length=16, max_length=128)
