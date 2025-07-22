from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from datetime import datetime

from ..config import ConfigManager
from ..providers import get_provider_adapter, list_available_providers
from ..models.api import APIResponse, APIError
from ..models.provider import (
    CreateProviderRequest, UpdateProviderRequest, TestInferenceRequest,
    ProviderInfo, ModelInfo, ProviderResponse
)
from ..models.config import ProviderConfig, ModelsCache
from ..utils.logging import get_logger
from ..utils.validation import validate_provider_name, validate_api_key, validate_url

router = APIRouter()
logger = get_logger("sourcerer.api.providers")


def get_config_manager() -> ConfigManager:
    """Get config manager dependency"""
    return ConfigManager()


@router.get("")
async def list_providers(config_manager: ConfigManager = Depends(get_config_manager)):
    """List all configured providers"""
    try:
        providers = []
        for provider_id, provider_config in config_manager.config.providers.items():
            status_info = config_manager.get_provider_status(provider_id)
            providers.append(ProviderInfo(
                id=provider_id,
                name=provider_config.alias or provider_id,
                type=provider_config.type,
                status=status_info.get("status", "unknown"),
                model_count=status_info.get("model_count", 0),
                last_updated=status_info.get("last_updated"),
                error_message=status_info.get("error_message")
            ))
        
        return APIResponse(data=providers)
        
    except Exception as e:
        logger.error(f"Failed to list providers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list providers: {e}")


@router.get("/available")
async def list_available_provider_types():
    """List available provider types"""
    return APIResponse(data=list_available_providers())


@router.post("")
async def create_provider(
    request: CreateProviderRequest,
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """Create a new provider"""
    try:
        # Validation
        if request.type == "custom":
            if not request.name:
                raise ValueError("Name is required for custom providers")
            if not validate_provider_name(request.name):
                raise ValueError("Invalid provider name format")
            provider_id = request.name.lower()
        else:
            # Built-in provider
            provider_id = request.type
        
        if not validate_api_key(request.api_key):
            raise ValueError("Invalid API key format")
        
        if request.base_url and not validate_url(request.base_url):
            raise ValueError("Invalid base URL format")
        
        # Check if provider already exists
        if provider_id in config_manager.config.providers:
            raise ValueError(f"Provider {provider_id} already exists")
        
        # Create provider config
        provider_config = ProviderConfig(
            type=request.type,
            alias=request.alias,
            api_key_enc="",  # Will be encrypted by config_manager
            base_url=request.base_url or _get_default_base_url(provider_id),
            auth_header=request.auth_header,
            auth_prefix=request.auth_prefix,
            models_endpoint=request.models_endpoint,
            models_json_path=request.models_json_path,
            default_model=request.default_model,
            payload_schema=request.payload_schema,
            test_prompt=request.test_prompt
        )
        
        # Test authentication and fetch models if requested
        adapter = get_provider_adapter(provider_id, provider_config, request.api_key)
        
        # Test auth
        if not await adapter.test_auth():
            raise ValueError("Authentication failed with provided credentials")
        
        # Fetch models if auto_fetch enabled
        models_cache = None
        if request.auto_fetch_models:
            try:
                models = await adapter.list_models()
                if models:
                    models_cache = ModelsCache(
                        fetched_at=datetime.now(),
                        ids=[model.id for model in models]
                    )
                    provider_config.models_cache = models_cache
                    logger.info(f"Fetched {len(models)} models for provider {provider_id}")
            except Exception as e:
                logger.warning(f"Failed to fetch models for provider {provider_id}: {e}")
                # Don't fail creation, just warn
        
        # Add provider to config
        config_manager.add_provider(provider_id, provider_config)
        
        return APIResponse(data={
            "message": f"Provider {provider_id} created successfully",
            "provider_id": provider_id,
            "models_fetched": len(models_cache.ids) if models_cache else 0
        })
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create provider: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create provider: {e}")


@router.get("/{provider_id}")
async def get_provider(
    provider_id: str,
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """Get provider details"""
    try:
        if provider_id not in config_manager.config.providers:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        provider_config = config_manager.config.providers[provider_id]
        status_info = config_manager.get_provider_status(provider_id)
        
        # Get obfuscated API key
        from ..utils.security import obfuscate_api_key
        try:
            api_key = config_manager.get_provider_api_key(provider_id)
            api_key_display = obfuscate_api_key(api_key)
        except:
            api_key_display = "***ERROR***"
        
        provider_data = provider_config.model_dump()
        provider_data["api_key_display"] = api_key_display
        provider_data["status"] = status_info
        del provider_data["api_key_enc"]
        
        return APIResponse(data=provider_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get provider: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get provider: {e}")


@router.put("/{provider_id}")
async def update_provider(
    provider_id: str,
    request: UpdateProviderRequest,
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """Update existing provider"""
    try:
        if provider_id not in config_manager.config.providers:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        # Build updates dict
        updates = {}
        for field, value in request.model_dump(exclude_unset=True).items():
            if value is not None:
                updates[field] = value
        
        # Validation
        if "api_key" in updates and not validate_api_key(updates["api_key"]):
            raise ValueError("Invalid API key format")
        
        if "base_url" in updates and not validate_url(updates["base_url"]):
            raise ValueError("Invalid base URL format")
        
        # Test new credentials if API key is being updated
        if "api_key" in updates:
            provider_config = config_manager.config.providers[provider_id]
            test_config = provider_config.model_copy()
            
            # Apply updates for testing
            for key, value in updates.items():
                if hasattr(test_config, key):
                    setattr(test_config, key, value)
            
            adapter = get_provider_adapter(provider_id, test_config, updates["api_key"])
            if not await adapter.test_auth():
                raise ValueError("Authentication failed with new credentials")
        
        # Apply updates
        config_manager.update_provider(provider_id, updates)
        
        return APIResponse(data={"message": f"Provider {provider_id} updated successfully"})
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update provider: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update provider: {e}")


@router.delete("/{provider_id}")
async def delete_provider(
    provider_id: str,
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """Delete provider"""
    try:
        if provider_id not in config_manager.config.providers:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        config_manager.remove_provider(provider_id)
        
        return APIResponse(data={"message": f"Provider {provider_id} deleted successfully"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete provider: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete provider: {e}")


@router.post("/{provider_id}/refresh-models")
async def refresh_provider_models(
    provider_id: str,
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """Refresh provider model list"""
    try:
        if provider_id not in config_manager.config.providers:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        provider_config = config_manager.config.providers[provider_id]
        api_key = config_manager.get_provider_api_key(provider_id)
        
        adapter = get_provider_adapter(provider_id, provider_config, api_key)
        models = await adapter.list_models()
        
        # Update models cache
        models_cache = ModelsCache(
            fetched_at=datetime.now(),
            ids=[model.id for model in models]
        )
        
        provider_config.models_cache = models_cache
        config_manager.save_config()
        
        return APIResponse(data={
            "message": f"Refreshed {len(models)} models for provider {provider_id}",
            "models": [model.model_dump() for model in models]
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh models: {e}")


@router.get("/{provider_id}/models")
async def get_provider_models(
    provider_id: str,
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """Get cached models for provider"""
    try:
        if provider_id not in config_manager.config.providers:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        provider_config = config_manager.config.providers[provider_id]
        
        if provider_config.models_cache:
            models = [{"id": model_id, "name": model_id} for model_id in provider_config.models_cache.ids]
            return APIResponse(data={
                "models": models,
                "fetched_at": provider_config.models_cache.fetched_at.isoformat(),
                "count": len(models)
            })
        else:
            return APIResponse(data={
                "models": [],
                "fetched_at": None,
                "count": 0,
                "message": "No cached models. Use refresh-models endpoint to fetch."
            })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get provider models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get provider models: {e}")


@router.post("/test-inference")
async def test_inference(
    request: TestInferenceRequest,
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """Test inference with active or specified provider/model"""
    try:
        provider_id = request.provider_id or config_manager.config.active_provider
        model_id = request.model_id or config_manager.config.active_model
        
        if not provider_id:
            raise ValueError("No provider specified and no active provider set")
        
        if provider_id not in config_manager.config.providers:
            raise ValueError(f"Provider {provider_id} not found")
        
        if not model_id:
            # Try to use first available model
            provider_config = config_manager.config.providers[provider_id]
            if provider_config.models_cache and provider_config.models_cache.ids:
                model_id = provider_config.models_cache.ids[0]
            else:
                raise ValueError("No model specified and no cached models available")
        
        # Get provider adapter
        provider_config = config_manager.config.providers[provider_id]
        api_key = config_manager.get_provider_api_key(provider_id)
        adapter = get_provider_adapter(provider_id, provider_config, api_key)
        
        # Test inference
        import time
        start_time = time.time()
        
        response = await adapter.chat(
            messages=[{"role": "user", "content": request.prompt}],
            model=model_id,
            params={"max_tokens": 50, "temperature": 0.7},
            stream=False
        )
        
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        return APIResponse(data={
            "success": True,
            "provider": provider_id,
            "model": model_id,
            "response_preview": response.content[:100] + "..." if len(response.content) > 100 else response.content,
            "latency_ms": latency_ms,
            "usage": response.usage or {},
            "finish_reason": response.finish_reason
        })
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to test inference: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test inference: {e}")


def _get_default_base_url(provider_type: str) -> str:
    """Get default base URL for provider type"""
    defaults = {
        "openai": "https://api.openai.com/v1",
        "anthropic": "https://api.anthropic.com/v1",
        "moonshot": "https://api.moonshot.cn/v1",
        "huggingface": "https://api-inference.huggingface.co",
    }
    return defaults.get(provider_type, "")