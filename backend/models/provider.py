from typing import Dict, List, Optional, Any, Union, AsyncGenerator
from pydantic import BaseModel
from enum import Enum


class ProviderType(str, Enum):
    BUILT_IN = "built_in"
    CUSTOM = "custom"


class ProviderStatus(str, Enum):
    OK = "ok"
    ERROR = "error" 
    WARNING = "warning"


class ModelInfo(BaseModel):
    id: str
    name: Optional[str] = None
    context_length: Optional[int] = None
    supports_streaming: bool = True


class ProviderResponse(BaseModel):
    content: str
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None


class StreamChunk(BaseModel):
    delta: str
    finish_reason: Optional[str] = None


class ProviderInfo(BaseModel):
    id: str
    name: str
    type: ProviderType
    status: ProviderStatus
    model_count: int
    last_updated: Optional[str] = None
    error_message: Optional[str] = None


class CreateProviderRequest(BaseModel):
    type: ProviderType
    name: Optional[str] = None  # For custom providers
    alias: Optional[str] = None
    api_key: str
    base_url: Optional[str] = None
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer "
    models_endpoint: Optional[str] = None
    models_json_path: str = "data[].id"
    default_model: Optional[str] = None
    payload_schema: str = "openai_chat"
    test_prompt: Optional[str] = None
    auto_fetch_models: bool = True


class UpdateProviderRequest(BaseModel):
    alias: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    auth_header: Optional[str] = None
    auth_prefix: Optional[str] = None
    models_endpoint: Optional[str] = None
    models_json_path: Optional[str] = None
    default_model: Optional[str] = None
    payload_schema: Optional[str] = None
    test_prompt: Optional[str] = None


class TestInferenceRequest(BaseModel):
    provider_id: Optional[str] = None
    model_id: Optional[str] = None
    prompt: str = "Hello, this is a test message."