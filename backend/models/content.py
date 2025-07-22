from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ContentType(str, Enum):
    SUMMARY = "summary"
    SCRIPTS = "scripts" 
    IMAGES = "images"
    VIDEO = "video"


class PlatformScript(BaseModel):
    platform: str  # tiktok, instagram, x, youtube
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GeneratedImage(BaseModel):
    prompt: str
    file_path: str
    url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GeneratedContent(BaseModel):
    type: ContentType
    title: str
    content: Optional[str] = None  # For summaries
    scripts: List[PlatformScript] = Field(default_factory=list)
    images: List[GeneratedImage] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class ContentPackage(BaseModel):
    id: str
    source_item_id: str
    research_summary: Optional[str] = None
    contents: List[GeneratedContent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    generation_params: Dict[str, Any] = Field(default_factory=dict)
    file_paths: List[str] = Field(default_factory=list)


class GenerateContentRequest(BaseModel):
    source_item_id: str
    content_types: List[ContentType] = Field(default=[ContentType.SUMMARY, ContentType.SCRIPTS])
    include_research: bool = True
    platforms: List[str] = Field(default=["tiktok", "instagram", "x", "youtube"])
    image_count: int = Field(default=1, ge=0, le=5)
    custom_instructions: Optional[str] = None


class ResearchDocument(BaseModel):
    item_id: str
    queries: List[str]
    results: List[Dict[str, Any]]
    summary: str
    created_at: datetime = Field(default_factory=datetime.now)