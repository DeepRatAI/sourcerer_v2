from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    RSS = "rss"
    HTML = "html"
    API = "api"
    TWITTER = "twitter"
    REDDIT = "reddit"
    CUSTOM = "custom"


class SourceStatus(str, Enum):
    ACTIVE = "active"
    ERROR = "error"
    PAUSED = "paused"


class SourceItem(BaseModel):
    id: str  # sha1(url)
    title: str
    url: str
    published_at: datetime
    summary: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    raw: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None


class Source(BaseModel):
    id: str
    alias: str
    type: SourceType
    url: str
    status: SourceStatus = SourceStatus.ACTIVE
    last_fetch: Optional[datetime] = None
    refresh_interval_sec: int = 1800  # 30 minutes
    fail_count: int = 0
    items: List[SourceItem] = Field(default_factory=list)
    headers: Dict[str, str] = Field(default_factory=dict)
    selectors: Dict[str, str] = Field(default_factory=dict)  # For HTML parsing
    max_items: int = 200
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CreateSourceRequest(BaseModel):
    alias: str
    type: SourceType
    url: HttpUrl
    refresh_interval_sec: int = Field(default=1800, ge=300, le=86400)  # 5min to 24h
    headers: Dict[str, str] = Field(default_factory=dict)
    selectors: Dict[str, str] = Field(default_factory=dict)
    max_items: int = Field(default=200, ge=10, le=1000)


class UpdateSourceRequest(BaseModel):
    alias: Optional[str] = None
    url: Optional[HttpUrl] = None
    refresh_interval_sec: Optional[int] = Field(None, ge=300, le=86400)
    headers: Optional[Dict[str, str]] = None
    selectors: Optional[Dict[str, str]] = None
    max_items: Optional[int] = Field(None, ge=10, le=1000)
    status: Optional[SourceStatus] = None


class SourceInfo(BaseModel):
    id: str
    alias: str
    type: SourceType
    status: SourceStatus
    item_count: int
    last_fetch: Optional[datetime] = None
    fail_count: int
    next_refresh: Optional[datetime] = None