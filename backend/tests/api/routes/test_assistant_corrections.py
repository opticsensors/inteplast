import asyncio
import copy
import json

import pytest

from app.assistant.answers import correction_answer
from app.assistant.config import AssistantSettings
from app.assistant.corrections import plan_evidence, recorded_limits
from app.assistant.drafting import messages as drafting_messages
from app.assistant.providers import ModelChunk
from app.assistant.schemas import ChatRequest
from app.assistant.service import answer, bounded_result
from app.assistant.summaries import page


def evidence(
    part="6842",
    characteristic="N431",
    action="3.7",
    proposal="Reducir el espesor local en 0,12 mm.",
    unit="mm",
):
    plan = plan_evidence(
        {
            "id": action,
            "plan": "3",
            "title": f"Correction {action} ({characteristic}) nominal 12",
            "features": [characteristic],
            "paragraphs": [
                "Current situation:",
                "Fuera de límites",
                "Tool correction plan:",
                proposal,
            ],
            "source": {"path": "private/plan.pptx", "locator": "Página 9"},
        }
    )
    return {
        "part": part,
        "name": "Valve Cover",
        "feature": "Side Pad",
        "revision": "B",
        "filters": {"characteristic": characteristic},
        "import_state": "ready",
        "actions": [plan],
        "total": 1,
        "recorded_limits": [
            {
                "characteristic": characteristic,
                "unit": unit,
                "nominal": 12,
                "lower": 11.8,
                "upper": 12.2,
                "series": ["S1"],
                "samples": ["02"],
                "cavities": ["c3"],
                "documents": ["report.csv"],
            }
        ],
        "coverage": {"actions": page(1, 0, 1), "recorded_limits": page(1, 0, 1)},
    }


@pytest.mark.parametrize(
    "heading",
    ["Tool correction plan:", "Plan de corrección:", "Proposta de correcció:"],
)
def test_assistant_plan_preserves_roles_and_only_quotes_explicit_proposal(heading):
    result = plan_evidence(
        {
            "id": "R-48",
            "title": "Angle 30 ±2 degrees",
            "features": ["N822"],
            "paragraphs": [
                "Current situation:",
                "Error actual 7",
                heading,
                "Girar el inserto 2 grados.",
                "Verification:",
                "Pendiente de revisión.",
            ],
            "source": {"path": "/private/angle-plan.pptx", "locator": "Slide 6"},
        }
    )
    assert result["proposal_quote"] == "Girar el inserto 2 grados."
    assert result["title"] == "Angle 30 ±2 degrees"
    assert result["title_role"] == "document_heading"
    assert result["action_id"] == "R-48"
    assert result["execution_status"] == "not_established_by_this_plan"
    assert result["source"]["document"] == "angle-plan.pptx"
    assert "/private" not in json.dumps(result)


def test_assistant_unknown_layout_keeps_source_instead_of_guessing_action():
    source = ["Cambio R-91", "Valor inicial 17", "Anotación: estudiar el material."]
    plan = plan_evidence({"paragraphs": source})
    assert plan["proposal_quote"] is None
    assert plan["proposal_status"] == "not_separated"
    assert plan["text"] == "\n".join(source)
    result = evidence()
    result["actions"] = [plan]
    reply = correction_answer("Qué correcciones hay?", result)
    assert "sin separar una propuesta" in reply
    assert "> Anotación: estudiar el material." in reply


def test_assistant_limits_do_not_mix_units_series_or_samples_or_infer_missing_values():
    entries = [
        {
            "id": "N822",
            "series": [
                {
                    "id": "force",
                    "unit": "N",
                    "records": {
                        "c1": {
                            "01": {
                                "nominal": 20,
                                "lower": 18,
                                "upper": 22,
                                "source": {"path": "private/a.csv"},
                            },
                            "02": {
                                "nominal": 20,
                                "lower": 19,
                                "upper": 21,
                                "source": {"path": "private/b.csv"},
                            },
                        }
                    },
                },
                {
                    "id": "angle",
                    "unit": "deg",
                    "records": {"c1": {"01": {"upper": 30}}},
                },
                {
                    "id": "unknown",
                    "unit": None,
                    "records": {
                        "c2": {
                            "01": {
                                "nominal": float("nan"),
                                "lower": True,
                                "upper": float("inf"),
                            }
                        }
                    },
                },
            ],
        }
    ]
    limits = recorded_limits(entries, cavity=None, sample=None)
    assert len(limits) == 3
    assert limits[0]["lower"] == 18 and limits[0]["samples"] == ["01"]
    assert limits[1]["lower"] == 19 and limits[1]["samples"] == ["02"]
    assert (
        limits[2]["unit"] == "deg"
        and limits[2]["nominal"] is None
        and limits[2]["lower"] is None
    )
    assert limits[0]["documents"] == ["a.csv"]
    filtered = recorded_limits(entries, cavity="c1", sample="02")
    assert len(filtered) == 1 and filtered[0]["upper"] == 21


@pytest.mark.parametrize(
    "part,cota,action,proposal,unit",
    [
        ("6842", "N431", "3.7", "Reducir el espesor local en 0,12 mm.", "mm"),
        ("7953", "N822", "R-48", "Girar el inserto 2 grados.", "deg"),
        (
            "8064",
            "N913",
            "A-27",
            "Sustituir el muelle y repetir el ensayo de fuerza.",
            "N",
        ),
    ],
)
def test_assistant_factual_rendering_follows_arbitrary_evidence_not_question_identity(
    part, cota, action, proposal, unit
):
    result = evidence(part, cota, action, proposal, unit)
    reply = correction_answer(
        f"Qué correcciones tiene {cota} de la pieza {part}?", result
    )
    assert part in reply and cota in reply and action in reply
    assert "> " + proposal in reply
    assert f"nominal 12 {unit}" in reply and f"11,8–12,2 {unit}" in reply
    assert "plan.pptx · Página 9" in reply
    assert "no acredita la ejecución" in reply
    assert all(x not in reply for x in ("N170", "3212", "Bolt Eye", "expulsores"))


def test_assistant_missing_limit_is_not_synthesized_from_heading():
    result = evidence()
    result["actions"][0]["title"] = "Tool correction: Ø9 +0.3"
    result["recorded_limits"] = []
    result["coverage"]["recorded_limits"] = page(0, 0, 0)
    reply = correction_answer("Qué corrección tiene?", result)
    assert "Ø9 +0.3" in reply
    assert "Límites de las cotas" not in reply
    assert "9–9,3" not in reply


@pytest.mark.parametrize(
    "question",
    [
        "Explica las causas de la corrección",
        "Compara las correcciones",
        "Se ha ejecutado el retoque?",
        "Cuál fue el efecto de la corrección?",
        "Qué corrección y qué tolerancias tiene?",
        "What correction is proposed?",
        "Traduce la corrección al inglés",
    ],
)
def test_assistant_interpretation_and_other_languages_keep_model_path(question):
    assert correction_answer(question, evidence()) is None


def test_assistant_partial_evidence_is_not_presented_as_complete():
    result = evidence()
    result["coverage"]["actions"] = page(7, 0, 1)
    assert correction_answer("Qué correcciones hay?", result) is None
    result = evidence()
    result["coverage"]["recorded_limits"] = page(7, 0, 1)
    reply = correction_answer("Qué correcciones hay?", result)
    assert "Reducir el espesor local" in reply
    assert "Límites de las cotas" not in reply
    result = evidence()
    result["actions"][0]["text_truncated"] = True
    assert correction_answer("Qué correcciones hay?", result) is None
    compact = json.loads(bounded_result(evidence(), 700))
    assert correction_answer("Qué correcciones hay?", compact) is None


def test_assistant_no_imported_plans_does_not_claim_no_rework_exists():
    result = evidence()
    result["actions"] = []
    result["total"] = 0
    result["coverage"]["actions"] = page(0, 0, 0)
    result["coverage"]["recorded_limits"] = page(200, 0, 8)
    reply = correction_answer("Qué correcciones hay?", result)
    assert "No se han recuperado planes de corrección importados" in reply
    assert "no existan retoques en otras fuentes" in reply
    assert "Límites de las cotas" not in reply


def test_assistant_drafting_keeps_action_reference_and_separates_heading_from_proposal():
    result = evidence()
    prompt = drafting_messages(
        [{"role": "user", "content": "Explica la corrección"}], [result]
    )
    data = json.loads(prompt[-1]["content"].split("Información recuperada:\n", 1)[1])
    action = data["actions"][0]
    assert action["action_id"] == "3.7"
    assert action["proposal_quote"] == "Reducir el espesor local en 0,12 mm."
    assert "text" not in action
    assert data["recorded_limits"][0]["lower"] == 11.8
    assert result["actions"][0]["text"]  # The original evidence is not mutated.


@pytest.mark.parametrize("discover", [False, True])
@pytest.mark.parametrize("large_supporting_scope", [False, True])
def test_assistant_factual_pipeline_is_independent_of_provider_drafting(
    discover, large_supporting_scope
):
    data = evidence()
    if large_supporting_scope:
        data["recorded_limits"][0]["series"] = [
            f"Evaluation {n} with a long descriptive label" for n in range(600)
        ]
        compact = json.loads(bounded_result(data, 9500))
        assert not compact["coverage"]["recorded_limits"]["complete"]

    class Knowledge:
        settings = AssistantSettings()
        sources = {}

        def initial_lookup(self, _question):
            return (
                None
                if discover
                else ("read_part", {"part": data["part"], "section": "corrections"})
            )

        def run(self, name, arguments):
            assert name == "read_part" and arguments["part"] == data["part"]
            return copy.deepcopy(data)

    class Provider:
        calls = 0

        async def stream(self, _messages, _tools):
            self.calls += 1
            if discover and self.calls == 1:
                yield ModelChunk(
                    tool_calls=[
                        {
                            "function": {
                                "name": "read_part",
                                "arguments": {
                                    "part": data["part"],
                                    "section": "corrections",
                                },
                            }
                        }
                    ]
                )
            else:
                raise AssertionError(
                    "Factual evidence must not be rewritten by any provider"
                )

    provider = Provider()
    request = ChatRequest.model_validate(
        {"messages": [{"role": "user", "content": "Qué corrección se propone?"}]}
    )

    async def collect():
        return [event async for event in answer(request, provider, Knowledge())]

    events = asyncio.run(collect())
    assert provider.calls == int(discover)
    reply = "".join(e.text or "" for e in events if e.type == "delta")
    assert "Reducir el espesor local en 0,12 mm." in reply
    assert "11,8–12,2 mm" in reply
    assert events[-1].type == "done" and events[-1].truncated is False
