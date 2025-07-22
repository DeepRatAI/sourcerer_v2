from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional

from ..config import ConfigManager
from ..models.api import APIResponse, APIError
from ..models.config import InferenceDefaults
from ..utils.logging import get_logger

router = APIRouter()
logger = get_logger("sourcerer.api.config")


def get_config_manager() -> ConfigManager:
    """Get config manager dependency"""
    return ConfigManager()


@router.get("")
async def get_config(config_manager: ConfigManager = Depends(get_config_manager)):
    """Get current configuration (excluding sensitive data)"""
    try:
        config_dict = config_manager.config.model_dump()
        
        # Remove sensitive data
        for provider_id, provider_data in config_dict.get("providers", {}).items():
            if isinstance(provider_data, dict) and "api_key_enc" in provider_data:
                # Obfuscate API key
                from ..utils.security import obfuscate_api_key
                try:
                    api_key = config_manager.get_provider_api_key(provider_id)
                    provider_data["api_key_display"] = obfuscate_api_key(api_key)
                except:
                    provider_data["api_key_display"] = "***ERROR***"
                del provider_data["api_key_enc"]
        
        return APIResponse(data=config_dict)
        
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get config: {e}")


@router.get("/first-run")
async def check_first_run(config_manager: ConfigManager = Depends(get_config_manager)):
    """Check if this is the first run"""
    return APIResponse(data={"first_run": config_manager.is_first_run})


@router.put("/active-provider")
async def set_active_provider(
    provider_id: str,
    model_id: Optional[str] = None,
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """Set active provider and model"""
    try:
        config_manager.set_active_provider(provider_id, model_id)
        return APIResponse(data={"message": "Active provider updated successfully"})
        
    except Exception as e:
        logger.error(f"Failed to set active provider: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to set active provider: {e}")


@router.put("/inference-defaults")
async def update_inference_defaults(
    updates: Dict[str, Any],
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """Update inference default parameters"""
    try:
        config_manager.update_inference_defaults(updates)
        return APIResponse(data={"message": "Inference defaults updated successfully"})
        
    except Exception as e:
        logger.error(f"Failed to update inference defaults: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to update inference defaults: {e}")


@router.put("/image-generation")
async def toggle_image_generation(
    enabled: bool,
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """Enable/disable image generation"""
    try:
        config_manager.enable_image_generation(enabled)
        return APIResponse(data={"message": f"Image generation {'enabled' if enabled else 'disabled'}"})
        
    except Exception as e:
        logger.error(f"Failed to toggle image generation: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to toggle image generation: {e}")


@router.get("/validation")
async def validate_config(config_manager: ConfigManager = Depends(get_config_manager)):
    """Validate current configuration"""
    try:
        errors = config_manager.validate_config()
        return APIResponse(data={
            "valid": len(errors) == 0,
            "errors": errors
        })
        
    except Exception as e:
        logger.error(f"Failed to validate config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to validate config: {e}")


@router.get("/debug")
async def get_debug_mode(config_manager: ConfigManager = Depends(get_config_manager)):
    """Get debug mode status"""
    return APIResponse(data={"debug_mode": config_manager.config.debug_mode})


@router.put("/debug")
async def set_debug_mode(
    debug_mode: bool,
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """Set debug mode"""
    try:
        config_manager.config.debug_mode = debug_mode
        config_manager.save_config()
        
        # Update logger level
        import logging
        level = logging.DEBUG if debug_mode else logging.INFO
        get_logger("sourcerer").setLevel(level)
        
        return APIResponse(data={"message": f"Debug mode {'enabled' if debug_mode else 'disabled'}"})
        
    except Exception as e:
        logger.error(f"Failed to set debug mode: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set debug mode: {e}")