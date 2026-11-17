"""Explicit, reusable source assignments. Empty configuration is the usual single part."""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class ComponentFile(BaseModel):
    # Relative to the piece folder, never an absolute path.
    path: str = Field(min_length=1, max_length=2048)
    revision: str = Field(default="", max_length=64)


class ComponentDefinition(BaseModel):
    key: str = Field(pattern=r"^[A-Z][A-Z0-9_-]{0,23}$")
    name: str = Field(min_length=1, max_length=80)
    sheets: list[str] = Field(default_factory=list, max_length=200)
    files: list[ComponentFile] = Field(default_factory=list, max_length=200)


class ComponentOrganization(BaseModel):
    components: list[ComponentDefinition] = Field(default_factory=list, max_length=20)
    # Sources the user left without component on purpose ("file:<path>" or
    # "sheet:<name>"). They are not proposed again; new sources are.
    unassigned: list[str] = Field(default_factory=list, max_length=5000)

    @model_validator(mode="after")
    def unique_assignments(self) -> "ComponentOrganization":
        for values in (
            [c.key for c in self.components],
            [s for c in self.components for s in c.sheets],
            [f.path for c in self.components for f in c.files],
        ):
            if len(values) != len(set(values)):
                raise ValueError(
                    "Cada clave, hoja y archivo debe tener un único componente."
                )
        return self


def qualified(code: str, component: str = "") -> str:
    return f"{component}:{code}" if component else code


def split_code(code: str) -> tuple[str, str]:
    component, separator, number = code.partition(":")
    return (component, number) if separator else ("", code)


def identity_expression() -> Any:
    """SQL counterpart of qualified(), shared by scoped searches."""
    from sqlalchemy import case
    from sqlmodel import col

    from app.knowledge_models import PartCharacteristic

    return case(
        (col(PartCharacteristic.component) == "", col(PartCharacteristic.code)),
        else_=col(PartCharacteristic.component) + ":" + col(PartCharacteristic.code),
    )


def assigned_component(
    components: list[dict[str, Any]], path: str, sheet: str = ""
) -> str:
    # A workbook assignment and a sheet assignment may not contradict one another.
    matches = {
        c["key"]
        for c in components
        if (sheet and sheet in c.get("sheets", []))
        or any(f["path"] == path for f in c.get("files", []))
    }
    return next(iter(matches)) if len(matches) == 1 else ""
