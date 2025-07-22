import json
import httpx
from typing import List, Dict, Any, Union, AsyncGenerator
from .base import ProviderAdapter, AuthenticationError, RateLimitError
from ..models.provider import ProviderResponse, StreamChunk, ModelInfo
from ..utils.logging import get_logger


class OpenAIProvider(ProviderAdapter):
    """OpenAI provider adapter"""
    
    def __init__(self, name: str, api_key: str, **kwargs):
        base_url = kwargs.get('base_url', 'https://api.openai.com/v1')
        super().__init__(name, base_url, api_key, **kwargs)
        self.logger = get_logger(f"sourcerer.providers.{name}")
    
    async def list_models(self) -> List[ModelInfo]:
        """List available models from OpenAI"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self.get_headers()
                )
                response.raise_for_status()
                data = response.json()
                
                models = []
                for model_data in data.get('data', []):
                    models.append(ModelInfo(
                        id=model_data['id'],
                        name=model_data.get('id'),
                        supports_streaming=True  # Most OpenAI models support streaming
                    ))
                
                self.logger.info(f"Found {len(models)} models")
                return models
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise AuthenticationError("Invalid OpenAI API key")
                raise await self.handle_error(e.response.json(), e.response.status_code)
            except Exception as e:
                self.logger.error(f"Failed to list models: {e}")
                raise Exception(f"Failed to list models: {e}")
    
    async def test_auth(self) -> bool:
        """Test authentication with OpenAI"""
        try:
            models = await self.list_models()
            return len(models) > 0
        except AuthenticationError:
            return False
        except Exception:
            return False
    
    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        model: str,
        params: Dict[str, Any],
        stream: bool = False
    ) -> Union[ProviderResponse, AsyncGenerator[StreamChunk, None]]:
        """Send chat completion request to OpenAI"""
        
        normalized_messages = self.normalize_messages(messages)
        normalized_params = self.normalize_params(params)
        
        payload = {
            "model": model,
            "messages": normalized_messages,
            "stream": stream,
            **normalized_params
        }
        
        # Add system prompt if provided
        system_prompt = params.get('system_prompt')
        if system_prompt and not any(msg.get('role') == 'system' for msg in normalized_messages):
            payload["messages"] = [{"role": "system", "content": system_prompt}] + payload["messages"]
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                if stream:
                    return self._stream_chat(client, payload)
                else:
                    return await self._complete_chat(client, payload)
                    
            except httpx.HTTPStatusError as e:
                error_data = {}
                try:
                    error_data = e.response.json()
                except:
                    pass
                
                if e.response.status_code == 401:
                    raise AuthenticationError("Invalid OpenAI API key")
                elif e.response.status_code == 429:
                    raise RateLimitError("OpenAI rate limit exceeded")
                
                raise await self.handle_error(error_data, e.response.status_code)
    
    async def _complete_chat(self, client: httpx.AsyncClient, payload: Dict[str, Any]) -> ProviderResponse:
        """Handle non-streaming chat completion"""
        response = await client.post(
            f"{self.base_url}/chat/completions",
            headers=self.get_headers(),
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
        choice = data['choices'][0]
        return ProviderResponse(
            content=choice['message']['content'],
            usage=data.get('usage', {}),
            model=data.get('model'),
            finish_reason=choice.get('finish_reason')
        )
    
    async def _stream_chat(self, client: httpx.AsyncClient, payload: Dict[str, Any]) -> AsyncGenerator[StreamChunk, None]:
        """Handle streaming chat completion"""
        async with client.stream(
            "POST",
            f"{self.base_url}/chat/completions", 
            headers=self.get_headers(),
            json=payload
        ) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]  # Remove "data: " prefix
                    
                    if data == "[DONE]":
                        break
                    
                    try:
                        chunk_data = json.loads(data)
                        choice = chunk_data['choices'][0]
                        delta = choice.get('delta', {})
                        
                        if 'content' in delta:
                            yield StreamChunk(
                                delta=delta['content'],
                                finish_reason=choice.get('finish_reason')
                            )
                    except json.JSONDecodeError:
                        continue
    
    def normalize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize parameters for OpenAI"""
        normalized = super().normalize_params(params)
        
        # OpenAI specific parameters
        if 'presence_penalty' in params:
            normalized['presence_penalty'] = float(params['presence_penalty'])
        if 'frequency_penalty' in params:
            normalized['frequency_penalty'] = float(params['frequency_penalty'])
            
        return normalized