from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    id: str
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    provider: Optional[str] = None
    model: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatSession(BaseModel):
    id: str
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    messages: List[ChatMessage] = Field(default_factory=list)
    context_sources: List[str] = Field(default_factory=list)  # Source IDs used in this chat
    total_tokens: int = 0
    archived: bool = False


class SendMessageRequest(BaseModel):
    content: str
    session_id: Optional[str] = None
    include_sources: bool = True
    max_context_items: int = 5


class ChatResponse(BaseModel):
    message: ChatMessage
    session_id: str
    context_items: List[Dict[str, Any]] = Field(default_factory=list)
    total_tokens_used: int = 0