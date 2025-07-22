import json
import httpx
from typing import List, Dict, Any, Union, AsyncGenerator
from .base import ProviderAdapter, AuthenticationError, RateLimitError
from ..models.provider import ProviderResponse, StreamChunk, ModelInfo
from ..utils.logging import get_logger


class AnthropicProvider(ProviderAdapter):
    """Anthropic provider adapter"""
    
    def __init__(self, name: str, api_key: str, **kwargs):
        base_url = kwargs.get('base_url', 'https://api.anthropic.com/v1')
        super().__init__(name, base_url, api_key, **kwargs)
        self.auth_header = 'x-api-key'
        self.auth_prefix = ''
        self.logger = get_logger(f"sourcerer.providers.{name}")
        
        # Anthropic models (static list since they don't have a models endpoint)
        self.available_models = [
            ModelInfo(id="claude-3-opus-20240229", name="Claude 3 Opus", supports_streaming=True),
            ModelInfo(id="claude-3-sonnet-20240229", name="Claude 3 Sonnet", supports_streaming=True),
            ModelInfo(id="claude-3-haiku-20240307", name="Claude 3 Haiku", supports_streaming=True),
            ModelInfo(id="claude-3-5-sonnet-20241022", name="Claude 3.5 Sonnet", supports_streaming=True),
        ]
    
    async def list_models(self) -> List[ModelInfo]:
        """List available models from Anthropic (static list)"""
        self.logger.info(f"Returning {len(self.available_models)} static models")
        return self.available_models
    
    async def test_auth(self) -> bool:
        """Test authentication with Anthropic by making a minimal request"""
        try:
            # Make a minimal chat request to test auth
            test_messages = [{"role": "user", "content": "Hello"}]
            await self.chat(
                messages=test_messages,
                model="claude-3-haiku-20240307",
                params={"max_tokens": 1},
                stream=False
            )
            return True
        except AuthenticationError:
            return False
        except Exception as e:
            self.logger.warning(f"Auth test failed with non-auth error: {e}")
            return False
    
    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        model: str,
        params: Dict[str, Any],
        stream: bool = False
    ) -> Union[ProviderResponse, AsyncGenerator[StreamChunk, None]]:
        """Send chat completion request to Anthropic"""
        
        normalized_messages = self.normalize_messages(messages)
        normalized_params = self.normalize_params(params)
        
        # Anthropic requires max_tokens
        if 'max_tokens' not in normalized_params:
            normalized_params['max_tokens'] = 1024
        
        payload = {
            "model": model,
            "messages": normalized_messages,
            "stream": stream,
            **normalized_params
        }
        
        # Handle system prompt (Anthropic uses separate system parameter)
        system_prompt = params.get('system_prompt')
        if system_prompt:
            payload["system"] = system_prompt
            # Remove system messages from messages array
            payload["messages"] = [msg for msg in normalized_messages if msg.get('role') != 'system']
        
        headers = self.get_headers({
            'anthropic-version': '2023-06-01'
        })
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                if stream:
                    return self._stream_chat(client, payload, headers)
                else:
                    return await self._complete_chat(client, payload, headers)
                    
            except httpx.HTTPStatusError as e:
                error_data = {}
                try:
                    error_data = e.response.json()
                except:
                    pass
                
                if e.response.status_code == 401:
                    raise AuthenticationError("Invalid Anthropic API key")
                elif e.response.status_code == 429:
                    raise RateLimitError("Anthropic rate limit exceeded")
                
                raise await self.handle_error(error_data, e.response.status_code)
    
    async def _complete_chat(self, client: httpx.AsyncClient, payload: Dict[str, Any], headers: Dict[str, str]) -> ProviderResponse:
        """Handle non-streaming chat completion"""
        response = await client.post(
            f"{self.base_url}/messages",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
        content = ""
        if data.get('content'):
            # Anthropic returns content as an array
            content = "".join([block.get('text', '') for block in data['content'] if block.get('type') == 'text'])
        
        return ProviderResponse(
            content=content,
            usage=data.get('usage', {}),
            model=data.get('model'),
            finish_reason=data.get('stop_reason')
        )
    
    async def _stream_chat(self, client: httpx.AsyncClient, payload: Dict[str, Any], headers: Dict[str, str]) -> AsyncGenerator[StreamChunk, None]:
        """Handle streaming chat completion"""
        async with client.stream(
            "POST",
            f"{self.base_url}/messages",
            headers=headers,
            json=payload
        ) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]  # Remove "data: " prefix
                    
                    try:
                        chunk_data = json.loads(data)
                        
                        if chunk_data.get('type') == 'content_block_delta':
                            delta_data = chunk_data.get('delta', {})
                            if delta_data.get('type') == 'text_delta':
                                yield StreamChunk(
                                    delta=delta_data.get('text', ''),
                                    finish_reason=None
                                )
                        elif chunk_data.get('type') == 'message_stop':
                            yield StreamChunk(
                                delta="",
                                finish_reason=chunk_data.get('stop_reason')
                            )
                    except json.JSONDecodeError:
                        continue
    
    def normalize_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Normalize messages for Anthropic format"""
        normalized = []
        
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            # Anthropic doesn't use 'system' role in messages
            if role == 'system':
                continue
                
            # Map 'assistant' to 'assistant'
            if role not in ['user', 'assistant']:
                role = 'user'
            
            normalized.append({
                'role': role,
                'content': content
            })
        
        return normalized
    
    def normalize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize parameters for Anthropic"""
        normalized = {}
        
        # Anthropic supported parameters
        if 'temperature' in params:
            normalized['temperature'] = float(params['temperature'])
        if 'top_p' in params:
            normalized['top_p'] = float(params['top_p'])
        if 'max_tokens' in params:
            normalized['max_tokens'] = int(params['max_tokens'])
        if 'stop' in params and params['stop']:
            normalized['stop_sequences'] = params['stop']
        
        # Anthropic doesn't support presence_penalty or frequency_penalty
        
        return normalized