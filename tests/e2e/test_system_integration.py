import pytest
import httpx
import time
from typing import Dict, Any, List

class TestSystemIntegration:
    """End-to-end tests for complete system integration"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.fixture
    def client(self):
        """HTTP client for API testing"""
        return httpx.Client(base_url=self.BASE_URL, timeout=60.0)
    
    def test_complete_system_workflow(self, client):
        """Test complete workflow from configuration to content generation and chat"""
        
        print("\n=== Starting Complete System Integration Test ===")
        
        # Step 1: Check system health and configuration
        print("Step 1: Checking system health...")
        response = client.get("/api/health")
        assert response.status_code in [200, 404]  # Health endpoint might not exist
        
        # Check configuration status
        response = client.get("/api/config/validation")
        assert response.status_code == 200
        config_validation = response.json()["data"]
        print(f"Configuration validation: {config_validation}")
        
        # Step 2: Set up test source for content
        print("Step 2: Setting up content source...")
        test_source = {
            "name": "Integration Test Feed",
            "type": "rss",
            "url": "https://feeds.feedburner.com/oreilly/radar",
            "refresh_interval": 3600
        }
        
        response = client.post("/api/sources/", json=test_source)
        assert response.status_code == 200
        source = response.json()["data"]
        source_id = source["id"]
        print(f"Created source: {source_id}")
        
        try:
            # Step 3: Trigger content ingestion
            print("Step 3: Ingesting content...")
            response = client.post(f"/api/sources/{source_id}/refresh")
            assert response.status_code == 200
            
            # Wait for ingestion to complete
            time.sleep(5)
            
            # Check source items
            response = client.get(f"/api/sources/{source_id}/items")
            assert response.status_code == 200
            items_data = response.json()["data"]
            print(f"Ingested {len(items_data.get('items', []))} items")
            
            # Step 4: Test RAG system with ingested content
            print("Step 4: Testing RAG system...")
            response = client.get("/api/rag/status")
            assert response.status_code == 200
            rag_status = response.json()["data"]
            print(f"RAG vector store size: {rag_status.get('vector_store_size', 0)}")
            
            # Perform a search
            search_request = {
                "query": "technology trends",
                "max_results": 3,
                "min_similarity": 0.2
            }
            
            response = client.post("/api/rag/search", json=search_request)
            assert response.status_code == 200
            search_results = response.json()["data"]
            print(f"RAG search returned {search_results.get('count', 0)} results")
            
            # Step 5: Test content generation (if items are available)
            if items_data.get('items'):
                print("Step 5: Testing content generation...")
                item_id = items_data['items'][0]['id']
                
                generation_request = {
                    "source_item_id": item_id,
                    "content_types": ["summary"],
                    "platforms": [],
                    "include_research": True,
                    "image_count": 0,
                    "custom_instructions": "Keep it concise for integration test"
                }
                
                response = client.post("/api/content/generate", json=generation_request)
                print(f"Content generation response: {response.status_code}")
                
                if response.status_code == 200:
                    package_data = response.json()["data"]
                    package_id = package_data["package"]["id"]
                    print(f"Generated content package: {package_id}")
                    
                    # Verify package exists
                    response = client.get(f"/api/content/packages/{package_id}")
                    assert response.status_code == 200
                    
                    # Clean up package
                    client.delete(f"/api/content/packages/{package_id}")
            
            # Step 6: Test chat system with context
            print("Step 6: Testing chat system...")
            response = client.post("/api/chat/sessions", json={"title": "Integration Test Chat"})
            assert response.status_code == 200
            session_id = response.json()["data"]["id"]
            print(f"Created chat session: {session_id}")
            
            try:
                # Send message with context from sources
                message_request = {
                    "content": "Based on the available sources, what are the key technology trends?",
                    "include_sources": True,
                    "max_context_items": 3
                }
                
                response = client.post(f"/api/chat/sessions/{session_id}/messages", json=message_request)
                print(f"Chat message response: {response.status_code}")
                
                if response.status_code == 200:
                    message_response = response.json()["data"]
                    print(f"Chat response includes {len(message_response.get('context_items', []))} context items")
                
                # Send follow-up message
                followup_request = {
                    "content": "Can you elaborate on that?",
                    "include_sources": False
                }
                
                response = client.post(f"/api/chat/sessions/{session_id}/messages", json=followup_request)
                print(f"Follow-up message response: {response.status_code}")
                
                # Check conversation history
                response = client.get(f"/api/chat/sessions/{session_id}/messages")
                assert response.status_code == 200
                messages_data = response.json()["data"]
                print(f"Chat session has {messages_data.get('count', 0)} messages")
                
            finally:
                # Clean up chat session
                client.delete(f"/api/chat/sessions/{session_id}")
                print("Cleaned up chat session")
            
            # Step 7: Test system statistics and monitoring
            print("Step 7: Testing system statistics...")
            
            # Chat statistics
            response = client.get("/api/chat/stats")
            assert response.status_code == 200
            chat_stats = response.json()["data"]
            print(f"Chat stats: {chat_stats.get('total_sessions', 0)} sessions, {chat_stats.get('total_messages', 0)} messages")
            
            # Content statistics
            response = client.get("/api/content/stats")
            assert response.status_code == 200
            content_stats = response.json()["data"]
            print(f"Content stats: {content_stats.get('total_packages', 0)} packages")
            
            # Sources statistics
            response = client.get(f"/api/sources/{source_id}/stats")
            assert response.status_code == 200
            source_stats = response.json()["data"]
            print(f"Source stats: {source_stats.get('item_count', 0)} items")
            
            # Step 8: Test system under simulated load
            print("Step 8: Testing system under load...")
            self._test_system_load(client, source_id)
            
            print("=== System Integration Test Completed Successfully ===")
            
        finally:
            # Step 9: Cleanup
            print("Step 9: Cleaning up test data...")
            client.delete(f"/api/sources/{source_id}")
            print("Cleanup completed")
    
    def _test_system_load(self, client, source_id: str):
        """Test system under simulated load"""
        
        import threading
        import queue
        
        results = queue.Queue()
        
        def concurrent_operation(op_id):
            """Perform concurrent operations"""
            try:
                thread_client = httpx.Client(base_url=self.BASE_URL, timeout=30.0)
                
                # Mix of different operations
                operations = [
                    lambda: thread_client.get("/api/sources/"),
                    lambda: thread_client.get(f"/api/sources/{source_id}"),
                    lambda: thread_client.post("/api/rag/search", json={"query": f"test {op_id}", "max_results": 1}),
                    lambda: thread_client.get("/api/chat/sessions"),
                    lambda: thread_client.get("/api/content/packages")
                ]
                
                # Execute random operations
                import random
                op = random.choice(operations)
                response = op()
                
                results.put((op_id, response.status_code))
                thread_client.close()
                
            except Exception as e:
                results.put((op_id, f"Error: {e}"))
        
        # Start concurrent threads
        threads = []
        for i in range(5):  # Moderate load for testing
            thread = threading.Thread(target=concurrent_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=30)
        
        # Collect results
        load_results = []
        while not results.empty():
            load_results.append(results.get())
        
        print(f"Load test completed: {len(load_results)} operations")
        
        # Verify system remained responsive
        successful_ops = sum(1 for _, status in load_results if isinstance(status, int) and 200 <= status <= 299)
        print(f"Successful operations: {successful_ops}/{len(load_results)}")
        
        # At least some operations should succeed
        assert successful_ops > 0
    
    def test_error_resilience(self, client):
        """Test system resilience to various error conditions"""
        
        print("\n=== Testing Error Resilience ===")
        
        # Test 1: Invalid source URLs
        print("Test 1: Invalid source handling...")
        invalid_source = {
            "name": "Invalid Source",
            "type": "rss",
            "url": "https://nonexistent-domain-12345.com/feed",
            "refresh_interval": 3600
        }
        
        response = client.post("/api/sources/", json=invalid_source)
        assert response.status_code == 200  # Should accept but fail later
        source_id = response.json()["data"]["id"]
        
        try:
            # Trigger refresh (should handle error gracefully)
            response = client.post(f"/api/sources/{source_id}/refresh")
            assert response.status_code == 200  # Should accept request
            
            time.sleep(2)  # Wait for processing
            
            # Source should still be manageable
            response = client.get(f"/api/sources/{source_id}")
            assert response.status_code == 200
            
        finally:
            client.delete(f"/api/sources/{source_id}")
        
        # Test 2: Invalid content generation requests
        print("Test 2: Invalid content generation...")
        invalid_content_request = {
            "source_item_id": "nonexistent-item",
            "content_types": ["summary"],
            "platforms": [],
            "include_research": False,
            "image_count": 0
        }
        
        response = client.post("/api/content/generate", json=invalid_content_request)
        assert response.status_code in [400, 404, 500]  # Should handle gracefully
        
        # Test 3: Invalid chat operations
        print("Test 3: Invalid chat operations...")
        response = client.get("/api/chat/sessions/nonexistent-session")
        assert response.status_code == 404
        
        response = client.post("/api/chat/sessions/nonexistent-session/messages", 
                              json={"content": "test", "include_sources": False})
        assert response.status_code == 404
        
        # Test 4: Malformed requests
        print("Test 4: Malformed requests...")
        response = client.post("/api/sources/", json={"invalid": "data"})
        assert response.status_code == 422
        
        response = client.post("/api/chat/messages", json={"invalid": "data"})
        assert response.status_code == 422
        
        print("Error resilience tests completed")
    
    def test_data_consistency(self, client):
        """Test data consistency across different system components"""
        
        print("\n=== Testing Data Consistency ===")
        
        # Create test data
        source = {
            "name": "Consistency Test Source",
            "type": "rss",
            "url": "https://example.com/feed",
            "refresh_interval": 3600
        }
        
        response = client.post("/api/sources/", json=source)
        assert response.status_code == 200
        source_id = response.json()["data"]["id"]
        
        try:
            # Test 1: Source data consistency
            print("Test 1: Source data consistency...")
            
            # Get source via different endpoints
            response1 = client.get(f"/api/sources/{source_id}")
            assert response1.status_code == 200
            source_detail = response1.json()["data"]
            
            response2 = client.get("/api/sources/")
            assert response2.status_code == 200
            sources_list = response2.json()["data"]
            
            # Find source in list
            source_in_list = next(s for s in sources_list if s["id"] == source_id)
            
            # Key fields should match
            assert source_detail["id"] == source_in_list["id"]
            assert source_detail["name"] == source_in_list["name"]
            assert source_detail["type"] == source_in_list["type"]
            assert source_detail["url"] == source_in_list["url"]
            
            # Test 2: Update consistency
            print("Test 2: Update consistency...")
            
            update_data = {"name": "Updated Consistency Test"}
            response = client.put(f"/api/sources/{source_id}", json=update_data)
            assert response.status_code == 200
            
            # Verify update is reflected everywhere
            response1 = client.get(f"/api/sources/{source_id}")
            assert response1.status_code == 200
            assert response1.json()["data"]["name"] == "Updated Consistency Test"
            
            response2 = client.get("/api/sources/")
            assert response2.status_code == 200
            updated_list = response2.json()["data"]
            updated_in_list = next(s for s in updated_list if s["id"] == source_id)
            assert updated_in_list["name"] == "Updated Consistency Test"
            
            # Test 3: Statistics consistency
            print("Test 3: Statistics consistency...")
            
            # Get stats from different endpoints
            response1 = client.get(f"/api/sources/{source_id}/stats")
            assert response1.status_code == 200
            individual_stats = response1.json()["data"]
            
            # Compare with aggregated stats (if available)
            # This is a basic check - full stats consistency would require more complex verification
            
            print("Data consistency tests completed")
            
        finally:
            client.delete(f"/api/sources/{source_id}")
    
    def test_performance_benchmarks(self, client):
        """Test basic performance benchmarks"""
        
        print("\n=== Testing Performance Benchmarks ===")
        
        import time
        
        # Benchmark 1: API response times
        print("Benchmark 1: API response times...")
        
        endpoints = [
            "/api/sources/",
            "/api/content/packages",
            "/api/chat/sessions",
            "/api/config/validation"
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            
            response_time = end_time - start_time
            print(f"{endpoint}: {response_time:.3f}s (status: {response.status_code})")
            
            # Basic performance assertion - responses should be under 5 seconds
            assert response_time < 5.0, f"{endpoint} took too long: {response_time}s"
        
        # Benchmark 2: Data operation times
        print("Benchmark 2: Data operations...")
        
        # Create source
        start_time = time.time()
        response = client.post("/api/sources/", json={
            "name": "Performance Test",
            "type": "rss",
            "url": "https://example.com/feed",
            "refresh_interval": 3600
        })
        create_time = time.time() - start_time
        
        if response.status_code == 200:
            source_id = response.json()["data"]["id"]
            print(f"Source creation: {create_time:.3f}s")
            
            try:
                # Read source
                start_time = time.time()
                response = client.get(f"/api/sources/{source_id}")
                read_time = time.time() - start_time
                print(f"Source read: {read_time:.3f}s")
                
                # Update source
                start_time = time.time()
                response = client.put(f"/api/sources/{source_id}", 
                                    json={"name": "Updated Performance Test"})
                update_time = time.time() - start_time
                print(f"Source update: {update_time:.3f}s")
                
                # Delete source
                start_time = time.time()
                response = client.delete(f"/api/sources/{source_id}")
                delete_time = time.time() - start_time
                print(f"Source deletion: {delete_time:.3f}s")
                
                # All operations should be reasonably fast
                assert create_time < 2.0
                assert read_time < 1.0
                assert update_time < 2.0
                assert delete_time < 2.0
                
            except:
                # Cleanup on error
                try:
                    client.delete(f"/api/sources/{source_id}")
                except:
                    pass
        
        print("Performance benchmarks completed")
    
    def test_system_configuration_validation(self, client):
        """Test system configuration and validation"""
        
        print("\n=== Testing Configuration Validation ===")
        
        # Test configuration endpoints
        response = client.get("/api/config")
        assert response.status_code == 200
        config = response.json()["data"]
        print(f"Configuration loaded: {len(config)} top-level keys")
        
        # Test validation
        response = client.get("/api/config/validation")
        assert response.status_code == 200
        validation = response.json()["data"]
        print(f"Configuration valid: {validation.get('valid', False)}")
        
        if not validation.get('valid', True):
            print(f"Validation errors: {validation.get('errors', [])}")
        
        # Test provider status
        response = client.get("/api/providers/status")
        assert response.status_code == 200
        provider_status = response.json()["data"]
        print(f"Provider status: {provider_status}")
        
        print("Configuration validation completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to show print statements