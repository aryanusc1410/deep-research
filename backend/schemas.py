from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Dict, Any

Provider = Literal["openai", "gemini"]
TemplateName = Literal["bullet_summary", "two_column", "detailed_report"]

class UserMessage(BaseModel):
    role: Literal["user","assistant","tool"] = "user"
    content: str

class RunConfig(BaseModel):
    provider: Provider = "openai"
    model: Optional[str] = None
    template: TemplateName = "bullet_summary"
    search_budget: int = 4

class RunRequest(BaseModel):
    query: str
    messages: List[UserMessage] = Field(default_factory=list)
    config: RunConfig = RunConfig()

class Report(BaseModel):
    structure: TemplateName
    content: str
    citations: List[Dict[str, Any]]

class StreamChunk(BaseModel):
    event: Literal["token","status","done"] = "token"
    data: Dict[str, Any] = Field(default_factory=dict)