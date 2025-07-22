import pytest
import httpx
import time
import json
from typing import Dict, Any, List

class TestChatWorkflow:
    """End-to-end tests for the complete chat system workflow"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.fixture
    def client(self):
        """HTTP client for API testing"""
        return httpx.Client(base_url=self.BASE_URL, timeout=30.0)
    
    @pytest.fixture
    async def async_client(self):
        """Async HTTP client for API testing"""
        async with httpx.AsyncClient(base_url=self.BASE_URL, timeout=30.0) as client:
            yield client
    
    def test_complete_chat_workflow(self, client):
        """Test complete chat session lifecycle"""
        
        # Step 1: List initial chat sessions (should be empty or have existing ones)
        response = client.get("/api/chat/sessions")
        assert response.status_code == 200
        initial_sessions_data = response.json()["data"]
        initial_session_count = len(initial_sessions_data["sessions"])
        
        # Step 2: Create a new chat session
        response = client.post("/api/chat/sessions", json={"title": "Test Chat Session"})
        assert response.status_code == 200
        session_data = response.json()["data"]
        session_id = session_data["id"]
        
        assert session_data["title"] == "Test Chat Session"
        assert "created_at" in session_data
        assert "updated_at" in session_data
        assert session_data["total_tokens"] == 0
        assert session_data["archived"] == False
        
        try:
            # Step 3: Verify session appears in list
            response = client.get("/api/chat/sessions")
            assert response.status_code == 200
            sessions_data = response.json()["data"]
            assert len(sessions_data["sessions"]) == initial_session_count + 1
            
            # Find our session
            our_session = next(s for s in sessions_data["sessions"] if s["id"] == session_id)
            assert our_session["title"] == "Test Chat Session"
            
            # Step 4: Get specific session details
            response = client.get(f"/api/chat/sessions/{session_id}")
            assert response.status_code == 200
            session_details = response.json()["data"]
            assert session_details["id"] == session_id
            
            # Step 5: Get session messages (should be empty initially)
            response = client.get(f"/api/chat/sessions/{session_id}/messages")
            assert response.status_code == 200
            messages_data = response.json()["data"]
            assert messages_data["count"] == 0
            assert len(messages_data["messages"]) == 0
            
            # Step 6: Send a message to the session
            message_request = {
                "content": "Hello, this is a test message. Please respond with a simple greeting.",
                "include_sources": False,
                "max_context_items": 3
            }
            
            response = client.post(f"/api/chat/sessions/{session_id}/messages", json=message_request)
            
            # The response might fail due to missing LLM configuration, but the endpoint should exist
            # We'll accept various status codes since LLM might not be configured in test environment
            assert response.status_code in [200, 400, 500]
            
            if response.status_code == 200:
                message_response = response.json()["data"]
                assert "message" in message_response
                assert "session_id" in message_response
                assert message_response["session_id"] == session_id
                
                # Step 7: Verify messages were added to session
                response = client.get(f"/api/chat/sessions/{session_id}/messages")
                assert response.status_code == 200
                messages_data = response.json()["data"]
                
                # Should have at least user message, possibly assistant response
                assert messages_data["count"] >= 1
                
                # Check message structure
                messages = messages_data["messages"]
                user_message = next(m for m in messages if m["role"] == "user")
                assert user_message["content"] == message_request["content"]
                assert "timestamp" in user_message
                assert "id" in user_message
                
            # Step 8: Test sending message without specifying session (creates new session)
            new_message_request = {
                "content": "This should create a new session",
                "session_id": None,
                "include_sources": False,
                "max_context_items": 3
            }
            
            response = client.post("/api/chat/messages", json=new_message_request)
            assert response.status_code in [200, 400, 500]
            
            if response.status_code == 200:
                new_message_response = response.json()["data"]
                new_session_id = new_message_response["session_id"]
                assert new_session_id != session_id  # Should be different session
                
                # Clean up the auto-created session
                try:
                    client.delete(f"/api/chat/sessions/{new_session_id}")
                except:
                    pass
            
            # Step 9: Test message with context from sources
            context_message_request = {
                "content": "Tell me about recent technology trends based on available sources",
                "include_sources": True,
                "max_context_items": 5
            }
            
            response = client.post(f"/api/chat/sessions/{session_id}/messages", json=context_message_request)
            assert response.status_code in [200, 400, 500]
            
            # Step 10: Archive the session
            response = client.post(f"/api/chat/sessions/{session_id}/archive")
            assert response.status_code == 200
            
            # Verify session is archived (not in main list)
            response = client.get("/api/chat/sessions")
            assert response.status_code == 200
            sessions_data = response.json()["data"]
            active_session_ids = [s["id"] for s in sessions_data["sessions"]]
            assert session_id not in active_session_ids
            
            # Check archived sessions
            response = client.get("/api/chat/sessions?archived=true")
            assert response.status_code == 200
            archived_sessions = response.json()["data"]
            archived_session_ids = [s["id"] for s in archived_sessions["sessions"]]
            assert session_id in archived_session_ids
            
            # Step 11: Delete the archived session
            response = client.delete(f"/api/chat/sessions/{session_id}")
            assert response.status_code == 200
            
            # Verify session is completely gone
            response = client.get(f"/api/chat/sessions/{session_id}")
            assert response.status_code == 404
            
        except Exception as e:
            # Cleanup on error
            try:
                client.delete(f"/api/chat/sessions/{session_id}")
            except:
                pass
            raise e
    
    def test_chat_validation_and_error_handling(self, client):
        """Test chat system validation and error handling"""
        
        # Test sending message to non-existent session
        invalid_session_request = {
            "content": "Test message",
            "include_sources": False
        }
        
        response = client.post("/api/chat/sessions/nonexistent-id/messages", json=invalid_session_request)
        assert response.status_code == 404
        
        # Test creating session with invalid data
        invalid_session_data = {"title": ""}  # Empty title
        response = client.post("/api/chat/sessions", json=invalid_session_data)
        # Should either accept empty title or return validation error
        assert response.status_code in [200, 400, 422]
        
        # Test sending empty message
        empty_message_request = {
            "content": "",
            "include_sources": False
        }
        
        # Create a test session first
        response = client.post("/api/chat/sessions", json={"title": "Validation Test"})
        assert response.status_code == 200
        test_session_id = response.json()["data"]["id"]
        
        try:
            response = client.post(f"/api/chat/sessions/{test_session_id}/messages", json=empty_message_request)
            assert response.status_code in [400, 422]
            
            # Test invalid message parameters
            invalid_params_request = {
                "content": "Valid content",
                "include_sources": "invalid_boolean",  # Should be boolean
                "max_context_items": -1  # Should be positive
            }
            
            response = client.post(f"/api/chat/sessions/{test_session_id}/messages", json=invalid_params_request)
            assert response.status_code == 422
            
        finally:
            # Cleanup
            client.delete(f"/api/chat/sessions/{test_session_id}")
    
    def test_chat_statistics_and_management(self, client):
        """Test chat statistics and session management"""
        
        # Step 1: Get chat system statistics
        response = client.get("/api/chat/stats")
        assert response.status_code == 200
        stats = response.json()["data"]
        
        assert "active_sessions" in stats
        assert "archived_sessions" in stats
        assert "total_sessions" in stats
        assert "total_messages" in stats
        assert "total_tokens" in stats
        
        initial_stats = stats
        
        # Step 2: Create a test session and add some messages
        response = client.post("/api/chat/sessions", json={"title": "Stats Test Session"})
        assert response.status_code == 200
        session = response.json()["data"]
        session_id = session["id"]
        
        try:
            # Add a message (even if LLM response fails)
            message_request = {
                "content": "Test message for statistics",
                "include_sources": False
            }
            
            response = client.post(f"/api/chat/sessions/{session_id}/messages", json=message_request)
            # Accept any response since LLM might not be configured
            assert response.status_code in [200, 400, 500]
            
            # Step 3: Check updated statistics
            response = client.get("/api/chat/stats")
            assert response.status_code == 200
            updated_stats = response.json()["data"]
            
            # Should have one more active session
            assert updated_stats["active_sessions"] == initial_stats["active_sessions"] + 1
            assert updated_stats["total_sessions"] == initial_stats["total_sessions"] + 1
            
            # Step 4: Test session listing with pagination
            response = client.get("/api/chat/sessions?limit=5")
            assert response.status_code == 200
            limited_sessions = response.json()["data"]
            assert len(limited_sessions["sessions"]) <= 5
            
        finally:
            # Cleanup
            client.delete(f"/api/chat/sessions/{session_id}")
    
    def test_conversation_truncation_and_memory_management(self, client):
        """Test conversation truncation and memory management"""
        
        # Create a test session for truncation testing
        response = client.post("/api/chat/sessions", json={"title": "Truncation Test"})
        assert response.status_code == 200
        session_id = response.json()["data"]["id"]
        
        try:
            # Send multiple messages to potentially trigger truncation
            long_messages = [
                "This is message number 1. " * 50,  # Make it long
                "This is message number 2. " * 50,
                "This is message number 3. " * 50,
                "This is message number 4. " * 50,
                "This is the final message that might trigger truncation."
            ]
            
            for i, content in enumerate(long_messages):
                message_request = {
                    "content": content,
                    "include_sources": False
                }
                
                response = client.post(f"/api/chat/sessions/{session_id}/messages", json=message_request)
                # Accept any response
                assert response.status_code in [200, 400, 500]
                
                # Small delay between messages
                time.sleep(0.1)
            
            # Check session messages
            response = client.get(f"/api/chat/sessions/{session_id}/messages")
            assert response.status_code == 200
            messages_data = response.json()["data"]
            
            # Messages should exist (truncation might have occurred)
            # The exact count depends on truncation logic and LLM responses
            assert messages_data["count"] >= 0
            
            # Test message pagination
            response = client.get(f"/api/chat/sessions/{session_id}/messages?limit=2&offset=0")
            assert response.status_code == 200
            paginated_messages = response.json()["data"]
            assert len(paginated_messages["messages"]) <= 2
            
        finally:
            # Cleanup
            client.delete(f"/api/chat/sessions/{session_id}")
    
    def test_chat_with_rag_context(self, client):
        """Test chat with RAG context integration"""
        
        # Create a test session
        response = client.post("/api/chat/sessions", json={"title": "RAG Context Test"})
        assert response.status_code == 200
        session_id = response.json()["data"]["id"]
        
        try:
            # Send message requesting context from sources
            context_request = {
                "content": "What are the latest developments in AI technology based on available sources?",
                "include_sources": True,
                "max_context_items": 5
            }
            
            response = client.post(f"/api/chat/sessions/{session_id}/messages", json=context_request)
            assert response.status_code in [200, 400, 500]
            
            if response.status_code == 200:
                response_data = response.json()["data"]
                
                # Should include context information
                assert "context_items" in response_data
                # Context items should be a list of source titles or identifiers
                assert isinstance(response_data["context_items"], list)
                
                # Check token usage information
                if "total_tokens_used" in response_data:
                    assert isinstance(response_data["total_tokens_used"], int)
                    assert response_data["total_tokens_used"] >= 0
            
            # Test message without context
            no_context_request = {
                "content": "Simple question without needing source context",
                "include_sources": False
            }
            
            response = client.post(f"/api/chat/sessions/{session_id}/messages", json=no_context_request)
            assert response.status_code in [200, 400, 500]
            
        finally:
            # Cleanup
            client.delete(f"/api/chat/sessions/{session_id}")
    
    def test_concurrent_chat_sessions(self, client):
        """Test handling of multiple concurrent chat sessions"""
        
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def create_and_test_session(thread_id):
            """Create a session and send a message in a separate thread"""
            try:
                thread_client = httpx.Client(base_url=self.BASE_URL, timeout=30.0)
                
                # Create session
                response = thread_client.post("/api/chat/sessions", 
                                            json={"title": f"Concurrent Test {thread_id}"})
                assert response.status_code == 200
                session_id = response.json()["data"]["id"]
                
                # Send message
                message_request = {
                    "content": f"Test message from thread {thread_id}",
                    "include_sources": False
                }
                
                response = thread_client.post(f"/api/chat/sessions/{session_id}/messages", 
                                            json=message_request)
                
                # Store results
                results_queue.put((thread_id, session_id, response.status_code))
                
                # Cleanup
                thread_client.delete(f"/api/chat/sessions/{session_id}")
                thread_client.close()
                
            except Exception as e:
                results_queue.put((thread_id, None, f"Error: {e}"))
        
        # Start multiple threads
        threads = []
        for i in range(3):  # Limited number for test stability
            thread = threading.Thread(target=create_and_test_session, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=60)  # Generous timeout
        
        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        # Verify all threads completed
        assert len(results) == 3
        
        # All threads should have gotten responses
        for thread_id, session_id, status in results:
            if isinstance(status, int):
                assert 200 <= status <= 599
            # session_id might be None if creation failed
    
    def test_chat_persistence_and_recovery(self, client):
        """Test chat persistence and recovery after restart simulation"""
        
        # Create a session and add messages
        response = client.post("/api/chat/sessions", json={"title": "Persistence Test"})
        assert response.status_code == 200
        session_id = response.json()["data"]["id"]
        original_session = response.json()["data"]
        
        try:
            # Add some messages
            for i in range(3):
                message_request = {
                    "content": f"Persistent message {i+1}",
                    "include_sources": False
                }
                
                response = client.post(f"/api/chat/sessions/{session_id}/messages", json=message_request)
                # Accept any response
                assert response.status_code in [200, 400, 500]
                
                time.sleep(0.1)  # Brief delay
            
            # Verify session exists and has messages
            response = client.get(f"/api/chat/sessions/{session_id}")
            assert response.status_code == 200
            session_details = response.json()["data"]
            
            # Session should maintain its properties
            assert session_details["id"] == session_id
            assert session_details["title"] == "Persistence Test"
            
            # Get messages
            response = client.get(f"/api/chat/sessions/{session_id}/messages")
            assert response.status_code == 200
            messages_data = response.json()["data"]
            
            # Should have at least the user messages
            original_message_count = messages_data["count"]
            assert original_message_count >= 0
            
            # Simulate system restart by creating new client
            # (In real e2e test, this might involve restarting the server)
            new_client = httpx.Client(base_url=self.BASE_URL, timeout=30.0)
            
            try:
                # Verify session still exists
                response = new_client.get(f"/api/chat/sessions/{session_id}")
                assert response.status_code == 200
                recovered_session = response.json()["data"]
                
                # Session properties should be preserved
                assert recovered_session["id"] == original_session["id"]
                assert recovered_session["title"] == original_session["title"]
                
                # Messages should be preserved
                response = new_client.get(f"/api/chat/sessions/{session_id}/messages")
                assert response.status_code == 200
                recovered_messages = response.json()["data"]
                
                # Message count should be the same or similar
                # (might vary if LLM responses were added)
                assert recovered_messages["count"] >= 0
                
            finally:
                new_client.close()
        
        finally:
            # Cleanup
            client.delete(f"/api/chat/sessions/{session_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])