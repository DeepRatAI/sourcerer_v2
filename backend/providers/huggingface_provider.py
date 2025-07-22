import json
import httpx
from typing import List, Dict, Any, Union, AsyncGenerator
from .base import ProviderAdapter, AuthenticationError, RateLimitError
from ..models.provider import ProviderResponse, StreamChunk, ModelInfo
from ..utils.logging import get_logger


class HuggingFaceProvider(ProviderAdapter):
    """HuggingFace Inference API provider adapter"""
    
    def __init__(self, name: str, api_key: str, **kwargs):
        base_url = kwargs.get('base_url', 'https://api-inference.huggingface.co')
        super().__init__(name, base_url, api_key, **kwargs)
        self.logger = get_logger(f"sourcerer.providers.{name}")
        
        # Common HuggingFace chat models
        self.static_models = [
            ModelInfo(id="microsoft/DialoGPT-large", name="DialoGPT Large", supports_streaming=False),
            ModelInfo(id="microsoft/DialoGPT-medium", name="DialoGPT Medium", supports_streaming=False),
            ModelInfo(id="facebook/blenderbot-400M-distill", name="BlenderBot 400M", supports_streaming=False),
            ModelInfo(id="HuggingFaceH4/zephyr-7b-beta", name="Zephyr 7B Beta", supports_streaming=False),
            ModelInfo(id="mistralai/Mixtral-8x7B-Instruct-v0.1", name="Mixtral 8x7B Instruct", supports_streaming=False),
        ]
    
    async def list_models(self) -> List[ModelInfo]:
        """List available models (using static list for HuggingFace)"""
        # HuggingFace doesn't have a standard models endpoint, return static list
        self.logger.info(f"Returning {len(self.static_models)} static models")
        return self.static_models
    
    async def test_auth(self) -> bool:
        """Test authentication with HuggingFace"""
        try:
            # Test with a simple model query
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/models/microsoft/DialoGPT-medium",
                    headers=self.get_headers(),
                    json={"inputs": "Hello"}
                )
                
                # HuggingFace returns various status codes, 200 or 503 (model loading) are acceptable
                return response.status_code in [200, 503]
                
        except Exception as e:
            self.logger.warning(f"Auth test failed: {e}")
            return False
    
    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        model: str,
        params: Dict[str, Any],
        stream: bool = False
    ) -> Union[ProviderResponse, AsyncGenerator[StreamChunk, None]]:
        """Send chat completion request to HuggingFace"""
        
        if stream:
            # HuggingFace Inference API doesn't support streaming for most models
            self.logger.warning("Streaming not supported for HuggingFace, falling back to non-streaming")
        
        # Convert messages to single prompt (HuggingFace models often expect single input)
        prompt = self._messages_to_prompt(messages, params.get('system_prompt'))
        
        normalized_params = self.normalize_params(params)
        
        payload = {
            "inputs": prompt,
            "parameters": normalized_params,
            "options": {
                "wait_for_model": True,
                "use_cache": False
            }
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/models/{model}",
                    headers=self.get_headers(),
                    json=payload
                )
                
                if response.status_code == 503:
                    # Model is loading, wait and retry
                    import asyncio
                    await asyncio.sleep(2)
                    response = await client.post(
                        f"{self.base_url}/models/{model}",
                        headers=self.get_headers(),
                        json=payload
                    )
                
                response.raise_for_status()
                data = response.json()
                
                # Handle different response formats
                content = ""
                if isinstance(data, list) and len(data) > 0:
                    if isinstance(data[0], dict):
                        content = data[0].get('generated_text', '') or data[0].get('text', '')
                    else:
                        content = str(data[0])
                elif isinstance(data, dict):
                    content = data.get('generated_text', '') or data.get('text', '') or str(data)
                else:
                    content = str(data)
                
                # Clean up response (remove input prompt if it's repeated)
                if content.startswith(prompt):
                    content = content[len(prompt):].strip()
                
                return ProviderResponse(
                    content=content,
                    usage={},
                    model=model,
                    finish_reason="stop"
                )
                
            except httpx.HTTPStatusError as e:
                error_data = {}
                try:
                    error_data = e.response.json()
                except:
                    pass
                
                if e.response.status_code == 401:
                    raise AuthenticationError("Invalid HuggingFace API key")
                elif e.response.status_code == 429:
                    raise RateLimitError("HuggingFace rate limit exceeded")
                
                raise await self.handle_error(error_data, e.response.status_code)
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        """Convert chat messages to a single prompt"""
        prompt_parts = []
        
        if system_prompt:
            prompt_parts.append(f"System: {system_prompt}")
        
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'system' and not system_prompt:
                prompt_parts.append(f"System: {content}")
            elif role == 'user':
                prompt_parts.append(f"Human: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}")
        
        # Add final Assistant prompt
        prompt_parts.append("Assistant:")
        
        return "\n".join(prompt_parts)
    
    def normalize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize parameters for HuggingFace"""
        normalized = {}
        
        # HuggingFace parameter names
        if 'temperature' in params:
            normalized['temperature'] = float(params['temperature'])
        if 'top_p' in params:
            normalized['top_p'] = float(params['top_p'])
        if 'max_tokens' in params:
            normalized['max_new_tokens'] = int(params['max_tokens'])
        if 'stop' in params and params['stop']:
            # Some models support stop sequences
            normalized['stop_sequences'] = params['stop']
        
        # Set reasonable defaults
        if 'max_new_tokens' not in normalized:
            normalized['max_new_tokens'] = 512
        
        return normalized