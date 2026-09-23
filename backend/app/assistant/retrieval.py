"""Ground an explicit piece in the question before asking the small local model.

Discovery and follow-up reads remain model tools. This avoids a small model
announcing a lookup without actually calling a tool.
"""

import re
import unicodedata
from typing import Any

from app.assistant.schemas import ChatRequest


def initial_read(request: ChatRequest) -> tuple[str, dict[str, Any]] | None:
    question = request.messages[-1].content
    normalized = "".join(
        c
        for c in unicodedata.normalize("NFD", question.lower())
        if not unicodedata.combining(c)
    )
    codes = re.findall(r"\b(?:pieza|part|proyecto)\s*(\d{4})\b", normalized)
    if re.fullmatch(r"\d{4}", normalized):
        codes = [normalized]
    if len(set(codes)) != 1:
        return None
    part = codes[0]
    section = "overview"
    if re.search(r"retoqu|correcci|correction|pptx", normalized):
        section = "corrections"
    elif re.search(r"medici|medida|measurement|valor|toleran|fuera|\bn\d+", normalized):
        section = "measurements"
    args: dict[str, Any] = {"part": str(part), "section": section}
    cotas = re.findall(r"\bN\d+(?:\.\d+)?\b", question, re.IGNORECASE)
    if len({c.upper() for c in cotas}) > 1:
        return None
    if len(set(cotas)) == 1:
        args["characteristic"] = cotas[0].upper()
    revision = re.search(
        r"\brev(?:ision)?\.?\s+([a-z0-9]*\d[a-z0-9]*|[a-z])\b", normalized
    )
    if revision:
        args["revision"] = revision[1].upper()
    if section == "overview" and re.search(
        r"advertenc|leccion|problema|contraccion|riesgo", normalized
    ):
        return "search_knowledge", {
            "query": question,
            **{k: v for k, v in args.items() if k != "section"},
        }
    cavities = re.findall(r"\bc(?:avidad)?\s*(\d+)\b", normalized)
    if len(set(cavities)) > 1:
        return None
    if len(set(cavities)) == 1:
        args["cavity"] = "c" + str(int(cavities[0]))
    samples = re.findall(r"\b(?:muestreo|intern[.]?)\s*(\d+)\b", normalized)
    if len(set(samples)) > 1:
        return None
    if len(set(samples)) == 1:
        args["sample"] = samples[0].zfill(2)
    if section == "measurements" and re.search(
        r"individual|fila|registro|valor exacto", normalized
    ):
        args["include_rows"] = True
    if section == "measurements" and re.search(
        r"minim|maxim|media|promedio|rango|estadistic|valores", normalized
    ):
        args["include_statistics"] = True
    return "read_part", args
