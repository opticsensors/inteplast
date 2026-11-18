"""Shared lists of piece families and customers.

Users extend them from the piece editor. Adding a name that already exists, with other
case or extra spaces, returns the existing entry. Renaming, merging and deleting are left
for when the language of the lists is corrected.
"""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    CatalogNameCreate,
    CatalogNamePublic,
    CatalogNamesPublic,
    Customer,
    PartFamily,
    catalog_key,
)

router = APIRouter(tags=["catalog"])

CatalogName = type[PartFamily] | type[Customer]


def list_names(session: Session, model: CatalogName) -> CatalogNamesPublic:
    rows = session.exec(select(model).order_by(func.lower(model.name))).all()
    return CatalogNamesPublic(
        data=[CatalogNamePublic.model_validate(row) for row in rows]
    )


def add_name(session: Session, model: CatalogName, body: CatalogNameCreate) -> Any:
    name = " ".join(body.name.split())
    if not name:
        raise HTTPException(422, "Escribe un nombre.")
    key = catalog_key(name)
    existing = session.exec(select(model).where(model.key == key)).first()
    if existing:
        return existing
    row = model(name=name, key=key)
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        # Someone added the same name at the same time: both get one entry.
        session.rollback()
        return session.exec(select(model).where(model.key == key)).one()
    session.refresh(row)
    return row


def check_names(
    session: Session, family_id: uuid.UUID | None, customer_id: uuid.UUID | None
) -> None:
    if family_id and not session.get(PartFamily, family_id):
        raise HTTPException(422, "La familia elegida ya no existe.")
    if customer_id and not session.get(Customer, customer_id):
        raise HTTPException(422, "El cliente elegido ya no existe.")


@router.get("/families", response_model=CatalogNamesPublic)
def read_families(session: SessionDep, _current_user: CurrentUser) -> Any:
    """Piece families, by name."""
    return list_names(session, PartFamily)


@router.post("/families", response_model=CatalogNamePublic)
def create_family(
    session: SessionDep, _current_user: CurrentUser, body: CatalogNameCreate
) -> Any:
    """Add a family, or return the one with the same name."""
    return add_name(session, PartFamily, body)


@router.get("/customers", response_model=CatalogNamesPublic)
def read_customers(session: SessionDep, _current_user: CurrentUser) -> Any:
    """Customers, by name."""
    return list_names(session, Customer)


@router.post("/customers", response_model=CatalogNamePublic)
def create_customer(
    session: SessionDep, _current_user: CurrentUser, body: CatalogNameCreate
) -> Any:
    """Add a customer, or return the one with the same name."""
    return add_name(session, Customer, body)
