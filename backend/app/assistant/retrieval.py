"""Ground an explicit piece in the question before asking the small local model.

Discovery and follow-up reads remain model tools. This avoids a small model
announcing a lookup without actually calling a tool.
"""

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

from app.assistant.schemas import ChatRequest


def normalize(value: str) -> str:
    return " ".join(
        re.findall(
            r"\w+",
            "".join(
                c
                for c in unicodedata.normalize("NFD", value.casefold())
                if not unicodedata.combining(c)
            ),
        )
    )


def name_score(question: str, name: str) -> float:
    """Match whole name phrases, allowing one small typo, never fuzzy numbers."""
    words, target = normalize(question).split(), normalize(name).split()
    if not target:
        return 0
    best = 0.0
    for start in range(len(words) - len(target) + 1):
        window = words[start : start + len(target)]
        if window == target:
            return 1.0
        different = [(a, b) for a, b in zip(window, target, strict=True) if a != b]
        if len(different) != 1 or len(" ".join(target)) < 6:
            continue
        a, b = different[0]
        if min(len(a), len(b)) < 4 or not a.isalpha() or not b.isalpha():
            continue
        # One substitution/insertion/deletion or adjacent transposition.
        edits = [
            op for op in SequenceMatcher(None, a, b).get_opcodes() if op[0] != "equal"
        ]
        small = (
            len(edits) == 1
            and max(edits[0][2] - edits[0][1], edits[0][4] - edits[0][3]) == 1
        )
        swapped = len(a) == len(b) and any(
            a[:i] + a[i + 1] + a[i] + a[i + 2 :] == b for i in range(len(a) - 1)
        )
        if small or swapped:
            best = 0.9
    return best


def correction_question(question: str) -> bool:
    return bool(re.search(r"retoqu|corre?c+ion|correction|pptx", normalize(question)))


def part_read(question: str, part: str) -> tuple[str, dict[str, Any]] | None:
    """Build filters only after resolving a unique part, preserving explicit scope."""
    normalized = "".join(
        c
        for c in unicodedata.normalize("NFD", question.lower())
        if not unicodedata.combining(c)
    )
    section = "overview"
    if correction_question(question):
        section = "corrections"
    elif re.search(r"medici|medida|measurement|valor|toleran|fuera|\bn\d+", normalized):
        section = "measurements"
    args: dict[str, Any] = {"part": str(part), "section": section}
    cotas = {
        c.upper() for c in re.findall(r"\bN\d+(?:\.\d+)?\b", question, re.IGNORECASE)
    }
    if len(cotas) > 1:
        return None
    if cotas:
        args["characteristic"] = next(iter(cotas))
    return _filters(question, normalized, args)


def initial_read(request: ChatRequest) -> tuple[str, dict[str, Any]] | None:
    question = request.messages[-1].content
    normalized = normalize(question)
    codes = re.findall(r"\b(?:pieza|part|proyecto)\s*(\d{4})\b", normalized)
    if re.fullmatch(r"\d{4}", normalized):
        codes = [normalized]
    if len(set(codes)) != 1:
        return None
    return part_read(question, codes[0])


def _filters(
    question: str, normalized: str, args: dict[str, Any]
) -> tuple[str, dict[str, Any]] | None:
    section = args["section"]
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
