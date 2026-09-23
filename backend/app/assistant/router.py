import asyncio
import logging
from collections.abc import AsyncIterator

import anyio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser
from app.assistant.config import AssistantSettings, get_settings
from app.assistant.index import index_lifespan
from app.assistant.providers import ProviderError, get_provider
from app.assistant.schemas import AssistantStatus, ChatRequest, StreamEvent
from app.assistant.service import answer
from app.assistant.tools import KnowledgeTools

router = APIRouter(prefix="/assistant", tags=["assistant"], lifespan=index_lifespan)
logger = logging.getLogger(__name__)
# One local inference at a time, with no unbounded queue on a small PC.
_slot = asyncio.Semaphore(1)


@router.get("/status", response_model=AssistantStatus)
def status(
    _current_user: CurrentUser, settings: AssistantSettings = Depends(get_settings)
) -> AssistantStatus:
    return AssistantStatus(
        enabled=settings.enabled, model=settings.model if settings.enabled else None
    )


@router.post(
    "/chat",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Newline-delimited StreamEvent objects (status, delta, sources, done, error).",
            "content": {"application/x-ndjson": {"schema": {"type": "string"}}},
        },
        503: {"description": "Assistant disabled"},
    },
)
async def chat(
    request: ChatRequest,
    current_user: CurrentUser,
    settings: AssistantSettings = Depends(get_settings),
) -> StreamingResponse:
    if not settings.enabled:
        raise HTTPException(503, "El asistente está desactivado.")
    knowledge = KnowledgeTools(current_user.id, settings)

    async def events() -> AsyncIterator[str]:
        acquired = False
        try:
            try:
                await asyncio.wait_for(_slot.acquire(), timeout=0.1)
                acquired = True
            except asyncio.TimeoutError:
                yield (
                    StreamEvent(
                        type="error",
                        text="El asistente está atendiendo otra consulta. Inténtalo en unos segundos.",
                    ).model_dump_json(exclude_none=True)
                    + "\n"
                )
                return
            with anyio.fail_after(settings.timeout_seconds):
                async for event in answer(request, get_provider(settings), knowledge):
                    yield event.model_dump_json(exclude_none=True) + "\n"
        except (ProviderError, TimeoutError, HTTPException) as error:
            message = (
                str(error)
                if isinstance(error, ProviderError)
                else (
                    "La sesión ya no está activa. Vuelve a iniciar sesión."
                    if isinstance(error, HTTPException)
                    else "La consulta ha tardado demasiado. Prueba una pregunta más concreta."
                )
            )
            yield (
                StreamEvent(type="error", text=message).model_dump_json(
                    exclude_none=True
                )
                + "\n"
            )
        except Exception:
            logger.exception("Assistant request failed")
            yield (
                StreamEvent(
                    type="error",
                    text="No se ha podido completar la consulta. Inténtalo de nuevo.",
                ).model_dump_json(exclude_none=True)
                + "\n"
            )
        finally:
            if acquired:
                _slot.release()

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
