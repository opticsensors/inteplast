"""Vocabulary supplied by the application to its chat providers."""

from importlib.resources import files

GLOSSARY = files(__name__).joinpath("glosario.md").read_text(encoding="utf-8").strip()
