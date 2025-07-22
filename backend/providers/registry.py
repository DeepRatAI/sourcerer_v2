from typing import Dict, Type, Optional
from .base import ProviderAdapter
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .moonshot_provider import MoonshotProvider
from .huggingface_provider import HuggingFaceProvider
from .custom_provider import CustomProvider
from ..models.config import ProviderConfig


class ProviderRegistry:
    """Registry for provider adapters"""
    
    def __init__(self):
        self._providers: Dict[str, Type[ProviderAdapter]] = {
            'openai': OpenAIProvider,
            'anthropic': AnthropicProvider,
            'moonshot': MoonshotProvider,
            'huggingface': HuggingFaceProvider,
            'custom': CustomProvider,
        }
    
    def register_provider(self, name: str, provider_class: Type[ProviderAdapter]) -> None:
        """Register a new provider class"""
        self._providers[name] = provider_class
    
    def get_provider_class(self, provider_type: str) -> Optional[Type[ProviderAdapter]]:
        """Get provider class by type"""
        return self._providers.get(provider_type)
    
    def create_adapter(self, provider_id: str, config: ProviderConfig, api_key: str) -> ProviderAdapter:
        """Create provider adapter instance"""
        provider_class = self.get_provider_class(config.type)
        
        if not provider_class:
            if config.type == 'built_in':
                # Try to determine built-in type from provider_id
                provider_class = self._providers.get(provider_id)
            
            if not provider_class:
                raise ValueError(f"Unknown provider type: {config.type}")
        
        # Prepare kwargs
        kwargs = {
            'base_url': config.base_url,
            'auth_header': config.auth_header,
            'auth_prefix': config.auth_prefix,
        }
        
        # Add custom provider specific kwargs
        if config.type == 'custom':
            kwargs.update({
                'models_endpoint': config.models_endpoint,
                'models_json_path': config.models_json_path,
                'default_model': config.default_model,
                'payload_schema': config.payload_schema,
                'test_prompt': config.test_prompt,
            })
        
        return provider_class(
            name=provider_id,
            api_key=api_key,
            **kwargs
        )
    
    def list_available_providers(self) -> Dict[str, str]:
        """List all available provider types"""
        return {
            'openai': 'OpenAI',
            'anthropic': 'Anthropic Claude',
            'moonshot': 'Moonshot AI',
            'huggingface': 'HuggingFace Inference',
            'custom': 'Custom Provider',
        }


# Global registry instance
_registry = ProviderRegistry()


def get_provider_adapter(provider_id: str, config: ProviderConfig, api_key: str) -> ProviderAdapter:
    """Get provider adapter instance"""
    return _registry.create_adapter(provider_id, config, api_key)


def register_provider(name: str, provider_class: Type[ProviderAdapter]) -> None:
    """Register a new provider class"""
    _registry.register_provider(name, provider_class)


def list_available_providers() -> Dict[str, str]:
    """List all available provider types"""
    return _registry.list_available_providers()