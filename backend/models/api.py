from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime


class APIResponse(BaseModel):
    ok: bool = True
    data: Optional[Union[Dict[str, Any], List[Any], str, int]] = None
    meta: Dict[str, Any] = Field(default_factory=lambda: {
        "timestamp": datetime.now().isoformat(),
        "request_id": None
    })


class APIError(BaseModel):
    ok: bool = False
    error: Dict[str, Any]
    meta: Dict[str, Any] = Field(default_factory=lambda: {
        "timestamp": datetime.now().isoformat(), 
        "request_id": None
    })


class ExportRequest(BaseModel):
    include_keys: bool = False
    passphrase: Optional[str] = None
    include_chats: bool = True
    include_sources: bool = True


class ImportRequest(BaseModel):
    file_content: str
    passphrase: Optional[str] = None
    overwrite_conflicts: bool = False