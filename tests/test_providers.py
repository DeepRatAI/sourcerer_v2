import pytest
from unittest.mock import AsyncMock, patch

from backend.providers.openai_provider import OpenAIProvider
from backend.providers.anthropic_provider import AnthropicProvider
from backend.models.provider import ModelInfo


class TestOpenAIProvider:
    
    @pytest.mark.asyncio
    async def test_provider_initialization(self):
        """Test provider initialization"""
        provider = OpenAIProvider("test-openai", "sk-test123")
        
        assert provider.name == "test-openai"
        assert provider.api_key == "sk-test123"
        assert provider.base_url == "https://api.openai.com/v1"
    
    def test_header_generation(self):
        """Test authentication header generation"""
        provider = OpenAIProvider("test-openai", "sk-test123")
        
        headers = provider.get_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer sk-test123"
        assert headers["Content-Type"] == "application/json"
    
    def test_message_normalization(self):
        """Test message format normalization"""
        provider = OpenAIProvider("test-openai", "sk-test123")
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        
        normalized = provider.normalize_messages(messages)
        
        assert len(normalized) == 2
        assert normalized[0]["role"] == "user"
        assert normalized[1]["role"] == "assistant"
    
    def test_params_normalization(self):
        """Test parameter normalization"""
        provider = OpenAIProvider("test-openai", "sk-test123")
        
        params = {
            "temperature": "0.7",
            "max_tokens": "100",
            "presence_penalty": "0.1"
        }
        
        normalized = provider.normalize_params(params)
        
        assert normalized["temperature"] == 0.7
        assert normalized["max_tokens"] == 100
        assert normalized["presence_penalty"] == 0.1


class TestAnthropicProvider:
    
    def test_anthropic_initialization(self):
        """Test Anthropic provider initialization"""
        provider = AnthropicProvider("test-anthropic", "sk-ant-test123")
        
        assert provider.name == "test-anthropic"
        assert provider.auth_header == "x-api-key"
        assert provider.auth_prefix == ""
    
    @pytest.mark.asyncio 
    async def test_static_models_list(self):
        """Test static models list"""
        provider = AnthropicProvider("test-anthropic", "sk-ant-test123")
        
        models = await provider.list_models()
        
        assert len(models) > 0
        assert any(model.id.startswith("claude-3") for model in models)
    
    def test_message_system_handling(self):
        """Test system message handling"""
        provider = AnthropicProvider("test-anthropic", "sk-ant-test123")
        
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"}
        ]
        
        normalized = provider.normalize_messages(messages)
        
        # System messages should be filtered out
        assert len(normalized) == 1
        assert normalized[0]["role"] == "user"


if __name__ == "__main__":
    pytest.main([__file__])