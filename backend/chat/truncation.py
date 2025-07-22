import tiktoken
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models.chat import ChatMessage, MessageRole
from ..config import ConfigManager
from ..utils.logging import get_logger


class ConversationTruncator:
    """Handles conversation truncation when token limits are exceeded"""
    
    def __init__(self):
        self.logger = get_logger("sourcerer.chat.truncation")
        self.config_manager = ConfigManager()
        
        # Token limits by provider
        self.provider_limits = {
            'openai': {
                'gpt-4': 8192,
                'gpt-4-32k': 32768,
                'gpt-3.5-turbo': 4096,
                'gpt-3.5-turbo-16k': 16384
            },
            'anthropic': {
                'claude-3-sonnet': 200000,
                'claude-3-haiku': 200000,
                'claude-3-opus': 200000
            },
            'moonshot': {
                'moonshot-v1-8k': 8192,
                'moonshot-v1-32k': 32768,
                'moonshot-v1-128k': 131072
            }
        }
        
        # Default limit if model not found
        self.default_limit = 4096
        
        # Reserve tokens for response and system prompt
        self.response_reserve = 1000
        self.system_reserve = 500
    
    async def truncate_if_needed(self, 
                                messages: List[ChatMessage], 
                                new_message_content: str) -> List[ChatMessage]:
        """Truncate conversation if needed to stay within token limits"""
        
        try:
            # Get current token limit
            token_limit = self._get_token_limit()
            available_tokens = token_limit - self.response_reserve - self.system_reserve
            
            # Count tokens in all messages including new one
            total_tokens = self._count_conversation_tokens(messages, new_message_content)
            
            if total_tokens <= available_tokens:
                # No truncation needed
                return messages
            
            self.logger.info(f"Conversation truncation needed: {total_tokens} > {available_tokens} tokens")
            
            # Perform truncation
            return await self._truncate_conversation(messages, available_tokens)
            
        except Exception as e:
            self.logger.error(f"Truncation failed: {e}")
            # Return original messages if truncation fails
            return messages
    
    def _get_token_limit(self) -> int:
        """Get token limit for active model"""
        try:
            active_provider = self.config_manager.config.active_provider
            active_model = self.config_manager.config.active_model
            
            if active_provider and active_model:
                provider_limits = self.provider_limits.get(active_provider, {})
                return provider_limits.get(active_model, self.default_limit)
            
            return self.default_limit
            
        except Exception as e:
            self.logger.warning(f"Failed to get token limit: {e}")
            return self.default_limit
    
    def _count_conversation_tokens(self, 
                                  messages: List[ChatMessage], 
                                  new_message_content: str = "") -> int:
        """Count total tokens in conversation"""
        
        try:
            # Get appropriate tokenizer
            encoding = self._get_encoding()
            
            total_tokens = 0
            
            # Count existing messages
            for message in messages:
                # Count content tokens
                total_tokens += len(encoding.encode(message.content))
                # Add overhead for role and formatting (approx 4 tokens per message)
                total_tokens += 4
            
            # Count new message if provided
            if new_message_content:
                total_tokens += len(encoding.encode(new_message_content))
                total_tokens += 4
            
            return total_tokens
            
        except Exception as e:
            self.logger.warning(f"Token counting failed, using character estimate: {e}")
            # Fallback: rough estimate (4 chars per token)
            char_count = sum(len(msg.content) for msg in messages)
            if new_message_content:
                char_count += len(new_message_content)
            return char_count // 4
    
    def _get_encoding(self):
        """Get appropriate tokenizer encoding"""
        try:
            active_provider = self.config_manager.config.active_provider
            
            if active_provider == 'openai':
                # Use cl100k_base for GPT-4 and GPT-3.5-turbo
                return tiktoken.get_encoding("cl100k_base")
            else:
                # Default to cl100k_base for other providers
                return tiktoken.get_encoding("cl100k_base")
                
        except Exception as e:
            self.logger.warning(f"Failed to get encoding: {e}")
            return tiktoken.get_encoding("cl100k_base")
    
    async def _truncate_conversation(self, 
                                   messages: List[ChatMessage], 
                                   target_tokens: int) -> List[ChatMessage]:
        """Truncate conversation to fit within token limit"""
        
        if not messages:
            return messages
        
        # Strategy: Keep the most recent messages and summarize older ones
        
        # Always keep the last few messages (recent context)
        min_keep_messages = 4
        
        if len(messages) <= min_keep_messages:
            return messages
        
        # Try to keep recent messages within token limit
        encoding = self._get_encoding()
        recent_messages = []
        recent_tokens = 0
        
        # Work backwards from the most recent messages
        for i in range(len(messages) - 1, -1, -1):
            message = messages[i]
            message_tokens = len(encoding.encode(message.content)) + 4
            
            if recent_tokens + message_tokens <= target_tokens * 0.7:  # Use 70% for recent messages
                recent_messages.insert(0, message)
                recent_tokens += message_tokens
            else:
                break
        
        # If we kept too few messages, just return the most recent ones
        if len(recent_messages) < min_keep_messages:
            return messages[-min_keep_messages:]
        
        # Summarize older messages if any
        older_messages = messages[:len(messages) - len(recent_messages)]
        
        if older_messages:
            summary_message = await self._create_conversation_summary(older_messages)
            if summary_message:
                return [summary_message] + recent_messages
        
        return recent_messages
    
    async def _create_conversation_summary(self, messages: List[ChatMessage]) -> Optional[ChatMessage]:
        """Create a summary of older conversation messages"""
        
        try:
            if not messages:
                return None
            
            # Extract key points from the conversation
            conversation_text = ""
            for msg in messages:
                role_prefix = "User: " if msg.role == MessageRole.USER else "Assistant: "
                conversation_text += f"{role_prefix}{msg.content}\n\n"
            
            # Create summary using LLM (if available)
            summary_content = await self._generate_summary(conversation_text)
            
            if not summary_content:
                # Fallback: simple truncation summary
                summary_content = f"[Conversation summary: {len(messages)} earlier messages from {messages[0].timestamp.strftime('%Y-%m-%d %H:%M')} to {messages[-1].timestamp.strftime('%Y-%m-%d %H:%M')}]"
            
            # Create summary message
            summary_message = ChatMessage(
                id=f"summary_{datetime.now().isoformat()}",
                role=MessageRole.SYSTEM,
                content=summary_content,
                timestamp=datetime.now(),
                metadata={'is_summary': True, 'summarized_count': len(messages)}
            )
            
            self.logger.info(f"Created conversation summary for {len(messages)} messages")
            return summary_message
            
        except Exception as e:
            self.logger.error(f"Failed to create conversation summary: {e}")
            return None
    
    async def _generate_summary(self, conversation_text: str) -> Optional[str]:
        """Generate LLM-based summary of conversation"""
        
        try:
            from ..providers import get_provider_adapter
            
            if not self.config_manager.config.active_provider:
                return None
            
            # Get provider adapter
            provider_config = self.config_manager.config.providers[self.config_manager.config.active_provider]
            api_key = self.config_manager.get_provider_api_key(self.config_manager.config.active_provider)
            adapter = get_provider_adapter(self.config_manager.config.active_provider, provider_config, api_key)
            
            # Create summary prompt
            summary_prompt = f"""Please create a concise summary of this conversation that captures the key topics, decisions, and context that would be important for continuing the discussion:

{conversation_text[:2000]}  # Limit input to prevent token overflow

Provide a summary in 2-3 sentences that maintains the essential context."""

            messages = [
                {'role': 'system', 'content': 'You are a helpful assistant that creates concise conversation summaries.'},
                {'role': 'user', 'content': summary_prompt}
            ]
            
            # Generate summary with minimal parameters
            response = await adapter.chat(
                messages=messages,
                model=self.config_manager.config.active_model,
                params={
                    'temperature': 0.1,
                    'max_tokens': 200
                },
                stream=False
            )
            
            return f"[Previous conversation summary: {response.content.strip()}]"
            
        except Exception as e:
            self.logger.warning(f"LLM summary generation failed: {e}")
            return None
    
    def get_truncation_stats(self) -> Dict[str, Any]:
        """Get truncation configuration and stats"""
        
        return {
            'token_limit': self._get_token_limit(),
            'response_reserve': self.response_reserve,
            'system_reserve': self.system_reserve,
            'available_tokens': self._get_token_limit() - self.response_reserve - self.system_reserve,
            'active_provider': self.config_manager.config.active_provider,
            'active_model': self.config_manager.config.active_model
        }