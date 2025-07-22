import httpx
from typing import List, Dict, Any, Union, AsyncGenerator
from .base import ProviderAdapter, AuthenticationError, RateLimitError
from .openai_provider import OpenAIProvider
from ..models.provider import ModelInfo
from ..utils.logging import get_logger


class MoonshotProvider(OpenAIProvider):
    """Moonshot provider adapter (OpenAI-compatible)"""
    
    def __init__(self, name: str, api_key: str, **kwargs):
        base_url = kwargs.get('base_url', 'https://api.moonshot.cn/v1')
        super().__init__(name, api_key, base_url=base_url, **kwargs)
        self.logger = get_logger(f"sourcerer.providers.{name}")
        
        # Moonshot-specific models (if API doesn't provide dynamic list)
        self.static_models = [
            ModelInfo(id="moonshot-v1-8k", name="Moonshot v1 8K", context_length=8192, supports_streaming=True),
            ModelInfo(id="moonshot-v1-32k", name="Moonshot v1 32K", context_length=32768, supports_streaming=True),
            ModelInfo(id="moonshot-v1-128k", name="Moonshot v1 128K", context_length=131072, supports_streaming=True),
        ]
    
    async def list_models(self) -> List[ModelInfo]:
        """List available models from Moonshot"""
        try:
            # Try to get models from API first
            return await super().list_models()
        except Exception as e:
            self.logger.warning(f"Failed to fetch models from API, using static list: {e}")
            # Fall back to static model list
            return self.static_models
    
    async def test_auth(self) -> bool:
        """Test authentication with Moonshot"""
        try:
            models = await self.list_models()
            return len(models) > 0
        except AuthenticationError:
            return False
        except Exception as e:
            self.logger.warning(f"Auth test failed: {e}")
            return False