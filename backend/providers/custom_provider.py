import json
import httpx
from typing import List, Dict, Any, Union, AsyncGenerator
from .base import ProviderAdapter, AuthenticationError, RateLimitError
from ..models.provider import ProviderResponse, StreamChunk, ModelInfo
from ..utils.logging import get_logger


class CustomProvider(ProviderAdapter):
    """Custom provider adapter for arbitrary OpenAI-compatible APIs"""
    
    def __init__(self, name: str, api_key: str, **kwargs):
        super().__init__(name, kwargs.get('base_url', ''), api_key, **kwargs)
        self.logger = get_logger(f"sourcerer.providers.{name}")
        
        # Custom provider configuration
        self.models_endpoint = kwargs.get('models_endpoint', '/models')
        self.models_json_path = kwargs.get('models_json_path', 'data[].id')
        self.default_model = kwargs.get('default_model')
        self.payload_schema = kwargs.get('payload_schema', 'openai_chat')
        self.test_prompt = kwargs.get('test_prompt', 'Hello')
        
    async def list_models(self) -> List[ModelInfo]:
        """List available models from custom provider"""
        if not self.models_endpoint:
            # No models endpoint, use default model if provided
            if self.default_model:
                return [ModelInfo(id=self.default_model, name=self.default_model)]
            else:
                return []
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}{self.models_endpoint}",
                    headers=self.get_headers()
                )
                response.raise_for_status()
                data = response.json()
                
                models = self._extract_models_from_response(data)
                self.logger.info(f"Found {len(models)} models from custom provider")
                return models
                
        except Exception as e:
            self.logger.warning(f"Failed to fetch models from custom provider: {e}")
            # Fall back to default model if available
            if self.default_model:
                return [ModelInfo(id=self.default_model, name=self.default_model)]
            else:
                return []
    
    def _extract_models_from_response(self, data: Dict[str, Any]) -> List[ModelInfo]:
        """Extract model IDs from API response using JSON path"""
        models = []
        
        try:
            # Parse simple JSON paths like "data[].id", "models[].name", etc.
            path_parts = self.models_json_path.split('.')
            current_data = data
            
            for part in path_parts:
                if part.endswith('[]'):
                    # Array access
                    key = part[:-2]
                    if key in current_data and isinstance(current_data[key], list):
                        current_data = current_data[key]
                    else:
                        return models
                else:
                    # Object access
                    if isinstance(current_data, list):
                        # Extract field from each item in array
                        extracted = []
                        for item in current_data:
                            if isinstance(item, dict) and part in item:
                                extracted.append(item[part])
                        current_data = extracted
                    elif isinstance(current_data, dict) and part in current_data:
                        current_data = current_data[part]
                    else:
                        return models
            
            # Convert final data to ModelInfo objects
            if isinstance(current_data, list):
                for item in current_data:
                    if isinstance(item, str):
                        models.append(ModelInfo(id=item, name=item))
                    elif isinstance(item, dict) and 'id' in item:
                        models.append(ModelInfo(
                            id=item['id'],
                            name=item.get('name', item['id']),
                            supports_streaming=item.get('supports_streaming', True)
                        ))
            
        except Exception as e:
            self.logger.warning(f"Failed to parse models from response: {e}")
        
        return models
    
    async def test_auth(self) -> bool:
        """Test authentication with custom provider"""
        try:
            if self.models_endpoint:
                # Test by listing models
                models = await self.list_models()
                return len(models) > 0
            elif self.default_model and self.test_prompt:
                # Test by making a small inference request
                await self.chat(
                    messages=[{"role": "user", "content": self.test_prompt}],
                    model=self.default_model,
                    params={"max_tokens": 1},
                    stream=False
                )
                return True
            else:
                # No way to test, assume valid
                return True
                
        except AuthenticationError:
            return False
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
        """Send chat completion request to custom provider"""
        
        if self.payload_schema == 'openai_chat':
            return await self._openai_chat(messages, model, params, stream)
        elif self.payload_schema == 'hf_text':
            return await self._hf_text_generation(messages, model, params, stream)
        elif self.payload_schema == 'raw_json':
            return await self._raw_json(messages, model, params, stream)
        else:
            raise Exception(f"Unsupported payload schema: {self.payload_schema}")
    
    async def _openai_chat(
        self, 
        messages: List[Dict[str, str]], 
        model: str,
        params: Dict[str, Any],
        stream: bool = False
    ) -> Union[ProviderResponse, AsyncGenerator[StreamChunk, None]]:
        """Handle OpenAI-compatible chat format"""
        
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
                    return self._stream_openai_chat(client, payload)
                else:
                    return await self._complete_openai_chat(client, payload)
                    
            except httpx.HTTPStatusError as e:
                error_data = {}
                try:
                    error_data = e.response.json()
                except:
                    pass
                
                if e.response.status_code == 401:
                    raise AuthenticationError("Invalid API key for custom provider")
                elif e.response.status_code == 429:
                    raise RateLimitError("Rate limit exceeded for custom provider")
                
                raise await self.handle_error(error_data, e.response.status_code)
    
    async def _complete_openai_chat(self, client: httpx.AsyncClient, payload: Dict[str, Any]) -> ProviderResponse:
        """Handle non-streaming OpenAI-compatible chat completion"""
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
    
    async def _stream_openai_chat(self, client: httpx.AsyncClient, payload: Dict[str, Any]) -> AsyncGenerator[StreamChunk, None]:
        """Handle streaming OpenAI-compatible chat completion"""
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
    
    async def _hf_text_generation(
        self, 
        messages: List[Dict[str, str]], 
        model: str,
        params: Dict[str, Any],
        stream: bool = False
    ) -> ProviderResponse:
        """Handle HuggingFace text generation format"""
        # Convert messages to prompt
        prompt = self._messages_to_prompt(messages, params.get('system_prompt'))
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": params.get('max_tokens', 512),
                "temperature": params.get('temperature', 0.7),
                "top_p": params.get('top_p', 1.0),
            }
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/generate",
                headers=self.get_headers(),
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            content = ""
            if isinstance(data, list) and len(data) > 0:
                content = data[0].get('generated_text', '')
            
            # Remove original prompt if it's included
            if content.startswith(prompt):
                content = content[len(prompt):].strip()
            
            return ProviderResponse(
                content=content,
                usage={},
                model=model,
                finish_reason="stop"
            )
    
    async def _raw_json(
        self, 
        messages: List[Dict[str, str]], 
        model: str,
        params: Dict[str, Any],
        stream: bool = False
    ) -> ProviderResponse:
        """Handle raw JSON format (custom implementation)"""
        # This would be highly customized based on the specific API
        payload = {
            "messages": messages,
            "model": model,
            **params
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/generate",
                headers=self.get_headers(),
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract content based on common response patterns
            content = (
                data.get('response') or
                data.get('text') or
                data.get('content') or
                str(data)
            )
            
            return ProviderResponse(
                content=content,
                usage=data.get('usage', {}),
                model=model,
                finish_reason="stop"
            )
    
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
        
        return "\n".join(prompt_parts)