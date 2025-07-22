from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from ..models.provider import ProviderResponse, StreamChunk, ModelInfo


class ProviderAdapter(ABC):
    """Base class for all LLM provider adapters"""
    
    def __init__(self, name: str, base_url: str, api_key: str, **kwargs):
        self.name = name
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.auth_header = kwargs.get('auth_header', 'Authorization')
        self.auth_prefix = kwargs.get('auth_prefix', 'Bearer ')
        self.timeout = kwargs.get('timeout', 30)
        
    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """List available models from the provider"""
        pass
    
    @abstractmethod
    async def test_auth(self) -> bool:
        """Test authentication with the provider"""
        pass
    
    @abstractmethod
    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        model: str,
        params: Dict[str, Any],
        stream: bool = False
    ) -> Union[ProviderResponse, AsyncGenerator[StreamChunk, None]]:
        """Send chat completion request"""
        pass
    
    def get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            'Content-Type': 'application/json',
            self.auth_header: f"{self.auth_prefix}{self.api_key}".strip()
        }
        
        if additional_headers:
            headers.update(additional_headers)
            
        return headers
    
    def normalize_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Normalize message format for the provider"""
        # Default implementation - can be overridden
        normalized = []
        for msg in messages:
            normalized.append({
                'role': msg.get('role', 'user'),
                'content': msg.get('content', '')
            })
        return normalized
    
    def normalize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize parameters for the provider"""
        # Default implementation - can be overridden
        normalized = {}
        
        # Common parameter mappings
        if 'temperature' in params:
            normalized['temperature'] = float(params['temperature'])
        if 'top_p' in params:
            normalized['top_p'] = float(params['top_p'])
        if 'max_tokens' in params:
            normalized['max_tokens'] = int(params['max_tokens'])
        if 'stop' in params and params['stop']:
            normalized['stop'] = params['stop']
            
        return normalized
    
    async def handle_error(self, response_data: Dict[str, Any], status_code: int) -> Exception:
        """Handle API errors and return appropriate exception"""
        error_message = "Unknown error"
        
        if isinstance(response_data, dict):
            # Try common error message fields
            error_message = (
                response_data.get('error', {}).get('message') or
                response_data.get('message') or 
                response_data.get('detail') or
                str(response_data)
            )
        
        if status_code == 401:
            return Exception(f"Authentication failed: {error_message}")
        elif status_code == 403:
            return Exception(f"Access forbidden: {error_message}")
        elif status_code == 429:
            return Exception(f"Rate limit exceeded: {error_message}")
        elif status_code >= 500:
            return Exception(f"Server error: {error_message}")
        else:
            return Exception(f"API error ({status_code}): {error_message}")


class ProviderError(Exception):
    """Base provider error"""
    pass


class AuthenticationError(ProviderError):
    """Authentication error"""
    pass


class RateLimitError(ProviderError):
    """Rate limit error"""
    pass


class ModelNotFoundError(ProviderError):
    """Model not found error"""
    pass