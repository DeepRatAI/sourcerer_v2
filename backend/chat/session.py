import uuid
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from pathlib import Path

from ..models.chat import ChatSession, ChatMessage, MessageRole, SendMessageRequest, ChatResponse
from ..utils.file_utils import safe_write_json, safe_read_json, append_jsonl, read_jsonl
from ..utils.logging import get_logger
from ..providers import get_provider_adapter
from ..config import ConfigManager
from .truncation import ConversationTruncator


class ChatSessionHandler:
    """Handles individual chat session operations"""
    
    def __init__(self, session_id: str, session_dir: Path):
        self.session_id = session_id
        self.session_dir = session_dir
        self.messages_file = session_dir / "messages.jsonl"
        self.metadata_file = session_dir / "metadata.json"
        
        self.logger = get_logger(f"sourcerer.chat.session.{session_id}")
        self.config_manager = ConfigManager()
        self.truncator = ConversationTruncator()
        
        # Message cache
        self._cached_messages: Optional[List[ChatMessage]] = None
        self._cache_dirty = False
    
    def save_session_metadata(self, session: ChatSession):
        """Save session metadata"""
        try:
            metadata = {
                'id': session.id,
                'title': session.title,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat(),
                'total_tokens': session.total_tokens,
                'archived': session.archived,
                'context_sources': session.context_sources
            }
            
            safe_write_json(metadata, self.metadata_file)
            self.logger.debug(f"Saved session metadata for {self.session_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to save session metadata: {e}")
            raise
    
    def get_session_metadata(self) -> Optional[ChatSession]:
        """Load session metadata"""
        try:
            if not self.metadata_file.exists():
                return None
            
            metadata = safe_read_json(self.metadata_file)
            if not metadata:
                return None
            
            return ChatSession(
                id=metadata['id'],
                title=metadata.get('title', f'Chat {self.session_id}'),
                created_at=datetime.fromisoformat(metadata['created_at']),
                updated_at=datetime.fromisoformat(metadata['updated_at']),
                total_tokens=metadata.get('total_tokens', 0),
                archived=metadata.get('archived', False),
                context_sources=metadata.get('context_sources', [])
            )
            
        except Exception as e:
            self.logger.error(f"Failed to load session metadata: {e}")
            return None
    
    def add_message(self, message: ChatMessage):
        """Add a message to the session"""
        try:
            # Add to JSONL file
            message_data = {
                'id': message.id,
                'role': message.role.value,
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
                'provider': message.provider,
                'model': message.model,
                'usage': message.usage,
                'metadata': message.metadata
            }
            
            append_jsonl(message_data, self.messages_file)
            
            # Invalidate cache
            self._cached_messages = None
            self._cache_dirty = True
            
            self.logger.debug(f"Added {message.role.value} message to session {self.session_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to add message: {e}")
            raise
    
    def get_messages(self, limit: Optional[int] = None, offset: int = 0) -> List[ChatMessage]:
        """Get messages from the session"""
        try:
            if self._cached_messages is None or self._cache_dirty:
                self._load_messages()
            
            messages = self._cached_messages or []
            
            # Apply offset and limit
            if offset > 0:
                messages = messages[offset:]
            
            if limit is not None:
                messages = messages[:limit]
            
            return messages
            
        except Exception as e:
            self.logger.error(f"Failed to get messages: {e}")
            return []
    
    def _load_messages(self):
        """Load messages from JSONL file"""
        try:
            if not self.messages_file.exists():
                self._cached_messages = []
                return
            
            messages_data = read_jsonl(self.messages_file)
            messages = []
            
            for msg_data in messages_data:
                try:
                    message = ChatMessage(
                        id=msg_data.get('id', str(uuid.uuid4())),
                        role=MessageRole(msg_data['role']),
                        content=msg_data['content'],
                        timestamp=datetime.fromisoformat(msg_data['timestamp']),
                        provider=msg_data.get('provider'),
                        model=msg_data.get('model'),
                        usage=msg_data.get('usage'),
                        metadata=msg_data.get('metadata', {})
                    )
                    messages.append(message)
                except Exception as e:
                    self.logger.warning(f"Failed to parse message: {e}")
                    continue
            
            self._cached_messages = messages
            self._cache_dirty = False
            
            self.logger.debug(f"Loaded {len(messages)} messages for session {self.session_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to load messages: {e}")
            self._cached_messages = []
    
    async def process_message(self, request: SendMessageRequest) -> Dict[str, Any]:
        """Process a user message and generate response"""
        try:
            self.logger.info(f"Processing message in session {self.session_id}")
            
            # Create user message
            user_message = ChatMessage(
                id=str(uuid.uuid4()),
                role=MessageRole.USER,
                content=request.content,
                timestamp=datetime.now()
            )
            
            # Add user message
            self.add_message(user_message)
            
            # Get conversation context
            context_items = []
            if request.include_sources:
                context_items = await self._get_context_items(request.content, request.max_context_items)
            
            # Get conversation history
            conversation_history = self.get_messages()
            
            # Check if truncation is needed
            truncated_history = await self.truncator.truncate_if_needed(conversation_history, request.content)
            
            if len(truncated_history) < len(conversation_history):
                # Save truncated conversation
                await self._save_truncated_conversation(truncated_history)
                self.logger.info(f"Conversation truncated: {len(conversation_history)} -> {len(truncated_history)} messages")
            
            # Prepare messages for LLM
            llm_messages = self._prepare_llm_messages(truncated_history, context_items)
            
            # Generate response
            response_content, usage_info = await self._generate_response(llm_messages)
            
            # Create assistant message
            assistant_message = ChatMessage(
                id=str(uuid.uuid4()),
                role=MessageRole.ASSISTANT,
                content=response_content,
                timestamp=datetime.now(),
                provider=self.config_manager.config.active_provider,
                model=self.config_manager.config.active_model,
                usage=usage_info,
                metadata={'context_items': len(context_items)}
            )
            
            # Add assistant message
            self.add_message(assistant_message)
            
            # Update session metadata
            await self._update_session_metadata(usage_info, context_items)
            
            # Prepare response
            response_data = {
                'message': assistant_message.model_dump(),
                'session_id': self.session_id,
                'context_items': [item.get('title', 'Unknown') for item in context_items],
                'total_tokens_used': usage_info.get('total_tokens', 0) if usage_info else 0
            }
            
            return response_data
            
        except Exception as e:
            self.logger.error(f"Failed to process message: {e}")
            raise
    
    async def _get_context_items(self, query: str, max_items: int) -> List[Dict[str, Any]]:
        """Get relevant context items using RAG"""
        try:
            from ..rag import RAGEngine
            
            rag_engine = RAGEngine()
            context_items = await rag_engine.search_similar_content(
                query=query,
                max_results=max_items,
                min_similarity=0.3
            )
            
            return context_items
            
        except Exception as e:
            self.logger.warning(f"Failed to get context items: {e}")
            return []
    
    def _prepare_llm_messages(self, 
                             conversation_history: List[ChatMessage],
                             context_items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Prepare messages for LLM"""
        
        messages = []
        
        # Add system prompt with context
        system_prompt = self.config_manager.config.inference_defaults.system_prompt
        
        if context_items:
            context_text = self._format_context_items(context_items)
            system_prompt += f"\n\nRelevant context from your knowledge base:\n{context_text}"
        
        messages.append({
            'role': 'system',
            'content': system_prompt
        })
        
        # Add conversation history
        for msg in conversation_history:
            if msg.role in [MessageRole.USER, MessageRole.ASSISTANT]:
                messages.append({
                    'role': msg.role.value,
                    'content': msg.content
                })
        
        return messages
    
    def _format_context_items(self, context_items: List[Dict[str, Any]]) -> str:
        """Format context items for LLM prompt"""
        
        if not context_items:
            return ""
        
        context_parts = []
        for i, item in enumerate(context_items[:3], 1):  # Limit to 3 items
            context_part = f"\nSource {i}:"
            
            if item.get('title'):
                context_part += f"\nTitle: {item['title']}"
            
            if item.get('url'):
                context_part += f"\nURL: {item['url']}"
            
            content = item.get('content') or item.get('summary')
            if content:
                # Truncate content
                if len(content) > 300:
                    content = content[:300] + "..."
                context_part += f"\nContent: {content}"
            
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    async def _generate_response(self, messages: List[Dict[str, str]]) -> tuple[str, Optional[Dict[str, int]]]:
        """Generate response using active LLM provider"""
        
        try:
            if not self.config_manager.config.active_provider:
                raise ValueError("No active provider configured")
            
            # Get provider adapter
            provider_config = self.config_manager.config.providers[self.config_manager.config.active_provider]
            api_key = self.config_manager.get_provider_api_key(self.config_manager.config.active_provider)
            adapter = get_provider_adapter(self.config_manager.config.active_provider, provider_config, api_key)
            
            # Get inference parameters
            inference_params = self.config_manager.config.inference_defaults.model_dump()
            inference_params.pop('system_prompt', None)  # Already included in messages
            inference_params.pop('stop', None)  # Handle separately
            
            if self.config_manager.config.inference_defaults.stop:
                inference_params['stop'] = self.config_manager.config.inference_defaults.stop
            
            # Generate response
            response = await adapter.chat(
                messages=messages,
                model=self.config_manager.config.active_model,
                params=inference_params,
                stream=False  # TODO: Implement streaming support
            )
            
            return response.content, response.usage
            
        except Exception as e:
            self.logger.error(f"Failed to generate response: {e}")
            raise
    
    async def _save_truncated_conversation(self, truncated_messages: List[ChatMessage]):
        """Save truncated conversation back to file"""
        try:
            # Backup original file
            if self.messages_file.exists():
                backup_file = self.messages_file.with_suffix('.jsonl.bak')
                import shutil
                shutil.copy2(self.messages_file, backup_file)
            
            # Rewrite messages file with truncated conversation
            with open(self.messages_file, 'w') as f:
                for message in truncated_messages:
                    message_data = {
                        'id': message.id,
                        'role': message.role.value,
                        'content': message.content,
                        'timestamp': message.timestamp.isoformat(),
                        'provider': message.provider,
                        'model': message.model,
                        'usage': message.usage,
                        'metadata': message.metadata
                    }
                    import json
                    f.write(json.dumps(message_data, default=str) + '\n')
            
            # Update cache
            self._cached_messages = truncated_messages
            self._cache_dirty = False
            
            self.logger.info(f"Saved truncated conversation with {len(truncated_messages)} messages")
            
        except Exception as e:
            self.logger.error(f"Failed to save truncated conversation: {e}")
    
    async def _update_session_metadata(self, usage_info: Optional[Dict[str, int]], context_items: List[Dict[str, Any]]):
        """Update session metadata after processing message"""
        try:
            session = self.get_session_metadata()
            if not session:
                return
            
            # Update token count
            if usage_info and 'total_tokens' in usage_info:
                session.total_tokens += usage_info['total_tokens']
            
            # Update timestamp
            session.updated_at = datetime.now()
            
            # Update context sources
            for item in context_items:
                source_id = item.get('source_id')
                if source_id and source_id not in session.context_sources:
                    session.context_sources.append(source_id)
            
            # Save updated metadata
            self.save_session_metadata(session)
            
        except Exception as e:
            self.logger.error(f"Failed to update session metadata: {e}")