from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from ..config import ConfigManager
from ..models.api import APIResponse, ExportRequest, ImportRequest
from ..utils.logging import get_logger

router = APIRouter()
logger = get_logger("sourcerer.api.export")


def get_config_manager() -> ConfigManager:
    """Get config manager dependency"""
    return ConfigManager()


@router.post("")
async def export_config(
    request: ExportRequest,
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """Export configuration"""
    try:
        export_data = config_manager.export_config(
            include_keys=request.include_keys,
            passphrase=request.passphrase
        )
        
        return APIResponse(data=export_data)
        
    except Exception as e:
        logger.error(f"Failed to export config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export config: {e}")


@router.post("/import")
async def import_config(
    request: ImportRequest,
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """Import configuration"""
    try:
        import json
        import_data = json.loads(request.file_content)
        
        config_manager.import_config(
            import_data=import_data,
            overwrite=request.overwrite_conflicts
        )
        
        return APIResponse(data={"message": "Configuration imported successfully"})
        
    except Exception as e:
        logger.error(f"Failed to import config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import config: {e}")