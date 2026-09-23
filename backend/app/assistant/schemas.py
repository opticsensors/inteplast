from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ChatMessage(StrictModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=3000)


class ChatRequest(StrictModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=9)

    @model_validator(mode="after")
    def conversation(self) -> "ChatRequest":
        if self.messages[-1].role != "user":
            raise ValueError("La última entrada debe ser una pregunta del usuario.")
        if sum(len(m.content) for m in self.messages) > 12000:
            raise ValueError("Conversación demasiado larga. Inicia una nueva consulta.")
        return self


class Source(BaseModel):
    label: str
    url: str


class AssistantStatus(BaseModel):
    enabled: bool
    model: str | None = None


class StreamEvent(BaseModel):
    type: Literal["status", "delta", "sources", "done", "error"]
    text: str | None = None
    sources: list[Source] | None = None
    truncated: bool | None = None
