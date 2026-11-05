from pydantic import BaseModel, ConfigDict, Field


class HelpChatQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=3, max_length=500)


class HelpChatSource(BaseModel):
    document: str
    section: str
    excerpt: str


class HelpChatRouteSuggestion(BaseModel):
    label: str
    path: str
    description: str


class HelpChatResponse(BaseModel):
    answer: str
    sources: list[HelpChatSource] = Field(default_factory=list)
    suggested_routes: list[HelpChatRouteSuggestion] = Field(
        default_factory=list
    )
    mode: str = "deterministic"
