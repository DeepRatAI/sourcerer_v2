from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ModelsCache(BaseModel):
    fetched_at: datetime
    ids: List[str]


class ProviderConfig(BaseModel):
    type: str  # built_in or custom
    alias: Optional[str] = None
    api_key_enc: str
    base_url: str
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer "
    models_endpoint: Optional[str] = None
    models_json_path: str = "data[].id"
    default_model: Optional[str] = None
    payload_schema: str = "openai_chat"
    test_prompt: Optional[str] = None
    models_cache: Optional[ModelsCache] = None


class InferenceDefaults(BaseModel):
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int = 1024
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    system_prompt: str = "You are Sourcerer assistant."
    stop: List[str] = Field(default_factory=list)
    streaming: bool = True


class ImageGenerationConfig(BaseModel):
    provider: str = "openai"
    model: str = "dall-e-3"
    output_format: str = "png"
    enabled: bool = False


class LimitsConfig(BaseModel):
    max_sources: int = 50
    max_items_per_source: int = 200
    max_research_results: int = 10
    max_image_prompts: int = 5


class ExternalResearchConfig(BaseModel):
    enabled: bool = False
    provider: Optional[str] = None
    api_key_enc: Optional[str] = None


class ConfigModel(BaseModel):
    version: int = 1
    active_provider: Optional[str] = None
    active_model: Optional[str] = None
    inference_defaults: InferenceDefaults = Field(default_factory=InferenceDefaults)
    image_generation: ImageGenerationConfig = Field(default_factory=ImageGenerationConfig)
    external_research: ExternalResearchConfig = Field(default_factory=ExternalResearchConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict)
    debug_mode: bool = False
    master_password_hash: Optional[str] = None