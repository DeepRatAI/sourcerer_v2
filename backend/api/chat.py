from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional

from ..models.api import APIResponse
from ..models.chat import SendMessageRequest, ChatResponse, ChatSession
from ..chat import ChatManager
from ..utils.logging import get_logger

router = APIRouter()
logger = get_logger("sourcerer.api.chat")


def get_chat_manager() -> ChatManager:
    """Get chat manager dependency"""
    return ChatManager()


@router.get("/sessions")
async def list_chat_sessions(
    limit: int = Query(50, ge=1, le=100),
    archived: bool = Query(False),
    chat_manager: ChatManager = Depends(get_chat_manager)
):
    """List all chat sessions"""
    try:
        sessions = chat_manager.list_sessions(limit=limit, archived=archived)
        return APIResponse(data={
            "sessions": sessions,
            "count": len(sessions)
        })
    except Exception as e:
        logger.error(f"Failed to list chat sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list chat sessions: {e}")


@router.post("/sessions")
async def create_chat_session(
    title: Optional[str] = None,
    chat_manager: ChatManager = Depends(get_chat_manager)
):
    """Create a new chat session"""
    try:
        session = chat_manager.create_session(title=title)
        return APIResponse(data=session.model_dump())
    except Exception as e:
        logger.error(f"Failed to create chat session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {e}")


@router.get("/sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    chat_manager: ChatManager = Depends(get_chat_manager)
):
    """Get chat session details"""
    try:
        session = chat_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return APIResponse(data=session.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chat session: {e}")


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: Optional[int] = Query(None, ge=1),
    offset: int = Query(0, ge=0),
    chat_manager: ChatManager = Depends(get_chat_manager)
):
    """Get messages from a chat session"""
    try:
        messages = chat_manager.get_session_messages(
            session_id=session_id,
            limit=limit,
            offset=offset
        )
        
        return APIResponse(data={
            "messages": [msg.model_dump() for msg in messages],
            "count": len(messages)
        })
        
    except Exception as e:
        logger.error(f"Failed to get session messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session messages: {e}")


@router.post("/messages")
async def send_message(
    request: SendMessageRequest,
    chat_manager: ChatManager = Depends(get_chat_manager)
):
    """Send a message (creates new session if session_id is None)"""
    try:
        response_data = await chat_manager.send_message(request)
        return APIResponse(data=response_data)
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {e}")


@router.post("/sessions/{session_id}/messages")
async def send_message_to_session(
    session_id: str,
    request: SendMessageRequest,
    chat_manager: ChatManager = Depends(get_chat_manager)
):
    """Send a message to a specific chat session"""
    try:
        # Override session_id from URL
        request.session_id = session_id
        response_data = await chat_manager.send_message(request)
        return APIResponse(data=response_data)
    except Exception as e:
        logger.error(f"Failed to send message to session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {e}")


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    chat_manager: ChatManager = Depends(get_chat_manager)
):
    """Delete chat session"""
    try:
        success = chat_manager.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return APIResponse(data={"message": f"Session {session_id} deleted successfully"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete chat session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete chat session: {e}")


@router.post("/sessions/{session_id}/archive")
async def archive_chat_session(
    session_id: str,
    chat_manager: ChatManager = Depends(get_chat_manager)
):
    """Archive chat session"""
    try:
        success = chat_manager.archive_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return APIResponse(data={"message": f"Session {session_id} archived successfully"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to archive chat session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to archive chat session: {e}")


@router.get("/stats")
async def get_chat_stats(
    chat_manager: ChatManager = Depends(get_chat_manager)
):
    """Get chat system statistics"""
    try:
        stats = chat_manager.get_chat_statistics()
        return APIResponse(data=stats)
    except Exception as e:
        logger.error(f"Failed to get chat statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chat statistics: {e}")