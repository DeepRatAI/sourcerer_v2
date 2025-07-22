import json
import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from ..config.paths import get_chats_dir
from ..models.chat import ChatSession, ChatMessage, MessageRole, SendMessageRequest
from ..utils.file_utils import ensure_directory, safe_write_json, safe_read_json, append_jsonl, read_jsonl
from ..utils.logging import get_logger
from .session import ChatSessionHandler


class ChatManager:
    """Manages chat sessions and message persistence"""
    
    def __init__(self):
        self.logger = get_logger("sourcerer.chat.manager")
        self.chats_dir = get_chats_dir()
        ensure_directory(self.chats_dir)
        self.sessions_index_file = self.chats_dir / "session_index.json"
        
        # In-memory session handlers cache
        self._session_handlers: Dict[str, ChatSessionHandler] = {}
        
        # Load existing sessions index
        self._load_sessions_index()
    
    def _load_sessions_index(self):
        """Load the sessions index"""
        try:
            if self.sessions_index_file.exists():
                index_data = safe_read_json(self.sessions_index_file)
                if index_data and 'sessions' in index_data:
                    self.logger.info(f"Loaded {len(index_data['sessions'])} chat sessions from index")
                else:
                    self.logger.info("No sessions index found, starting fresh")
            else:
                self.logger.info("No sessions index file found")
                
        except Exception as e:
            self.logger.error(f"Failed to load sessions index: {e}")
    
    def _save_sessions_index(self):
        """Save the sessions index"""
        try:
            sessions_info = []
            
            # Get session info from directories
            for session_dir in self.chats_dir.iterdir():
                if session_dir.is_dir() and session_dir.name != "archives":
                    try:
                        session_info = self._get_session_info(session_dir.name)
                        if session_info:
                            sessions_info.append(session_info)
                    except Exception as e:
                        self.logger.warning(f"Failed to get info for session {session_dir.name}: {e}")
            
            index_data = {
                'version': 1,
                'updated_at': datetime.now().isoformat(),
                'sessions': sessions_info
            }
            
            safe_write_json(index_data, self.sessions_index_file)
            self.logger.debug(f"Saved sessions index with {len(sessions_info)} sessions")
            
        except Exception as e:
            self.logger.error(f"Failed to save sessions index: {e}")
    
    def create_session(self, title: Optional[str] = None) -> ChatSession:
        """Create a new chat session"""
        try:
            session_id = str(uuid.uuid4())[:12]  # Shorter ID for readability
            
            session = ChatSession(
                id=session_id,
                title=title or f"Chat {session_id}",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Create session directory
            session_dir = self.chats_dir / session_id
            ensure_directory(session_dir)
            
            # Create session handler
            session_handler = ChatSessionHandler(session_id, session_dir)
            self._session_handlers[session_id] = session_handler
            
            # Save session metadata
            session_handler.save_session_metadata(session)
            
            # Update index
            self._save_sessions_index()
            
            self.logger.info(f"Created chat session: {session_id}")
            return session
            
        except Exception as e:
            self.logger.error(f"Failed to create chat session: {e}")
            raise
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get chat session by ID"""
        try:
            if session_id in self._session_handlers:
                return self._session_handlers[session_id].get_session_metadata()
            
            # Try to load from disk
            session_dir = self.chats_dir / session_id
            if session_dir.exists():
                session_handler = ChatSessionHandler(session_id, session_dir)
                session = session_handler.get_session_metadata()
                
                if session:
                    self._session_handlers[session_id] = session_handler
                    return session
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    def list_sessions(self, limit: int = 50, archived: bool = False) -> List[Dict[str, Any]]:
        """List chat sessions with basic info"""
        try:
            sessions = []
            search_dir = self.chats_dir / "archives" if archived else self.chats_dir
            
            if not search_dir.exists():
                return sessions
            
            for session_dir in search_dir.iterdir():
                if session_dir.is_dir() and session_dir.name != "archives":
                    try:
                        session_info = self._get_session_info(session_dir.name, archived=archived)
                        if session_info:
                            sessions.append(session_info)
                    except Exception as e:
                        self.logger.warning(f"Failed to get session info for {session_dir.name}: {e}")
            
            # Sort by updated_at (most recent first)
            sessions.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
            
            return sessions[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to list sessions: {e}")
            return []
    
    def _get_session_info(self, session_id: str, archived: bool = False) -> Optional[Dict[str, Any]]:
        """Get basic session information"""
        try:
            base_dir = self.chats_dir / "archives" if archived else self.chats_dir
            session_dir = base_dir / session_id
            
            if not session_dir.exists():
                return None
            
            # Load session metadata
            metadata_file = session_dir / "metadata.json"
            if metadata_file.exists():
                metadata = safe_read_json(metadata_file)
                if metadata:
                    # Count messages
                    messages_file = session_dir / "messages.jsonl"
                    message_count = 0
                    if messages_file.exists():
                        try:
                            with open(messages_file, 'r') as f:
                                message_count = sum(1 for line in f if line.strip())
                        except:
                            message_count = 0
                    
                    return {
                        'id': session_id,
                        'title': metadata.get('title', f'Chat {session_id}'),
                        'created_at': metadata.get('created_at'),
                        'updated_at': metadata.get('updated_at'),
                        'message_count': message_count,
                        'total_tokens': metadata.get('total_tokens', 0),
                        'archived': archived
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get session info for {session_id}: {e}")
            return None
    
    async def send_message(self, request: SendMessageRequest) -> Dict[str, Any]:
        """Send a message in a chat session"""
        try:
            # Get or create session
            session_id = request.session_id
            if not session_id:
                # Create new session
                session = self.create_session()
                session_id = session.id
            else:
                session = self.get_session(session_id)
                if not session:
                    raise ValueError(f"Session {session_id} not found")
            
            # Get session handler
            session_handler = self._session_handlers.get(session_id)
            if not session_handler:
                session_dir = self.chats_dir / session_id
                session_handler = ChatSessionHandler(session_id, session_dir)
                self._session_handlers[session_id] = session_handler
            
            # Process the message and get response
            response_data = await session_handler.process_message(request)
            
            # Update sessions index
            self._save_sessions_index()
            
            return response_data
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            raise
    
    def get_session_messages(self, 
                           session_id: str, 
                           limit: Optional[int] = None, 
                           offset: int = 0) -> List[ChatMessage]:
        """Get messages from a session"""
        try:
            session = self.get_session(session_id)
            if not session:
                return []
            
            session_handler = self._session_handlers.get(session_id)
            if not session_handler:
                session_dir = self.chats_dir / session_id
                session_handler = ChatSessionHandler(session_id, session_dir)
                self._session_handlers[session_id] = session_handler
            
            return session_handler.get_messages(limit=limit, offset=offset)
            
        except Exception as e:
            self.logger.error(f"Failed to get session messages: {e}")
            return []
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a chat session"""
        try:
            session_dir = self.chats_dir / session_id
            
            if session_dir.exists():
                import shutil
                shutil.rmtree(session_dir)
                
                # Remove from cache
                if session_id in self._session_handlers:
                    del self._session_handlers[session_id]
                
                # Update index
                self._save_sessions_index()
                
                self.logger.info(f"Deleted chat session: {session_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    def archive_session(self, session_id: str) -> bool:
        """Archive a chat session"""
        try:
            session_dir = self.chats_dir / session_id
            archives_dir = self.chats_dir / "archives"
            ensure_directory(archives_dir)
            
            if session_dir.exists():
                archived_path = archives_dir / session_id
                session_dir.rename(archived_path)
                
                # Remove from cache
                if session_id in self._session_handlers:
                    del self._session_handlers[session_id]
                
                # Update index
                self._save_sessions_index()
                
                self.logger.info(f"Archived chat session: {session_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to archive session {session_id}: {e}")
            return False
    
    def get_chat_statistics(self) -> Dict[str, Any]:
        """Get chat system statistics"""
        try:
            active_sessions = self.list_sessions(limit=1000, archived=False)
            archived_sessions = self.list_sessions(limit=1000, archived=True)
            
            total_messages = sum(s.get('message_count', 0) for s in active_sessions)
            total_tokens = sum(s.get('total_tokens', 0) for s in active_sessions)
            
            return {
                'active_sessions': len(active_sessions),
                'archived_sessions': len(archived_sessions),
                'total_sessions': len(active_sessions) + len(archived_sessions),
                'total_messages': total_messages,
                'total_tokens': total_tokens,
                'recent_activity': active_sessions[:5]  # 5 most recent
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get chat statistics: {e}")
            return {}